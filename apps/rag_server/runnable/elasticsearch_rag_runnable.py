from typing import Dict, List

from langchain.chains.hyde.base import HypotheticalDocumentEmbedder
from langchain_community.chat_models import ChatOpenAI
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from langchain_elasticsearch import ElasticsearchRetriever
from langserve import RemoteRunnable
from loguru import logger

from apps.rag_server.user_types.elasticsearch_retriever_request import ElasticSearchRetrieverRequest
from core.embedding.remote_embeddings import RemoteEmbeddings


def vector_query(
        self,
        req: ElasticSearchRetrieverRequest
) -> Dict:
    es_query = {
        "size": req.size,
    }

    metadata_filter = []
    for key, value in req.metadata_filter.items():
        if isinstance(value, str):
            metadata_filter.append({"term": {f"metadata.{key}.keyword": value}})
        elif isinstance(value, bool):
            metadata_filter.append({"term": {f"metadata.{key}": value}})
        elif isinstance(value, (int, float)):
            metadata_filter.append({"term": {f"metadata.{key}": value}})
        else:
            raise ValueError(f"Unsupported metadata filter type for key {key}: {type(value)}")

    if req.enable_term_search is True:
        es_query["query"] = {
            "bool": {
                "must": {req.text_search_mode: {"text": req.search_query}},
                "filter": metadata_filter,
                "boost": req.text_search_weight,
            }
        }

    if req.enable_vector_search is True:
        embedding = RemoteEmbeddings(req.embed_model_address)
        if req.enable_hyde_enhance is True:
            hyde_llm = ChatOpenAI(
                openai_api_key=req.hyde_enhance_api_key,
                openai_api_base=req.hyde_enhance_base_url,
                temperature=req.hyde_enhance_temperature,
                model=req.hyde_enhance_model,
                max_retries=3,
            )
            hyde_embeddings = HypotheticalDocumentEmbedder.from_llm(
                hyde_llm,
                base_embeddings=embedding,
                prompt_key="web_search",
            )
            vector = hyde_embeddings.embed_query(req.search_query)
        else:
            vector = embedding.embed_query(req.search_query)

        es_query["knn"] = {
            "field": "vector",
            "query_vector": vector,
            "k": req.rag_k,
            "filter": metadata_filter,
            "num_candidates": req.rag_num_candidates,
            "boost": req.vector_search_weight,
        }

    logger.info(f"ES Query: {es_query}")
    return es_query


class ElasticSearchRagRunnable:
    def __init__(self):
        pass

    def execute(self, req: ElasticSearchRetrieverRequest) -> List[Document]:
        documents_retriever = ElasticsearchRetriever.from_es_params(
            index_name=req.index_name,
            body_func=lambda x: vector_query(x, req),
            content_field="text",
            url=req.elasticsearch_url,
            username="elastic",
            password=req.elasticsearch_password,
        )

        search_result = documents_retriever.invoke(req.search_query)
        if req.enable_rerank is True:
            reranker = RemoteRunnable(req.rerank_model_address)
            params = {
                "docs": search_result,
                "query": req.search_query,
                "top_n": req.rerank_top_k
            }
            search_result = reranker.invoke(params)

        for doc in search_result:
            if 'vector' in doc.metadata['_source']:
                del doc.metadata['_source']['vector']

        return search_result

    def instance(self):
        elasticsearch_rag_runnable = RunnableLambda(self.execute).with_types(
            input_type=ElasticSearchRetrieverRequest,
            output_type=List[Document])
        return elasticsearch_rag_runnable