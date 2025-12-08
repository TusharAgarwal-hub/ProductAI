"""
Service to process DOM events and generate frontend instructions.
This service converts raw DOM events into structured instructions
that can be used by the frontend to apply visual effects and
by the RAG model for script generation.
"""
from typing import List, Dict, Optional
from app.models.dom_event_models import (
    RecordingSession,
    InteractionEvent,
    FrontendInstruction,
    ProcessRecordingResponse
)


def process_dom_events(session: RecordingSession) -> ProcessRecordingResponse:
    """
    Process DOM events and generate frontend instructions.
    
    Args:
        session: RecordingSession containing all DOM events
        
    Returns:
        ProcessRecordingResponse with structured instructions
    """
    instructions: List[FrontendInstruction] = []
    
    for event in session.events:
        instruction = convert_event_to_instruction(event)
        if instruction:
            instructions.append(instruction)
    
    # Add metadata about processing
    metadata = {
        "totalEvents": len(session.events),
        "instructionsGenerated": len(instructions),
        "duration": session.endTime - session.startTime,
        "url": session.url
    }
    
    return ProcessRecordingResponse(
        sessionId=session.sessionId,
        instructions=instructions,
        metadata=metadata
    )


def convert_event_to_instruction(event: InteractionEvent) -> Optional[FrontendInstruction]:
    """
    Convert a single DOM event to a frontend instruction.
    
    Args:
        event: InteractionEvent to convert
        
    Returns:
        FrontendInstruction or None if event should be skipped
    """
    # Skip scroll events that don't have significant movement
    if event.type == "scroll" and event.metadata.scrollPosition:
        # Only include scroll events with meaningful movement
        if event.metadata.scrollPosition.y == 0 and event.metadata.scrollPosition.x == 0:
            return None
    
    instruction = FrontendInstruction(
        timestamp=event.timestamp,
        action=event.type,
        value=event.value,
        selector=event.target.selector if event.target else None,
        bbox=event.target.bbox if event.target else None,
        confidence=1.0  # DOM events are 100% accurate
    )
    
    # Add target information for frontend
    if event.target:
        instruction.target = {
            "tag": event.target.tag,
            "id": event.target.id,
            "classes": event.target.classes,
            "text": event.target.text,
            "type": event.target.type,
            "name": event.target.name,
            "attributes": event.target.attributes
        }
    
    return instruction


def extract_text_from_events(events: List[InteractionEvent]) -> str:
    """
    Extract all text content from events for RAG model processing.
    This includes button text, input values, and other visible text.
    
    Args:
        events: List of interaction events
        
    Returns:
        Combined text content from all events
    """
    text_parts = []
    
    for event in events:
        if event.type == "click" and event.target and event.target.text:
            text_parts.append(f"Clicked: {event.target.text}")
        elif event.type == "type" and event.value:
            text_parts.append(f"Typed: {event.value}")
        elif event.type == "focus" and event.target:
            if event.target.text:
                text_parts.append(f"Focused: {event.target.text}")
            elif event.target.attributes.get("data-testid"):
                text_parts.append(f"Focused: {event.target.attributes['data-testid']}")
    
    return " ".join(text_parts)


def group_events_by_step(events: List[InteractionEvent]) -> List[Dict]:
    """
    Group events into logical steps based on timing and event types.
    Useful for RAG model to understand workflow stages.
    
    Args:
        events: List of interaction events
        
    Returns:
        List of step dictionaries with grouped events
    """
    if not events:
        return []
    
    steps = []
    current_step = {
        "stepNumber": 1,
        "startTime": events[0].timestamp,
        "endTime": events[0].timestamp,
        "events": [events[0]],
        "description": ""
    }
    
    # Threshold for step separation (2 seconds of inactivity)
    STEP_THRESHOLD_MS = 2000
    
    for i, event in enumerate(events[1:], 1):
        time_gap = event.timestamp - current_step["endTime"]
        
        # If there's a significant gap or step_change event, start new step
        if time_gap > STEP_THRESHOLD_MS or event.type == "step_change":
            # Finalize current step
            current_step["endTime"] = events[i-1].timestamp
            steps.append(current_step)
            
            # Start new step
            current_step = {
                "stepNumber": len(steps) + 1,
                "startTime": event.timestamp,
                "endTime": event.timestamp,
                "events": [event],
                "description": ""
            }
        else:
            current_step["events"].append(event)
            current_step["endTime"] = event.timestamp
    
    # Add final step
    if current_step["events"]:
        steps.append(current_step)
    
    return steps

