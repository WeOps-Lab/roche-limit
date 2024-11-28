from typing import List

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.runnables import RunnableLambda


class BCEEmbedRunnable:
    def __init__(self):
        self.embedding = HuggingFaceEmbeddings(
            model_name="./models/bce-embedding-base_v1",
            encode_kwargs={
                "normalize_embeddings": True,
                "batch_size": 32,
            },
        )

    def instance(self):
        return RunnableLambda(self.execute).with_types(input_type=str, output_type=List[float])

    def execute(self, req: str) -> List[float]:
        return self.embedding.embed_query(req)
