import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

load_dotenv()

API_KEY = os.getenv("ELEVENLABS_API_KEY")

client = ElevenLabs(api_key=API_KEY) if API_KEY else None

DEFAULT_VOICE_ID = "TX3LPaxmHKxFdv7VOQHJ"
MODEL = "eleven_multilingual_v2"


def generate_voice_from_text(text: str, voice_id: str = DEFAULT_VOICE_ID) -> bytes:

    if not API_KEY or client is None:
        raise RuntimeError("ELEVENLABS_API_KEY missing")

    try:
        # realtime API always streams chunks
        stream = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id=MODEL,
            output_format="mp3_44100_128",
            voice_settings=VoiceSettings(
                stability=0.4,
                similarity_boost=0.8,
                style=0.3,
                use_speaker_boost=True,
            )
        )

        # join streaming chunks into a full mp3 byte blob
        audio_bytes = b"".join(chunk for chunk in stream)

        if not audio_bytes:
            raise RuntimeError("Empty audio response")

        return audio_bytes

    except Exception as e:
        raise RuntimeError(f"ElevenLabs error: {e}") from e
