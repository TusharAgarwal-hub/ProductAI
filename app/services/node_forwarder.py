import requests
import os

NODE_SERVER_URL = os.getenv("NODE_SERVER_URL") or "http://localhost:3000/api/test-audio"


def send_audio_to_node(audio_bytes: bytes, text: str):
    """
    Sends audio + cleaned text to Node.
    """
    try:
        print("[Python] Sending audio to Node.js server...")
        files = {
            "audio": ("output.mp3", audio_bytes, "audio/mpeg")
        }

        data = {"text": text}

        response = requests.post(NODE_SERVER_URL, data=data, files=files)
        return response.json()

    except Exception as e:
        return {"error": f"Failed to send audio to Node: {str(e)}"}
