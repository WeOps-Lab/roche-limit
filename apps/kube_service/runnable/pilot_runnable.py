from typing import List

import yaml
from langchain_core.runnables import RunnableLambda
from langserve import add_routes
from loguru import logger

from apps.kube_service.user_types.pilot import ListPilotRequest, PilotInfo, StartPilotRequest, StopPilotRequest
from apps.kube_service.utils.kubernetes_client import KubernetesClient
from core.utils.template_loader import core_template


class PilotRunnable:
    def __init__(self):
        self.client = KubernetesClient()

    def list_pilot(self, req: ListPilotRequest) -> List[PilotInfo]:
        logger.info(f"列出命名空间'{req.namespace}'中的Pod，标签选择器: {req.label_selector}")

        try:
            pods = self.client.core_api.list_namespaced_pod(namespace=req.namespace, label_selector=req.label_selector)
            pod_list = [PilotInfo(name=pod.metadata.name, status=pod.status.phase) for pod in pods.items if
                        pod.metadata.name.startswith("pilot-")]
            logger.info(f"共找到 {len(pods.items)} 个Pod")
            return pod_list

        except Exception as e:
            logger.error(f"列出命名空间'{req.namespace}'中的Pod失败: {e}")
            return []

    def start_pilot(self, req: StartPilotRequest) -> bool:
        logger.info(f"启动Pilot: {req.pilot_id}")
        dynamic_dict = {
            "bot_id": req.pilot_id,
            "api_key": req.api_key,
            "replicas": req.replicas,
            "base_url": req.munchkin_url,
            "rabbitmq_host": req.rabbitmq_host,
            "rabbitmq_port": req.rabbitmq_port,
            "rabbitmq_user": req.rabbitmq_user,
            "rabbitmq_password": req.rabbitmq_password,
            "enable_ssl": req.enable_ssl,
            "bot_domain": req.bot_domain,
            "enable_nodeport": req.enable_node_port,
            "web_nodeport": req.node_port,
        }

        try:
            deployment_template = core_template.get_template("pilot/deployment.yml")
            deployment = deployment_template.render(dynamic_dict)
            self.client.app_api.create_namespaced_deployment(
                namespace=req.namespace, body=yaml.safe_load(deployment)
            )
            logger.info(f"启动Pilot[{req.pilot_id}]Pod成功")
        except Exception as e:
            logger.error(f"启动Pilot[{req.pilot_id}]Pod失败: {e}")

        try:
            svc_template = core_template.get_template("pilot/svc.yml")
            svc = svc_template.render(dynamic_dict)
            self.client.core_api.create_namespaced_service(
                namespace=req.namespace, body=yaml.safe_load(svc)
            )
            logger.info(f"启动Pilot[{req.pilot_id}]Service成功")
        except Exception as e:
            logger.error(f"启动Pilot[{req.pilot_id}]Service失败: {e}")

        if req.enable_bot_domain:
            try:
                ingress_template = core_template.get_template("pilot/ingress.yml")
                ingress = ingress_template.render(dynamic_dict)
                self.client.custom_object_api.create_namespaced_custom_object(
                    group=self.client.traefik_resource_group,
                    version="v1alpha1",
                    plural="ingressroutes",
                    body=yaml.safe_load(ingress),
                    namespace=req.namespace,
                )
                logger.info(f"启动Pilot[{req.pilot_id}]Ingress成功。")
            except Exception as e:
                logger.error(f"启动Pilot[{req.pilot_id}] Ingress失败: {e}")
        return True

    def stop_pilot(self, req: StopPilotRequest) -> bool:
        try:
            self.client.app_api.delete_namespaced_deployment(
                name=f"pilot-{req.bot_id}", namespace=req.namespace
            )
            logger.info(f"停止Pilot[{req.bot_id}]Pod成功")
        except Exception as e:
            logger.error(f"停止Pilot[{req.bot_id}]Pod失败: {e}")

        try:
            self.client.core_api.delete_namespaced_service(
                name=f"pilot-{req.bot_id}-service", namespace=req.namespace
            )
            logger.info(f"停止Pilot[{req.bot_id}]Service成功")
        except Exception as e:
            logger.error(f"停止Pilot[{req.bot_id}]Service失败: {e}")

        try:
            self.client.custom_object_api.delete_namespaced_custom_object(
                group=self.client.traefik_resource_group,
                version="v1alpha1",
                plural="ingressroutes",
                namespace=req.namespace,
                name=f"pilot-{req.bot_id}",
            )
        except Exception as e:
            logger.error(f"停止Pilot[{req.bot_id}]Ingress失败: {e}")

        return True

    def register(self, app):
        add_routes(app,
                   RunnableLambda(self.list_pilot).with_types(input_type=ListPilotRequest, output_type=list),
                   path='/list_pilot')
        add_routes(app,
                   RunnableLambda(self.start_pilot).with_types(input_type=StartPilotRequest, output_type=bool),
                   path='/start_pilot')
        add_routes(app,
                   RunnableLambda(self.stop_pilot).with_types(input_type=StopPilotRequest, output_type=bool),
                   path='/stop_pilot')
