"""Authentication routes — local JWT register/login + existing /me and admin user APIs."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from dependencies import require_admin, get_current_user
from models.db_models import User, UserRole
from models.api_schemas import UserOut, LoginRequest, RegisterRequest, TokenResponse
from services.auth_service import create_access_token
from services.password_utils import hash_password, verify_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Create a local user and return a JWT. First user becomes admin if no admin_email match else student."""
    email = body.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    is_first = db.query(User).count() == 0
    role = UserRole.STUDENT
    if is_first:
        role = UserRole.ADMIN
    if settings.admin_email and email == settings.admin_email.strip().lower():
        role = UserRole.ADMIN

    uid = uuid.uuid4().hex
    user = User(
        id=uid,
        email=email,
        display_name=body.display_name.strip(),
        role=role,
        is_active=True,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, user.email)
    logger.info(f"Registered local user {email} role={role.value}")
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is deactivated")
    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user.

    Also serves as token validation — if the Supabase token is valid,
    the user is auto-synced to the local DB and returned.
    """
    return UserOut.model_validate(current_user)


@router.patch("/me", response_model=UserOut)
async def update_me(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the current user's display name."""
    if "display_name" in body:
        current_user.display_name = body["display_name"]
        db.commit()
        db.refresh(current_user)
    return UserOut.model_validate(current_user)


@router.get("/users", response_model=list[UserOut])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all users (admin only)."""
    users = db.query(User).order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return [UserOut.model_validate(u) for u in users]


@router.patch("/users/{user_id}/role", response_model=UserOut)
async def update_user_role(
    user_id: str,
    body: dict,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Change a user's role (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    role_str = body.get("role", "")
    if role_str not in ("admin", "student"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

    user.role = UserRole(role_str)
    db.commit()
    db.refresh(user)
    logger.info(f"Admin '{admin.email}' changed role of '{user.email}' to {role_str}")
    return UserOut.model_validate(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Deactivate a user (admin only). Does not delete, just sets is_active=False."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate yourself")

    user.is_active = False
    db.commit()
    logger.info(f"Admin '{admin.email}' deactivated user '{user.email}'")
