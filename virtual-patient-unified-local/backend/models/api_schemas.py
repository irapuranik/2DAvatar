"""Pydantic schemas for API request/response validation."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Auth ──

class UserOut(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str = Field(..., min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Cases ──

class CaseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    system_prompt: str = Field(..., min_length=1)
    patient_name: Optional[str] = None
    has_avatar: bool = False
    avatar_filename: Optional[str] = None
    voice_id: Optional[str] = None
    scenario_type: str = "custom"
    status: str = Field(default="draft", pattern="^(draft|published)$")


class CaseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    patient_name: Optional[str] = None
    has_avatar: Optional[bool] = None
    avatar_filename: Optional[str] = None
    voice_id: Optional[str] = None
    scenario_type: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(draft|published)$")


class CaseOut(BaseModel):
    """Case detail for admins; viseme_shapes_base_url is set when HF visemes were generated for this case."""

    id: str
    title: str
    description: Optional[str]
    system_prompt: str
    patient_name: Optional[str]
    has_avatar: bool
    avatar_filename: Optional[str]
    avatar_url: Optional[str] = None
    voice_id: Optional[str]
    scenario_type: str
    status: str
    created_by: str
    creator_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    viseme_shapes_base_url: Optional[str] = None

    model_config = {"from_attributes": True}


class CaseOutStudent(BaseModel):
    """Case detail view for students — no system_prompt or voice_id."""
    id: str
    title: str
    description: Optional[str]
    patient_name: Optional[str]
    has_avatar: bool
    avatar_filename: Optional[str]
    avatar_url: Optional[str] = None
    scenario_type: str
    status: str
    created_by: str
    creator_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    viseme_shapes_base_url: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Assignments ──

class AssignmentCreate(BaseModel):
    student_id: str
    case_id: str
    due_date: Optional[datetime] = None


class AssignmentUpdate(BaseModel):
    due_date: Optional[datetime] = None
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed)$")


class AssignmentOut(BaseModel):
    id: str
    student_id: str
    case_id: str
    assigned_by: str
    due_date: Optional[datetime]
    status: str
    completed_at: Optional[datetime]
    created_at: datetime
    student_email: Optional[str] = None
    student_name: Optional[str] = None
    case_title: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Practice Sessions ──

class PracticeSessionOut(BaseModel):
    id: str
    user_id: str
    case_id: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PracticeSessionUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(not_started|in_progress|submitted)$")


class CaseListOut(BaseModel):
    """Lighter version for list views — no system_prompt."""
    id: str
    title: str
    description: Optional[str]
    patient_name: Optional[str]
    has_avatar: bool
    avatar_filename: Optional[str] = None
    avatar_url: Optional[str] = None
    scenario_type: str
    status: str
    creator_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    viseme_shapes_base_url: Optional[str] = None

    model_config = {"from_attributes": True}
