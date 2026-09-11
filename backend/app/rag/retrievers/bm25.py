"""BM25 检索器：jieba 分词 + rank-bm25，语料来自 MySQL 分片表。

索引策略：启动时从 MySQL 全量重建（分片表是唯一事实来源），
入库/删除时增量更新内存索引。校园知识库规模下重建成本可忽略。
"""
import asyncio
import logging

import jieba
from rank_bm25 import BM25Okapi
from sqlalchemy import select

from app.db.engine import AsyncSessionLocal
from app.db.models import Chunk, Document
from app.rag.retrievers.base import BaseRetriever, RetrievedChunk

logger = logging.getLogger(__name__)

jieba.setLogLevel(logging.WARNING)


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in jieba.lcut_for_search(text) if t.strip()]


class BM25Index:
    """进程内 BM25 索引，单例使用。"""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._bm25: BM25Okapi | None = None
        self._keys: list[str] = []
        # key(chroma_id) -> (content, metadata)
        self._corpus: dict[str, tuple[str, dict]] = {}

    async def rebuild_from_db(self) -> int:
        """启动时全量重建。"""
        async with AsyncSessionLocal() as db:
            rows = (
                (
                    await db.execute(
                        select(Chunk.chroma_id, Chunk.content, Chunk.chunk_meta, Chunk.document_id)
                    )
                )
                .all()
            )
            doc_names = dict((await db.execute(select(Document.id, Document.filename))).all())
        corpus: dict[str, tuple[str, dict]] = {}
        for chroma_id, content, meta, document_id in rows:
            corpus[chroma_id] = (
                content,
                {
                    "document_id": document_id,
                    "filename": doc_names.get(document_id, ""),
                    "section": str((meta or {}).get("section", "")),
                    "chunk_index": int((meta or {}).get("chunk_index", 0)),
                },
            )
        async with self._lock:
            self._corpus = corpus
            self._rebuild_bm25()
        logger.info("BM25 索引重建完成: %d 个分片", len(corpus))
        return len(corpus)

    async def add_document(self, document_id: int) -> None:
        """入库后增量添加某文档的全部分片。"""
        async with AsyncSessionLocal() as db:
            doc_name = await db.scalar(
                select(Document.filename).where(Document.id == document_id)
            )
            rows = (
                await db.execute(
                    select(Chunk.chroma_id, Chunk.content, Chunk.chunk_meta).where(
                        Chunk.document_id == document_id
                    )
                )
            ).all()
        if not rows:
            return
        async with self._lock:
            for chroma_id, content, meta in rows:
                self._corpus[chroma_id] = (
                    content,
                    {
                        "document_id": document_id,
                        "filename": doc_name or "",
                        "section": str((meta or {}).get("section", "")),
                        "chunk_index": int((meta or {}).get("chunk_index", 0)),
                    },
                )
            self._rebuild_bm25()

    async def remove_document(self, document_id: int) -> None:
        """删除文档时移除其全部分片。"""
        async with self._lock:
            self._corpus = {
                k: v for k, v in self._corpus.items() if v[1]["document_id"] != document_id
            }
            self._rebuild_bm25()

    def _rebuild_bm25(self) -> None:
        if not self._corpus:
            self._bm25 = None
            return
        keys = list(self._corpus.keys())
        corpus_tokens = [_tokenize(self._corpus[k][0]) for k in keys]
        self._bm25 = BM25Okapi(corpus_tokens)
        self._keys = keys

    async def search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        async with self._lock:
            if self._bm25 is None:
                return []
            scores = self._bm25.get_scores(_tokenize(query))
            ranked = sorted(zip(self._keys, scores), key=lambda x: x[1], reverse=True)[:top_k]
            results: list[RetrievedChunk] = []
            for rank, (key, score) in enumerate(ranked):
                if score <= 0:
                    break
                content, meta = self._corpus[key]
                results.append(
                    RetrievedChunk(
                        key=key,
                        content=content,
                        document_id=meta["document_id"],
                        filename=meta["filename"],
                        section=meta["section"],
                        chunk_index=meta["chunk_index"],
                        score=round(float(score), 4),
                        extra={"rank": rank},
                    )
                )
            return results


bm25_index = BM25Index()


class BM25Retriever(BaseRetriever):
    name = "bm25"

    async def retrieve(self, query: str, top_k: int) -> list[RetrievedChunk]:
        return await bm25_index.search(query, top_k)
