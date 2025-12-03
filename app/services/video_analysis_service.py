import cv2
import numpy as np
import pytesseract
from typing import List, Dict
import os

# Configure Tesseract (optional path override)
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_PATH", "tesseract")


def detect_clicks(frame):
    """
    Detect clickable UI elements using template matching + edge detection.
    Returns list of bounding boxes.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Detect edges (helps find button-like shapes)
    edges = cv2.Canny(gray, 80, 160)

    # Find contours → likely buttons / inputs
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    click_regions = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)

        # Ignore very small or very large regions
        if w < 40 or h < 20 or w > 500 or h > 200:
            continue

        aspect_ratio = w / float(h)
        if 1.5 < aspect_ratio < 6:  # heuristic for button-like shapes
            click_regions.append({"x": x, "y": y, "w": w, "h": h})

    return click_regions


def selective_ocr(frame, regions):
    """
    Extract text only from detected clickable / interactive regions.
    """
    results = []

    for r in regions:
        x, y, w, h = r["x"], r["y"], r["w"], r["h"]
        crop = frame[y:y+h, x:x+w]

        text = pytesseract.image_to_string(crop).strip()

        if text:
            results.append({
                "text": text,
                "bbox": r
            })

    return results


def process_video(video_path: str) -> Dict:
    """
    MASTER FUNCTION:
    - Iterates through frames
    - Detects clickable elements
    - Extracts button/input labels
    - Captures UI change events
    - Returns an event timeline to Next.js frontend
    """

    cap = cv2.VideoCapture(video_path)
    frame_idx = 0

    events = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        clickable = detect_clicks(frame)
        ocr_texts = selective_ocr(frame, clickable)

        events.append({
            "frame": frame_idx,
            "clickable_regions": clickable,
            "detected_text": ocr_texts
        })

        frame_idx += 1

    cap.release()

    return {
        "total_frames": frame_idx,
        "events": events
    }
