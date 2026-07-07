"""
Purple Object Detector + HSV Sampler
-------------------------------------
- Left-click anywhere on the video feed to print that pixel's HSV value
  (great for sampling your purple tape under your actual lighting).
- Live mask shows what's currently being detected as "purple" based on
  the PURPLE_LOWER / PURPLE_UPPER thresholds below.
- Press 'q' to quit, 's' to save a snapshot of the current frame.

Controls:
  q - quit
  s - save current frame + mask to disk
  c - print the average HSV of the last clicked region (5x5 box)
"""

import cv2
import numpy as np

# Starting thresholds - tune these based on what you sample below
PURPLE_LOWER = np.array([125, 40, 40])
PURPLE_UPPER = np.array([160, 255, 255])

# Global state for mouse callback
clicked_point = None
hsv_frame_global = None

# Smoothing state for the bounding box (reduces jitter)
smoothed_box = None  # (x, y, w, h) as floats
SMOOTHING_ALPHA = 0.3  # lower = smoother/slower to react, higher = snappier/more jitter


def mouse_callback(event, x, y, flags, param):
    global clicked_point
    if event == cv2.EVENT_LBUTTONDOWN:
        clicked_point = (x, y)
        if hsv_frame_global is not None:
            h, s, v = hsv_frame_global[y, x]
            print(f"Clicked at ({x}, {y}) -> HSV: ({h}, {s}, {v})")

            # Also print average of a small neighborhood, more reliable than 1 px
            region = hsv_frame_global[max(0, y-2):y+3, max(0, x-2):x+3]
            avg_h = int(np.mean(region[:, :, 0]))
            avg_s = int(np.mean(region[:, :, 1]))
            avg_v = int(np.mean(region[:, :, 2]))
            print(f"  5x5 avg HSV: ({avg_h}, {avg_s}, {avg_v})")


def main():
    global hsv_frame_global

    cap = cv2.VideoCapture(0)  # change index if you have multiple cameras

    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    cv2.namedWindow("Camera Feed")
    cv2.setMouseCallback("Camera Feed", mouse_callback)

    print("Instructions:")
    print(" - Click on the purple object to print its HSV value")
    print(" - Press 'q' to quit, 's' to save a snapshot")
    print(f" - Current thresholds: LOWER={PURPLE_LOWER.tolist()} UPPER={PURPLE_UPPER.tolist()}")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to grab frame.")
            break

        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hsv_frame_global = hsv_frame

        # Slight blur before thresholding smooths out per-pixel sensor noise,
        # which is a major source of jittery mask edges/contours
        hsv_blurred = cv2.GaussianBlur(hsv_frame, (5, 5), 0)

        # Build mask + clean it up
        mask = cv2.inRange(hsv_blurred, PURPLE_LOWER, PURPLE_UPPER)
        # Stronger morphology: opening removes small noise specks,
        # closing fills small holes so the blob shape is more stable frame-to-frame
        kernel = np.ones((7, 7), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Find contours and draw the largest one (assume that's your object)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        display_frame = frame.copy()

        global smoothed_box

        if contours:
            largest = max(contours, key=cv2.contourArea)
            if cv2.contourArea(largest) > 500:  # ignore small noise blobs (raised from 200)
                x, y, w, h = cv2.boundingRect(largest)

                # Exponential moving average smoothing on box coordinates.
                # This is what actually kills jitter: instead of drawing the
                # raw (noisy) box every frame, we ease toward the new
                # position each frame.
                if smoothed_box is None:
                    smoothed_box = np.array([x, y, w, h], dtype=float)
                else:
                    new_box = np.array([x, y, w, h], dtype=float)
                    smoothed_box = (SMOOTHING_ALPHA * new_box +
                                     (1 - SMOOTHING_ALPHA) * smoothed_box)

                sx, sy, sw, sh = smoothed_box.astype(int)
                cv2.rectangle(display_frame, (sx, sy), (sx + sw, sy + sh), (0, 255, 0), 2)
                cx, cy = sx + sw // 2, sy + sh // 2
                cv2.circle(display_frame, (cx, cy), 5, (0, 0, 255), -1)
                cv2.putText(display_frame, "Purple Object", (sx, sy - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            else:
                smoothed_box = None  # object lost, reset so it doesn't ease from stale position
        else:
            smoothed_box = None

        # Show where you last clicked
        if clicked_point:
            cv2.circle(display_frame, clicked_point, 6, (0, 255, 255), 2)

        # Overlay current threshold values on screen
        cv2.putText(display_frame, f"LOWER: {PURPLE_LOWER.tolist()}", (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(display_frame, f"UPPER: {PURPLE_UPPER.tolist()}", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.imshow("Camera Feed", display_frame)
        cv2.imshow("Purple Mask", mask)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            cv2.imwrite("snapshot_frame.png", display_frame)
            cv2.imwrite("snapshot_mask.png", mask)
            print("Saved snapshot_frame.png and snapshot_mask.png")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()