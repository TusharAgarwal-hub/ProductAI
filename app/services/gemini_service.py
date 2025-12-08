import google.generativeai as genai
from dotenv import load_dotenv
import os
import re

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash-lite")


def clean_output(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([.,!?])", r"\1", text)

    return text.strip()


def generate_product_text(raw_text: str) -> str:

    prompt = f"""
    You are an AI that converts messy raw speech transcripts
    into structured product demo narration.

    RAW INPUT:
    {raw_text}

    OUTPUT RULES:
    - Add correct punctuation.
    - Remove filler words.
    - Keep narration concise and professional.
    - Keep action sequence IDENTICAL.
    - No hallucinated UI elements.
    - Single continuous paragraph.
    - NO newline characters at all.
    - Maintain similar character length.

    FINAL OUTPUT:
    """

    try:
        response = model.generate_content(prompt)
        cleaned_text = clean_output(response.text)
        return cleaned_text

    except Exception as e:
        return f"Error generating text: {str(e)}"
