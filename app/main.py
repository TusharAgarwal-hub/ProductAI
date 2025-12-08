import requests
from fastapi import FastAPI, HTTPException, UploadFile, File
from typing import Optional
from fastapi.responses import JSONResponse
from app.services.gemini_service import generate_product_text
from app.services.elevenlabs_service import generate_voice_from_text
from app.models.request_models import ProductTextRequest, SyncedNarrationRequest
from app.models.dom_event_models import RecordingSession, ProcessRecordingResponse
from app.services.dom_event_service import process_dom_events, extract_text_from_events, group_events_by_step
from app.services.synced_narration_service import generate_synced_narration, generate_step_by_step_narration
import os
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional

NODE_SERVER_URL = os.getenv("NODE_SERVER_URL")  

app = FastAPI(title="ProductAI Backend", version="2.0.0")

# Request model matching Node.js payload
class AudioProcessRequest(BaseModel):
    text: str
    domEvents: List[Dict[str, Any]] = []
    recordingsPath: str  # Node.js provides this!
    metadata: Dict[str, Any] = {}


@app.post("/audio-full-process")
async def full_process(payload: AudioProcessRequest):
    """
    Process raw transcript: clean with Gemini and convert to audio with ElevenLabs.
    Save processed audio to the path provided by Node.js.
    """
    try:
        print(f"[Python] Processing audio request")
        print(f"[Python] Text length: {len(payload.text)}")
        print(f"[Python] Recordings path from Node: {payload.recordingsPath}")

        # 1) Clean text using Gemini
        cleaned_text = generate_product_text(payload.text)
        print(f"[Python] Cleaned text: {cleaned_text[:100]}...")

        # 2) Convert cleaned text to audio (bytes)
        audio_bytes = generate_voice_from_text(cleaned_text)
        print(f"[Python] Generated audio: {len(audio_bytes)} bytes")

        # 3) Save to recordings folder (path provided by Node.js)
        timestamp = int(time.time() * 1000)
        session_id = payload.metadata.get("sessionId", "unknown")
        filename = f"processed_audio_{session_id}_{timestamp}.webm"  # Include sessionId for clarity
        
        # Use the path provided by Node.js
        recordings_path = Path(payload.recordingsPath)
        recordings_path.mkdir(parents=True, exist_ok=True)
        
        file_path = recordings_path / filename
        
        with open(file_path, "wb") as f:
            f.write(audio_bytes)
        
        print(f"[Python] Saved processed audio to: {file_path}")

        # 4) Return filename so Node can find it
        return JSONResponse({
            "cleaned_text": cleaned_text,
            "processed_audio_filename": filename,
            "success": True
        })

    except Exception as e:
        error_msg = f"Processing failed: {str(e)}"
        print(f"[Python] Error: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/process-recording", response_model=ProcessRecordingResponse)
async def process_recording(
    session: RecordingSession,
    video: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None)
):
    """
    Process DOM events from browser extension and generate frontend instructions.
    
    This endpoint:
    1. Accepts DOM events JSON (from extension)
    2. Optionally accepts video/audio files (for sync purposes)
    3. Generates structured instructions for frontend effects
    4. Extracts text content for RAG model processing
    
    The instructions can be used by:
    - Frontend: To apply visual effects (highlights, animations) synchronized with audio
    - RAG Model: To generate product demo scripts based on user interactions
    """
    try:
        # Process DOM events and generate instructions
        response = process_dom_events(session)
        
        # Extract text content for RAG model (can be used later)
        extracted_text = extract_text_from_events(session.events)
        grouped_steps = group_events_by_step(session.events)
        
        # Add RAG-ready data to metadata
        response.metadata["extractedText"] = extracted_text
        response.metadata["groupedSteps"] = grouped_steps
        response.metadata["hasVideo"] = video is not None
        response.metadata["hasAudio"] = audio is not None
        
        # TODO: Save video/audio files if provided (for sync purposes)
        # TODO: Integrate with RAG model to generate script based on events + text
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process recording: {str(e)}")


@app.post("/process-recording-json")
async def process_recording_json(
    session_json: dict
):
    """
    Alternative endpoint that accepts raw JSON instead of Pydantic model.
    Useful for direct JSON uploads from extension.
    """
    try:
        # Convert dict to Pydantic model
        session = RecordingSession(**session_json)
        
        # Process using main endpoint logic
        response = process_dom_events(session)
        
        # Extract text content for RAG model
        extracted_text = extract_text_from_events(session.events)
        grouped_steps = group_events_by_step(session.events)
        
        response.metadata["extractedText"] = extracted_text
        response.metadata["groupedSteps"] = grouped_steps
        
        return response.dict()
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid session data: {str(e)}")


@app.post("/generate-synced-narration")
async def generate_synced_narration_endpoint(payload: SyncedNarrationRequest):
    """
    Generate synced product demo narration using RAG context from DOM events.
    
    This endpoint:
    1. Takes raw user transcript/narration
    2. Uses DOM events as RAG context to understand screen recording actions
    3. Generates professional narration that syncs with the recording
    4. Can return continuous or step-by-step narration
    
    The RAG model uses DOM events to understand:
    - What UI elements were clicked
    - What text was typed
    - The sequence and timing of actions
    - The overall workflow/steps
    
    This helps Gemini generate narration that accurately describes what's
    happening in the screen recording, synced with the user's raw transcript.
    """
    try:
        if payload.narration_type == "step_by_step":
            result = generate_step_by_step_narration(
                raw_text=payload.raw_text,
                session=payload.session
            )
        else:
            result = generate_synced_narration(
                raw_text=payload.raw_text,
                session=payload.session
            )
        
        return JSONResponse(result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate synced narration: {str(e)}"
        )


@app.post("/generate-synced-narration-with-audio")
async def generate_synced_narration_with_audio(payload: SyncedNarrationRequest):
    """
    Generate synced narration AND convert it to audio in one request.
    
    This is a convenience endpoint that:
    1. Generates synced narration using RAG context
    2. Converts the narration to audio using ElevenLabs
    3. Returns both the text and audio
    
    Perfect for end-to-end workflow: raw transcript + DOM events → synced narration + audio
    """
    try:
        # Generate synced narration
        if payload.narration_type == "step_by_step":
            narration_result = generate_step_by_step_narration(
                raw_text=payload.raw_text,
                session=payload.session
            )
            narration_text = narration_result.get("step_by_step", "")
        else:
            narration_result = generate_synced_narration(
                raw_text=payload.raw_text,
                session=payload.session
            )
            narration_text = narration_result.get("synced_narration", "")
        
        # Convert to audio
        audio_bytes = generate_voice_from_text(narration_text)
        
        # Prepare response
        result = {
            **narration_result,
            "audio_generated": True,
            "audio_size_bytes": len(audio_bytes)
        }
        
        # Return JSON with audio as base64 or send audio separately
        # For now, return metadata. Audio can be sent via separate endpoint or multipart
        return JSONResponse(result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate synced narration with audio: {str(e)}"
        )
