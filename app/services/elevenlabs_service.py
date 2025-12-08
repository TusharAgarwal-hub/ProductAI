import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

load_dotenv()

API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Initialize ElevenLabs client only if key is present
client = ElevenLabs(api_key=API_KEY) if API_KEY else None

# Default voice (you may change it later)
DEFAULT_VOICE_ID = "bIHbv24MWmeRgasZH58o"     # built-in free voice
MODEL = "eleven_multilingual_v2"  # best quality, supports many languages


def generate_voice_from_text(text: str, voice_id: str = DEFAULT_VOICE_ID) -> bytes:
    """
    Convert product demo text into realistic narrated audio.
    Returns raw audio bytes (mp3 format).
    """

    if not API_KEY or client is None:
        raise RuntimeError("ELEVENLABS_API_KEY is missing. Provide a valid key or disable TTS.")

    try:
        # Convert text → audio stream generator
        audio_stream = client.text_to_speech.convert(
            voice_id=voice_id,
            model_id=MODEL,
            text=text,
            voice_settings=VoiceSettings(
                stability=0.4,
                similarity_boost=0.8,
                style=0.3,
                use_speaker_boost=True,
            )
        )

        # Combine the stream into bytes
        audio_bytes = b"".join(chunk for chunk in audio_stream)

        return audio_bytes

    except Exception as e:
        err_msg = str(e)

        # Common ElevenLabs free-tier / auth failure pattern
        if "401" in err_msg or "Unusual activity detected" in err_msg or "detected_unusual_activity" in err_msg:
            raise RuntimeError(
                "ElevenLabs rejected the request (401 / unusual activity). "
                "Free tier may be blocked or API key invalid. Use a paid key or different account."
            ) from e

        # Generic fallback
        raise RuntimeError(f"Failed to generate audio from ElevenLabs: {err_msg}") from e
