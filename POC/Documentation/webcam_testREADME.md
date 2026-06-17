# webcam_diagnostic.py README

---

This is a standalone troubleshooting script, separate from the main game. It isn't called by `main.py` — it's meant to be run on its own when the webcam isn't being detected, to figure out whether the problem is the hardware, the driver, or something else blocking access to it.

```python
import cv2
import sys
import time
```

### What each library does:

| Library | Function |
| :--- | :--- |
| `import cv2` | OpenCV, the library actually responsible for talking to the webcam — opening it, reading frames from it, and displaying a preview window. |
| `import sys` | Used to immediately exit the script if the webcam fails to open at all. |
| `import time` | Used to pause the script for a few seconds so the user has time to check if the webcam's hardware light turns on. |

## Section 1: Opening the Camera

```python
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if not cap.isOpened():
    cap = cv2.VideoCapture(0)
```

The script first tries to open camera index 0 using the DirectShow backend, which tends to be the more reliable option for USB webcams on Windows. If that fails, it tries again using OpenCV's default backend instead, in case DirectShow itself is the problem rather than the camera.

If both attempts fail, the script prints a list of likely causes — another app already using the camera, Windows privacy settings blocking access, or a stuck driver — and exits immediately rather than continuing.

## Section 2: Forcing the Hardware to Wake Up

```python
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
```

Even after the camera reports as "open," some USB webcams stay in a low-power state until a resolution is explicitly requested. Setting the width and height here is meant to nudge the hardware to fully power on. The script then waits 3 seconds with a countdown, giving the user time to physically check whether the camera's indicator light has turned on.

## Section 3: Reading a Test Frame

```python
success, frame = cap.read()
```

This attempts to pull a single frame from the camera. The result tells the script which of two failure modes it's dealing with:

- If `success` is `True`, the camera is actually working — it prints the frame's resolution and moves on to the live preview.
- If `success` is `False`, the camera was detected by the system but isn't actually streaming usable video data, which usually points to a driver issue rather than a connection issue.

## Section 4: Live Preview Window

```python
while True:
    ret, live_frame = cap.read()
    cv2.imshow("Webcam Diagnostic Test Window", live_frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q') or key == 27:
        break
```

If the test frame succeeded, the script opens a separate window (outside of Pygame) showing the raw, live webcam feed, so the user can visually confirm the camera is working properly. This loop continues reading and displaying frames until the user presses `q` or `Esc`, or until a frame fails to read, at which point it prints a warning and stops.

## Section 5: Cleanup

```python
cap.release()
cv2.destroyAllWindows()
```

Regardless of whether the test succeeded or failed, the script releases the camera and closes any OpenCV windows before printing a final "DIAGNOSTIC TEST COMPLETE" message, so the webcam isn't left locked by this script after it finishes.

## Function Summary

| Function | Purpose |
| :--- | :--- |
| `run_isolated_test()` | Opens the webcam, checks if it powers on and streams real frames, shows a live preview if successful, and reports the likely cause if any step fails. |
