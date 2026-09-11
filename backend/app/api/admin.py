"""管理员路由：JWT 登录 + 文档管理。"""
import math

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.core.deps import get_current_admin, get_db
from app.db.models import Chunk, Document
from app.rag import pipeline
from app.rag.parsers.factory import UnsupportedFileTypeError
from app.services import config_service, prompt_service, stats_service

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class DocumentOut(BaseModel):
    id: int
    filename: str
    file_type: str
    size: int
    status: str
    error: str | None
    chunk_count: int
    char_count: int | None
    created_at: object
    updated_at: object


# ============ 认证 ============


@router.post("/auth/login", summary="管理员登录，返回 JWT")
async def admin_login(body: LoginRequest):
    if not security.verify_admin(body.username, body.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = security.create_access_token(subject=body.username)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/auth/me", summary="查看当前管理员信息")
async def admin_me(admin: str = Depends(get_current_admin)):
    return {"username": admin}


# ============ 文档管理 ============


@router.post("/documents/upload", summary="上传文档并后台入库")
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    try:
        file_type = pipeline.parser_factory.detect_file_type(file.filename)
    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if file.size and file.size > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"文件过大（上限 {settings.max_upload_mb}MB）",
        )
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"文件过大（上限 {settings.max_upload_mb}MB）",
        )
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")
    md5 = pipeline.file_md5(content)

    existing = await db.scalar(
        select(Document).where(Document.md5 == md5, Document.status != "failed")
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"相同内容文档已存在: id={existing.id} {existing.filename}",
        )

    doc = Document(
        filename=file.filename,
        file_type=file_type,
        md5=md5,
        size=len(content),
        status="pending",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    doc.file_path = pipeline.save_upload(doc.id, file.filename, content)
    await db.commit()
    background.add_task(pipeline.process_document, doc.id)
    return _doc_out(doc)


@router.get("/documents", summary="文档列表")
async def list_documents(
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    query = select(Document).order_by(Document.id.desc())
    count_query = select(func.count(Document.id))
    if status:
        query = query.where(Document.status == status)
        count_query = count_query.where(Document.status == status)

    total = await db.scalar(count_query)
    rows = (
        (await db.execute(query.offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 0,
        "items": [_doc_out(d) for d in rows],
    }


@router.get("/documents/{doc_id}", summary="文档详情")
async def get_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    doc = await db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return _doc_out(doc)


@router.get("/documents/{doc_id}/chunks", summary="查看文档分片")
async def list_chunks(
    doc_id: int,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    doc = await db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    total = await db.scalar(select(func.count(Chunk.id)).where(Chunk.document_id == doc_id))
    rows = (
        (
            await db.execute(
                select(Chunk)
                .where(Chunk.document_id == doc_id)
                .order_by(Chunk.chunk_index)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": c.id,
                "chunk_index": c.chunk_index,
                "content": c.content,
                "char_count": c.char_count,
                "chroma_id": c.chroma_id,
                "meta": c.chunk_meta,
            }
            for c in rows
        ],
    }


@router.delete("/documents/{doc_id}", summary="删除文档(含向量与分片)")
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    doc = await db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    await pipeline.delete_document_data(doc)
    return {"deleted": doc_id}


@router.post("/documents/{doc_id}/retry", summary="重试失败文档")
async def retry_document(
    doc_id: int,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    doc = await db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    if doc.status not in ("failed", "done"):
        raise HTTPException(status_code=400, detail=f"当前状态 {doc.status} 不允许重试")
    if not doc.file_path:
        raise HTTPException(status_code=400, detail="缺少原始文件，无法重试")
    # 已入库的文档重处理前必须清空旧分片与向量，否则数据翻倍
    if doc.status == "done":
        await pipeline.clear_document_chunks(doc.id)
        doc.chunk_count = 0
        doc.char_count = None
    doc.status = "pending"
    doc.error = None
    await db.commit()
    background.add_task(pipeline.process_document, doc.id)
    return _doc_out(doc)


def _doc_out(doc: Document) -> dict:
    return DocumentOut(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        size=doc.size,
        status=doc.status,
        error=doc.error,
        chunk_count=doc.chunk_count,
        char_count=doc.char_count,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    ).model_dump(mode="json")


# ============ 系统提示词 ============


class PromptUpdate(BaseModel):
    content: str


@router.get("/prompts", summary="提示词列表(含当前生效内容)")
async def list_prompts(
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    return {"items": await prompt_service.list_prompts(db)}


@router.put("/prompts/{key}", summary="更新提示词(即时生效)")
async def update_prompt(
    key: str,
    body: PromptUpdate,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    try:
        await prompt_service.upsert_prompt(db, key, body.content)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"updated": key}


# ============ 运行时配置(热更新) ============


class ConfigUpdate(BaseModel):
    values: dict[str, str]


@router.get("/config", summary="查看当前配置(敏感项脱敏)")
async def get_config(
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    return {"items": await config_service.get_all(db)}


@router.put("/config", summary="批量更新配置(热更新，立即生效)")
async def update_config(
    body: ConfigUpdate,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    try:
        updated = await config_service.set_many(db, body.values)
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"updated": updated}


# ============ 运行统计 ============


@router.get("/stats/overview", summary="仪表盘统计(汇总+按日序列)")
async def stats_overview(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(get_current_admin),
):
    days = max(1, min(days, 90))
    return await stats_service.get_overview(db, days)
