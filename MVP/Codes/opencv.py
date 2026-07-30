import cv2
import numpy as np
import mediapipe as mp
import csv
import sys
import pygame
from collections import defaultdict
import math
import threading

import color_logger  # NEW: live HSV/RGB sampling + CSV logging

GREEN_LOWER = np.array([50, 100, 60])
GREEN_UPPER = np.array([84, 255, 255])

# === MULTIPLAYER: BLUE OBJECT TRACKING RANGE ===
# NOTE: your TV's green, under bright light, drifts into H=91-97 and
# V=190-237 -- both fully inside your old blue range. HSV alone can't
# separate the two colors here (their H/S/V distributions overlap too
# much), so the bounds below are intentionally loose. The real filtering
# now happens in get_blue_mask()'s blue-minus-green channel check.
BLUE_LOWER = np.array([85, 100, 100])
BLUE_UPPER = np.array([130, 255, 255])

# Minimum (B - G) raw channel gap required to count as "blue enough".
# Your real blue prop measured B-G in the 70-120 range; the TV's green
# measured B-G around 10-20. 30 sits safely between the two.
BLUE_GREEN_DIFF_THRESHOLD = 30


def get_blue_mask(bgr_frame, hsv_frame):
    """
    HSV thresholding alone can't distinguish this rig's blue prop from
    the TV's green under bright light -- their hue/saturation/value
    distributions overlap too much. This adds a raw-channel check
    (blue channel must clearly dominate green channel) on top of the
    HSV mask to kill the TV false-positives without also clipping real
    blue pixels.
    """
    hsv_mask = cv2.inRange(hsv_frame, BLUE_LOWER, BLUE_UPPER)

    b, g, r = cv2.split(bgr_frame)
    diff = cv2.subtract(b, g)  # uint8 subtract clips at 0, which is fine here
    _, diff_mask = cv2.threshold(diff, BLUE_GREEN_DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)

    return cv2.bitwise_and(hsv_mask, diff_mask)

mp_hands = mp.solutions.hands.Hands(
    static_image_mode=False,  
    max_num_hands=1,
    model_complexity=0,
    min_detection_confidence=0.90,
    min_tracking_confidence=0.90
)

# =================================================================
# === BACKGROUND CAMERA THREAD ===
# Reads frames continuously in a separate thread so cap.read()
# never blocks the main game loop.
# =================================================================
class CameraThread:
    def __init__(self, cap):
        self.cap = cap
        self.frame = None
        self.success = False
        self.lock = threading.Lock()
        self.running = True
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self):
        while self.running:
            ret, frame = self.cap.read()
            with self.lock:
                self.success = ret
                self.frame = frame

    def read(self):
        with self.lock:
            if self.frame is None:
                return False, None
            return self.success, self.frame.copy()

    def stop(self):
        self.running = False
        self.thread.join()

import cv2

def init_camera():
    print("[HARDWARE] Waking up USB WebCam pipeline...")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
        
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 60)

        # Wrap the camera in a background thread so reads never block
        camera_thread = CameraThread(cap)
        print("[HARDWARE] Camera thread started.")
        return camera_thread
    else:
        print("[ERROR] Could not open webcam source.")
        return None

def load_relational_gesture_csv(file_path="okhandsign.csv"):
    capture_groups = defaultdict(dict)
    try:
        with open(file_path, mode='r') as f:
            reader = csv.reader(f)
            header = [h.strip().lower() for h in next(reader, [])]
            try:
                idx_capture = header.index('capture_id')
                idx_x = header.index('x')
                idx_y = header.index('y')
                idx_z = header.index('z')
                idx_landmark = [i for i, h in enumerate(header) if 'landmark' in h][0]
            except (ValueError, IndexError):
                print("[ERROR] CSV layout mismatch! Check column naming definitions.")
                return []

            for row in reader:
                if not row: continue
                try:
                    c_id = row[idx_capture].strip()
                    lm_idx = int(row[idx_landmark].strip())
                    x_val = float(row[idx_x].strip())
                    y_val = float(row[idx_y].strip())
                    z_val = float(row[idx_z].strip())
                    capture_groups[c_id][lm_idx] = (x_val, y_val, z_val)
                except (ValueError, IndexError):
                    continue

        reference_vectors = []
        for c_id, landmarks in capture_groups.items():
            if len(landmarks) == 21:
                sorted_points = [landmarks[i] for i in range(21)]
                base_x, base_y, base_z = sorted_points[0]
                vector = []
                for x, y, z in sorted_points:
                    vector.extend([x - base_x, y - base_y, z - base_z])
                reference_vectors.append(vector)
        return reference_vectors
    except FileNotFoundError:
        print(f"[ERROR] '{file_path}' not found! Algorithmic fallback context active.")
        return []

def check_csv_thumbs_up(live_landmarks, reference_samples, threshold=0.35):
    thumb_is_up = live_landmarks[4].y < live_landmarks[3].y
    fingers_curled = (
        live_landmarks[8].y > live_landmarks[5].y and
        live_landmarks[12].y > live_landmarks[9].y and
        live_landmarks[16].y > live_landmarks[13].y and
        live_landmarks[20].y > live_landmarks[17].y
    )
    
    if not reference_samples:
        thumb_is_up = live_landmarks[4].y < live_landmarks[5].y
        fingers_curled = (live_landmarks[8].y > live_landmarks[5].y and
                          live_landmarks[12].y > live_landmarks[5].y)
        return thumb_is_up and fingers_curled

    base_x, base_y, base_z = live_landmarks[0].x, live_landmarks[0].y, live_landmarks[0].z
    live_vector = []
    for lm in live_landmarks:
        live_vector.extend([lm.x - base_x, lm.y - base_y, lm.z - base_z])
    live_arr = np.array(live_vector)
    
    for sample in reference_samples:
        sample_arr = np.array(sample)
        if len(sample_arr) == len(live_arr):
            if np.linalg.norm(live_arr - sample_arr) < threshold:
                return True
    return False

def process_cv_frame(cap, cursor_pos, width_max, height_max, run_skeletal_check=False, start_time_ms=None):
    """Processes webcam frames with color tracking and selective skeletal tracking.
    cap is now a CameraThread instance — reads return instantly from the latest frame.

    start_time_ms: optional — pass your game's start tick (e.g. the pygame.time.get_ticks()
    value from when the session/stage began) so color_logger's elapsed_ms column is
    meaningful. Safe to leave as None if you don't care about elapsed time.
    """
    global mp_hands

    # Non-blocking read from the background thread
    success, frame = cap.read()
    if not success or frame is None:
        return False, None, None, cursor_pos, None, False, None

    frame = cv2.flip(frame, 1)

    # NEW: take an untouched copy for color logging BEFORE any debug circles
    # get drawn on `frame` further down — those solid (0,255,0)/(180,0,220)
    # circles sit directly on top of the tracked object and would otherwise
    # contaminate the HSV/RGB sample with pure debug-marker color.
    frame_for_logging = frame.copy()

    # === 1. CAPTURE CLEAN RGB ARRAY FOR MEDIAPIPE BEFORE DRAWING ===
    rgb_check_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Convert to HSV for colour segmentation tracking
    hsv_roi = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # === 2. GREEN OBJECT TRACKING (P1 — ALWAYS RUNS) ===
    mask_green = cv2.inRange(hsv_roi, GREEN_LOWER, GREEN_UPPER)
    mask_green = cv2.erode(mask_green, None, iterations=2)
    mask_green = cv2.dilate(mask_green, None, iterations=2)

    contours_green, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    tracked_cursor = None
    size_alert = False
    largest_contour = None  # NEW: always defined, even if nothing detected this frame

    if contours_green:
        largest_contour = max(contours_green, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        MIN_PROP_SIZE = 800

        if area < MIN_PROP_SIZE:
            size_alert = True
        elif area < 150000:
            M = cv2.moments(largest_contour)
            if M["m00"] != 0:
                local_x = int(M["m10"] / M["m00"])
                local_y = int(M["m01"] / M["m00"])
                tracked_cursor = (int(local_x * (width_max / 640)), int(local_y * (height_max / 480)))
                cv2.circle(frame, (local_x, local_y), 15, (0, 255, 0), -1)

    # === 3. BLUE OBJECT TRACKING (P2 — ALWAYS RUNS) ===
    mask_blue = get_blue_mask(frame, hsv_roi)
    mask_blue = cv2.erode(mask_blue, None, iterations=2)
    mask_blue = cv2.dilate(mask_blue, None, iterations=2)

    contours_blue, _ = cv2.findContours(mask_blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    tracked_cursor_p2 = None
    largest_blue = None  # NEW: always defined, even if nothing detected this frame

    if contours_blue:
        largest_blue = max(contours_blue, key=cv2.contourArea)
        area_blue = cv2.contourArea(largest_blue)

        if area_blue >= 800 and area_blue < 150000:
            M2 = cv2.moments(largest_blue)
            if M2["m00"] != 0:
                local_px = int(M2["m10"] / M2["m00"])
                local_py = int(M2["m01"] / M2["m00"])
                tracked_cursor_p2 = (int(local_px * (width_max / 640)), int(local_py * (height_max / 480)))
                cv2.circle(frame, (local_px, local_py), 15, (180, 0, 220), -1)

    # === NEW: LIVE HSV/RGB COLOR LOGGING ===
    # Uses frame_for_logging (captured before any debug circles were drawn)
    # so the sampled pixels reflect the prop's real color under current
    # lighting, not the debug overlay marker color.
    color_logger.log_frame_colors(frame_for_logging, largest_contour, largest_blue, start_time_ms)

    # === 4. SELECTIVE SKELETAL TRACKING (ONLY RUNS ON DEMAND) ===
    hand_landmarks_list = None
    wrist_pixel_pos = None

    if run_skeletal_check:
        results = mp_hands.process(rgb_check_frame)
        
        if results.multi_hand_landmarks:
            hand_landmarks_list = results.multi_hand_landmarks[0]
            wrist = hand_landmarks_list.landmark[0]
            wrist_pixel_pos = (int(wrist.x * width_max), int(wrist.y * height_max))
            local_wx = int(wrist.x * 640)
            local_wy = int(wrist.y * 480)
            cv2.circle(frame, (local_wx, local_wy), 12, (0, 100, 255), -1)

    rgb_full_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    return True, rgb_full_frame, hand_landmarks_list, tracked_cursor, wrist_pixel_pos, size_alert, tracked_cursor_p2


def check_csv_ok_sign(landmarks, reference_landmarks, threshold=5.0):
    if landmarks is None:
        return False
        
    try:
        pinch_dist = math.hypot(landmarks[4].x - landmarks[8].x, landmarks[4].y - landmarks[8].y)
        knuckle_len = math.hypot(landmarks[6].x - landmarks[5].x, landmarks[6].y - landmarks[5].y)
        
        if knuckle_len > 0:
            is_pinching = (pinch_dist / knuckle_len) < 0.95
            mid_extended   = landmarks[12].y < landmarks[9].y
            ring_extended  = landmarks[16].y < landmarks[13].y
            pinky_extended = landmarks[20].y < landmarks[17].y
            
            if is_pinching and mid_extended and ring_extended and pinky_extended:
                return True

    except Exception as e:
        print(f"[RELAXED GESTURE ERROR] {e}")
        return False
        
    return False
