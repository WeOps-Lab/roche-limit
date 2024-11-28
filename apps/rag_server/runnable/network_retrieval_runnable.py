from itertools import islice
from typing import List

from duckduckgo_search import DDGS
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from apps.rag_server.user_types.network_retrieval_request import NetworkRetrievalRequest


class NetworkRetrievalRunnable:
    def __init__(self):
        pass

    def execute(self, req: NetworkRetrievalRequest) -> List[Document]:
        doc_list = []
        with DDGS() as ddgs:
            ddgs_gen = ddgs.text(req.query, backend="lite")
            for r in islice(ddgs_gen, 10):
                doc_list.append(Document(r["body"], metadata={"url": r["href"], "title": r['title']}))
        return doc_list

    def instance(self):
        return RunnableLambda(self.execute).with_types(
            input_type=NetworkRetrievalRequest,
            output_type=List[Document])