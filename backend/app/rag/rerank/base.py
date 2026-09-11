"""Reranker 抽象与默认 Noop 实现。

后续接入真实 rerank（智谱 API / 本地 BGE）时：
1. 新增实现 BaseReranker；
2. 修改 get_reranker() 按配置返回，检索链路无需改动。
"""
from app.core.config import settings
from app.rag.retrievers.base import RetrievedChunk


class BaseReranker:
    name: str = "base"

    async def rerank(
        self, query: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        raise NotImplementedError


class NoopReranker(BaseReranker):
    """直通实现：保持原顺序截断。"""

    name = "noop"

    async def rerank(
        self, query: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        return candidates[:top_k]


_reranker: BaseReranker | None = None


def get_reranker() -> BaseReranker:
    global _reranker
    if _reranker is None:
        # 预留: settings 增加 rerank_provider 后按配置分发
        _reranker = NoopReranker()
    return _reranker
