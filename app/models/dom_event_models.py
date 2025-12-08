from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal, Any
from datetime import datetime


class BoundingBox(BaseModel):
    """Bounding box coordinates for UI elements"""
    x: float
    y: float
    width: float
    height: float


class EventTarget(BaseModel):
    """Target element information for DOM events"""
    tag: str
    id: Optional[str] = None
    classes: List[str] = Field(default_factory=list)
    text: Optional[str] = None
    selector: str
    bbox: BoundingBox
    attributes: Dict[str, str] = Field(default_factory=dict)
    type: Optional[str] = None  # For inputs: 'text', 'email', 'password', etc.
    name: Optional[str] = None  # For inputs: name attribute


class ScrollPosition(BaseModel):
    """Scroll position coordinates"""
    x: float
    y: float


class Viewport(BaseModel):
    """Viewport dimensions"""
    width: int
    height: int


class EventMetadata(BaseModel):
    """Metadata associated with DOM events"""
    url: str
    viewport: Viewport
    scrollPosition: Optional[ScrollPosition] = None


class InteractionEvent(BaseModel):
    """Individual DOM interaction event"""
    timestamp: int  # Milliseconds since recording start
    type: Literal["click", "type", "focus", "blur", "scroll", "step_change"]
    target: Optional[EventTarget] = None  # None for scroll/step_change events
    value: Optional[str] = None  # For input events: current field value
    metadata: EventMetadata


class RecordingSession(BaseModel):
    """Complete recording session with all events"""
    sessionId: str
    startTime: int  # Unix timestamp in milliseconds
    endTime: int  # Unix timestamp in milliseconds
    url: str
    viewport: Viewport
    events: List[InteractionEvent]
    videoPath: Optional[str] = None
    audioPath: Optional[str] = None
    processedAt: Optional[datetime] = None


class FrontendInstruction(BaseModel):
    """Instruction for frontend to apply visual effects"""
    timestamp: int  # Milliseconds since recording start
    action: Literal["click", "type", "focus", "blur", "scroll", "step_change"]
    target: Optional[Dict[str, Any]] = None  # Target element info for frontend
    value: Optional[str] = None  # For input events
    bbox: Optional[BoundingBox] = None  # For visual highlighting
    selector: Optional[str] = None  # CSS selector for element targeting
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)  # Confidence score


class ProcessRecordingResponse(BaseModel):
    """Response from processing recording session"""
    sessionId: str
    instructions: List[FrontendInstruction]
    metadata: Dict[str, Any] = Field(default_factory=dict)