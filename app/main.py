import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from app.services.gemini_service import generate_product_text
from app.services.elevenlabs_service import generate_voice_from_text
from app.models.request_models import ProductTextRequest
from fastapi import UploadFile, File
from app.services.video_analysis_service import process_video
import os

NODE_SERVER_URL = os.getenv("NODE_SERVER_URL")  # e.g. http://localhost:3000/api/upload-audio

app = FastAPI(title="ProductAI Python Backend", version="1.0.0")


@app.post("/audio-full-process")
async def full_process(payload: ProductTextRequest):
    try:
        # 1) Clean text using Gemini
        cleaned_text = generate_product_text(payload.text)

        # 2) Convert cleaned text to audio (bytes)
        audio_bytes = generate_voice_from_text(cleaned_text)

        # 3) Send audio to Node server
        files = {
            "audio": ("output.mp3", audio_bytes, "audio/mpeg")
        }
        data = {
            "text": cleaned_text
        }

        node_response = requests.post(NODE_SERVER_URL, files=files, data=data)

        if node_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Node server upload failed")

        return JSONResponse({
            "cleaned_text": cleaned_text,
            "audio_sent_to_node": True
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze-video")
async def analyze_video(file: UploadFile = File(...)):
    """
    Accepts screen recording from Node → returns UI events + OCR text.
    """

    file_path = f"temp_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    events = process_video(file_path)

    # Remove local file to save memory
    os.remove(file_path)

    return events