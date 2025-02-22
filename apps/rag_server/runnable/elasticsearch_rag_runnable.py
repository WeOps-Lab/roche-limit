from typing import Dict, List
import os
import pickle

from langchain.chains.hyde.base import HypotheticalDocumentEmbedder
from langchain_community.chat_models import ChatOpenAI
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from langchain_elasticsearch import ElasticsearchRetriever
from langserve import RemoteRunnable
from loguru import logger

from apps.rag_server.user_types.elasticsearch_retriever_request import ElasticSearchRetrieverRequest
from core.server_settings import server_settings
from core.embedding.remote_embeddings import RemoteEmbeddings
from apps.rag_server.query.query_builder import ElasticsearchQueryBuilder
from apps.rag_server.memory.rag_memory import RagMemoryManager


class ElasticSearchRagRunnable:
    def __init__(self):
        self.memory_manager = RagMemoryManager(server_settings.memory_dir)

    def _process_search_result(self, docs: List[Document]) -> List[Document]:
        for doc in docs:
            if 'vector' in doc.metadata.get('_source', {}):
                del doc.metadata['_source']['vector']
        return docs

    def execute(self, req: ElasticSearchRetrieverRequest) -> List[Document]:
        # 构建检索器 (使用固定的size)
        documents_retriever = ElasticsearchRetriever.from_es_params(
            index_name=req.index_name,
            body_func=lambda x: ElasticsearchQueryBuilder.build_query(req),
            content_field="text",
            url=req.elasticsearch_url,
            username="elastic",
            password=req.elasticsearch_password,
        )

        # 执行搜索
        search_result = documents_retriever.invoke(req.search_query)
        search_result = self._process_search_result(search_result)

        # 重排序处理
        if req.enable_rerank:
            reranker = RemoteRunnable(req.rerank_model_address)
            search_result = reranker.invoke({
                "docs": search_result,
                "query": req.search_query,
                "top_n": req.rerank_top_k
            })

        final_results = search_result

        # 内存管理
        if req.enable_rag_memory:
            # 更新记忆但不合并结果
            self.memory_manager.update_memory(
                memory_id=req.memory_id,
                search_result=search_result,
                max_size=req.max_short_term_memory_size,
                max_time=req.max_short_term_memory_time
            )
            
            # 获取当前结果的ID集合
            current_ids = {doc.metadata.get('_id') for doc in search_result}
            
            # 从记忆中获取补充文档
            memories = self.memory_manager.get_memories(
                memory_id=req.memory_id,
                exclude_ids=current_ids
            )
            final_results.extend(memories)

        return final_results

    def instance(self):
        return RunnableLambda(self.execute).with_types(
            input_type=ElasticSearchRetrieverRequest,
            output_type=List[Document]
        )