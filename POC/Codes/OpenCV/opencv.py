import cv2
import numpy as np
import mediapipe as mp
import csv
import sys
import pygame
from collections import defaultdict
import math

GREEN_LOWER = np.array([35, 100, 100])
GREEN_UPPER = np.array([85, 255, 255])

# === MULTIPLAYER: PURPLE OBJECT TRACKING RANGE ===
PURPLE_LOWER = np.array([130, 100, 100])
PURPLE_UPPER = np.array([155, 255, 255])

mp_hands = mp.solutions.hands.Hands(
    static_image_mode=False,       # Live video mode
    max_num_hands=1,               # Single player optimization
    model_complexity=0,            # 0 = Fastest/Most forgiving tracker, 1 = Heavy/Strict
    min_detection_confidence=0.90,  # Loosened from 0.50 -> Aggressive tracking
    min_tracking_confidence=0.90   # Loosened from 0.50
)

import cv2

def init_camera():
    print("[HARDWARE] Waking up USB WebCam pipeline...")
    # Initialize the camera using DirectShow (which matched our successful test script)
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
        
    if cap.isOpened():
        # Apply the exact same resolution settings from our successful test script
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Explicitly request 60 FPS if the hardware supports it
        cap.set(cv2.CAP_PROP_FPS, 60) 
        
        return cap
    else:
        print("[ERROR] Could not open webcam source.")
        return None
    
def load_relational_gesture_csv(file_path="thumbsup.csv"):
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

    # 1. ENFORCE HARD ANATOMICAL RULES (Blocks open hands or flat palms)
    # Check if the thumb tip (4) is higher than the thumb joint (3)
    thumb_is_up = live_landmarks[4].y < live_landmarks[3].y
    
    # Check if the tips of fingers (8, 12, 16, 20) are curled BELOW their base joints (5, 9, 13, 17)
    fingers_curled = (
        live_landmarks[8].y > live_landmarks[5].y and   # Index finger curled
        live_landmarks[12].y > live_landmarks[9].y and  # Middle finger curled
        live_landmarks[16].y > live_landmarks[13].y and # Ring finger curled
        live_landmarks[20].y > live_landmarks[17].y     # Pinky finger curled
    )
    
    if not reference_samples:
        # High-range fallback: Is thumb tip higher than index knuckle, and are other fingers curled below index knuckle?
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

def process_cv_frame(cap, cursor_pos, width_max, height_max, run_skeletal_check=False):
    """Processes webcam frames with color tracking and selective skeletal tracking."""
    global mp_hands  # Explicitly declare global access to the initialized ML model
    
    success, frame = cap.read()
    if not success or frame is None:
        return False, None, None, cursor_pos, None, False, None

    frame = cv2.flip(frame, 1)

    # === 1. CAPTURE CLEAN RGB ARRAY FOR MEDIAPIPE BEFORE DRAWING ===
    # We convert the pristine frame to RGB *immediately* so MediaPipe gets a perfect,
    # un-altered image of your hand without any digital crosshair circles drawn on it.
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
                
                # Draw the green dot on the frame AFTER copying it for MediaPipe
                cv2.circle(frame, (local_x, local_y), 15, (0, 255, 0), -1)

    # === 3. PURPLE OBJECT TRACKING (P2 — ALWAYS RUNS) ===
    mask_purple = cv2.inRange(hsv_roi, PURPLE_LOWER, PURPLE_UPPER)
    mask_purple = cv2.erode(mask_purple, None, iterations=2)
    mask_purple = cv2.dilate(mask_purple, None, iterations=2)

    contours_purple, _ = cv2.findContours(mask_purple, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    tracked_cursor_p2 = None

    if contours_purple:
        largest_purple = max(contours_purple, key=cv2.contourArea)
        area_purple = cv2.contourArea(largest_purple)

        if area_purple >= 800 and area_purple < 150000:
            M2 = cv2.moments(largest_purple)
            if M2["m00"] != 0:
                local_px = int(M2["m10"] / M2["m00"])
                local_py = int(M2["m01"] / M2["m00"])

                tracked_cursor_p2 = (int(local_px * (width_max / 640)), int(local_py * (height_max / 480)))

                # Draw a purple dot on the debug camera preview
                cv2.circle(frame, (local_px, local_py), 15, (180, 0, 220), -1)

    # === 4. SELECTIVE SKELETAL TRACKING (ONLY RUNS ON DEMAND) ===
    hand_landmarks_list = None
    wrist_pixel_pos = None

    if run_skeletal_check:
        # Feed the clean, circle-free RGB frame into the processor
        results = mp_hands.process(rgb_check_frame)
        
        if results.multi_hand_landmarks:
            # Grab the landmarks for the first detected hand
            hand_landmarks_list = results.multi_hand_landmarks[0]
            
            # Extract the wrist point (Landmark 0) and project it onto display dimensions
            wrist = hand_landmarks_list.landmark[0]
            wrist_pixel_pos = (int(wrist.x * width_max), int(wrist.y * height_max))

            # Draw the orange wrist circle indicator onto the display frame array
            local_wx = int(wrist.x * 640)
            local_wy = int(wrist.y * 480)
            cv2.circle(frame, (local_wx, local_wy), 12, (0, 100, 255), -1)

    # Final RGB transformation pass for the Pygame preview window surface
    rgb_full_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    return True, rgb_full_frame, hand_landmarks_list, tracked_cursor, wrist_pixel_pos, size_alert, tracked_cursor_p2


def check_csv_ok_sign(landmarks, reference_landmarks, threshold=5.0):
    """
    Bypasses rigid absolute CSV coordinate checks.
    Evaluates relative hand geometry to ensure an OK sign is formed,
    making the gesture highly reliable across all camera distances.
    """
    if landmarks is None:
        return False
        
    try:
        # 1. Measure the index-tip (8) to thumb-tip (4) pinch distance
        pinch_dist = math.hypot(landmarks[4].x - landmarks[8].x, landmarks[4].y - landmarks[8].y)
        
        # Normalize the distance using your index knuckle length so it scales with your distance from camera
        knuckle_len = math.hypot(landmarks[6].x - landmarks[5].x, landmarks[6].y - landmarks[5].y)
        
        if knuckle_len > 0:
            # A low ratio means thumb and index tips are firmly pinched together forming the "O"
            is_pinching = (pinch_dist / knuckle_len) < 0.95
            
            # 2. Check if the remaining three fingers are standing upward (The "K" part of OK)
            # In MediaPipe, smaller Y values are higher up on the screen.
            mid_extended   = landmarks[12].y < landmarks[9].y
            ring_extended  = landmarks[16].y < landmarks[13].y
            pinky_extended = landmarks[20].y < landmarks[17].y
            
            # If your hand matches the structural OK pose shape, automatically accept it!
            if is_pinching and mid_extended and ring_extended and pinky_extended:
                return True

    except Exception as e:
        print(f"[RELAXED GESTURE ERROR] {e}")
        return False
        
    return False
        
    average_error = total_difference / 21
    
    # Debug tracking to see your exact closeness score in the console
    # Lower value means a closer match to your training profile!
    print(f"[GESTURE MATCH] Current Distance Score: {average_error:.4f} (Needs to be below {threshold})")
    
    return average_error < threshold