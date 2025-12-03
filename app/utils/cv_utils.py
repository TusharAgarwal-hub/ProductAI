import cv2
import numpy as np

def extract_frames(video_path: str, step: int = 5):
    """
    Extract 1 frame every `step` frames.
    Faster + enough accuracy for UI interactions.
    """
    cap = cv2.VideoCapture(video_path)
    frames = []
    frame_index = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_index % step == 0:
            timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            frames.append((timestamp, frame))

        frame_index += 1

    cap.release()
    return frames


def detect_click(frame):
    """
    Very lightweight click detection using simple heuristics:
    - Look for cursor presence
    - Look for cursor 'press' state (smaller pointer)
    - Look for cursor blur from movement -> click event stops motion
    """

    # You will later point this to your mouse template
    cursor_template = cv2.imread("app/assets/cursor.png", 0)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    result = cv2.matchTemplate(gray, cursor_template, cv2.TM_CCOEFF_NORMED)
    (_, max_val, _, max_loc) = cv2.minMaxLoc(result)

    if max_val > 0.70:
        return True, max_loc  # cursor found
    return False, None
