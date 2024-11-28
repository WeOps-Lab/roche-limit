from langserve import add_routes

from apps.rag_server.runnable.elasticsearch_delete_runnable import ElasticSearchDeleteRunnable
from apps.rag_server.runnable.elasticsearch_index_runnable import ElasticSearchIndexRunnable
from apps.rag_server.runnable.elasticsearch_rag_runnable import ElasticSearchRagRunnable
from apps.rag_server.runnable.network_retrieval_runnable import NetworkRetrievalRunnable


def register_routes(app):
    add_routes(app, ElasticSearchIndexRunnable().instance(), path='/elasticsearch_index')
    add_routes(app, ElasticSearchDeleteRunnable().instance(), path='/elasticsearch_delete')
    add_routes(app, ElasticSearchRagRunnable().instance(), path='/elasticsearch_rag')
    add_routes(app, NetworkRetrievalRunnable().instance(), path='/network_retrieval')
