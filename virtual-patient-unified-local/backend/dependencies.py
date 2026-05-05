"""FastAPI dependencies — local JWT + optional Supabase user sync."""
import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.db_models import User, UserRole
from services.auth_service import decode_access_token

logger = logging.getLogger(__name__)
security = HTTPBearer()


def _determine_role(email: str, user_metadata: dict) -> UserRole:
    meta_role = user_metadata.get("role", "")
    if meta_role == "admin":
        return UserRole.ADMIN
    if settings.admin_email and email.lower() == settings.admin_email.lower():
        return UserRole.ADMIN
    return UserRole.STUDENT


def _sync_user_from_token(payload: dict, db: Session) -> User:
    """Ensure a local User row exists (Supabase-style payload)."""
    supabase_uid = payload["sub"]
    email = payload.get("email", "")
    user_metadata = payload.get("user_metadata", {})
    expected_role = _determine_role(email, user_metadata)

    user = db.query(User).filter(User.id == supabase_uid).first()
    if user:
        changed = False
        if user.email != email:
            user.email = email
            changed = True
        if expected_role == UserRole.ADMIN and user.role != UserRole.ADMIN:
            user.role = UserRole.ADMIN
            changed = True
        meta_name = (
            user_metadata.get("display_name")
            or user_metadata.get("full_name")
            or user_metadata.get("name")
        )
        if meta_name and user.display_name == email.split("@")[0]:
            user.display_name = meta_name
            changed = True
        if changed:
            db.commit()
            db.refresh(user)
        return user

    existing_by_email = db.query(User).filter(User.email == email).first()
    if existing_by_email:
        existing_by_email.id = supabase_uid
        meta_name = (
            user_metadata.get("display_name")
            or user_metadata.get("full_name")
            or user_metadata.get("name")
        )
        if meta_name:
            existing_by_email.display_name = meta_name
        if expected_role == UserRole.ADMIN:
            existing_by_email.role = UserRole.ADMIN
        db.commit()
        db.refresh(existing_by_email)
        return existing_by_email

    display_name = (
        user_metadata.get("display_name")
        or user_metadata.get("full_name")
        or user_metadata.get("name")
        or email.split("@")[0]
    )

    user = User(
        id=supabase_uid,
        email=email,
        display_name=display_name,
        role=expected_role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if user:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated",
            )
        return user

    # Supabase-first-login path
    if payload.get("email"):
        user = _sync_user_from_token(payload, db)
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated",
            )
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
