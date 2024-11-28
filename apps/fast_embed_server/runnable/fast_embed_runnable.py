from typing import List

from fastembed import TextEmbedding
from langchain_core.runnables import RunnableLambda

from core.server_settings import server_settings


class FastEmbedRunnable:
    def __init__(self):
        self.embedding = TextEmbedding(model_name=server_settings.model_name, cache_dir="models")

    def instance(self):
        return RunnableLambda(self.execute).with_types(input_type=str, output_type=List[float])

    def execute(self, text: str) -> List[float]:
        result = self.embedding.embed(text)
        result = [item for sublist in result for item in sublist.tolist()]
        return result
