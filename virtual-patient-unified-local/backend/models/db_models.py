"""SQLAlchemy ORM models for AIMII."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Enum as SAEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    STUDENT = "student"


class CaseStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class User(Base):
    """App user — local auth (password_hash) or legacy Supabase-synced rows."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False, default=UserRole.STUDENT)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    cases_created: Mapped[List["Case"]] = relationship(back_populates="creator", lazy="selectin")


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Patient persona config
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    patient_name: Mapped[str] = mapped_column(String(200), nullable=True)

    # Avatar is optional — cases can be text/voice-only
    has_avatar: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar_filename: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # When set (e.g. generated/cases/{id}/shapes), 2D viseme PNGs are under frontend public/; practice uses this URL prefix.
    viseme_shapes_public_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Voice config
    voice_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Scenario preset (angry-parent, rude-patient, anxious-patient, custom)
    scenario_type: Mapped[str] = mapped_column(String(50), default="custom")

    # Publishing
    status: Mapped[CaseStatus] = mapped_column(SAEnum(CaseStatus), default=CaseStatus.DRAFT)

    # Metadata
    created_by: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    creator: Mapped["User"] = relationship(back_populates="cases_created", lazy="selectin")
    practice_sessions: Mapped[List["PracticeSession"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", lazy="selectin",
    )


class PracticeStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"


class AssignmentStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class CaseAssignment(Base):
    """Tracks which cases are assigned to which students, with due dates and completion."""
    __tablename__ = "case_assignments"
    __table_args__ = (UniqueConstraint("student_id", "case_id", name="uq_student_case_assignment"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    student_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(32), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[AssignmentStatus] = mapped_column(
        SAEnum(AssignmentStatus), default=AssignmentStatus.PENDING, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    student: Mapped["User"] = relationship(foreign_keys=[student_id], lazy="selectin")
    case: Mapped["Case"] = relationship(lazy="selectin")
    assigner: Mapped["User"] = relationship(foreign_keys=[assigned_by], lazy="selectin")


class AppSettings(Base):
    """Key-value store for app-wide settings (e.g. global prompt)."""
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class PracticeSession(Base):
    __tablename__ = "practice_sessions"
    __table_args__ = (UniqueConstraint("user_id", "case_id", name="uq_user_case"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(32), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_history: Mapped[str] = mapped_column(Text, default="[]")  # JSON-serialized list of {role, content}
    status: Mapped[PracticeStatus] = mapped_column(
        SAEnum(PracticeStatus, values_callable=lambda x: [e.value for e in x]),
        default=PracticeStatus.NOT_STARTED, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    case: Mapped["Case"] = relationship(back_populates="practice_sessions")
