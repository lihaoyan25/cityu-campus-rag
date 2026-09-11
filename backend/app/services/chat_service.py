"""会话管理与问答编排（SSE 事件流）。"""
import logging
import time
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import agent, memory
from app.core.config import settings
from app.core.textutil import strip_4byte
from app.db.engine import AsyncSessionLocal
from app.db.models import ChatSession, Message
from app.llm import prompts
from app.rag import query_rewriter
from app.rag.retrievers import get_retriever
from app.rag.retrievers.base import RetrievedChunk
from app.services import stats_service

logger = logging.getLogger(__name__)


# ============ 会话 CRUD ============


async def create_session(db: AsyncSession, visitor_id: str) -> dict:
    session = ChatSession(visitor_id=visitor_id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return _session_out(session)


async def list_sessions(db: AsyncSession, visitor_id: str) -> list[dict]:
    rows = (
        await db.execute(
            select(ChatSession)
            .where(ChatSession.visitor_id == visitor_id)
            .order_by(ChatSession.updated_at.desc())
        )
    ).scalars().all()
    return [_session_out(s) for s in rows]


async def get_messages(db: AsyncSession, session_id: int, visitor_id: str) -> list[dict] | None:
    session = await db.get(ChatSession, session_id)
    if session is None or (session.visitor_id or "legacy") != visitor_id:
        return None
    rows = (
        await db.execute(
            select(Message).where(Message.session_id == session_id).order_by(Message.id)
        )
    ).scalars().all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "reasoning": m.reasoning,
            "sources": m.sources,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in rows
        if m.role in ("user", "assistant")  # tool 中间消息不暴露给前端
    ]


async def delete_session(db: AsyncSession, session_id: int, visitor_id: str) -> bool:
    session = await db.get(ChatSession, session_id)
    if session is None or (session.visitor_id or "legacy") != visitor_id:
        return False
    await db.delete(session)  # messages 级联删除
    await db.commit()
    return True


# ============ 问答编排 ============


async def run_chat_stream(
    session_id: int, question: str, deep_thinking: bool = False
) -> AsyncIterator[dict]:
    """完整问答链路，yield 统一事件流（由 API 层转为 SSE）。"""
    t0 = time.perf_counter()
    async with AsyncSessionLocal() as db:
        session = await db.get(ChatSession, session_id)
        if session is None:
            yield {"type": "error", "message": "会话不存在"}
            return

        db.add(Message(session_id=session_id, role="user", content=strip_4byte(question)))
        if session.title == "新对话":
            session.title = strip_4byte(question[:30]) or "新对话"
        await db.commit()

        llm_messages, recent_history = await memory.build_context(db, session, question)

    # 检索：查询改写 + 混合检索（失败不阻断回答，退化为直接生成）
    rewritten = question
    retrieved: list[RetrievedChunk] = []
    try:
        rewritten = await query_rewriter.rewrite_query(question, recent_history)
        retrieved = await get_retriever().retrieve(rewritten, settings.retrieval_top_k)
    except Exception:
        logger.exception("检索阶段失败，退化为无上下文回答 doc=%s", question[:50])

    sources = [_source_out(item) for item in retrieved]
    if sources:
        # 检索上下文插到最后一条用户消息之前
        context_block = _format_context(rewritten, retrieved)
        llm_messages.insert(-1, {"role": "system", "content": context_block})
        yield {"type": "sources", "sources": sources}

    final_content = ""
    final_reasoning = ""
    usage = None
    async for event in agent.run_agent_stream(llm_messages, thinking=deep_thinking):
        if event["type"] == "finish":
            final_content = event["content"]
            final_reasoning = event.get("reasoning") or ""
            usage = event.get("usage")
            continue
        if event["type"] == "error":
            yield event
            return
        yield event

    # 持久化 assistant 消息 + 触发记忆压缩
    async with AsyncSessionLocal() as db:
        db.add(
            Message(
                session_id=session_id,
                role="assistant",
                content=strip_4byte(final_content),
                reasoning=strip_4byte(final_reasoning) or None,
                sources=sources or None,
            )
        )
        await db.commit()
        session = await db.get(ChatSession, session_id)
        if session is not None:
            await memory.maybe_compress(db, session)

    # 问答统计：次数 + token + 耗时
    stats_service.record_event_bg(
        event_type="chat",
        duration_ms=int((time.perf_counter() - t0) * 1000),
        prompt_tokens=(usage or {}).get("prompt_tokens", 0),
        completion_tokens=(usage or {}).get("completion_tokens", 0),
        total_tokens=(usage or {}).get("total_tokens", 0),
    )

    yield {
        "type": "done",
        "content": final_content,
        "sources": sources,
        "usage": usage,
    }


# ============ 内部工具函数 ============


def _format_context(question: str, items: list[RetrievedChunk]) -> str:
    blocks = []
    for i, item in enumerate(items, start=1):
        source = item.filename + (f" - {item.section}" if item.section else "")
        blocks.append(prompts.CONTEXT_BLOCK_TEMPLATE.format(index=i, source=source, content=item.content))
    return prompts.CONTEXT_TEMPLATE.format(question=question, context_blocks="\n\n".join(blocks))


def _source_out(item: RetrievedChunk) -> dict:
    return {
        "filename": item.filename,
        "section": item.section,
        "chunk_index": item.chunk_index,
        "document_id": item.document_id,
        "score": item.score,
    }


def _session_out(session: ChatSession) -> dict:
    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }
