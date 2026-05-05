"""Admin: generate B–H, X, blink PNGs from reference A.png (HF image-to-image)."""
from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from dependencies import require_admin
from models.db_models import Case, User
from services.viseme_generation_service import (
    ensure_case_shapes_dir,
    get_default_shapes_dir,
    run_full_viseme_generation,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/visemes", tags=["admin-visemes"])

_jobs_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def _merge_character_text(prompt: Optional[str], character_hint: str) -> str:
    parts = []
    if prompt and str(prompt).strip():
        parts.append(str(prompt).strip())
    if character_hint and str(character_hint).strip():
        parts.append(str(character_hint).strip())
    return ". ".join(parts) if parts else ""


class VisemeGenFromARequest(BaseModel):
    """Global shapes: writes under frontend-react/public/static/shapes/."""

    prompt: str = Field("", max_length=800, description="Primary character / style description for all visemes")
    character_hint: str = Field("", max_length=800, description="Additional hint merged with prompt")
    strength: Optional[float] = Field(
        None,
        ge=0.05,
        le=0.95,
        description="Img2img strength; lower = closer to A.png.",
    )
    generate_base_face_from_prompt: bool = Field(
        False,
        description="If true, text-to-image creates A.png from prompt+hint, then B…blink from that A (no upload).",
    )


class VisemeGenForCaseRequest(BaseModel):
    """Per-case shapes under public/generated/cases/{case_id}/shapes/; sets Case.viseme_shapes_public_path when done."""

    case_id: str = Field(..., min_length=8, max_length=64)
    prompt: str = Field("", max_length=800)
    character_hint: str = Field("", max_length=800)
    strength: Optional[float] = Field(None, ge=0.05, le=0.95)
    generate_base_face_from_prompt: bool = Field(
        False,
        description="If true, text-to-image creates A.png first; else use uploaded/copied A.png.",
    )


class VisemeGenStartResponse(BaseModel):
    job_id: str
    message: str


class VisemeGenJobStatus(BaseModel):
    job_id: str
    status: str
    created_at: str
    updated_at: str
    case_id: Optional[str] = None
    current_viseme: Optional[str] = None
    progress: Optional[str] = None
    written: Optional[list[str]] = None
    diagnostics: Optional[dict[str, Any]] = None
    error: Optional[str] = None


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_error_message(exc: BaseException) -> str:
    """Avoid empty UI messages (e.g. str(StopIteration) is '')."""
    s = str(exc).strip()
    return s if s else f"{type(exc).__name__}"


def _run_job(
    job_id: str,
    merged_hint: str,
    strength: Optional[float],
    case_id: Optional[str],
    generate_base_face_from_prompt: bool,
) -> None:
    def on_progress(name: str, step: int, total: int) -> None:
        with _jobs_lock:
            j = _jobs.get(job_id)
            if j:
                j["current_viseme"] = name
                j["progress"] = f"{step}/{total}"
                j["updated_at"] = _utc_iso()

    def on_diagnostic(payload: dict[str, Any]) -> None:
        with _jobs_lock:
            j = _jobs.get(job_id)
            if j:
                j["diagnostics"] = payload
                j["updated_at"] = _utc_iso()

    with _jobs_lock:
        j = _jobs.get(job_id)
        if j:
            j["status"] = "running"
            j["updated_at"] = _utc_iso()

    try:
        if case_id:
            shapes_dir = ensure_case_shapes_dir(case_id)
            written = run_full_viseme_generation(
                shapes_dir=shapes_dir,
                merged_prompt=merged_hint,
                strength=strength,
                generate_base_from_prompt=generate_base_face_from_prompt,
                use_copy_default_a_if_missing=not generate_base_face_from_prompt,
                on_progress=on_progress,
                on_diagnostic=on_diagnostic,
            )
            rel = f"generated/cases/{case_id}/shapes"
            db = SessionLocal()
            try:
                case = db.query(Case).filter(Case.id == case_id).first()
                if case:
                    case.viseme_shapes_public_path = rel
                    db.commit()
            finally:
                db.close()
        else:
            shapes_dir = get_default_shapes_dir()
            written = run_full_viseme_generation(
                shapes_dir=shapes_dir,
                merged_prompt=merged_hint,
                strength=strength,
                generate_base_from_prompt=generate_base_face_from_prompt,
                use_copy_default_a_if_missing=False,
                on_progress=on_progress,
                on_diagnostic=on_diagnostic,
            )

        with _jobs_lock:
            j = _jobs.get(job_id)
            if j:
                j["status"] = "completed"
                j["written"] = written
                j["current_viseme"] = None
                j["progress"] = None
                j["updated_at"] = _utc_iso()
    except Exception as e:
        logger.exception("Viseme job %s failed", job_id)
        with _jobs_lock:
            j = _jobs.get(job_id)
            if j:
                j["status"] = "failed"
                j["error"] = _job_error_message(e)
                j["updated_at"] = _utc_iso()


@router.post("/generate-from-reference-a", response_model=VisemeGenStartResponse)
async def start_generate_from_a(
    body: VisemeGenFromARequest,
    background_tasks: BackgroundTasks,
    _admin: User = Depends(require_admin),
) -> VisemeGenStartResponse:
    """
    Queue generation into **global** `public/static/shapes/` (A optional via text, then B…blink).
    """
    shapes = get_default_shapes_dir()
    merged = _merge_character_text(body.prompt, body.character_hint)
    if body.generate_base_face_from_prompt and not merged.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="generate_base_face_from_prompt requires a non-empty prompt and/or character_hint.",
        )
    if not body.generate_base_face_from_prompt and not (shapes / "A.png").is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing reference {shapes / 'A.png'}. Upload or enable generate_base_face_from_prompt.",
        )

    job_id = uuid.uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = {
            "status": "queued",
            "created_at": _utc_iso(),
            "updated_at": _utc_iso(),
            "case_id": None,
            "current_viseme": None,
            "progress": None,
            "written": None,
            "diagnostics": None,
            "error": None,
        }

    background_tasks.add_task(
        _run_job,
        job_id,
        merged,
        body.strength,
        None,
        body.generate_base_face_from_prompt,
    )

    return VisemeGenStartResponse(
        job_id=job_id,
        message="Poll GET /api/admin/visemes/jobs/{job_id} until completed or failed.",
    )


@router.post("/generate-for-case", response_model=VisemeGenStartResponse)
async def start_generate_for_case(
    body: VisemeGenForCaseRequest,
    background_tasks: BackgroundTasks,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> VisemeGenStartResponse:
    """
    Queue B…blink into `public/generated/cases/{case_id}/shapes/` from that folder's **A.png**
    (upload via `POST /api/cases/{id}/viseme-reference` or copied from global A on first run).
    On success, sets `viseme_shapes_public_path` so practice loads `/generated/cases/.../shapes/`.
    """
    case = db.query(Case).filter(Case.id == body.case_id).first()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    merged = _merge_character_text(body.prompt, body.character_hint)
    if body.generate_base_face_from_prompt and not merged.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="generate_base_face_from_prompt requires a non-empty prompt and/or character_hint.",
        )

    job_id = uuid.uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = {
            "status": "queued",
            "created_at": _utc_iso(),
            "updated_at": _utc_iso(),
            "case_id": body.case_id,
            "current_viseme": None,
            "progress": None,
            "written": None,
            "diagnostics": None,
            "error": None,
        }

    background_tasks.add_task(
        _run_job,
        job_id,
        merged,
        body.strength,
        body.case_id,
        body.generate_base_face_from_prompt,
    )

    return VisemeGenStartResponse(
        job_id=job_id,
        message="Poll GET /api/admin/visemes/jobs/{job_id} until completed or failed.",
    )


@router.get("/jobs/{job_id}", response_model=VisemeGenJobStatus)
async def get_job_status(job_id: str, _admin: User = Depends(require_admin)) -> VisemeGenJobStatus:
    with _jobs_lock:
        j = _jobs.get(job_id)
    if not j:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown job_id")
    return VisemeGenJobStatus(
        job_id=job_id,
        status=j["status"],
        created_at=j["created_at"],
        updated_at=j["updated_at"],
        case_id=j.get("case_id"),
        current_viseme=j.get("current_viseme"),
        progress=j.get("progress"),
        written=j.get("written"),
        diagnostics=j.get("diagnostics"),
        error=j.get("error"),
    )
