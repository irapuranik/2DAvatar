"""Assignment routes — admin assigns cases to students with optional due dates."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from dependencies import require_admin, get_current_user
from models.db_models import User, UserRole, Case, CaseAssignment, AssignmentStatus
from models.api_schemas import AssignmentCreate, AssignmentUpdate, AssignmentOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/assignments", tags=["assignments"])


def _assignment_to_out(a: CaseAssignment) -> AssignmentOut:
    """Convert a CaseAssignment ORM object to the API response schema."""
    return AssignmentOut(
        id=a.id,
        student_id=a.student_id,
        case_id=a.case_id,
        assigned_by=a.assigned_by,
        due_date=a.due_date,
        status=a.status.value if isinstance(a.status, AssignmentStatus) else a.status,
        completed_at=a.completed_at,
        created_at=a.created_at,
        student_email=a.student.email if a.student else None,
        student_name=a.student.display_name if a.student else None,
        case_title=a.case.title if a.case else None,
    )


@router.get("", response_model=list[AssignmentOut])
async def list_assignments(
    case_id: str | None = Query(None),
    student_id: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List assignments, optionally filtered by case or student (admin only)."""
    q = db.query(CaseAssignment)
    if case_id:
        q = q.filter(CaseAssignment.case_id == case_id)
    if student_id:
        q = q.filter(CaseAssignment.student_id == student_id)
    assignments = q.order_by(CaseAssignment.created_at.desc()).offset(skip).limit(limit).all()
    return [_assignment_to_out(a) for a in assignments]


@router.post("", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    body: AssignmentCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Assign a case to a student (admin only)."""
    # Validate student exists and is a student
    student = db.query(User).filter(User.id == body.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Validate case exists
    case = db.query(Case).filter(Case.id == body.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Check for duplicate
    existing = db.query(CaseAssignment).filter_by(
        student_id=body.student_id, case_id=body.case_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Case already assigned to this student")

    assignment = CaseAssignment(
        student_id=body.student_id,
        case_id=body.case_id,
        assigned_by=admin.id,
        due_date=body.due_date,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    logger.info(f"Admin '{admin.email}' assigned case '{case.title}' to student '{student.email}'")
    return _assignment_to_out(assignment)


@router.post("/bulk", response_model=list[AssignmentOut], status_code=status.HTTP_201_CREATED)
async def bulk_assign(
    body: list[AssignmentCreate],
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Assign a case to multiple students at once (admin only)."""
    results = []
    for item in body:
        existing = db.query(CaseAssignment).filter_by(
            student_id=item.student_id, case_id=item.case_id
        ).first()
        if existing:
            continue  # Skip duplicates silently in bulk

        assignment = CaseAssignment(
            student_id=item.student_id,
            case_id=item.case_id,
            assigned_by=admin.id,
            due_date=item.due_date,
        )
        db.add(assignment)
        results.append(assignment)

    db.commit()
    for a in results:
        db.refresh(a)
    return [_assignment_to_out(a) for a in results]


@router.patch("/{assignment_id}", response_model=AssignmentOut)
async def update_assignment(
    assignment_id: str,
    body: AssignmentUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update an assignment's due date or status (admin only)."""
    assignment = db.query(CaseAssignment).filter(CaseAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if body.due_date is not None:
        assignment.due_date = body.due_date
    if body.status is not None:
        assignment.status = AssignmentStatus(body.status)
        if body.status == "completed" and not assignment.completed_at:
            assignment.completed_at = datetime.now(timezone.utc)
        elif body.status != "completed":
            assignment.completed_at = None

    db.commit()
    db.refresh(assignment)
    return _assignment_to_out(assignment)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Remove an assignment (admin only)."""
    assignment = db.query(CaseAssignment).filter(CaseAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(assignment)
    db.commit()


@router.get("/my", response_model=list[AssignmentOut])
async def my_assignments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current student's assignments."""
    assignments = (
        db.query(CaseAssignment)
        .filter(CaseAssignment.student_id == current_user.id)
        .order_by(CaseAssignment.due_date.asc().nullslast(), CaseAssignment.created_at.desc())
        .all()
    )
    return [_assignment_to_out(a) for a in assignments]
