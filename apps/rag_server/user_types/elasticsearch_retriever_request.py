from apps.rag_server.user_types.elasticsearch_request import ElasticSearchRequest


class ElasticSearchRetrieverRequest(ElasticSearchRequest):
    index_name: str
    search_query: str
    size: int = 10
    metadata_filter: dict = {}

    enable_term_search: bool = True
    text_search_weight: float = 0.9
    text_search_mode: str = 'match'

    enable_vector_search: bool = True
    vector_search_weight: float = 0.1

    rag_k: int = 10
    rag_num_candidates: int = 1000

    enable_rerank: bool = False
    rerank_model_address: str = ''
    rerank_top_k: int = 5

    enable_hyde_enhance: bool = False
    hyde_enhance_base_url: str = ''
    hyde_enhance_api_key: str = ''
    hyde_enhance_temperature: float = 0.7
    hyde_enhance_model: str = 'gpt-4-o'
    hyde_prompt_key: str = 'web_search'