"""FastAPI 入口。

启动: uvicorn app.main:app --reload --port 8000
"""
import time
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from app.api.router import api_router
from app.core.config import DATA_DIR, settings
from app.core.ratelimit import SlidingWindowLimiter
from app.db.engine import AsyncSessionLocal, engine
from app.db.models import Base, Chunk
from app.rag.retrievers.bm25 import bm25_index
from app.rag import vector_store
from app.services import config_service, stats_service

logger = logging.getLogger(__name__)

# IP 限流器: 问答流式接口(防刷 API 费用) / 普通 API
_chat_limiter = SlidingWindowLimiter()
_api_limiter = SlidingWindowLimiter()


async def _ensure_columns(conn) -> None:
    """轻量列迁移：create_all 不给已有表加新列，这里自动补齐（新列一律 NULL）。"""
    from sqlalchemy import text

    for table in Base.metadata.sorted_tables:
        result = await conn.execute(text(f"SHOW COLUMNS FROM `{table.name}`"))
        existing = {row[0] for row in result}
        for col in table.columns:
            if col.name not in existing:
                col_type = col.type.compile()
                await conn.execute(
                    text(f"ALTER TABLE `{table.name}` ADD COLUMN `{col.name}` {col_type} NULL")
                )
                logger.info("表 %s 补充新列: %s %s", table.name, col.name, col_type)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动: 建表（开发期用 create_all，后续可换 Alembic）
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_columns(conn)
    # BM25 索引从 MySQL 全量重建
    await bm25_index.rebuild_from_db()
    # 重放 DB 配置覆盖（管理后台热更新的配置，重启后继续生效）
    await config_service.apply_db_overrides()
    # 清理过期统计明细，防止公共访问下 stats_events 无限增长
    await stats_service.cleanup_old_events(keep_days=90)
    # ChromaDB 连接检查 + 数据一致性自检
    if vector_store.heartbeat():
        try:
            chroma_count = vector_store.count()
            async with AsyncSessionLocal() as db:
                mysql_chunks = (await db.execute(select(func.count(Chunk.id)))).scalar() or 0
            if chroma_count != mysql_chunks:
                logger.warning(
                    "⚠️ 向量库与 MySQL 分片数不一致: chroma=%d, mysql=%d。"
                    "若 chroma=0，多半是 Chroma server 启在了错误的数据目录"
                    "（必须在 backend 目录下运行: chroma run --path data/chroma），"
                    "此时 BM25 仍可检索但向量检索为空。",
                    chroma_count, mysql_chunks,
                )
        except Exception:
            logger.warning("ChromaDB 数据自检失败", exc_info=True)
    else:
        logger.warning(
            "ChromaDB 不可达 (mode=%s, http=%s:%d)。http 模式请先启动 chroma server, "
            "注意必须在 backend 目录下运行: chroma run --path data/chroma --port %d",
            settings.chroma_mode, settings.chroma_http_host, settings.chroma_http_port,
            settings.chroma_http_port,
        )
    yield
    await engine.dispose()


app = FastAPI(title="CityU Campus RAG API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        o.strip() for o in settings.allowed_origins.split(",") if o.strip()
    ] or ["*"],
    allow_credentials="*" not in settings.allowed_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.middleware("http")
async def ratelimit_middleware(request: Request, call_next):
    """IP 限流: 问答流式接口严格限制(防刷 API 费用)，普通 API 宽松限制。"""
    path = request.url.path
    if path.startswith("/api"):
        client_ip = request.client.host if request.client else "unknown"
        if path.startswith("/api/chat") and path.endswith("/stream"):
            if not _chat_limiter.allow(
                client_ip, settings.rate_limit_chat_per_min, 60
            ):
                return JSONResponse(
                    {"detail": "问答请求过于频繁，请稍后再试"},
                    status_code=429,
                )
        elif not _api_limiter.allow(
            client_ip, settings.rate_limit_api_per_min, 60
        ):
            return JSONResponse(
                {"detail": "请求过于频繁，请稍后再试"},
                status_code=429,
            )
    return await call_next(request)


@app.middleware("http")
async def stats_middleware(request: Request, call_next):
    """API 访问埋点：PV + 响应耗时（异步落库，不阻塞请求）。"""
    if not request.url.path.startswith("/api"):
        return await call_next(request)
    t0 = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        stats_service.record_event_bg(
            event_type="api",
            path=request.url.path,
            status_code=500,
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
        raise
    stats_service.record_event_bg(
        event_type="api",
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=int((time.perf_counter() - t0) * 1000),
    )
    return response


@app.get("/", tags=["meta"])
async def root():
    return {"service": "cityu-rag-backend", "docs": "/docs"}
