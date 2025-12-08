# Clueso Python Layer - Production-Ready Script Generation

## Overview

This Python backend processes screen recordings with **RAG (Retrieval-Augmented Generation)** to generate production-ready product demo scripts and audio. It receives **three critical inputs** from the Node.js layer and orchestrates a comprehensive processing pipeline.

---

## Architecture

```
Node.js Layer → Python Layer → Production Audio + Script
                     ↓
        ┌────────────┴────────────┐
        │  /audio-full-process    │  (Main Orchestrator)
        └────────────┬────────────┘
                     ↓
        ┌────────────────────────────────────┐
        │  THREE INPUTS FROM NODE.JS:        │
        │  1. Raw Transcript (text)          │
        │  2. Character Timings (JSON)       │
        │  3. DOM Events (RecordingSession)  │
        └────────────┬───────────────────────┘
                     ↓
        ┌────────────────────────────────────┐
        │  PROCESSING PIPELINE:              │
        │                                    │
        │  Step 1: Analyze Character Timing  │
        │          ↓ (detect gaps/pauses)    │
        │  Step 2: Build RAG Context         │
        │          ↓ (from DOM events)       │
        │  Step 3: Generate Script           │
        │          ↓ (Gemini AI)             │
        │  Step 4: Convert to Audio          │
        │          ↓ (ElevenLabs TTS)        │
        │  Step 5: Save & Return             │
        └────────────┬───────────────────────┘
                     ↓
        ┌────────────────────────────────────┐
        │  OUTPUT TO NODE.JS:                │
        │  - Production-ready script         │
        │  - Audio filename (.mp3)           │
        │  - Timing analysis metadata        │
        │  - Processing statistics           │
        └────────────────────────────────────┘
```

---

## The Three Inputs

### 1. **Raw Transcript** (`text`)
- Raw speech-to-text output from Deepgram
- Contains filler words, pauses, and natural speech patterns
- Example: `"um so I'm going to click on this button and uh type something"`

### 2. **Character-Level Timing** (`characterTimings`)
- **Critical for gap detection and sync**
- Array of character/word timing objects from Deepgram
- Each object contains:
  - Character/word text
  - Start time (seconds)
  - End time (seconds)
  
**Example:**
```json
[
  {"char": "H", "start": 0.0, "end": 0.05},
  {"char": "e", "start": 0.05, "end": 0.1},
  {"char": "l", "start": 0.1, "end": 0.15},
  // ... gap detected here (200ms+) ...
  {"char": "w", "start": 0.5, "end": 0.55}
]
```

**What we do with it:**
- Identify pauses/gaps (>200ms between characters)
- Detect speaking segments vs silence
- Structure narration around natural pauses
- Calculate speaking rate and pacing

### 3. **DOM Events** (`session`)
- User interactions captured during screen recording
- Wrapped in `RecordingSession` model
- Includes:
  - Clicks, typing, focus, blur, scroll events
  - UI element details (tag, text, selector, bbox)
  - Timestamps synchronized with recording
  
**Example:**
```json
{
  "sessionId": "session_123",
  "events": [
    {
      "timestamp": 1500,
      "type": "click",
      "target": {
        "tag": "BUTTON",
        "text": "Submit",
        "selector": "#submit-btn"
      }
    }
  ]
}
```

---

## Main Endpoint: `/audio-full-process`

### Request

```json
{
  "text": "um so I'm going to search for good voices and then click on Roger",
  "characterTimings": [
    {"char": "u", "start": 0.0, "end": 0.05},
    // ... full character timing array
  ],
  "session": {
    "sessionId": "session_123",
    "startTime": 1764880934009,
    "endTime": 1764880953143,
    "url": "https://example.com",
    "viewport": {"width": 1536, "height": 695},
    "events": [
      // ... DOM events array
    ]
  },
  "recordingsPath": "D:\\recordings\\session_123",
  "metadata": {
    "sessionId": "session_123"
  }
}
```

### Response

```json
{
  "success": true,
  "script": "I'm searching for good voices in the search input field. I type 'good' and then click on the Roger voice option to select it.",
  "raw_text": "um so I'm going to search for good voices and then click on Roger",
  "processed_audio_filename": "processed_audio_session_123_1733645678901.mp3",
  "audio_size_bytes": 45678,
  "timing_analysis": {
    "total_duration": 15.5,
    "num_gaps": 3,
    "average_gap": 0.35,
    "has_timing_data": true
  },
  "dom_context_used": true,
  "session_id": "session_123"
}
```

---

## Processing Pipeline Details

### Step 1: Character Timing Analysis

**Service:** `script_generation_service.py` → `analyze_character_timings()`

**What it does:**
- Analyzes character-level timing data
- Identifies gaps >200ms (indicates pauses)
- Groups characters into speaking segments
- Calculates speaking rate and patterns

**Output:**
```python
{
    "total_duration": 15.5,
    "gaps": [
        {"start": 2.5, "end": 2.8, "duration": 0.3},
        {"start": 7.2, "end": 7.6, "duration": 0.4}
    ],
    "speaking_segments": [
        {"start": 0.0, "end": 2.5, "characters": [...]},
        {"start": 2.8, "end": 7.2, "characters": [...]}
    ]
}
```

### Step 2: RAG Context Building

**Service:** `rag_service.py` → `build_rag_context_from_events()`

**What it does:**
- Converts DOM events to human-readable descriptions
- Groups events into logical steps (2-second threshold)
- Extracts UI elements and interactions
- Creates timeline of actions

**Output:**
```
Recording Session: session_123
URL: https://example.com
Duration: 19.1 seconds

Step 1 (Duration: 6.5s):
  [0.0s] Focused on search-input
  [1.2s] Typed 'good' in search-input

Step 2 (Duration: 4.2s):
  [7.4s] Clicked on 'Roger'
```

### Step 3: Script Generation

**Service:** `script_generation_service.py` → `generate_product_script()`

**What it does:**
- Combines all three inputs into comprehensive prompt
- Uses Gemini AI to generate production-ready script
- Maintains original intent while adding polish
- References specific UI elements from DOM events
- Structures narration around timing gaps

**Prompt includes:**
- Raw transcript
- Timing analysis with gaps
- DOM events context
- UI elements summary
- Timeline of actions

### Step 4: Audio Conversion

**Service:** `elevenlabs_service.py` → `generate_voice_from_text()`

**What it does:**
- Converts production script to audio
- Uses ElevenLabs TTS API
- Returns MP3 audio bytes

### Step 5: Save & Return

**What it does:**
- Saves audio to Node.js recordings folder
- Returns comprehensive response with:
  - Production script
  - Audio filename
  - Timing analysis
  - Processing metadata

---

## Key Services

### 1. **Script Generation Service** (NEW)
`app/services/script_generation_service.py`

**Main Functions:**
- `generate_product_script()` - Main orchestrator
- `analyze_character_timings()` - Gap detection
- `build_timing_context()` - Format timing for prompt

### 2. **RAG Service**
`app/services/rag_service.py`

**Main Functions:**
- `build_rag_context_from_events()` - Build context from DOM
- `build_timeline_context()` - Create action timeline
- `extract_ui_elements_summary()` - Summarize UI elements

### 3. **Gemini Service**
`app/services/gemini_service.py`

**Main Functions:**
- `generate_product_text()` - Clean text (legacy)
- Uses Gemini 2.5 Flash for AI generation

### 4. **ElevenLabs Service**
`app/services/elevenlabs_service.py`

**Main Functions:**
- `generate_voice_from_text()` - Text-to-speech conversion

---

## How Gap Detection Works

The character timing analysis is **critical** for creating natural-sounding narration:

1. **Identify Gaps:** Detect pauses >200ms between characters
2. **Segment Speech:** Group characters into continuous speaking segments
3. **Structure Narration:** Use gaps to add natural pauses in script
4. **Fill Intelligently:** Where there are long pauses, add smooth transitions

**Example:**

**Input Timing:**
```
"Hello" [0.0s - 0.5s] ... GAP (300ms) ... "world" [0.8s - 1.2s]
```

**Generated Script:**
```
"Hello. Let me show you the world of possibilities."
```

The gap is used to add a natural pause and smooth transition.

---

## Future Enhancements

### Immediate (Mentioned in Request)
- [ ] Generate **frontend instructions** for visual effects
- [ ] Return instructions alongside audio for synchronized playback

### Planned
- [ ] Fine-tune timing sync between script and audio
- [ ] Support multiple voice options
- [ ] Multi-language script generation
- [ ] Export SRT/VTT subtitle files
- [ ] Advanced gap filling strategies

---

## Testing

### Test the Endpoint

```bash
# Start the server
uvicorn app.main:app --reload --port 8000

# Test with curl
curl -X POST "http://localhost:8000/audio-full-process" \
  -H "Content-Type: application/json" \
  -d @test_payload.json
```

### Example Test Payload

See `test_events.json` for sample DOM events structure.

---

## Environment Variables

Required in `.env`:
```bash
GEMINI_API_KEY=your_gemini_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
NODE_SERVER_URL=http://localhost:3000
```

---

## Integration with Node.js

**Node.js sends:**
```javascript
const response = await axios.post('http://localhost:8000/audio-full-process', {
  text: deepgramTranscript,
  characterTimings: deepgramCharacterTimings,
  session: {
    sessionId: sessionId,
    events: domEvents,
    // ... other session data
  },
  recordingsPath: path.join(__dirname, 'recordings', sessionId),
  metadata: { sessionId }
});

// Node.js receives:
const { script, processed_audio_filename } = response.data;
```

---

## Summary

This Python layer is a **comprehensive RAG-powered script generation system** that:

1. ✅ Analyzes **character-level timing** to detect gaps and pauses
2. ✅ Builds **RAG context** from DOM events to understand user actions
3. ✅ Generates **production-ready scripts** using Gemini AI
4. ✅ Converts scripts to **professional audio** using ElevenLabs
5. ✅ Returns **complete metadata** for Node.js integration

The system transforms raw screen recordings into polished product demos by intelligently combining timing data, user interactions, and AI-powered script generation.
