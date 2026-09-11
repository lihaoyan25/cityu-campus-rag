"""检索层：统一 Retriever 抽象 + 向量/BM25/混合实现。"""
from app.rag.retrievers.base import BaseRetriever, RetrievedChunk
from app.rag.retrievers.hybrid import HybridRetriever
from app.rag.retrievers.instance import get_retriever

__all__ = ["BaseRetriever", "RetrievedChunk", "HybridRetriever", "get_retriever"]
