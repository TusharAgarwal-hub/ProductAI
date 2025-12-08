# Implementation Summary - RAG-Based Script Generation with Deepgram

## What We Built

A comprehensive **RAG-powered script generation system** that processes:
1. **Raw transcript** from Deepgram
2. **Word-level timing data** with confidence scores
3. **DOM events** from screen recordings

To generate **production-ready product demo scripts** with synchronized audio.

---

## Key Changes Made

### 1. **Analyzed Actual Deepgram JSON Structure**
- Created `DEEPGRAM_ANALYSIS.md` documenting the real structure
- Identified word-level timing (not character-level)
- Discovered confidence scores, punctuation, and hierarchical structure

### 2. **Created Script Generation Service**
**File:** `app/services/script_generation_service.py`

**Key Functions:**
- `analyze_word_timings()` - Analyzes Deepgram word timing data
  - Detects gaps >0.3s (minor), >0.5s (natural), >0.8s (major)
  - Identifies filler words (um, uh, like, etc.)
  - Detects repetitions (the the, as as)
  - Finds low confidence words (<0.8)
  - Calculates speaking rate (words/second)

- `build_timing_context()` - Formats timing analysis for AI prompt
  - Shows gaps with context (after/before words)
  - Lists filler words detected
  - Highlights low confidence words

- `generate_product_script()` - Main orchestrator
  - Combines timing + DOM events + raw transcript
  - Generates comprehensive Gemini prompt
  - Returns production-ready script

### 3. **Updated Data Models**
**File:** `app/models/request_models.py`

**AudioProcessRequest:**
```python
{
    "text": str,  # Raw transcript
    "deepgramData": {  # Complete Deepgram response
        "words": [...],  # Word-level timing
        "sentences": [...],  # Sentence boundaries
        "paragraphs": [...]  # Paragraph structure
    },
    "session": RecordingSession,  # DOM events
    "recordingsPath": str,
    "metadata": dict
}
```

**Added Properties:**
- `payload.words` - Extract words array
- `payload.sentences` - Extract sentences
- `payload.paragraphs` - Extract paragraphs

### 4. **Refactored Main Endpoint**
**File:** `app/main.py`

**`/audio-full-process` Pipeline:**
1. Analyze word timings (gaps, fillers, confidence)
2. Build RAG context from DOM events
3. Generate production script using Gemini
4. Convert script to audio (ElevenLabs)
5. Save audio and return results

**Enhanced Response:**
```json
{
    "success": true,
    "script": "production-ready script",
    "raw_text": "original transcript",
    "processed_audio_filename": "audio.mp3",
    "audio_size_bytes": 45678,
    "timing_analysis": {
        "total_duration": 25.5,
        "total_words": 63,
        "speaking_rate": 2.47,
        "num_gaps": 12,
        "average_gap": 0.45,
        "num_filler_words": 5,
        "num_low_confidence": 2
    },
    "dom_context_used": true,
    "session_id": "session_123"
}
```

### 5. **Created Documentation**
- `DEEPGRAM_ANALYSIS.md` - Deep dive into Deepgram JSON structure
- `Readme.md` - Complete architecture and usage guide

---

## How It Works

### Gap Detection Example

From the provided Deepgram JSON:

```
"celebrating," (end: 3.3) → "the" (start: 4.4)
Gap: 1.1 seconds → MAJOR PAUSE (thinking/breath)

"team," (end: 7.86) → "I" (start: 8.395)
Gap: 0.535 seconds → NATURAL PAUSE (sentence boundary)

"normal." (end: 12.495) → "And," (start: 12.715)
Gap: 0.22 seconds → MINOR PAUSE (continuation)
```

### Filler Word Detection

```python
# Detected from example:
- "as as" (repetition at 0.8s - 1.04s)
- "the the" (repetition at 17.58s - 17.74s and 23.42s - 23.66s)
```

### Low Confidence Detection

```python
# Words with confidence < 0.8:
- "the" (0.7626953 at 23.18s)
- "the" (0.625 at 23.42s)
```

### RAG Context Building

Combines:
1. **Timing Analysis:**
   - Total duration, word count, speaking rate
   - Gap locations and types
   - Filler words and low confidence words

2. **DOM Events:**
   - User actions (clicks, typing, scrolling)
   - UI elements interacted with
   - Timeline of interactions

3. **Gemini Prompt:**
   - Uses all context to generate professional script
   - Removes fillers, fixes repetitions
   - Adds smooth transitions at gaps
   - References specific UI elements

---

## Example Processing Flow

### Input from Node.js:
```json
{
    "text": "Yeah. As as much as, it's worth celebrating...",
    "deepgramData": {
        "words": [
            {"word": "yeah", "start": 0.08, "end": 0.32, "confidence": 0.9975586},
            {"word": "as", "start": 0.32, "end": 0.8, "confidence": 0.9921875},
            {"word": "as", "start": 0.8, "end": 1.04, "confidence": 0.96777344},
            // ... more words
        ]
    },
    "session": {
        "sessionId": "session_123",
        "events": [/* DOM events */]
    }
}
```

### Processing:
1. **Analyze Timing:**
   - Detect "as as" repetition
   - Identify 1.1s gap after "celebrating,"
   - Calculate speaking rate: 2.47 words/second

2. **Build Context:**
   - Format gaps with word context
   - List filler words
   - Extract DOM event timeline

3. **Generate Script:**
   - Remove "as as" repetition
   - Add smooth transition at 1.1s gap
   - Reference UI elements from DOM events
   - Polish language and add punctuation

### Output:
```json
{
    "script": "It's worth celebrating the first spacewalk with an all-female team. I think many of us are looking forward to it just being normal. I think if it signifies anything, it is to honor the women who came before us who were skilled and qualified, and didn't get the same opportunities that we have today.",
    "timing_analysis": {
        "total_duration": 25.44,
        "total_words": 63,
        "speaking_rate": 2.47,
        "num_gaps": 12,
        "num_filler_words": 2,
        "num_low_confidence": 2
    }
}
```

---

## Benefits

✅ **Accurate Gap Detection** - Uses actual word boundaries from Deepgram  
✅ **Confidence-Based Filtering** - Identifies uncertain transcriptions  
✅ **Filler Word Removal** - Automatically detects and removes um, uh, repetitions  
✅ **Context-Aware** - Combines timing + DOM events for better understanding  
✅ **Production-Ready** - Generates polished, professional scripts  
✅ **Rich Metadata** - Returns detailed timing analysis for debugging  

---

## Node.js Integration

### What Node.js Should Send:

```javascript
// Extract from Deepgram response
const deepgramResponse = await deepgram.transcribe(audioFile);
const words = deepgramResponse.results.channels[0].alternatives[0].words;
const transcript = deepgramResponse.results.channels[0].alternatives[0].transcript;

// Send to Python
const response = await axios.post('http://localhost:8000/audio-full-process', {
    text: transcript,
    deepgramData: {
        words: words,
        sentences: deepgramResponse.results.channels[0].alternatives[0].paragraphs?.sentences || [],
        paragraphs: deepgramResponse.results.channels[0].alternatives[0].paragraphs?.paragraphs || []
    },
    session: {
        sessionId: sessionId,
        events: domEvents,
        // ... other session data
    },
    recordingsPath: path.join(__dirname, 'recordings', sessionId),
    metadata: { sessionId }
});
```

---

## Testing

### Test with Example Deepgram JSON:

```bash
# Create test payload
cat > test_deepgram_payload.json << 'EOF'
{
    "text": "Yeah. As as much as, it's worth celebrating...",
    "deepgramData": {
        "words": [
            {"word": "yeah", "start": 0.08, "end": 0.32, "confidence": 0.9975586, "punctuated_word": "Yeah."},
            {"word": "as", "start": 0.32, "end": 0.8, "confidence": 0.9921875, "punctuated_word": "As"}
        ]
    },
    "session": null,
    "recordingsPath": "./recordings",
    "metadata": {"sessionId": "test_123"}
}
EOF

# Test endpoint
curl -X POST "http://localhost:8000/audio-full-process" \
  -H "Content-Type: application/json" \
  -d @test_deepgram_payload.json
```

---

## Next Steps

### Immediate:
- [ ] Test with real Deepgram data from Node.js
- [ ] Verify gap detection accuracy
- [ ] Fine-tune filler word patterns

### Future:
- [ ] Generate frontend instructions for visual effects
- [ ] Add sentence-level timing for better sync
- [ ] Support multiple languages
- [ ] Export SRT/VTT subtitle files
- [ ] Advanced gap filling strategies (use DOM context to explain pauses)

---

## Files Modified/Created

### Created:
- `app/services/script_generation_service.py` - Main script generation logic
- `DEEPGRAM_ANALYSIS.md` - Deepgram structure documentation
- `Readme.md` - Complete architecture guide

### Modified:
- `app/main.py` - Updated `/audio-full-process` endpoint
- `app/models/request_models.py` - Updated AudioProcessRequest model

### Unchanged (but used):
- `app/services/rag_service.py` - DOM event context building
- `app/services/gemini_service.py` - AI text generation
- `app/services/elevenlabs_service.py` - Text-to-speech conversion

---

## Summary

We've built a sophisticated system that:
1. ✅ Properly handles **Deepgram's word-level timing structure**
2. ✅ Detects **gaps, fillers, and low-confidence words**
3. ✅ Combines **timing + DOM events** for RAG context
4. ✅ Generates **production-ready scripts** with Gemini
5. ✅ Returns **rich metadata** for debugging and analysis

The system is ready to receive Deepgram data from Node.js and produce professional product demo narration!
