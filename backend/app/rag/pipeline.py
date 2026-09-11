"""入库管线编排：解析 → LLM清洗 → 分块 → 向量化 → ChromaDB + MySQL 双写。

所有阶段推进文档状态机，任一阶段失败置 failed 并记录错误。
"""
import hashlib
import logging
import re
import uuid
from pathlib import Path

from sqlalchemy import delete as sa_delete

from app.core.config import DATA_DIR
from app.core.textutil import strip_4byte
from app.db.engine import AsyncSessionLocal
from app.db.models import Chunk, Document
from app.llm import glm_embedding
from app.rag import chunker, cleaner, vector_store
from app.rag.parsers import factory as parser_factory
from app.rag.retrievers.bm25 import bm25_index
from app.services import stats_service

logger = logging.getLogger(__name__)

UPLOAD_DIR = DATA_DIR / "uploads"


def file_md5(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()


def save_upload(doc_id: int, filename: str, content: bytes) -> str:
    """保存上传文件，返回绝对路径字符串。"""
    safe_name = re.sub(r"[^\w.\-\u4e00-\u9fff]", "_", filename)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"doc{doc_id}_{uuid.uuid4().hex[:8]}_{safe_name}"
    path.write_bytes(content)
    return str(path)


async def process_document(doc_id: int) -> None:
    """后台任务入口：按状态机推进文档处理。"""
    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, doc_id)
        if doc is None:
            logger.warning("process_document: 文档不存在 doc_id=%s", doc_id)
            return
        try:
            raw_text = await _stage_parse(db, doc)
            cleaned = await _stage_clean(db, doc, raw_text)
            pieces = await _stage_chunk(db, doc, cleaned)
            await _stage_embed_and_save(db, doc, pieces)
            await bm25_index.add_document(doc.id)
            logger.info("文档处理完成 doc_id=%s chunks=%d", doc_id, doc.chunk_count)
        except Exception as e:
            logger.exception("文档处理失败 doc_id=%s", doc_id)
            doc.status = "failed"
            doc.error = str(e)[:2000]
            await db.commit()


async def clear_document_chunks(document_id: int) -> None:
    """清空某文档的全部分片与向量（保留文档记录本身），用于重处理前防重复。"""
    vector_store.delete_by_document(document_id)
    await bm25_index.remove_document(document_id)
    async with AsyncSessionLocal() as db:
        await db.execute(
            sa_delete(Chunk).where(Chunk.document_id == document_id)
        )
        await db.commit()


async def delete_document_data(doc: Document) -> None:
    """删除文档：级联清空向量、分片与上传的物理文件。"""
    vector_store.delete_by_document(doc.id)
    await bm25_index.remove_document(doc.id)
    if doc.file_path:
        try:
            Path(doc.file_path).unlink(missing_ok=True)
        except OSError:
            logger.warning("删除物理文件失败: %s", doc.file_path, exc_info=True)
    async with AsyncSessionLocal() as db:
        attached = await db.get(Document, doc.id)
        if attached is not None:
            await db.delete(attached)  # chunks 级联删除
            await db.commit()


# ============ 各阶段实现 ============


async def _stage_parse(db, doc: Document) -> str:
    doc.status = "parsing"
    await db.commit()
    content = Path(doc.file_path).read_bytes()
    raw_text = parser_factory.parse_document(doc.file_type, content)
    if not raw_text.strip():
        raise ValueError("解析结果为空文本，无法入库")
    return raw_text


async def _stage_clean(db, doc: Document, raw_text: str) -> str:
    doc.status = "cleaning"
    await db.commit()
    return await cleaner.clean_text(raw_text, doc.filename)


async def _stage_chunk(db, doc: Document, cleaned: str):
    doc.status = "chunking"
    await db.commit()
    pieces = chunker.chunk_text(cleaned)
    if not pieces:
        raise ValueError("分块结果为空")
    return pieces


async def _stage_embed_and_save(db, doc: Document, pieces) -> None:
    doc.status = "embedding"
    await db.commit()

    # 过滤4字节字符，适配 MySQL 5.1 utf8(3字节)；Chroma 与 MySQL 保持一致
    contents = [strip_4byte(p.content) or "" for p in pieces]
    embedding_usage: dict[str, int] = {}
    embeddings = await glm_embedding.embed_texts(contents, usage_out=embedding_usage)

    chroma_ids = [uuid.uuid4().hex for _ in pieces]
    metadatas = [
        {
            "document_id": doc.id,
            "filename": doc.filename,
            "chunk_index": p.index,
            "section": str(p.meta.get("section", "")),
        }
        for p in pieces
    ]
    vector_store.upsert_chunks(
        ids=chroma_ids, embeddings=embeddings, documents=contents, metadatas=metadatas
    )

    for p, cid in zip(pieces, chroma_ids):
        db.add(
            Chunk(
                document_id=doc.id,
                chunk_index=p.index,
                content=p.content,
                char_count=len(p.content),
                chroma_id=cid,
                chunk_meta=p.meta,
            )
        )
    doc.chunk_count = len(pieces)
    doc.char_count = sum(len(c) for c in contents)
    doc.status = "done"
    doc.error = None
    await db.commit()

    # 入库 embedding token 统计
    if embedding_usage.get("total_tokens"):
        stats_service.record_event_bg(
            event_type="embedding",
            prompt_tokens=embedding_usage.get("prompt_tokens", 0),
            total_tokens=embedding_usage.get("total_tokens", 0),
        )
