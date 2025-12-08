"""
Service to generate synced narration using RAG context from DOM events
and raw user transcript. Uses Gemini to create narration that matches
the timing and actions from screen recordings.
"""
import google.generativeai as genai
from typing import List, Dict, Optional
from dotenv import load_dotenv
import os
import re
from app.models.dom_event_models import RecordingSession
from app.services.rag_service import build_rag_context_from_events, build_timeline_context, extract_ui_elements_summary

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")


def clean_output(text: str) -> str:
    """Clean and normalize output text."""
    if not text:
        return ""
    
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([.,!?])", r"\1", text)
    
    return text.strip()


def generate_synced_narration(
    raw_text: str,
    session: RecordingSession
) -> Dict[str, any]:
    """
    Generate synced product demo narration using RAG context from DOM events.
    
    Args:
        raw_text: Raw user transcript/narration
        session: RecordingSession with DOM events for context
        
    Returns:
        Dictionary with synced narration and metadata
    """
    # Build RAG context from DOM events
    rag_context = build_rag_context_from_events(session)
    timeline = build_timeline_context(session.events)
    ui_summary = extract_ui_elements_summary(session.events)
    
    # Create comprehensive prompt with context
    prompt = f"""
You are an AI that creates professional product demo narration synchronized with screen recordings.

CONTEXT FROM SCREEN RECORDING (DOM Events):
{rag_context}

UI ELEMENTS INTERACTED WITH:
{ui_summary}

TIMELINE OF ACTIONS:
{_format_timeline(timeline)}

RAW USER TRANSCRIPT:
{raw_text}

TASK:
Generate a clean, professional product demo narration that:
1. Syncs with the actions shown in the screen recording (use the timeline above)
2. Describes what the user is doing at each step
3. Maintains the natural flow from the raw transcript
4. Adds professional polish while keeping the original intent
5. References specific UI elements and actions from the context
6. Matches the timing and sequence of interactions

OUTPUT RULES:
- Single continuous paragraph (no line breaks)
- Use present tense to describe actions ("Click the button" not "Clicked")
- Reference specific UI elements when mentioned in context
- Keep narration concise and professional
- Maintain similar length to raw transcript (±20%)
- NO newline characters
- Add proper punctuation
- Remove filler words (um, uh, like, etc.)

SYNCED NARRATION:
"""
    
    try:
        response = model.generate_content(prompt)
        synced_narration = clean_output(response.text)
        
        return {
            "synced_narration": synced_narration,
            "raw_text": raw_text,
            "rag_context_used": True,
            "timeline_events": timeline["significant_events"],
            "total_dom_events": len(session.events),
            "session_id": session.sessionId
        }
        
    except Exception as e:
        return {
            "synced_narration": f"Error generating synced narration: {str(e)}",
            "raw_text": raw_text,
            "rag_context_used": True,
            "error": str(e)
        }


def _format_timeline(timeline: Dict) -> str:
    """Format timeline for prompt."""
    if not timeline.get("timeline"):
        return "No significant actions recorded."
    
    lines = []
    for item in timeline["timeline"]:
        lines.append(f"  {item['timestamp_seconds']:.1f}s: {item['description']}")
    
    return "\n".join(lines)


def generate_step_by_step_narration(
    raw_text: str,
    session: RecordingSession
) -> Dict[str, any]:
    """
    Generate narration broken down by steps, synced with DOM events.
    Useful for creating step-by-step product demo scripts.
    
    Args:
        raw_text: Raw user transcript
        session: RecordingSession with DOM events
        
    Returns:
        Dictionary with step-by-step narration
    """
    rag_context = build_rag_context_from_events(session)
    timeline = build_timeline_context(session.events)
    
    prompt = f"""
You are an AI that creates step-by-step product demo narration synchronized with screen recordings.

CONTEXT FROM SCREEN RECORDING:
{rag_context}

TIMELINE OF ACTIONS:
{_format_timeline(timeline)}

RAW USER TRANSCRIPT:
{raw_text}

TASK:
Generate step-by-step narration where each step corresponds to a logical action group from the screen recording.
Each step should:
1. Have a clear action description
2. Reference specific UI elements from the context
3. Match the timing from the timeline
4. Use the raw transcript as inspiration for natural language

OUTPUT FORMAT:
Step 1: [narration for first action group]
Step 2: [narration for second action group]
...

Each step should be a single sentence or short paragraph describing what happens in that step.
"""
    
    try:
        response = model.generate_content(prompt)
        step_narration = response.text.strip()
        
        # Parse steps if possible
        steps = _parse_steps(step_narration)
        
        return {
            "step_by_step": step_narration,
            "parsed_steps": steps,
            "raw_text": raw_text,
            "rag_context_used": True,
            "session_id": session.sessionId
        }
        
    except Exception as e:
        return {
            "step_by_step": f"Error: {str(e)}",
            "raw_text": raw_text,
            "error": str(e)
        }


def _parse_steps(narration: str) -> List[Dict]:
    """Parse step-by-step narration into structured format."""
    steps = []
    lines = narration.split("\n")
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Try to extract step number and content
        match = re.match(r"Step\s+(\d+):\s*(.+)", line, re.IGNORECASE)
        if match:
            steps.append({
                "step_number": int(match.group(1)),
                "narration": match.group(2).strip()
            })
        elif line and not line.startswith("Step"):
            # If no step number, treat as continuation
            if steps:
                steps[-1]["narration"] += " " + line
    
    return steps

