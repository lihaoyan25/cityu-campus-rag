"""运行时配置热更新：DB 覆盖 .env，改完立即生效，重启自动重放。

敏感项（API key）读取时脱敏；前端回传脱敏值时不覆盖真实值。
"""
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.db.engine import AsyncSessionLocal
from app.db.models import AppConfig

logger = logging.getLogger(__name__)

# 可在线修改的配置白名单（均为 Settings 字段）
ALLOWED_KEYS: set[str] = {
    # DeepSeek
    "deepseek_api_key", "deepseek_base_url", "deepseek_model",
    "deepseek_temperature", "deepseek_max_tokens", "deepseek_top_p",
    # GLM embedding
    "glm_api_key", "glm_base_url", "glm_model",
    "glm_embedding_dimensions", "glm_embedding_batch_size",
    # 检索
    "retrieval_top_k", "hybrid_enabled", "rrf_k", "rerank_enabled",
    # 分块与预处理
    "chunk_size", "chunk_overlap", "doc_clean_enabled",
    # 记忆
    "memory_window_messages", "memory_summary_trigger",
}

SENSITIVE_KEYS: set[str] = {"deepseek_api_key", "glm_api_key"}
MASK_PREFIX = "••••"


def mask_value(value: str) -> str:
    value = str(value)
    if len(value) <= 4:
        return MASK_PREFIX
    return MASK_PREFIX + value[-4:]


def _coerce(key: str, value) -> Any:
    """按 Settings 字段类型转换。"""
    annotation = Settings.model_fields[key].annotation
    if annotation is bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("1", "true", "yes", "on")
    if annotation is int:
        return int(float(str(value)))
    if annotation is float:
        return float(str(value))
    return str(value)


async def get_all(db: AsyncSession) -> dict[str, dict]:
    """返回白名单内所有配置的当前生效值（敏感项脱敏）。"""
    rows = (await db.execute(select(AppConfig))).scalars().all()
    overrides = {r.key: r.value for r in rows}
    out: dict[str, dict] = {}
    for key in sorted(ALLOWED_KEYS):
        raw = overrides.get(key, str(getattr(settings, key)))
        display = mask_value(raw) if key in SENSITIVE_KEYS else raw
        out[key] = {
            "value": display,
            "modified": key in overrides,
            "sensitive": key in SENSITIVE_KEYS,
        }
    return out


async def set_many(db: AsyncSession, values: dict[str, str]) -> int:
    """批量更新：写 DB + 热更新内存。返回实际更新数。"""
    updated = 0
    for key, value in values.items():
        if key not in ALLOWED_KEYS:
            raise KeyError(f"不支持的配置项: {key}")
        if key in SENSITIVE_KEYS and str(value).startswith(MASK_PREFIX):
            continue  # 脱敏值原样回传，视为不修改
        coerced = _coerce(key, value)
        setattr(settings, key, coerced)
        row = await db.scalar(select(AppConfig).where(AppConfig.key == key))
        if row is None:
            db.add(AppConfig(key=key, value=str(coerced)))
        else:
            row.value = str(coerced)
        updated += 1
    await db.commit()
    logger.info("运行时配置更新 %d 项", updated)
    return updated


async def apply_db_overrides() -> int:
    """启动时重放 DB 配置覆盖。"""
    try:
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(select(AppConfig))).scalars().all()
        for row in rows:
            if row.key in ALLOWED_KEYS:
                try:
                    setattr(settings, row.key, _coerce(row.key, row.value))
                except (ValueError, TypeError):
                    logger.warning("配置覆盖值无效，跳过: %s=%s", row.key, row.value)
        if rows:
            logger.info("已应用 %d 项 DB 配置覆盖", len(rows))
        return len(rows)
    except Exception:
        logger.warning("加载 DB 配置覆盖失败，使用 .env 默认值", exc_info=True)
        return 0
