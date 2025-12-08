import requests
from fastapi import FastAPI, HTTPException, UploadFile, File
from typing import Optional, Dict, List, Any
from fastapi.responses import JSONResponse
from app.services.gemini_service import generate_product_text
from app.services.elevenlabs_service import generate_voice_from_text
from app.models.request_models import ProductTextRequest, SyncedNarrationRequest, AudioProcessRequest
from app.models.dom_event_models import RecordingSession, ProcessRecordingResponse
from app.services.dom_event_service import process_dom_events, extract_text_from_events, group_events_by_step
from app.services.synced_narration_service import generate_synced_narration, generate_step_by_step_narration
import os
import time
from pathlib import Path

NODE_SERVER_URL = os.getenv("NODE_SERVER_URL")  

app = FastAPI(title="ProductAI Backend", version="2.0.0")


@app.post("/audio-full-process")
async def full_process(payload: AudioProcessRequest):

    try:
        print(f"[Python] ===== FULL PROCESSING PIPELINE STARTED =====")
        print(f"[Python] Raw text length: {len(payload.text)}")

        has_new_format = payload.deepgramData is not None
        has_old_format = payload.deepgramResponse is not None
        print(f"[Python] Format detected: {'NEW (deepgramData)' if has_new_format else 'OLD (deepgramResponse)' if has_old_format else 'UNKNOWN'}")

        words = payload.words
        print(f"[Python] Deepgram words: {len(words)} words")


        # ----------------------------------------------------------------------
        # 👇 RAG FIX — Safe legacy wrapper for raw domEvents
        # ----------------------------------------------------------------------
        session = payload.get_session_or_create()

        if session:
            print(f"[Python] DOM events: {len(session.events)} events")

        elif payload.domEvents:
            print(f"[Python] DOM events (raw): {len(payload.domEvents)} events (no RecordingSession)")

            try:
                session_id = payload.metadata.get("sessionId", "legacy_session")

                session = RecordingSession(
                    sessionId=session_id,
                    events=payload.domEvents,
                    startTime=payload.metadata.get("startTime") or 0,
                    endTime=payload.metadata.get("endTime") or 0,
                    url=payload.metadata.get("url") or "unknown",
                    viewport=payload.metadata.get("viewport") or {"width": 0, "height": 0}
                )

                print(f"[Python] ✅ Wrapped raw domEvents into RecordingSession "
                      f"(sessionId={session.sessionId}, events={len(session.events)})")

            except Exception as wrap_error:
                print(f"[Python] ❌ Failed to wrap raw domEvents:", wrap_error)
                session = None

        else:
            print(f"[Python] No DOM events available")

        # ----------------------------------------------------------------------


        print(f"[Python] Recordings path: {payload.recordingsPath}")

        print(f"[Python] Step 1: Generating production-ready script...")
        from app.services.script_generation_service import generate_product_script

        script_result = generate_product_script(
            raw_text=payload.text,
            word_timings=words,
            session=session
        )

        if not script_result.get("success"):
            error_msg = script_result.get('error', 'Unknown error')
            print(f"[Python] ❌ Script generation failed: {error_msg}")
            raise Exception(f"Script generation failed: {error_msg}")

        production_script = script_result["script"]
        print(f"\n[Python] ✅ STEP 1 COMPLETE - Script Generated")
        print(f"[Python]   - Script length: {len(production_script)} characters")
        print(f"[Python]   - Script preview: {production_script[:150]}...")
        print(f"[Python]   - Timing analysis: {script_result.get('timing_analysis', {})}")


        print(f"\n[Python] ===== STEP 2: AUDIO GENERATION =====")
        print(f"[Python] Converting script to audio using ElevenLabs...")
        print(f"[Python]   - Text length: {len(production_script)} characters")

        try:
            audio_bytes = generate_voice_from_text(production_script)
            print(f"[Python] ✅ Audio generated successfully")
            print(f"[Python]   - Audio size: {len(audio_bytes)} bytes ({len(audio_bytes) / 1024:.2f} KB)")
        except Exception as e:
            print(f"[Python] ❌ Audio generation failed: {str(e)}")
            raise


        print(f"\n[Python] ===== STEP 3: SAVING AUDIO FILE =====")
        timestamp = int(time.time() * 1000)
        session_id = payload.metadata.get("sessionId", "unknown")
        filename = f"processed_audio_{session_id}_{timestamp}.mp3"

        print(f"[Python]   - Session ID: {session_id}")
        print(f"[Python]   - Filename: {filename}")
        print(f"[Python]   - Recordings path: {payload.recordingsPath}")

        recordings_path = Path(payload.recordingsPath)
        recordings_path.mkdir(parents=True, exist_ok=True)
        print(f"[Python]   - Directory created/verified: {recordings_path}")

        file_path = recordings_path / filename

        with open(file_path, "wb") as f:
            f.write(audio_bytes)

        print(f"[Python] ✅ Audio file saved successfully")
        print(f"[Python]   - Full path: {file_path}")
        print(f"[Python]   - File size: {len(audio_bytes)} bytes")


        print(f"\n[Python] ===== STEP 4: PREPARING RESPONSE =====")

        response_data = {
            "success": True,
            "script": production_script,
            "raw_text": payload.text,
            "processed_audio_filename": filename,
            "audio_size_bytes": len(audio_bytes),
            "timing_analysis": script_result.get("timing_analysis", {}),
            "dom_context_used": script_result.get("dom_context_used", False),
            "session_id": session_id,
        }

        print(f"[Python]   - DOM context used: {response_data['dom_context_used']}")
        print(f"\n[Python] ===== ✅ ALL PROCESSING COMPLETE ✅ =====")

        return JSONResponse(response_data)

    except Exception as e:
        error_msg = f"Processing failed: {str(e)}"
        print(f"[Python] ❌ ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)



@app.post("/process-recording", response_model=ProcessRecordingResponse)
async def process_recording(
    session: RecordingSession,
    video: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None)
):
    try:
        response = process_dom_events(session)
        extracted_text = extract_text_from_events(session.events)
        grouped_steps = group_events_by_step(session.events)

        response.metadata["extractedText"] = extracted_text
        response.metadata["groupedSteps"] = grouped_steps
        response.metadata["hasVideo"] = video is not None
        response.metadata["hasAudio"] = audio is not None

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process recording: {str(e)}")
