import pytesseract
import cv2

def selective_ocr(frame):
    """
    Performs OCR **only on detected UI text regions**.
    Very fast compared to full frame OCR.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Detect high contrast regions → assume text is there
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

    # Find contours → potential text blocks
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detected_text = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)

        if w < 40 or h < 15:
            continue  # ignore small noise

        roi = gray[y:y+h, x:x+w]
        text = pytesseract.image_to_string(roi).strip()

        if text:
            detected_text.append({"bbox": (x, y, w, h), "text": text})

    return detected_text
