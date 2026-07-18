"""
Shared FastAPI dependencies.

These are injected via Depends() into route handlers.
They provide: DB session, Redis connection, current user.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.base import get_db
from app.db.models import User
from app.modules.auth.jwt import decode_token
from app.modules.auth.service import is_token_blacklisted

settings = get_settings()
_security = HTTPBearer()
_redis: Redis | None = None


async def get_redis() -> Redis:
    """Return the shared Redis connection pool."""
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> User:
    """
    Validate JWT, check blacklist, load and return current user.
    Used as a dependency for any protected route.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
    except JWTError:
        raise credentials_exception

    jti = payload.get("jti")
    if jti and await is_token_blacklisted(jti, redis):
        raise credentials_exception

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise credentials_exception

    return user
