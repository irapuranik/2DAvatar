"""Authentication — local JWT (default) and optional Supabase JWT verification."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from jwt import PyJWKClient

from config import settings

logger = logging.getLogger(__name__)

SUPABASE_JWT_SECRET = settings.supabase_jwt_secret or settings.jwt_secret_legacy
SUPABASE_URL = settings.supabase_url
_jwks_client = None
if SUPABASE_URL:
    jwks_url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
    _jwks_client = PyJWKClient(jwks_url, cache_keys=True)


def create_access_token(user_id: str, email: str) -> str:
    """Issue HS256 JWT for local auth."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_expire_days),
        "typ": "local",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_local_token(token: str) -> Optional[dict]:
    """Verify local HS256 JWT."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        logger.warning("Local JWT expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid local JWT: {e}")
        return None


def decode_supabase_token(token: str) -> Optional[dict]:
    """Decode Supabase JWT (ES256/HS256). Optional when using hosted Supabase."""
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "")

        if alg == "ES256":
            if not _jwks_client:
                return None
            signing_key = _jwks_client.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                audience="authenticated",
            )
        if alg == "HS256":
            if not SUPABASE_JWT_SECRET:
                return None
            return jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        return None
    except Exception as e:
        logger.warning(f"Supabase token verify failed: {e}")
        return None


def decode_access_token(token: str) -> Optional[dict]:
    """Try local JWT first, then Supabase (for mixed migrations)."""
    p = decode_local_token(token)
    if p is not None:
        return p
    return decode_supabase_token(token)

