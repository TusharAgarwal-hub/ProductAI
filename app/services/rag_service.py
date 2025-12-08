"""
RAG (Retrieval-Augmented Generation) service for building context from DOM events.
This service processes DOM events to create structured context that helps Gemini
generate synced product demo narration.
"""
from typing import List, Dict
from app.models.dom_event_models import InteractionEvent, RecordingSession


def build_rag_context_from_events(session: RecordingSession) -> str:
    """
    Build RAG context from DOM events for Gemini to understand the screen recording.
    
    Args:
        session: RecordingSession with all DOM events
        
    Returns:
        Formatted context string describing the user's actions and UI interactions
    """
    context_parts = []
    
    # Add session metadata
    context_parts.append(f"Recording Session: {session.sessionId}")
    context_parts.append(f"URL: {session.url}")
    context_parts.append(f"Duration: {(session.endTime - session.startTime) / 1000:.1f} seconds")
    context_parts.append("")
    
    # Group events by steps
    steps = _group_events_into_steps(session.events)
    
    # Build context for each step
    for step_num, step in enumerate(steps, 1):
        step_context = _build_step_context(step_num, step)
        context_parts.append(step_context)
        context_parts.append("")
    
    return "\n".join(context_parts)


def _group_events_into_steps(events: List[InteractionEvent]) -> List[Dict]:
    """
    Group events into logical steps with timing information.
    """
    if not events:
        return []
    
    steps = []
    current_step = {
        "stepNumber": 1,
        "startTime": events[0].timestamp,
        "endTime": events[0].timestamp,
        "events": [events[0]]
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
                "events": [event]
            }
        else:
            current_step["events"].append(event)
            current_step["endTime"] = event.timestamp
    
    # Add final step
    if current_step["events"]:
        steps.append(current_step)
    
    return steps


def _build_step_context(step_num: int, step: Dict) -> str:
    """
    Build context description for a single step.
    """
    duration = (step["endTime"] - step["startTime"]) / 1000.0
    context_lines = [f"Step {step_num} (Duration: {duration:.1f}s):"]
    
    # Process events in chronological order
    for event in step["events"]:
        event_desc = _describe_event(event)
        if event_desc:
            timestamp_sec = event.timestamp / 1000.0
            context_lines.append(f"  [{timestamp_sec:.1f}s] {event_desc}")
    
    return "\n".join(context_lines)


def _describe_event(event: InteractionEvent) -> str:
    """
    Convert a DOM event into a human-readable description.
    """
    if event.type == "click":
        if event.target:
            if event.target.text:
                return f"Clicked on '{event.target.text}'"
            elif event.target.attributes.get("data-testid"):
                return f"Clicked on {event.target.attributes['data-testid']}"
            elif event.target.tag:
                return f"Clicked on {event.target.tag.lower()} element"
        return "Clicked"
    
    elif event.type == "type":
        if event.value:
            # Show what was typed (truncate long values)
            display_value = event.value[:50] + "..." if len(event.value) > 50 else event.value
            if event.target:
                if event.target.attributes.get("data-testid"):
                    return f"Typed '{display_value}' in {event.target.attributes['data-testid']}"
                elif event.target.type:
                    return f"Typed '{display_value}' in {event.target.type} field"
            return f"Typed '{display_value}'"
        return "Typed in input field"
    
    elif event.type == "focus":
        if event.target:
            if event.target.attributes.get("data-testid"):
                return f"Focused on {event.target.attributes['data-testid']}"
            elif event.target.type:
                return f"Focused on {event.target.type} input field"
        return "Focused on input field"
    
    elif event.type == "blur":
        return "Left input field"
    
    elif event.type == "scroll":
        if event.metadata.scrollPosition:
            return f"Scrolled to position ({event.metadata.scrollPosition.x}, {event.metadata.scrollPosition.y})"
        return "Scrolled page"
    
    elif event.type == "step_change":
        return "Page/UI state changed"
    
    return None


def extract_ui_elements_summary(events: List[InteractionEvent]) -> str:
    """
    Extract a summary of UI elements interacted with.
    Useful for understanding the interface structure.
    """
    elements = set()
    
    for event in events:
        if event.target:
            if event.target.text:
                elements.add(event.target.text)
            if event.target.attributes.get("data-testid"):
                elements.add(event.target.attributes["data-testid"])
            if event.target.attributes.get("aria-label"):
                elements.add(event.target.attributes["aria-label"])
    
    if elements:
        return f"UI Elements: {', '.join(sorted(elements))}"
    return "UI Elements: (none identified)"


def build_timeline_context(events: List[InteractionEvent]) -> Dict:
    """
    Build a timeline structure that can be used for syncing narration with actions.
    
    Returns:
        Dictionary with timeline information for each significant event
    """
    timeline = []
    
    for event in events:
        # Only include significant events (clicks, typing, step changes)
        if event.type in ["click", "type", "step_change"]:
            timeline.append({
                "timestamp": event.timestamp,
                "timestamp_seconds": event.timestamp / 1000.0,
                "action": event.type,
                "description": _describe_event(event)
            })
    
    return {
        "total_events": len(events),
        "significant_events": len(timeline),
        "timeline": timeline
    }

