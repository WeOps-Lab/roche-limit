from typing import List

from langserve import CustomUserType


class ElasticSearchDeleteRequest(CustomUserType):
    elasticsearch_url: str = "http://elasticsearch.ops-pilot:9200"
    elasticsearch_password: str

    index_name: str
    mode: str = "delete_index"
    metadata_filter: dict = {}