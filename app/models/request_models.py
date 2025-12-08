from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.models.dom_event_models import RecordingSession


class ProductTextRequest(BaseModel):
    text: str


class SyncedNarrationRequest(BaseModel):
    """Request model for generating synced narration with DOM events context"""
    raw_text: str
    session: RecordingSession
    narration_type: Optional[str] = "continuous"  # "continuous" or "step_by_step"


class AudioProcessRequest(BaseModel):
    """
    Complete request from Node.js for full audio processing pipeline.
    
    BACKWARD COMPATIBLE: Accepts both old Node.js format and new format.
    
    Old Node.js format:
    - deepgramResponse (with timeline and raw Deepgram data)
    - domEvents (flat array)
    
    New format:
    - deepgramData (with words, sentences, paragraphs)
    - session (RecordingSession object)
    """
    text: str  # Raw transcript from Deepgram
    
    # Accept BOTH field names for backward compatibility
    deepgramResponse: Optional[Dict[str, Any]] = None  # From Node.js (old format)
    deepgramData: Optional[Dict[str, Any]] = None      # New format
    
    # Accept BOTH DOM event formats
    domEvents: List[Dict[str, Any]] = []               # From Node.js (old format)
    session: Optional[RecordingSession] = None         # New format
    
    recordingsPath: str  # Path where Node.js stores recordings
    metadata: Dict[str, Any] = {}  # Additional metadata (sessionId, etc.)
    
    @property
    def words(self) -> List[Dict[str, Any]]:
        """
        Extract words array from either format.
        
        Priority:
        1. deepgramData.words (new format)
        2. deepgramResponse.raw.results.channels[0].alternatives[0].words (Node.js format)
        3. Empty array
        """
        # Try new format first
        if self.deepgramData and "words" in self.deepgramData:
            return self.deepgramData["words"]
        
        # Try extracting from Node.js format (raw Deepgram response)
        if self.deepgramResponse and "raw" in self.deepgramResponse:
            raw = self.deepgramResponse["raw"]
            try:
                # Navigate Deepgram's nested structure
                channels = raw.get("results", {}).get("channels", [])
                if channels:
                    alternatives = channels[0].get("alternatives", [])
                    if alternatives:
                        words = alternatives[0].get("words", [])
                        return words
            except (KeyError, IndexError, AttributeError):
                pass
        
        return []
    
    @property
    def sentences(self) -> List[Dict[str, Any]]:
        """Extract sentences array from either format."""
        if self.deepgramData and "sentences" in self.deepgramData:
            return self.deepgramData["sentences"]
        
        # Try extracting from Node.js format
        if self.deepgramResponse and "raw" in self.deepgramResponse:
            raw = self.deepgramResponse["raw"]
            try:
                channels = raw.get("results", {}).get("channels", [])
                if channels:
                    alternatives = channels[0].get("alternatives", [])
                    if alternatives:
                        paragraphs = alternatives[0].get("paragraphs", {})
                        sentences = paragraphs.get("sentences", [])
                        return sentences
            except (KeyError, IndexError, AttributeError):
                pass
        
        return []
    
    @property
    def paragraphs(self) -> List[Dict[str, Any]]:
        """Extract paragraphs array from either format."""
        if self.deepgramData and "paragraphs" in self.deepgramData:
            return self.deepgramData["paragraphs"]
        
        # Try extracting from Node.js format
        if self.deepgramResponse and "raw" in self.deepgramResponse:
            raw = self.deepgramResponse["raw"]
            try:
                channels = raw.get("results", {}).get("channels", [])
                if channels:
                    alternatives = channels[0].get("alternatives", [])
                    if alternatives:
                        paragraphs_obj = alternatives[0].get("paragraphs", {})
                        paragraphs = paragraphs_obj.get("paragraphs", [])
                        return paragraphs
            except (KeyError, IndexError, AttributeError):
                pass
        
        return []
    
    @property
    def timeline(self) -> List[Dict[str, Any]]:
        """
        Extract timeline from Node.js format (speech/silence segments).
        Only available in old Node.js format.
        """
        if self.deepgramResponse and "timeline" in self.deepgramResponse:
            return self.deepgramResponse["timeline"]
        return []
    
    def get_session_or_create(self) -> Optional[RecordingSession]:
        """
        Get RecordingSession object, or create one from domEvents if needed.
        
        Returns None if no session data available.
        """
        # If we have a proper session object, return it
        if self.session:
            return self.session
        
        # If we have domEvents but no session, we can't create a proper RecordingSession
        # because we need sessionId, startTime, endTime, url, viewport
        # This would need to come from metadata
        if self.domEvents and self.metadata:
            # For now, return None - Node.js should send proper session object
            # TODO: Implement conversion if needed
            return None
        
        return None
