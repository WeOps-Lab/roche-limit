from typing import Dict, List
import os
import pickle
import time
from cachetools import LRUCache
from langchain_core.documents import Document
from loguru import logger

class RagMemoryManager:
    def __init__(self, memory_dir: str):
        self.memory_dir = memory_dir
        self._cache = LRUCache(maxsize=1000)  # 设置合适的缓存大小
        
    def _get_memory_path(self, memory_id: str) -> str:
        return os.path.join(self.memory_dir, f"{memory_id}.pickle")

    def load_memory(self, memory_id: str) -> List[Document]:
        if (memory_id in self._cache):
            return self._cache[memory_id]
            
        memory_path = self._get_memory_path(memory_id)
        if os.path.exists(memory_path):
            with open(memory_path, 'rb') as f:
                memory_list = pickle.load(f)
            self._cache[memory_id] = memory_list
            return memory_list
        return []

    def get_memories(self, 
                    memory_id: str, 
                    exclude_ids: set) -> List[Document]:
        """获取所有记忆文档（按使用频率排序）"""
        memory_list = self.load_memory(memory_id)
        if not memory_list:
            return []
            
        # 过滤掉已在结果中的文档，并按使用频率排序
        filtered_memories = [
            doc for doc in memory_list 
            if doc.metadata.get('_id') not in exclude_ids
        ]
        filtered_memories.sort(
            key=lambda d: (d.metadata.get('usage', 0), d.metadata.get('last_used', 0)),
            reverse=True
        )
        
        return filtered_memories  # 返回所有符合条件的记忆

    def update_memory(self, 
                     memory_id: str, 
                     search_result: List[Document],
                     max_size: int,
                     max_time: float) -> None:
        now = time.time()
        memory_list = self.load_memory(memory_id)
        
        # 构建内存映射
        memory_map = {
            doc.metadata.get('_id'): doc for doc in memory_list
        }
        
        # 更新记忆
        hit_ids = set()
        for doc in search_result:
            doc_id = doc.metadata.get('_id')
            hit_ids.add(doc_id)
            if doc_id in memory_map:
                mem = memory_map[doc_id]
                mem.metadata['usage'] = min(10, mem.metadata.get('usage', 1) + 1)  # 限制最大值为10
                mem.metadata['last_used'] = now
            else:
                doc.metadata.update({
                    'usage': 5,
                    'last_used': now
                })
                memory_map[doc_id] = doc

        # 对未命中的记录进行usage计数衰减
        for doc_id, doc in memory_map.items():
            if doc_id not in hit_ids:
                doc.metadata['usage'] = max(0, doc.metadata.get('usage', 0) - 1)

        # 更新使用计数和清理过期记忆
        memory_map = {
            k: v for k, v in memory_map.items()
            if (k in hit_ids or v.metadata.get('usage', 0) > 0) and
            (now - v.metadata.get('last_used', now) <= max_time)
        }

        # LRU 策略保留最常用的记忆
        memory_list = list(memory_map.values())
        if len(memory_list) > max_size:
            memory_list.sort(
                key=lambda d: (d.metadata.get('usage', 0), d.metadata.get('last_used', 0))
            )
            memory_list = memory_list[-max_size:]

        # 保存更新后的记忆
        memory_path = self._get_memory_path(memory_id)
        with open(memory_path, 'wb') as f:
            pickle.dump(memory_list, f)
        self._cache[memory_id] = memory_list
