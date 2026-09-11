"""API 路由聚合。"""
from fastapi import APIRouter

from app.api import admin, chat

api_router = APIRouter()
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
