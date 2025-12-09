"""
Script Generation Service - RAG-based product demo script generation.

This service combines:
1. Raw transcript text
2. Word-level timing data from Deepgram (for gap detection and sync)
3. DOM events (for understanding user actions)

To generate a production-ready script that can be converted to audio.
"""
import google.generativeai as genai
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import os
import re
from app.models.dom_event_models import RecordingSession
from app.services.rag_service import (
    build_rag_context_from_events,
    build_timeline_context,
    extract_ui_elements_summary,
)

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash-lite")


def analyze_word_timings(words: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze word-level timing data from Deepgram to identify gaps, pauses, and speaking patterns.
    """
    print(f"[Timing Analysis] Starting analysis of {len(words)} words...")

    if not words:
        print(f"[Timing Analysis] ⚠️  No words provided, returning empty analysis")
        return {
            "total_duration": 0,
            "gaps": [],
            "average_gap": 0,
            "speaking_segments": [],
            "low_confidence_words": [],
            "filler_words": [],
            "speaking_rate": 0,
            "has_timing_data": False,
        }

    gaps = []
    speaking_segments: List[Dict[str, Any]] = []
    low_confidence_words = []
    filler_words = []
    current_segment = None

    # Common filler words to detect
    FILLER_PATTERNS = [
        "um",
        "uh",
        "like",
        "you know",
        "so",
        "well",
        "actually",
        "basically",
    ]

    print(f"[Timing Analysis] Analyzing gaps, fillers, and confidence...")

    # Analyze gaps between words and detect issues
    for i in range(len(words) - 1):
        current = words[i]
        next_word = words[i + 1]

        current_end = current.get("end", 0)
        next_start = next_word.get("start", 0)

        gap_duration = next_start - current_end

        # Detect low confidence words
        if current.get("confidence", 1.0) < 0.8:
            low_confidence_words.append(
                {
                    "word": current.get("word", ""),
                    "punctuated_word": current.get("punctuated_word", ""),
                    "confidence": current.get("confidence", 0),
                    "position": i,
                    "start": current.get("start", 0),
                }
            )
            print(
                f"[Timing Analysis]   ⚠️  Low confidence word detected: "
                f"'{current.get('word')}' (confidence: {current.get('confidence', 0):.2f})"
            )

        # Detect filler words
        word_lower = current.get("word", "").lower()
        if word_lower in FILLER_PATTERNS:
            filler_words.append(
                {
                    "word": current.get("word", ""),
                    "position": i,
                    "start": current.get("start", 0),
                }
            )
            print(
                f"[Timing Analysis]   🗑️  Filler word detected: "
                f"'{current.get('word')}' at {current.get('start', 0):.2f}s"
            )

        # Detect repetitions (e.g., "the the", "as as")
        if current.get("word", "") == next_word.get("word", ""):
            filler_words.append(
                {
                    "word": f"{current.get('word', '')} (repeated)",
                    "position": i,
                    "start": current.get("start", 0),
                    "type": "repetition",
                }
            )
            print(
                f"[Timing Analysis]   🔁 Repetition detected: "
                f"'{current.get('word')} {next_word.get('word')}' at {current.get('start', 0):.2f}s"
            )

        # Identify significant gaps (> 0.3s indicates pause)
        if gap_duration > 0.3:
            gap_type = (
                "major"
                if gap_duration > 0.8
                else "natural"
                if gap_duration > 0.5
                else "minor"
            )

            gaps.append(
                {
                    "after_word": current.get(
                        "punctuated_word", current.get("word", "")
                    ),
                    "before_word": next_word.get(
                        "punctuated_word", next_word.get("word", "")
                    ),
                    "start": current_end,
                    "end": next_start,
                    "duration": gap_duration,
                    "position": i,
                    "type": gap_type,
                }
            )

            print(
                f"[Timing Analysis]   ⏸️  {gap_type.upper()} gap detected: "
                f"{gap_duration:.2f}s after "
                f"'{current.get('punctuated_word', current.get('word'))}' "
                f"at {current_end:.2f}s"
            )

            # End current speaking segment
            if current_segment:
                current_segment["end"] = current_end
                current_segment["word_count"] = len(current_segment["words"])
                speaking_segments.append(current_segment)
                print(
                    f"[Timing Analysis]   📊 Speaking segment ended: "
                    f"{current_segment['word_count']} words, "
                    f"{current_segment['end'] - current_segment['start']:.2f}s"
                )
                current_segment = None
        else:
            # Continue or start speaking segment
            if not current_segment:
                current_segment = {
                    "start": current.get("start", 0),
                    "end": current_end,
                    "words": [],
                }
                print(
                    f"[Timing Analysis]   ▶️  New speaking segment started "
                    f"at {current.get('start', 0):.2f}s"
                )
            current_segment["words"].append(current)
            current_segment["end"] = current_end

    # Add final segment
    if current_segment:
        current_segment["end"] = words[-1].get("end", 0)
        current_segment["word_count"] = len(current_segment["words"])
        speaking_segments.append(current_segment)
        print(
            f"[Timing Analysis]   📊 Final speaking segment: "
            f"{current_segment['word_count']} words, "
            f"{current_segment['end'] - current_segment['start']:.2f}s"
        )

    # Calculate statistics
    total_duration = words[-1].get("end", 0) - words[0].get("start", 0)
    average_gap = sum(g["duration"] for g in gaps) / len(gaps) if gaps else 0
    speaking_rate = len(words) / total_duration if total_duration > 0 else 0

    print(f"[Timing Analysis] --->Analysis complete:")
    print(f"[Timing Analysis]   - Total duration: {total_duration:.2f}s")
    print(f"[Timing Analysis]   - Total words: {len(words)}")
    print(f"[Timing Analysis]   - Speaking rate: {speaking_rate:.2f} words/sec")
    print(f"[Timing Analysis]   - Gaps detected: {len(gaps)}")
    print(f"[Timing Analysis]   - Filler words: {len(filler_words)}")
    print(f"[Timing Analysis]   - Low confidence: {len(low_confidence_words)}")
    print(f"[Timing Analysis]   - Speaking segments: {len(speaking_segments)}")

    return {
        "total_duration": total_duration,
        "total_words": len(words),
        "gaps": gaps,
        "average_gap": average_gap,
        "speaking_segments": speaking_segments,
        "num_gaps": len(gaps),
        "low_confidence_words": low_confidence_words,
        "filler_words": filler_words,
        "speaking_rate": speaking_rate,  # words per second
        "has_timing_data": True,
    }


def build_timing_context(timing_analysis: Dict[str, Any]) -> str:
    """
    Build human-readable context from timing analysis.
    """
    if not timing_analysis.get("has_timing_data"):
        return "No timing data available."

    context_parts = [
        f"Total Duration: {timing_analysis['total_duration']:.1f} seconds",
        f"Total Words: {timing_analysis['total_words']}",
        f"Speaking Rate: {timing_analysis['speaking_rate']:.2f} words/second",
        f"Speaking Segments: {len(timing_analysis['speaking_segments'])}",
        f"Identified Gaps: {timing_analysis['num_gaps']}",
        f"Average Gap Duration: {timing_analysis['average_gap']:.2f} seconds",
    ]

    # Add filler words detected
    if timing_analysis.get("filler_words"):
        context_parts.append("")  # Empty line
        context_parts.append(
            f"Filler Words Detected: {len(timing_analysis['filler_words'])}"
        )
        filler_list = [
            f"'{f['word']}'" for f in timing_analysis["filler_words"][:5]
        ]
        if filler_list:
            context_parts.append(f"  Examples: {', '.join(filler_list)}")

    # Add low confidence words
    if timing_analysis.get("low_confidence_words"):
        context_parts.append("")  # Empty line
        context_parts.append(
            f"Low Confidence Words: {len(timing_analysis['low_confidence_words'])}"
        )
        low_conf_list = [
            f"'{w['word']}' ({w['confidence']:.2f})"
            for w in timing_analysis["low_confidence_words"][:3]
        ]
        if low_conf_list:
            context_parts.append(f"  Examples: {', '.join(low_conf_list)}")

    # Add significant gaps
    if timing_analysis["gaps"]:
        context_parts.append("")  # Empty line
        context_parts.append("Significant Pauses/Gaps:")
        for i, gap in enumerate(timing_analysis["gaps"][:5], 1):
            gap_type = gap.get("type", "unknown")
            gap_info = (
                f"  Gap {i} ({gap_type}): after '{gap['after_word']}' "
                f"→ before '{gap['before_word']}' "
                f"({gap['duration']:.2f}s at {gap['start']:.1f}s)"
            )
            context_parts.append(gap_info)

    return "\n".join(context_parts)


def generate_product_script(
    raw_text: str,
    word_timings: List[Dict[str, Any]],
    session: Optional[RecordingSession] = None,
) -> Dict[str, Any]:
    """
    Generate production-ready script using RAG context from all three inputs.
    """
    print(f"\n[Script Generation] ===== STARTING SCRIPT GENERATION =====")
    print(f"[Script Generation] Raw text length: {len(raw_text)} characters")
    print(f"[Script Generation] Word timings: {len(word_timings)} words")
    print(f"[Script Generation] Session provided: {session is not None}")

    # 1. Analyze word timings
    print(f"\n[Script Generation] Step 1/4: Analyzing word timings...")
    timing_analysis = analyze_word_timings(word_timings)
    timing_context = build_timing_context(timing_analysis)
    print(f"[Script Generation] --->Timing analysis complete")

    # 2. Build RAG context from DOM events (if available)
    print(f"\n[Script Generation] Step 2/4: Building RAG context from DOM events...")
    dom_context = ""
    timeline_context = ""
    ui_elements = ""

    if session and session.events:
        print(
            f"[Script Generation]   - Building context from "
            f"{len(session.events)} DOM events..."
        )
        dom_context = build_rag_context_from_events(session)
        print(f"[Script Generation]   - Building timeline context...")
        timeline = build_timeline_context(session.events)
        timeline_context = _format_timeline(timeline)
        print(f"[Script Generation]   - Extracting UI elements...")
        ui_elements = extract_ui_elements_summary(session.events)
        print(f"[Script Generation] --->RAG context built successfully")
    else:
        print(
            f"[Script Generation]   ⚠️  No DOM events available, skipping RAG context"
        )

    # 3. Build prompt-safe contextual text (never put logic inside an f-string!)
    print(f"\n[Script Generation] Step 3/4: Building Gemini prompt...")

    # Convert everything to simple safe strings FOR the f-string below
    dom_text = str(dom_context or "No DOM events available").replace("\\", "\\\\")
    timeline_text = str(timeline_context or "").replace("\\", "\\\\")
    ui_text = str(ui_elements or "").replace("\\", "\\\\")
    raw_text_safe = str(raw_text).replace("\\", "\\\\")
    timing_context_safe = str(timing_context).replace("\\", "\\\\")

    # Build optional blocks
    ui_section = (
        f"UI ELEMENTS INTERACTED WITH:\n{ui_text}" if ui_text.strip() else ""
    )
    timeline_section = (
        f"TIMELINE OF ACTIONS:\n{timeline_text}" if timeline_text.strip() else ""
    )

    # Final text – ONLY simple {variables}, never conditions inside {}
    prompt = f"""
You are an AI that creates professional, production-ready product demo scripts.

You have access to THREE sources of information:

1. RAW TRANSCRIPT (from speech-to-text):
{raw_text_safe}

2. TIMING ANALYSIS (word-level timing with gaps and filler detection):
{timing_context_safe}

3. SCREEN RECORDING CONTEXT (DOM events showing user actions):
{dom_text}

{ui_section}

{timeline_section}

TASK:
Generate a clean, professional product demo script that:

1. Uses the raw transcript as the base
2. Syncs with timing gaps to create natural pacing
3. References actual UI actions (buttons, inputs, navigation)
4. Fills pauses with meaningful connecting narration
5. Maintains a polished professional tone
6. Removes filler words like "um", "uh", "like"
7. Outputs a clean, single-paragraph narration

OUTPUT RULES:
- Single continuous paragraph
- No newlines inside the script
- Present tense actions ("click the button")
- Reference UI elements when provided
- ±20% length tolerance versus original transcript
- Must be clear, natural, and professional

PRODUCTION-READY SCRIPT:
""".strip()

    print(f"[Script Generation]   - Prompt length: {len(prompt)} characters")
    print(f"[Script Generation] --->Prompt built")

    # 4. Generate script with Gemini
    print(f"\n[Script Generation] Step 4/4: Calling Gemini API...")
    try:
        print(f"[Script Generation]   - Sending request to Gemini...")
        response = model.generate_content(prompt)
        print(f"[Script Generation]   - Response received from Gemini")

        script = _clean_script_output(response.text)
        print(f"[Script Generation]   - Script cleaned and formatted")
        print(f"[Script Generation]   - Final script length: {len(script)} characters")

        print(f"\n[Script Generation] ===== SCRIPT GENERATION COMPLETE =====")
        print(
            f"[Script Generation] Generated script preview: "
            f"{script[:100]}..."
        )

        return {
            "script": script,
            "raw_text": raw_text,
            "timing_analysis": {
                "total_duration": timing_analysis["total_duration"],
                "total_words": timing_analysis["total_words"],
                "speaking_rate": timing_analysis["speaking_rate"],
                "num_gaps": timing_analysis["num_gaps"],
                "average_gap": timing_analysis["average_gap"],
                "num_filler_words": len(
                    timing_analysis.get("filler_words", [])
                ),
                "num_low_confidence": len(
                    timing_analysis.get("low_confidence_words", [])
                ),
                "has_timing_data": timing_analysis["has_timing_data"],
            },
            "dom_context_used": bool(session and session.events),
            "session_id": session.sessionId if session else None,
            "success": True,
        }

    except Exception as e:
        print(
            f"\n[Script Generation] ❌ ERROR during Gemini API call: {str(e)}"
        )
        import traceback

        traceback.print_exc()

        return {
            "script": f"Error generating script: {str(e)}",
            "raw_text": raw_text,
            "success": False,
            "error": str(e),
        }


def _clean_script_output(text: str) -> str:
    """Clean and normalize script output."""
    if not text:
        return ""

    # Remove markdown formatting if present
    text = re.sub(r"\*\*", "", text)
    text = re.sub(r"\*", "", text)

    # Remove newlines and extra spaces
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    # Fix punctuation spacing
    text = re.sub(r"\s+([.,!?])", r"\1", text)

    return text.strip()


def _format_timeline(timeline: Dict[str, Any]) -> str:
    """Format timeline for prompt."""
    if not timeline.get("timeline"):
        return "No significant actions recorded."

    lines = []
    for item in timeline["timeline"]:
        lines.append(f"  {item['timestamp_seconds']:.1f}s: {item['description']}")

    return "\n".join(lines)
