"""App settings routes — global prompt and other admin-configurable settings."""
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from dependencies import require_admin, get_current_user
from models.db_models import User, AppSettings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])

GLOBAL_PROMPT_KEY = "global_prompt"


class GlobalPromptBody(BaseModel):
    prompt: str


class GlobalPromptOut(BaseModel):
    prompt: str


def get_global_prompt(db: Session) -> str:
    """Helper used by other modules (e.g. WebSocket) to fetch the global prompt."""
    row = db.query(AppSettings).filter(AppSettings.key == GLOBAL_PROMPT_KEY).first()
    return row.value if row else ""


@router.get("/global-prompt", response_model=GlobalPromptOut)
async def read_global_prompt(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get the current global prompt (admin only)."""
    return GlobalPromptOut(prompt=get_global_prompt(db))


@router.put("/global-prompt", response_model=GlobalPromptOut)
async def update_global_prompt(
    body: GlobalPromptBody,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Set or update the global prompt (admin only)."""
    row = db.query(AppSettings).filter(AppSettings.key == GLOBAL_PROMPT_KEY).first()
    if row:
        row.value = body.prompt
    else:
        row = AppSettings(key=GLOBAL_PROMPT_KEY, value=body.prompt)
        db.add(row)
    db.commit()
    logger.info(f"Admin '{admin.email}' updated global prompt ({len(body.prompt)} chars)")
    return GlobalPromptOut(prompt=body.prompt)
