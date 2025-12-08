# Node.js Integration Compatibility Analysis

## Current Situation

### What Node.js Actually Sends (from integration guide):
```json
{
    "text": "transcript text",
    "domEvents": [...],
    "deepgramResponse": {
        "text": "same transcript",
        "timeline": [
            {
                "start": 0.0,
                "end": 5.2,
                "text": "utterance text",
                "type": "speech"
            },
            {
                "start": 5.2,
                "end": 7.8,
                "text": "—",
                "type": "silence"
            }
        ],
        "metadata": {...},
        "raw": {
            // Full Deepgram API response
        }
    },
    "recordingsPath": "path",
    "metadata": {...}
}
```

### What Our Implementation Expects:
```json
{
    "text": "transcript text",
    "deepgramData": {
        "words": [
            {
                "word": "hello",
                "start": 0.08,
                "end": 0.32,
                "confidence": 0.99,
                "punctuated_word": "Hello."
            }
        ],
        "sentences": [...],
        "paragraphs": [...]
    },
    "session": RecordingSession,
    "recordingsPath": "path",
    "metadata": {...}
}
```

## Key Differences

1. **Field Name:**
   - Node.js: `deepgramResponse`
   - Our code: `deepgramData`

2. **Structure:**
   - Node.js: Has `timeline` with speech/silence segments
   - Our code: Expects `words` array with word-level timing

3. **DOM Events:**
   - Node.js: Sends as `domEvents` (flat array)
   - Our code: Expects `session` (RecordingSession object)

4. **Raw Deepgram Data:**
   - Node.js: Has `raw` field with full Deepgram response
   - Our code: Needs to extract `words` from this raw response

## Solution

We need to:

1. **Update `AudioProcessRequest` model** to accept both formats
2. **Extract words from `deepgramResponse.raw`** if available
3. **Convert `domEvents` array to `RecordingSession`** if needed
4. **Create compatibility layer** that handles both old and new formats

## Implementation Plan

### 1. Update Request Model
```python
class AudioProcessRequest(BaseModel):
    text: str
    
    # Accept both field names
    deepgramResponse: Optional[Dict[str, Any]] = None  # From Node.js
    deepgramData: Optional[Dict[str, Any]] = None      # New format
    
    # Accept both DOM event formats
    domEvents: List[Dict[str, Any]] = []               # From Node.js
    session: Optional[RecordingSession] = None         # New format
    
    recordingsPath: str
    metadata: Dict[str, Any] = {}
    
    @property
    def words(self) -> List[Dict[str, Any]]:
        """Extract words from either format."""
        # Try new format first
        if self.deepgramData and "words" in self.deepgramData:
            return self.deepgramData["words"]
        
        # Try extracting from Node.js format
        if self.deepgramResponse and "raw" in self.deepgramResponse:
            raw = self.deepgramResponse["raw"]
            # Navigate Deepgram structure
            try:
                return raw["results"]["channels"][0]["alternatives"][0]["words"]
            except (KeyError, IndexError):
                return []
        
        return []
```

### 2. Extract Words from Raw Deepgram Response

The actual Deepgram JSON structure is:
```json
{
    "results": {
        "channels": [
            {
                "alternatives": [
                    {
                        "words": [...]  // This is what we need
                    }
                ]
            }
        ]
    }
}
```

### 3. Convert DOM Events to RecordingSession

```python
def convert_dom_events_to_session(
    dom_events: List[Dict[str, Any]],
    metadata: Dict[str, Any]
) -> RecordingSession:
    """Convert flat DOM events array to RecordingSession object."""
    # Implementation needed
```

## Recommended Approach

**Option 1: Update Node.js to send correct format** ✅ RECOMMENDED
- Modify Node.js to extract `words` from Deepgram response
- Send as `deepgramData.words`
- Convert DOM events to proper RecordingSession format

**Option 2: Create compatibility layer in Python**
- Accept both formats
- Extract words from `deepgramResponse.raw`
- Convert `domEvents` to `RecordingSession`
- More complex but backwards compatible

## Next Steps

1. Check what Node.js is actually sending right now
2. Decide on compatibility approach
3. Implement chosen solution
4. Test with real data from Node.js
