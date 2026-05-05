"""Practice session routes — student session status tracking, submit, reset, and admin transcripts."""
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, require_admin
from models.db_models import User, UserRole, Case, PracticeSession, PracticeStatus, CaseAssignment, AssignmentStatus
from models.api_schemas import PracticeSessionOut, PracticeSessionUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/practice", tags=["practice"])


def _session_to_out(s: PracticeSession) -> PracticeSessionOut:
    return PracticeSessionOut(
        id=s.id,
        user_id=s.user_id,
        case_id=s.case_id,
        status=s.status.value if isinstance(s.status, PracticeStatus) else s.status,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


@router.get("/my", response_model=list[PracticeSessionOut])
async def my_practice_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all practice sessions for the current student."""
    sessions = (
        db.query(PracticeSession)
        .filter(PracticeSession.user_id == current_user.id)
        .all()
    )
    return [_session_to_out(s) for s in sessions]


@router.patch("/{case_id}/status", response_model=PracticeSessionOut)
async def update_practice_status(
    case_id: str,
    body: PracticeSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a practice session's status (e.g. mark as in_progress)."""
    session = db.query(PracticeSession).filter_by(
        user_id=current_user.id, case_id=case_id
    ).first()

    if not session:
        # Auto-create if it doesn't exist yet
        session = PracticeSession(
            user_id=current_user.id,
            case_id=case_id,
            conversation_history="[]",
            status=PracticeStatus.NOT_STARTED,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    if body.status:
        session.status = PracticeStatus(body.status)
        db.commit()
        db.refresh(session)

    return _session_to_out(session)


@router.post("/{case_id}/submit", response_model=PracticeSessionOut)
async def submit_practice(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit/complete a practice session. Also marks the assignment as completed."""
    session = db.query(PracticeSession).filter_by(
        user_id=current_user.id, case_id=case_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Practice session not found")

    session.status = PracticeStatus.SUBMITTED
    db.commit()
    db.refresh(session)

    # Also mark the corresponding assignment as completed
    assignment = db.query(CaseAssignment).filter_by(
        student_id=current_user.id, case_id=case_id
    ).first()
    if assignment and assignment.status != AssignmentStatus.COMPLETED:
        assignment.status = AssignmentStatus.COMPLETED
        assignment.completed_at = datetime.now(timezone.utc)
        db.commit()

    logger.info(f"Student '{current_user.email}' submitted practice for case '{case_id}'")
    return _session_to_out(session)


@router.post("/{case_id}/reset", response_model=PracticeSessionOut)
async def reset_practice(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reset a practice session — clears conversation and sets status back to not_started."""
    session = db.query(PracticeSession).filter_by(
        user_id=current_user.id, case_id=case_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Practice session not found")

    session.conversation_history = "[]"
    session.status = PracticeStatus.NOT_STARTED
    db.commit()
    db.refresh(session)

    logger.info(f"Student '{current_user.email}' reset practice for case '{case_id}'")
    return _session_to_out(session)


# ── Admin transcript endpoints ──

@router.get("/admin/students")
async def list_students_with_sessions(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List students who have at least one submitted practice session."""
    # Get distinct user_ids that have submitted sessions
    submitted_sessions = (
        db.query(PracticeSession)
        .filter(PracticeSession.status == PracticeStatus.SUBMITTED)
        .all()
    )
    student_ids = list(set(s.user_id for s in submitted_sessions))
    students = db.query(User).filter(User.id.in_(student_ids)).all() if student_ids else []

    result = []
    for stu in students:
        session_count = sum(1 for s in submitted_sessions if s.user_id == stu.id)
        result.append({
            "id": stu.id,
            "email": stu.email,
            "display_name": stu.display_name,
            "submitted_count": session_count,
        })
    return result


@router.get("/admin/students/{student_id}/sessions")
async def list_student_sessions(
    student_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all practice sessions for a given student (admin view)."""
    sessions = (
        db.query(PracticeSession)
        .filter(PracticeSession.user_id == student_id)
        .order_by(PracticeSession.updated_at.desc())
        .all()
    )

    result = []
    for s in sessions:
        case = db.query(Case).filter(Case.id == s.case_id).first()
        history = json.loads(s.conversation_history) if s.conversation_history else []
        result.append({
            "id": s.id,
            "case_id": s.case_id,
            "case_title": case.title if case else "Unknown",
            "patient_name": case.patient_name if case else None,
            "status": s.status.value if isinstance(s.status, PracticeStatus) else s.status,
            "message_count": len(history),
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        })
    return result


@router.get("/admin/sessions/{session_id}/transcript")
async def get_transcript(
    session_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get the full conversation transcript for a practice session."""
    session = db.query(PracticeSession).filter(PracticeSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    case = db.query(Case).filter(Case.id == session.case_id).first()
    student = db.query(User).filter(User.id == session.user_id).first()
    history = json.loads(session.conversation_history) if session.conversation_history else []

    return {
        "session_id": session.id,
        "student_name": student.display_name if student else "Unknown",
        "student_email": student.email if student else "Unknown",
        "case_title": case.title if case else "Unknown",
        "patient_name": case.patient_name if case else None,
        "status": session.status.value if isinstance(session.status, PracticeStatus) else session.status,
        "messages": history,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


@router.get("/admin/sessions/{session_id}/transcript.txt")
async def download_transcript(
    session_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Download the transcript as a .txt file."""
    session = db.query(PracticeSession).filter(PracticeSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    case = db.query(Case).filter(Case.id == session.case_id).first()
    student = db.query(User).filter(User.id == session.user_id).first()
    history = json.loads(session.conversation_history) if session.conversation_history else []

    patient_name = case.patient_name if case and case.patient_name else "patient"
    student_name = student.display_name if student else "Student"

    # Build numbered format: 1::Coach:: message2::Partner:: message...
    parts = []
    for i, msg in enumerate(history, 1):
        role_label = "Coach" if msg.get("role") == "user" else "Partner"
        content = msg.get("content", "")
        parts.append(f"{i}::{role_label}:: {content}")
    text = "\n".join(parts)

    date_str = session.updated_at.strftime("%m-%d-%Y") if session.updated_at else "unknown"
    filename = f"transcript_{student_name}_{date_str}_{patient_name}.txt".replace(" ", "_")

    return PlainTextResponse(
        content=text,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
