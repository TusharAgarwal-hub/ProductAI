from pydantic import BaseModel
from typing import Optional
from app.models.dom_event_models import RecordingSession


class ProductTextRequest(BaseModel):
    text: str


class SyncedNarrationRequest(BaseModel):
    """Request model for generating synced narration with DOM events context"""
    raw_text: str
    session: RecordingSession
    narration_type: Optional[str] = "continuous"  # "continuous" or "step_by_step"
