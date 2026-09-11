"""混合检索器：多路召回 + RRF 融合 + Rerank 接口。"""
import asyncio
import logging

from app.core.config import settings
from app.rag.rerank import get_reranker
from app.rag.retrievers.base import BaseRetriever, RetrievedChunk
from app.rag.retrievers.bm25 import BM25Retriever
from app.rag.retrievers.vector import VectorRetriever

logger = logging.getLogger(__name__)


def rrf_fuse(
    result_lists: list[list[RetrievedChunk]], k: int, top_k: int
) -> list[RetrievedChunk]:
    """Reciprocal Rank Fusion：score = Σ 1/(k + rank)。"""
    fused_scores: dict[str, float] = {}
    items: dict[str, RetrievedChunk] = {}
    for results in result_lists:
        for rank, item in enumerate(results):
            fused_scores[item.key] = fused_scores.get(item.key, 0.0) + 1.0 / (k + rank + 1)
            if item.key not in items:
                items[item.key] = item
    ordered_keys = sorted(fused_scores, key=lambda key: fused_scores[key], reverse=True)[:top_k]
    fused: list[RetrievedChunk] = []
    for key in ordered_keys:
        item = items[key]
        item.score = round(fused_scores[key], 4)
        fused.append(item)
    return fused


class HybridRetriever(BaseRetriever):
    name = "hybrid"

    def __init__(
        self,
        vector: BaseRetriever | None = None,
        bm25: BaseRetriever | None = None,
    ) -> None:
        self.vector = vector or VectorRetriever()
        self.bm25 = bm25 or BM25Retriever()

    async def retrieve(self, query: str, top_k: int) -> list[RetrievedChunk]:
        # 每路多召回一些，融合后再截断
        recall_k = max(top_k * 2, settings.retrieval_top_k)
        tasks = [self.vector.retrieve(query, recall_k)]
        if settings.hybrid_enabled:
            tasks.append(self.bm25.retrieve(query, recall_k))
        result_lists = await asyncio.gather(*tasks, return_exceptions=False)

        valid_lists = [r for r in result_lists if r]
        if not valid_lists:
            return []
        if len(valid_lists) == 1:
            candidates = valid_lists[0][:top_k]
        else:
            candidates = rrf_fuse(valid_lists, k=settings.rrf_k, top_k=top_k)

        # Rerank 插槽：Noop 直通，后续接入真实 rerank 服务只改 get_reranker
        reranker = get_reranker()
        candidates = await reranker.rerank(query, candidates, top_k)
        return candidates[:top_k]
