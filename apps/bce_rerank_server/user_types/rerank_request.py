from typing import List

from langchain_core.documents import Document
from langserve import CustomUserType


class ReRankerRequest(CustomUserType):
    docs: List[Document]
    query: str
    top_n: int = 10