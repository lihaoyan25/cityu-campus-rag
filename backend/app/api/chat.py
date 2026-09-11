"""对话路由：会话管理与 SSE 流式问答（开放访问，无需登录）。

会话按匿名访客(X-Visitor-Id)隔离：每个浏览器只能看到/操作自己的会话。
"""
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.services import chat_service

router = APIRouter()

VISITOR_HEADER = "X-Visitor-Id"


def get_visitor_id(request: Request) -> str:
    """从请求头取访客标识；缺失时归入 legacy（历史遗留会话，任何人都不可见）。"""
    vid = (request.headers.get(VISITOR_HEADER) or "").strip()
    return vid[:64] if vid else "legacy"


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000, description="用户问题")
    deep_thinking: bool = Field(default=False, description="是否开启深度思考")


@router.post("/sessions", summary="创建新会话")
async def create_session(request: Request, db: AsyncSession = Depends(get_db)):
    return await chat_service.create_session(db, get_visitor_id(request))


@router.get("/sessions", summary="当前访客的会话列表")
async def list_sessions(request: Request, db: AsyncSession = Depends(get_db)):
    return {"items": await chat_service.list_sessions(db, get_visitor_id(request))}


@router.get("/sessions/{session_id}/messages", summary="会话历史消息")
async def get_messages(
    session_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    messages = await chat_service.get_messages(db, session_id, get_visitor_id(request))
    if messages is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"items": messages}


@router.delete("/sessions/{session_id}", summary="删除会话")
async def delete_session(
    session_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not await chat_service.delete_session(db, session_id, get_visitor_id(request)):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"deleted": session_id}


@router.post("/sessions/{session_id}/stream", summary="流式问答(SSE)")
async def chat_stream(
    session_id: int,
    body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from app.db.models import ChatSession

    vid = get_visitor_id(request)
    session = await db.get(ChatSession, session_id)
    # 归属校验: 不能向别人的会话提问
    if session is None or (session.visitor_id or "legacy") != vid:
        raise HTTPException(status_code=404, detail="会话不存在")

    async def event_gen():
        try:
            async for event in chat_service.run_chat_stream(
                session_id, body.question, body.deep_thinking
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:  # 兜底: 持久化等内部异常也以 error 事件告知前端
            yield f"data: {json.dumps({'type': 'error', 'message': f'服务内部错误: {e}'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
