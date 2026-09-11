"""会话记忆：滑窗历史 + LLM 摘要压缩。"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.textutil import strip_4byte
from app.db.models import ChatSession, Message
from app.llm import deepseek, prompts
from app.services import prompt_service

logger = logging.getLogger(__name__)


async def build_context(
    db: AsyncSession, session: ChatSession, question: str
) -> tuple[list[dict], list[dict]]:
    """组装 Agent 消息列表，返回 (llm_messages, recent_history)。

    recent_history 用于查询改写。
    """
    window = settings.memory_window_messages
    rows = (
        (
            await db.execute(
                select(Message)
                .where(
                    Message.session_id == session.id,
                    Message.role.in_(["user", "assistant"]),
                    Message.content.isnot(None),
                )
                .order_by(Message.id.desc())
                .limit(window)
            )
        )
        .scalars()
        .all()
    )
    recent = list(reversed(rows))
    recent_history = [{"role": m.role, "content": m.content} for m in recent]

    system_parts = [await prompt_service.get_prompt(db, "agent_system")]
    if session.summary:
        system_parts.append(f"<历史对话记忆>\n{session.summary}\n</历史对话记忆>")
    system_content = "\n\n".join(system_parts)

    messages: list[dict] = [{"role": "system", "content": system_content}]
    messages.extend(recent_history)
    messages.append({"role": "user", "content": question})
    return messages, recent_history


async def maybe_compress(db: AsyncSession, session: ChatSession) -> None:
    """消息数超过滑窗时，把窗口外的增量对话压缩进摘要。"""
    window = settings.memory_window_messages
    trigger = settings.memory_summary_trigger
    total = await db.scalar(
        select(Message.id).where(
            Message.session_id == session.id, Message.role.in_(["user", "assistant"])
        ).order_by(Message.id.desc()).limit(1).offset(trigger - 1)
    )
    if total is None:
        return

    # 窗口外的消息（早于最近 window 条）
    rows = (
        (
            await db.execute(
                select(Message)
                .where(
                    Message.session_id == session.id,
                    Message.role.in_(["user", "assistant"]),
                    Message.content.isnot(None),
                )
                .order_by(Message.id.desc())
                .offset(window)
            )
        )
        .scalars()
        .all()
    )
    # 过滤掉已被摘要覆盖的
    pending = [m for m in reversed(rows) if m.id > session.summarized_until_id]
    if not pending:
        return

    dialogue = "\n".join(
        f"{'用户' if m.role == 'user' else '助手'}: {m.content[:800]}" for m in pending
    )
    try:
        user_msg = prompts.MEMORY_SUMMARY_USER_TEMPLATE.format(
            existing_summary=session.summary or "（无）", dialogue=dialogue
        )
        result = await deepseek.chat(
            [
                {"role": "system", "content": prompts.MEMORY_SUMMARY_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        summary = (result.get("content") or "").strip()
        if summary:
            session.summary = strip_4byte(summary)
            session.summarized_until_id = pending[-1].id
            await db.commit()
            logger.info(
                "会话 %s 记忆已压缩: 覆盖至 message_id=%s", session.id, pending[-1].id
            )
    except Exception:
        logger.exception("会话 %s 记忆压缩失败（不影响回答）", session.id)
