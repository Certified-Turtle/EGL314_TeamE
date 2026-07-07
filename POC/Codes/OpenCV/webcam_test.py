import cv2
import sys
import time

def run_isolated_test():
    print("==================================================")
    print("         USB WEBCAM ISOLATED DIAGNOSTIC          ")
    print("==================================================")
    
    # 1. Attempt connection using the DirectShow backend (Best for Windows USB)
    print("[STEP 1] Initializing VideoCapture port 0 with DirectShow...")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    # Fallback to default backend if DirectShow fails
    if not cap.isOpened():
        print("[INFO] DirectShow failed. Retrying with default system backend...")
        cap = cv2.VideoCapture(0)
        
    # 2. Check if hardware pipeline successfully connected
    if not cap.isOpened():
        print("\n[CRITICAL ERROR] Windows refused to open VideoCapture(0).")
        print("-> Potential Causes:")
        print("   1. Another app (Discord, Zoom, Chrome, OBS) is currently using your webcam.")
        print("   2. Windows Privacy Settings are blocking Visual Studio Code / Python.")
        print("   3. Your webcam driver is locked up. Try unplugging and replugging the USB.")
        sys.exit()
        
    print("[SUCCESS] Hardware pipeline link established!")
    
    # 3. Force stream properties to nudge the USB hardware power hub
    print("[STEP 2] Sending resolution request to force hardware power-on...")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("\n>>> LOOK AT YOUR WEBCAM RIGHT NOW <<<")
    print("Did the physical hardware indicator light turn on? (Checking for 3 seconds...)")
    
    # Give the hardware a brief window to warm up its sensors
    for i in range(3, 0, -1):
        print(f"Waiting... {i}")
        time.sleep(1)
        
    # 4. Attempt to grab a live frame matrix
    print("\n[STEP 3] Attempting to read a test frame...")
    success, frame = cap.read()
    
    if success:
        print("[SUCCESS] Successfully read pixels from your webcam!")
        print(f"Captured Frame Resolution: {frame.shape[1]}x{frame.shape[0]}")
        print("\n[STEP 4] Opening diagnostic preview window. Press 'q' or 'ESC' on your keyboard to close it.")
        
        # Keep displaying the raw webcam feed in a lightweight window
        while True:
            ret, live_frame = cap.read()
            if not ret:
                print("[WARNING] Frame drop detected during live stream preview.")
                break
                
            # Render the raw camera window outside of Pygame
            cv2.imshow("Webcam Diagnostic Test Window", live_frame)
            
            # Break loop on 'q' key or ESC key press
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
    else:
        print("\n[CRITICAL ERROR] Camera channel opened, but frame retrieval returned nothing (NoneType).")
        print("Your computer detects the USB device plug, but the device is failing to stream visual data.")

    # Clean up the hardware footprints completely on termination
    cap.release()
    cv2.destroyAllWindows()
    print("\n==================================================")
    print("            DIAGNOSTIC TEST COMPLETE              ")
    print("==================================================")

if __name__ == "__main__":
    run_isolated_test()