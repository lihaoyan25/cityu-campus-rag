"""系统提示词服务：DB 覆盖 prompts.py 默认值，管理后台在线编辑即时生效。"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SystemPrompt
from app.llm import prompts

logger = logging.getLogger(__name__)

# 可编辑的提示词 key -> 默认值
PROMPT_REGISTRY: dict[str, str] = {
    "agent_system": prompts.AGENT_SYSTEM,
}


async def get_prompt(db: AsyncSession, key: str) -> str:
    """读取提示词：DB 有则用 DB，否则回退默认值。"""
    default = PROMPT_REGISTRY.get(key)
    if default is None:
        raise KeyError(f"未知提示词: {key}")
    try:
        row = await db.scalar(select(SystemPrompt).where(SystemPrompt.key == key))
        if row and row.content.strip():
            return row.content
    except Exception:
        logger.warning("读取提示词 %s 失败，使用默认值", key, exc_info=True)
    return default


async def list_prompts(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(select(SystemPrompt))).scalars().all()
    by_key = {r.key: r for r in rows}
    out = []
    for key, default in PROMPT_REGISTRY.items():
        row = by_key.get(key)
        out.append(
            {
                "key": key,
                "content": row.content if row else default,
                "modified": row is not None,
                "updated_at": row.updated_at.isoformat() if row else None,
            }
        )
    return out


async def upsert_prompt(db: AsyncSession, key: str, content: str) -> None:
    if key not in PROMPT_REGISTRY:
        raise KeyError(f"未知提示词: {key}")
    row = await db.scalar(select(SystemPrompt).where(SystemPrompt.key == key))
    if row is None:
        db.add(SystemPrompt(key=key, content=content))
    else:
        row.content = content
    await db.commit()
