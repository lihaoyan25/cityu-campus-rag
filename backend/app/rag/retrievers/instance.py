"""检索器实例装配（依据 .env 配置）。"""
from functools import lru_cache

from app.rag.retrievers.base import BaseRetriever
from app.rag.retrievers.hybrid import HybridRetriever
from app.rag.retrievers.vector import VectorRetriever


@lru_cache
def get_retriever() -> BaseRetriever:
    """默认混合检索器；settings.hybrid_enabled=False 时仅向量检索。"""
    return HybridRetriever(vector=VectorRetriever())
