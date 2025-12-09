# elevenlabs_service.py — Deepgram + background music, NO ffmpeg REQUIRED

import os
import re
import tempfile
from pathlib import Path
from typing import List

import requests
from dotenv import load_dotenv
from pydub import AudioSegment

load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
DEFAULT_VOICE_MODEL = "aura-2-thalia-en"
DEEPGRAM_SPEAK_URL = "https://api.deepgram.com/v1/speak"


def chunk_by_sentence(text: str) -> List[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def ensure_sentence_endings(text: str) -> str:
    txt = re.sub(r'\s+', ' ', text).strip()
    if txt and txt[-1] not in ".!?":
        txt += "."
    return txt


def call_deepgram(text: str, model: str) -> bytes:
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "application/json",
    }
    params = {
        "model": model,
        "encoding": "mp3",
        "bit_rate": "32000",
    }
    resp = requests.post(DEEPGRAM_SPEAK_URL, headers=headers, params=params, json={"text": text})
    if not resp.ok:
        raise RuntimeError(f"Deepgram error {resp.status_code}: {resp.text}")
    return resp.content


def generate_voice_from_text(text: str, voice_id: str = DEFAULT_VOICE_MODEL) -> bytes:
    if not text.strip():
        return b""

    text = ensure_sentence_endings(text)

    # CALL DEEPGRAM ONCE — fastest
    resp = requests.post(
        DEEPGRAM_SPEAK_URL,
        headers={
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "application/json",
        },
        params={
            "model": voice_id,
            "encoding": "mp3",
            "bit_rate": "32000",
        },
        json={"text": text},
        stream=True,
        timeout=30,
    )

    if not resp.ok:
        raise RuntimeError(f"Deepgram error {resp.status_code}: {resp.text}")

    return resp.content
