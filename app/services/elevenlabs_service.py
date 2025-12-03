import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

load_dotenv()

API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Initialize ElevenLabs client
client = ElevenLabs(api_key=API_KEY)

# Default voice (you may change it later)
DEFAULT_VOICE_ID = "Xb7hH8MSUJpSbSDYk0k2"     # built-in free voice
MODEL = "eleven_multilingual_v2"  # best quality, supports many languages


def generate_voice_from_text(text: str, voice_id: str = DEFAULT_VOICE_ID) -> bytes:
    """
    Convert product demo text into realistic narrated audio.
    Returns raw audio bytes (mp3 format).
    """

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
        print("ElevenLabs TTS Error:", str(e))
        raise RuntimeError("Failed to generate audio from ElevenLabs.")
