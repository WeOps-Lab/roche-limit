from langchain_core.runnables import RunnableLambda
from langchain_elasticsearch import ElasticsearchStore

import elasticsearch
from loguru import logger

from apps.rag_server.user_types.elasticsearch_store_request import ElasticSearchStoreRequest
from core.embedding.remote_embeddings import RemoteEmbeddings


class ElasticSearchIndexRunnable:
    def __init__(self):
        pass

    def execute(self, req: ElasticSearchStoreRequest) -> bool:
        es = elasticsearch.Elasticsearch(hosts=[req.elasticsearch_url],
                                         basic_auth=("elastic", req.elasticsearch_password))
        embedding_service = RemoteEmbeddings(req.embed_model_address)
        if req.index_mode == 'overwrite' and es.indices.exists(index=req.index_name):
            logger.info(f"删除已存在的索引: {req.index_name}")
            es.indices.delete(index=req.index_name)

        logger.info(f"索引文档到Elasticsearch: {req.index_name}")
        db = ElasticsearchStore.from_documents(
            req.docs, embedding=embedding_service,
            es_connection=es, index_name=req.index_name,
            bulk_kwargs={
                "chunk_size": req.chunk_size,
                "max_chunk_bytes": req.max_chunk_bytes
            }
        )
        db.client.indices.refresh(index=req.index_name)
        return True

    def instance(self):
        elasticsearch_index_runnable = RunnableLambda(self.execute).with_types(
            input_type=ElasticSearchStoreRequest, output_type=bool)
        return elasticsearch_index_runnable