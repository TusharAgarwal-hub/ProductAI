# RAG-Based Synced Narration Guide

## Overview

The backend now includes a RAG (Retrieval-Augmented Generation) system that uses DOM events from screen recordings as context to generate synced product demo narration. This allows Gemini to understand what's happening in the screen recording and create narration that matches the user's actions.

## Architecture

```
Raw Transcript + DOM Events → RAG Context → Gemini → Synced Narration → TTS → Audio
```

### Flow:

1. **Extension captures DOM events** → User interactions (clicks, typing, etc.)
2. **RAG Service builds context** → Converts DOM events into structured context (Future)
3. **Gemini generates narration** → Uses DOM events + raw transcript to create synced narration
4. **ElevenLabs converts to audio** → Text-to-speech with synced timing

## Components

### 1. RAG Service (`app/services/rag_service.py`)

Builds structured context from DOM events:

- **`build_rag_context_from_events()`** - Main function that creates context string
- **`build_timeline_context()`** - Creates timeline of significant actions
- **`extract_ui_elements_summary()`** - Summarizes UI elements interacted with
- **`_group_events_into_steps()`** - Groups events into logical steps
- **`_describe_event()`** - Converts DOM events to human-readable descriptions

**Example Context Output:**
```
Recording Session: session_123
URL: https://example.com/demo
Duration: 19.1 seconds

Step 1 (Duration: 6.5s):
  [0.0s] Focused on search-input
  [1.2s] Typed 'g' in search-input
  [2.1s] Typed 'go' in search-input
  [3.0s] Typed 'goo' in search-input
  [4.0s] Typed 'good' in search-input

Step 2 (Duration: 4.2s):
  [7.4s] Clicked on 'Roger'
  [9.5s] Clicked on 'Young adult woman...'
```

### 2. Synced Narration Service (`app/services/synced_narration_service.py`)

Uses RAG context to generate synced narration:

- **`generate_synced_narration()`** - Generates continuous narration synced with actions
- **`generate_step_by_step_narration()`** - Generates step-by-step narration
- Uses Gemini with comprehensive prompt including:
  - RAG context from DOM events
  - Timeline of actions
  - UI elements summary
  - Raw user transcript

### 3. API Endpoints

#### `/generate-synced-narration` (POST)

**Request:**
```json
{
  "raw_text": "um so I'm going to search for good voices and then click on Roger",
  "session": {
    "sessionId": "session_123",
    "startTime": 1764880934009,
    "endTime": 1764880953143,
    "url": "https://elevenlabs.io/app/default-voices",
    "viewport": {"width": 1536, "height": 695},
    "events": [
      {
        "timestamp": 10565,
        "type": "focus",
        "target": {
          "tag": "INPUT",
          "selector": "input[data-testid='voices-search-input']",
          "bbox": {"x": 309, "y": 80, "width": 857, "height": 40},
          "attributes": {"data-testid": "voices-search-input"},
          "type": "text"
        },
        "metadata": {
          "url": "https://elevenlabs.io/app/default-voices",
          "viewport": {"width": 1536, "height": 695}
        }
      },
      {
        "timestamp": 11833,
        "type": "type",
        "target": {...},
        "value": "g",
        "metadata": {...}
      }
    ]
  },
  "narration_type": "continuous"  // or "step_by_step"
}
```

**Response:**
```json
{
  "synced_narration": "I'm searching for good voices in the search input field. I type 'good' and then click on the Roger voice option to select it.",
  "raw_text": "um so I'm going to search for good voices and then click on Roger",
  "rag_context_used": true,
  "timeline_events": 5,
  "total_dom_events": 12,
  "session_id": "session_123"
}
```

#### `/generate-synced-narration-with-audio` (POST)

Same request format, but also generates audio:

**Response:**
```json
{
  "synced_narration": "...",
  "raw_text": "...",
  "rag_context_used": true,
  "audio_generated": true,
  "audio_size_bytes": 45678
}
```

## How RAG Works

### Step 1: Context Building

DOM events are processed to create structured context:

1. **Group events into steps** - Events are grouped by timing (2-second threshold)
2. **Describe each event** - Convert technical DOM events to human-readable actions
3. **Build timeline** - Create chronological timeline of significant actions
4. **Extract UI elements** - Identify buttons, inputs, and other UI components

### Step 2: Prompt Engineering

The RAG context is combined with the raw transcript in a comprehensive prompt:

```
CONTEXT FROM SCREEN RECORDING (DOM Events):
[Structured context showing what happened]

TIMELINE OF ACTIONS:
[Chronological list of actions with timestamps]

RAW USER TRANSCRIPT:
[User's raw narration]

TASK:
Generate narration that syncs with the actions...
```

### Step 3: Gemini Generation

Gemini uses the context to:
- Understand what UI elements were interacted with
- Match narration to the sequence of actions
- Reference specific elements mentioned in context
- Maintain natural flow from raw transcript
- Add professional polish

## Benefits

✅ **Accurate Sync** - Narration matches actual screen recording actions  
✅ **Context-Aware** - Understands UI elements and interactions  
✅ **Natural Language** - Maintains user's original intent  
✅ **Professional Output** - Polished narration ready for product demos  
✅ **Timeline Aware** - Can reference specific timestamps and actions  

## Usage Examples

### Example 1: Basic Synced Narration

```python
import requests

payload = {
    "raw_text": "I'm going to search for voices and pick one",
    "session": {
        # ... DOM events from extension
    },
    "narration_type": "continuous"
}

response = requests.post(
    "http://localhost:8000/generate-synced-narration",
    json=payload
)

result = response.json()
print(result["synced_narration"])
```

### Example 2: Step-by-Step Narration

```python
payload = {
    "raw_text": "First I search, then I click on a voice",
    "session": {
        # ... DOM events
    },
    "narration_type": "step_by_step"
}

response = requests.post(
    "http://localhost:8000/generate-synced-narration",
    json=payload
)

result = response.json()
# result["parsed_steps"] contains structured steps
```

### Example 3: End-to-End (Narration + Audio)

```python
payload = {
    "raw_text": "Let me show you how to use our voice search",
    "session": {
        # ... DOM events
    }
}

response = requests.post(
    "http://localhost:8000/generate-synced-narration-with-audio",
    json=payload
)

result = response.json()
# result contains both narration and audio metadata
```

## Integration with Frontend

The synced narration can be used with frontend instructions:

1. **Get instructions** from `/process-recording` endpoint
2. **Get synced narration** from `/generate-synced-narration` endpoint
3. **Sync playback**:
   - Play audio narration
   - Apply visual effects at timestamps from instructions
   - Highlight UI elements as mentioned in narration

## Timeline Sync

The RAG system creates a timeline that can be used for precise sync:

```python
timeline = build_timeline_context(session.events)
# Returns:
{
    "total_events": 12,
    "significant_events": 5,
    "timeline": [
        {
            "timestamp": 10565,
            "timestamp_seconds": 10.565,
            "action": "focus",
            "description": "Focused on search-input"
        },
        # ...
    ]
}
```

This timeline can be used to:
- Sync narration with video playback
- Trigger UI highlights at specific times
- Create interactive product demos

## Next Steps

1. **Enhance RAG Context** - Add more semantic understanding of UI patterns
2. **Improve Sync Accuracy** - Fine-tune timing between narration and actions
3. **Add Voice Selection** - Allow users to choose narration style/tone
4. **Multi-language Support** - Generate narration in different languages
5. **Export Formats** - Support SRT/VTT subtitle files for video sync

## Testing

Test the endpoint with your example JSON file:

```bash
# Create test payload
python -c "
import json

# Load your example session
with open('recording_session_1764880953143_vvrxy7jsv_1764880953162.json') as f:
    session = json.load(f)

payload = {
    'raw_text': 'I searched for good voices and clicked on Roger',
    'session': session,
    'narration_type': 'continuous'
}

print(json.dumps(payload, indent=2))
" > test_payload.json

# Test endpoint
curl -X POST "http://localhost:8000/generate-synced-narration" \
  -H "Content-Type: application/json" \
  -d @test_payload.json
```

## Notes

- The RAG context is built entirely from DOM events (no video analysis needed)
- Gemini uses the context to understand the workflow and generate appropriate narration
- The system maintains the user's original intent while adding professional polish
- Timeline information allows for precise sync with video playback

