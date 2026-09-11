"""ChromaDB 封装：持久化客户端 + cosine 相似度集合。"""
import logging
from typing import Any

import chromadb

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: chromadb.api.ClientAPI | None = None
_collection: chromadb.api.Collection | None = None


def get_collection() -> chromadb.api.Collection:
    global _client, _collection
    if _collection is None:
        if settings.chroma_mode == "http":
            _client = chromadb.HttpClient(
                host=settings.chroma_http_host,
                port=settings.chroma_http_port,
            )
            logger.info(
                "ChromaDB HTTP 客户端就绪: %s:%d", settings.chroma_http_host, settings.chroma_http_port
            )
        else:
            _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        _collection = _client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB 集合已就绪: %s (%d 条)", _collection.name, _collection.count())
    return _collection


def heartbeat() -> bool:
    """检查 ChromaDB 连接可用性（http 模式下 server 未启动时返回 False）。"""
    try:
        if settings.chroma_mode == "http":
            chromadb.HttpClient(
                host=settings.chroma_http_host, port=settings.chroma_http_port
            ).heartbeat()
        return True
    except Exception as e:
        logger.warning("ChromaDB 连接失败: %s", e)
        return False


def upsert_chunks(
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict[str, Any]],
) -> None:
    get_collection().upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)


def delete_by_document(document_id: int) -> None:
    get_collection().delete(where={"document_id": document_id})


def query(embedding: list[float], top_k: int) -> list[dict[str, Any]]:
    """返回 [{id, document, metadata, distance}]，按距离升序。"""
    res = get_collection().query(
        query_embeddings=[embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    out: list[dict[str, Any]] = []
    ids = res.get("ids", [[]])[0]
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    for i, cid in enumerate(ids):
        out.append(
            {
                "id": cid,
                "document": docs[i] if i < len(docs) else "",
                "metadata": metas[i] if i < len(metas) else {},
                "distance": dists[i] if i < len(dists) else None,
            }
        )
    return out


def count() -> int:
    return get_collection().count()
