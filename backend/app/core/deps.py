"""FastAPI 依赖注入。"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.db.engine import get_db

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_admin(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录")
    try:
        sub = security.verify_token(cred.credentials)
    except security.AuthError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "凭证无效或已过期")
    if sub != settings.admin_username:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员权限")
    return sub


__all__ = ["get_db", "get_current_admin", "AsyncSession"]
