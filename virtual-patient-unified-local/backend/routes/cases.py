"""Case CRUD routes — create, read, update, delete, publish cases."""
import io
import logging
import os
import re
import shutil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from PIL import Image
from sqlalchemy.orm import Session

from config import FRONTEND_PUBLIC_DIR
from database import get_db
from dependencies import require_admin, get_current_user
from models.db_models import Case, CaseStatus, User, UserRole, PracticeSession
from models.api_schemas import CaseCreate, CaseUpdate, CaseOut, CaseOutStudent, CaseListOut
from services import storage_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cases", tags=["cases"])

_PUBLIC = FRONTEND_PUBLIC_DIR


def _viseme_shapes_base_url(case: Case) -> Optional[str]:
    p = (case.viseme_shapes_public_path or "").strip().strip("/")
    if not p:
        return None
    return f"/{p}/"


def _avatar_url(case: Case) -> Optional[str]:
    """Resolve the public URL for a case's avatar image."""
    if case.avatar_filename:
        return storage_service.get_public_url(case.avatar_filename)
    return None


def _case_to_out(case: Case) -> CaseOut:
    """Convert a Case ORM object to CaseOut schema."""
    return CaseOut(
        id=case.id,
        title=case.title,
        description=case.description,
        system_prompt=case.system_prompt,
        patient_name=case.patient_name,
        has_avatar=case.has_avatar,
        avatar_filename=case.avatar_filename,
        avatar_url=_avatar_url(case),
        voice_id=case.voice_id,
        scenario_type=case.scenario_type,
        status=case.status.value,
        created_by=case.created_by,
        creator_name=case.creator.display_name if case.creator else None,
        created_at=case.created_at,
        updated_at=case.updated_at,
        viseme_shapes_base_url=_viseme_shapes_base_url(case),
    )


def _case_to_student_out(case: Case) -> CaseOutStudent:
    """Convert a Case ORM object to CaseOutStudent schema (no system_prompt/voice_id)."""
    return CaseOutStudent(
        id=case.id,
        title=case.title,
        description=case.description,
        patient_name=case.patient_name,
        has_avatar=case.has_avatar,
        avatar_filename=case.avatar_filename,
        avatar_url=_avatar_url(case),
        scenario_type=case.scenario_type,
        status=case.status.value,
        created_by=case.created_by,
        creator_name=case.creator.display_name if case.creator else None,
        created_at=case.created_at,
        updated_at=case.updated_at,
        viseme_shapes_base_url=_viseme_shapes_base_url(case),
    )


def _case_to_list(case: Case) -> CaseListOut:
    """Convert a Case ORM object to CaseListOut schema."""
    return CaseListOut(
        id=case.id,
        title=case.title,
        description=case.description,
        patient_name=case.patient_name,
        has_avatar=case.has_avatar,
        avatar_filename=case.avatar_filename,
        avatar_url=_avatar_url(case),
        scenario_type=case.scenario_type,
        status=case.status.value,
        creator_name=case.creator.display_name if case.creator else None,
        created_at=case.created_at,
        updated_at=case.updated_at,
        viseme_shapes_base_url=_viseme_shapes_base_url(case),
    )


# ── Avatar library ──

@router.get("/avatars/library")
async def list_avatar_library(admin: User = Depends(require_admin)):
    """Return filenames and signed URLs for all images in the avatar library."""
    filenames = storage_service.list_images()
    # Use batch signed URLs for efficiency (single API call to Supabase)
    url_map = storage_service.get_signed_urls(filenames)
    images = [
        {"filename": f, "url": url_map.get(f, "")}
        for f in filenames
    ]
    return {"filenames": filenames, "images": images}


@router.post("/avatars/library")
async def upload_library_avatar(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
):
    """Upload a new image to the shared avatar library."""
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{file.content_type}' not allowed. Use JPG, PNG, or WebP.",
        )

    raw_name = file.filename if file.filename else "upload.png"
    safe_name = os.path.basename(raw_name)
    safe_name = re.sub(r'[^\w.\-]', '_', safe_name)
    content = await file.read()
    try:
        final_name = storage_service.upload_image(safe_name, content, file.content_type)
    except Exception as e:
        logger.error(f"Failed to upload avatar: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload image")

    logger.info(f"Admin '{admin.email}' uploaded library avatar '{final_name}'")
    return {"filename": final_name}


@router.delete("/avatars/library/{filename}")
async def delete_library_avatar(
    filename: str,
    admin: User = Depends(require_admin),
):
    """Delete an image from the shared avatar library."""
    try:
        storage_service.delete_image(filename)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    logger.info(f"Admin '{admin.email}' deleted library avatar '{filename}'")
    return {"deleted": filename}


# ── Admin: Full CRUD ──

@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
async def create_case(
    body: CaseCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new case (admin only)."""
    case = Case(
        title=body.title,
        description=body.description,
        system_prompt=body.system_prompt,
        patient_name=body.patient_name,
        has_avatar=body.has_avatar,
        avatar_filename=body.avatar_filename,
        voice_id=body.voice_id,
        scenario_type=body.scenario_type,
        status=CaseStatus(body.status),
        created_by=admin.id,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    logger.info(f"Admin '{admin.email}' created case '{case.title}' (id={case.id})")
    return _case_to_out(case)


@router.get("")
async def list_cases(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List cases. Admins see all, students see only published."""
    query = db.query(Case)
    if current_user.role == UserRole.STUDENT:
        query = query.filter(Case.status == CaseStatus.PUBLISHED)
    cases = query.order_by(Case.updated_at.desc()).offset(skip).limit(limit).all()
    return [_case_to_list(c) for c in cases]


@router.get("/{case_id}")
async def get_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full case details. Students can only access published cases."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    # Students can only see published cases
    if current_user.role == UserRole.STUDENT and case.status != CaseStatus.PUBLISHED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    if current_user.role == UserRole.STUDENT:
        return _case_to_student_out(case)
    return _case_to_out(case)


@router.patch("/{case_id}", response_model=CaseOut)
async def update_case(
    case_id: str,
    body: CaseUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update a case (admin only). Partial update — only provided fields change."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    update_data = body.model_dump(exclude_unset=True)
    if "status" in update_data:
        update_data["status"] = CaseStatus(update_data["status"])

    for key, value in update_data.items():
        setattr(case, key, value)

    db.commit()
    db.refresh(case)

    logger.info(f"Admin '{admin.email}' updated case '{case.title}' (id={case.id})")
    return _case_to_out(case)


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a case (admin only)."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    # Delete associated practice sessions first (in case DB lacks CASCADE)
    db.query(PracticeSession).filter_by(case_id=case_id).delete()

    # Clean up avatar file if it exists
    if case.avatar_filename:
        try:
            storage_service.delete_image(case.avatar_filename)
        except Exception:
            pass  # non-fatal — still delete the case

    gen_dir = _PUBLIC / "generated" / "cases" / case_id
    if gen_dir.is_dir():
        try:
            shutil.rmtree(gen_dir, ignore_errors=True)
        except Exception:
            pass

    title = case.title
    db.delete(case)
    db.commit()
    logger.info(f"Admin '{admin.email}' deleted case '{title}' (id={case_id})")


@router.post("/{case_id}/avatar", response_model=CaseOut)
async def upload_avatar(
    case_id: str,
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Upload an avatar image for a case (admin only)."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    # Validate file type
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{file.content_type}' not allowed. Use JPG, PNG, or WebP.",
        )

    # Remove old avatar if exists
    if case.avatar_filename:
        try:
            storage_service.delete_image(case.avatar_filename)
        except Exception:
            pass

    # Save new avatar — sanitize the extension from the uploaded filename
    raw_name = os.path.basename(file.filename) if file.filename else "upload.jpg"
    sanitized_name = re.sub(r'[^\w.\-]', '_', raw_name)
    ext = sanitized_name.split(".")[-1] if "." in sanitized_name else "jpg"
    target_name = f"{case.id}.{ext}"
    content = await file.read()
    filename = storage_service.upload_image(target_name, content, file.content_type)

    case.avatar_filename = filename
    case.has_avatar = True
    db.commit()
    db.refresh(case)

    logger.info(f"Avatar uploaded for case '{case.title}' (id={case.id})")
    return _case_to_out(case)


@router.post("/{case_id}/viseme-reference", response_model=CaseOut)
async def upload_viseme_reference(
    case_id: str,
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Save reference A.png for HF viseme generation (public/generated/cases/{id}/shapes/A.png)."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{file.content_type}' not allowed. Use JPG, PNG, or WebP.",
        )

    raw = await file.read()
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file.",
        )

    out_dir = _PUBLIC / "generated" / "cases" / case_id / "shapes"
    out_dir.mkdir(parents=True, exist_ok=True)
    a_path = out_dir / "A.png"
    img.save(a_path, format="PNG")

    logger.info("Viseme reference A.png saved for case %s at %s", case_id, a_path)
    return _case_to_out(case)


@router.post("/{case_id}/publish", response_model=CaseOut)
async def publish_case(
    case_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Publish a draft case (admin only)."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case.status = CaseStatus.PUBLISHED
    db.commit()
    db.refresh(case)

    logger.info(f"Case '{case.title}' published by '{admin.email}'")
    return _case_to_out(case)


@router.post("/{case_id}/unpublish", response_model=CaseOut)
async def unpublish_case(
    case_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Unpublish a case back to draft (admin only)."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    case.status = CaseStatus.DRAFT
    db.commit()
    db.refresh(case)

    logger.info(f"Case '{case.title}' unpublished by '{admin.email}'")
    return _case_to_out(case)
