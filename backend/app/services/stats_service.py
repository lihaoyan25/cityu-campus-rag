"""统计服务：埋点写入（异步不阻塞）+ 管理端聚合查询。"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import case, func, select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import AsyncSessionLocal
from app.db.models import ChatSession, Chunk, Document, StatsEvent

logger = logging.getLogger(__name__)


async def record_event(
    event_type: str,
    path: str | None = None,
    status_code: int | None = None,
    duration_ms: int | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
) -> None:
    """写入一条埋点。独立短会话 + 异常吞掉，绝不影响主流程。"""
    try:
        async with AsyncSessionLocal() as db:
            db.add(
                StatsEvent(
                    event_type=event_type,
                    path=path[:200] if path else None,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                )
            )
            await db.commit()
    except Exception:
        logger.warning("统计埋点写入失败", exc_info=True)


def record_event_bg(**kwargs) -> None:
    """fire-and-forget 版本，用于请求链路中不阻塞。"""
    try:
        asyncio.get_running_loop()
        asyncio.create_task(record_event(**kwargs))
    except RuntimeError:
        asyncio.run(record_event(**kwargs))


async def cleanup_old_events(keep_days: int = 90) -> int:
    """清理过期统计明细，防止公共访问下表无限增长。返回删除行数。"""
    try:
        cutoff = datetime.now() - timedelta(days=keep_days)
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                sa_delete(StatsEvent).where(StatsEvent.created_at < cutoff)
            )
            await db.commit()
            deleted = result.rowcount or 0
            if deleted:
                logger.info("已清理 %d 条 %d 天前的统计明细", deleted, keep_days)
            return deleted
    except Exception:
        logger.warning("清理过期统计明细失败", exc_info=True)
        return 0


async def get_overview(db: AsyncSession, days: int = 7) -> dict[str, Any]:
    """管理端仪表盘数据：汇总 + 按日序列。"""
    start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start = start - timedelta(days=days - 1)

    async def _scalar(q):
        return (await db.execute(q)).scalar() or 0

    pv = await _scalar(
        select(func.count(StatsEvent.id)).where(
            StatsEvent.event_type == "api", StatsEvent.created_at >= start
        )
    )
    chat_count = await _scalar(
        select(func.count(StatsEvent.id)).where(
            StatsEvent.event_type == "chat", StatsEvent.created_at >= start
        )
    )
    prompt_tokens = await _scalar(
        select(func.coalesce(func.sum(StatsEvent.prompt_tokens), 0)).where(
            StatsEvent.created_at >= start, StatsEvent.event_type.in_(["chat", "embedding"])
        )
    )
    completion_tokens = await _scalar(
        select(func.coalesce(func.sum(StatsEvent.completion_tokens), 0)).where(
            StatsEvent.created_at >= start, StatsEvent.event_type == "chat"
        )
    )
    avg_chat_ms = await _scalar(
        select(func.coalesce(func.avg(StatsEvent.duration_ms), 0)).where(
            StatsEvent.event_type == "chat", StatsEvent.created_at >= start
        )
    )
    session_count = await _scalar(select(func.count(ChatSession.id)))
    document_count = await _scalar(
        select(func.count(Document.id)).where(Document.status == "done")
    )
    chunk_count = await _scalar(select(func.count(Chunk.id)))

    # ---- 按日序列（MySQL IF 用 case 表达，跨版本安全） ----
    daily_rows = (
        await db.execute(
            select(
                func.date(StatsEvent.created_at).label("day"),
                func.sum(case((StatsEvent.event_type == "api", 1), else_=0)).label("pv"),
                func.sum(case((StatsEvent.event_type == "chat", 1), else_=0)).label("chat_count"),
                func.coalesce(
                    func.sum(
                        case(
                            (StatsEvent.event_type.in_(["chat", "embedding"]), StatsEvent.prompt_tokens),
                            else_=0,
                        )
                    ),
                    0,
                ).label("prompt_tokens"),
                func.coalesce(
                    func.sum(
                        case(
                            (StatsEvent.event_type == "chat", StatsEvent.completion_tokens),
                            else_=0,
                        )
                    ),
                    0,
                ).label("completion_tokens"),
                func.coalesce(
                    func.avg(
                        case(
                            (StatsEvent.event_type == "chat", StatsEvent.duration_ms),
                            else_=None,
                        )
                    ),
                    0,
                ).label("avg_chat_ms"),
            )
            .where(StatsEvent.created_at >= start)
            .group_by(func.date(StatsEvent.created_at))
            .order_by(func.date(StatsEvent.created_at))
        )
    ).all()

    daily_map = {
        str(row.day): {
            "date": str(row.day),
            "pv": int(row.pv or 0),
            "chat_count": int(row.chat_count or 0),
            "prompt_tokens": int(row.prompt_tokens or 0),
            "completion_tokens": int(row.completion_tokens or 0),
            "avg_chat_ms": round(float(row.avg_chat_ms or 0)),
        }
        for row in daily_rows
    }
    # 补齐空缺日期，保证图表连续
    daily = []
    for i in range(days):
        d = (start + timedelta(days=i)).date().isoformat()
        daily.append(
            daily_map.get(
                d,
                {
                    "date": d,
                    "pv": 0,
                    "chat_count": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "avg_chat_ms": 0,
                },
            )
        )

    return {
        "summary": {
            "pv": pv,
            "chat_count": chat_count,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "avg_chat_ms": round(float(avg_chat_ms)),
            "session_count": session_count,
            "document_count": document_count,
            "chunk_count": chunk_count,
        },
        "daily": daily,
    }
