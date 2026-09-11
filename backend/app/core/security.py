"""JWT 签发/校验 与 管理员凭证校验。"""
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings


class AuthError(Exception):
    """凭证无效或已过期。"""


def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": "admin",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm="HS256")


def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as e:
        raise AuthError("token 无效或已过期") from e
    sub = payload.get("sub")
    if not sub:
        raise AuthError("token 缺少 subject")
    return sub


def verify_admin(username: str, password: str) -> bool:
    return username == settings.admin_username and password == settings.admin_password
