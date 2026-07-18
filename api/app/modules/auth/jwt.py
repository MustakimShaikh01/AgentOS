from datetime import datetime, timezone, timedelta
from typing import Any
import hashlib
import base64

from jose import jwt, JWTError

from app.config import get_settings

settings = get_settings()

# ──────────────────────────────────────────────────────────────────────────────
# JWT utilities
# ──────────────────────────────────────────────────────────────────────────────

def create_access_token(user_id: str, org_id: str, role: str) -> str:
    """
    Issue a short-lived access token (15 min by default).
    Includes jti (JWT ID) for blacklisting on logout.
    """
    import uuid
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "org": org_id,
        "role": role,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_expiry_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    """Issue a longer-lived refresh token (7 days by default)."""
    import uuid
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_refresh_expiry_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError if invalid."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def get_remaining_ttl_seconds(token: str) -> int:
    """How many seconds until this token expires."""
    payload = decode_token(token)
    exp = payload.get("exp", 0)
    remaining = int(exp - datetime.now(timezone.utc).timestamp())
    return max(0, remaining)


# ──────────────────────────────────────────────────────────────────────────────
# Token hashing (for refresh token storage)
# ──────────────────────────────────────────────────────────────────────────────

def hash_token(token: str) -> str:
    """SHA-256 hash a token value for safe storage."""
    digest = hashlib.sha256(token.encode()).digest()
    return base64.b64encode(digest).decode()
