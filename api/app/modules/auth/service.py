import re
import uuid
from datetime import datetime, timezone, timedelta

from passlib.context import CryptContext
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import User, Organization, RefreshToken
from app.modules.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_remaining_ttl_seconds,
    hash_token,
)
from app.modules.auth.schemas import AuthResponse, LoginRequest, RegisterRequest, TokenResponse, UserInfo

settings = get_settings()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

BLACKLIST_PREFIX = "jwt:blacklist:"


# ── Public Interface ──────────────────────────────────────────────────────────

async def register(request: RegisterRequest, db: AsyncSession) -> AuthResponse:
    # Check email uniqueness
    existing = await db.scalar(select(User).where(User.email == request.email.lower()))
    if existing:
        raise ValueError("Email already registered")

    # Create or fetch organization
    slug = _slugify(request.org_name)
    org = await db.scalar(select(Organization).where(Organization.slug == slug))
    if not org:
        org = Organization(name=request.org_name, slug=slug)
        db.add(org)
        await db.flush()

    # Create user
    user = User(
        org_id=org.id,
        email=request.email.lower(),
        password_hash=pwd_ctx.hash(request.password),
        full_name=request.full_name,
        role="OWNER",
    )
    db.add(user)
    await db.flush()

    return await _build_auth_response(user, org, db)


async def login(request: LoginRequest, db: AsyncSession) -> AuthResponse:
    user = await db.scalar(select(User).where(User.email == request.email.lower()))
    if not user or not user.is_active:
        raise ValueError("Invalid credentials")

    if not pwd_ctx.verify(request.password, user.password_hash):
        raise ValueError("Invalid credentials")

    # Load org
    org = await db.get(Organization, user.org_id)

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    return await _build_auth_response(user, org, db)


async def refresh(refresh_token_value: str, db: AsyncSession) -> TokenResponse:
    token_hash = hash_token(refresh_token_value)
    stored = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    if not stored or not stored.is_valid:
        raise ValueError("Invalid or expired refresh token")

    user = await db.get(User, stored.user_id)
    org = await db.get(Organization, user.org_id)

    access_token = create_access_token(
        user_id=str(user.id),
        org_id=str(org.id),
        role=user.role,
    )
    return TokenResponse(access_token=access_token)


async def logout(access_token: str, db: AsyncSession, redis: Redis) -> None:
    try:
        payload = decode_token(access_token)
        jti = payload.get("jti")
        user_id = payload.get("sub")
        ttl = get_remaining_ttl_seconds(access_token)

        if jti and ttl > 0:
            await redis.setex(f"{BLACKLIST_PREFIX}{jti}", ttl, "1")

        if user_id:
            await db.execute(
                update(RefreshToken)
                .where(RefreshToken.user_id == uuid.UUID(user_id))
                .values(revoked=True)
            )
    except Exception:
        pass  # Best-effort logout


async def is_token_blacklisted(jti: str, redis: Redis) -> bool:
    return await redis.exists(f"{BLACKLIST_PREFIX}{jti}") > 0


# ── Private Helpers ───────────────────────────────────────────────────────────

async def _build_auth_response(user: User, org: Organization, db: AsyncSession) -> AuthResponse:
    access_token = create_access_token(
        user_id=str(user.id),
        org_id=str(org.id),
        role=user.role,
    )
    refresh_token_value = create_refresh_token(user_id=str(user.id))

    token = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token_value),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expiry_days),
    )
    db.add(token)
    await db.flush()

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token_value,
        user=UserInfo(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            org_id=str(org.id),
            org_name=org.name,
        ),
    )


def _slugify(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")
