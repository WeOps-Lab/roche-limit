from typing import List

from BCEmbedding.tools.langchain import BCERerank
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from apps.bce_rerank_server.user_types.rerank_request import ReRankerRequest


class BCEReRankRunnable:
    def __init__(self):
        reranker_args = {
            "model": './models/bce-reranker-base_v1',
        }
        self.reranker = BCERerank(**reranker_args)

    def instance(self):
        return RunnableLambda(self.execute).with_types(input_type=ReRankerRequest, output_type=List[Document])

    def execute(self, req: ReRankerRequest) -> List[float]:
        self.reranker.top_n = req.top_n
        compressed_data = self.reranker.compress_documents(req.docs, req.query)
        return compressed_data
