import pygame
import pygame.gfxdraw
import random
import sys
import os
import math
import time

# Import modularized components
import designs
import opencv
import start_button
import tutorial
import gameplay
import restart_quit
import addons 
import config
from pythonosc import udp_client
import lighting
import audio
import assets

# =================================================================
# === 1. CONFIGURATION STAGE & PERFORMANCE CANVAS RESCALING ===
# =================================================================
osc_client = None
print("[INFO] Running in safe, local-only offline mode.")

os.environ['SDL_RENDER_SCALE_QUALITY'] = 'linear'
pygame.init()

# =================================================================
# === MULTI-MONITOR DETECTION (EXTENDED DESKTOP MODE) ===
# =================================================================
desktop_sizes = pygame.display.get_desktop_sizes()
print(f"[DISPLAY] Detected {len(desktop_sizes)} monitor(s): {desktop_sizes}")

# Change this index to target whichever monitor is your projector/second screen.
# 0 = primary, 1 = secondary, etc. Windows must already be set to
# "Extend these displays" (not "Duplicate") in Display Settings for this to work.
TARGET_DISPLAY_INDEX = 1

if TARGET_DISPLAY_INDEX >= len(desktop_sizes):
    print(f"[DISPLAY] WARNING: Display index {TARGET_DISPLAY_INDEX} not found — "
          f"only {len(desktop_sizes)} monitor(s) detected. Falling back to display 0.")
    TARGET_DISPLAY_INDEX = 0

NATIVE_WIDTH, NATIVE_HEIGHT = desktop_sizes[TARGET_DISPLAY_INDEX]

# Build the borderless window on the CHOSEN monitor
real_screen = pygame.display.set_mode(
    (NATIVE_WIDTH, NATIVE_HEIGHT),
    pygame.NOFRAME | pygame.DOUBLEBUF,
    display=TARGET_DISPLAY_INDEX
)

WIDTH, HEIGHT = 1920, 1080
screen = pygame.Surface((WIDTH, HEIGHT))

# Build the borderless window container across the native screen pixels
real_screen = pygame.display.set_mode(
    (NATIVE_WIDTH, NATIVE_HEIGHT), 
    pygame.NOFRAME | pygame.DOUBLEBUF
)

# Instantiate the virtual canvas surface that all your modules draw onto
screen = pygame.Surface((WIDTH, HEIGHT))

# Create a dedicated transparent scratchpad surface for the vortex death animations
designs.vortex_scratch_surf = pygame.Surface((300, 150), pygame.SRCALPHA)

pygame.display.set_caption("Training Simulation: Phantom Sweep")
clock = pygame.time.Clock()

active_entity_type = "GHOST"   # "GHOST" or "DECOY"

designs.init_assets()
assets.init_assets()

ui_font = pygame.font.SysFont("Courier New", 36, bold=True)
title_font = pygame.font.SysFont("Courier New", 68, bold=True)
countdown_font = pygame.font.SysFont("Courier New", 180, bold=True)

# =================================================================
# === 2. GAME STATE VARIABLE COMPARTMENTS ===
# =================================================================
PHASE_INTRO = -1
PHASE_TUTORIAL = 0
PHASE_INSTRUCT = 1
PHASE_PREPARE = 2
PHASE_GAMEPLAY = 3
PHASE_GAMEOVER = 4
PHASE_TUTORIAL_MP = 5    # Multiplayer combined training session
PHASE_STAGE_CLEAR = 6    # Between-stage screen with score + hover to continue

game_phase = PHASE_INTRO  
tutorial_count = 0
mp_tutorial_count = 0    # Combined hit counter for multiplayer training
hover_start_progress = 0

# === STAGE SYSTEM ===
current_stage = 1                          # 1, 2, or 3
STAGE_DURATION = 30                        # Seconds per stage
STAGE_TARGETS = {1: 30, 2: 20, 3: 10}    # Score needed to pass each stage
STAGE_SPEEDS = {1: 1300, 2: 750, 3: 250}  # Move interval ms — noticeably faster each stage
stage_clear_hover = 0                      # Hover progress for stage clear button
stage_passed = False                       # Whether player hit the target this stage

score, time_left, start_ticks, current_hole, game_over = restart_quit.reset_game()
last_move_time = pygame.time.get_ticks()
ghost_y_offset = 0
ghost_state = "UP"
death_sequences = []

AUDIO_LAPTOP_IP = "192.168.254.12" 
audio_sender = udp_client.SimpleUDPClient(AUDIO_LAPTOP_IP, 9000) #Edit IP and port as needed

# LIGHTING_LAPTOP_IP and lighting_sender removed — lighting.py manages its own connection

total_ghosts_spawned = 0
total_decoys_spawned = 0

show_debug_camera = True

# === MULTIPLAYER STATE ===
multiplayer_mode = True
cursor_vector_p2 = pygame.math.Vector2(WIDTH // 2, HEIGHT // 2)
velocity_vector_p2 = pygame.math.Vector2(0, 0)
cursor_pos_p2 = [int(cursor_vector_p2.x), int(cursor_vector_p2.y)]
object_was_visible_p2 = False
last_frame_pos_p2 = pygame.math.Vector2(WIDTH // 2, HEIGHT // 2)

# === MULTIPLAYER TRACKING LOCK STATE ===
# Freezes gameplay when either object is lost from camera view
mp_tracking_locked = False       # True = game is frozen waiting for objects to return
mp_lock_start_time = 0           # When the lock began (used to freeze the ghost timer)
mp_ghost_timer_debt = 0          # Accumulated frozen time to add back to last_move_time

# === NEW: CONTROLLED SPAWN POOL ===
# === VERIFIED FIXED LAYOUT DECK ===
# Exactly 50 GHOSTS, exactly 7 DECOYS. Total = 57 elements.
spawn_pool = [
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",   # Decoy 1 (Index 6)
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",   # Decoy 2 (Index 13)
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",   # Decoy 3 (Index 20)
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",   # Decoy 4 (Index 27)
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",   # Decoy 5 (Index 34)
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",   # Decoy 6 (Index 41)
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",   # Decoy 7 (Index 48)
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",   # Clean Run to finish (49-55)
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY", 
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY", 
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY", 
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY", 
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY", 
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY", 
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY", 
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY", 
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       # Final element (56)
]
pool_pointer = 0

lightning_active, lightning_trigger_time, lightning_duration = False, 0, 0

# === PAUSE STATE ===
is_paused = False
pause_start_time = 0
pause_time_debt = 0

cursor_vector = pygame.math.Vector2(WIDTH // 2, HEIGHT // 2)
velocity_vector = pygame.math.Vector2(0, 0)

# Keep your original cursor list format for compatibility with other modules
cursor_pos = [int(cursor_vector.x), int(cursor_vector.y)]

cap = None
reference_ok_sign = None  # Holds data from okhandsign.csv
camera_fully_initialized = False
camera_trigger_time = None  # CHANGED: Use None as an explicit "not started yet" state

# --- 3. MAIN RUNTIME LOOP ---
while True:
    now = pygame.time.get_ticks()

    # === ASYNCHRONOUS CAMERA DELAY ENGINE ===
    if not camera_fully_initialized:
        # CHANGED: Capture time ONCE. Do not update it again.
        if camera_trigger_time is None:
            camera_trigger_time = now
        
        # Keep window alive and rendering while waiting
        screen.fill((10, 8, 20))
        loading_txt = ui_font.render("Loading Whack-A-Ghost...", True, (100, 90, 120))
        screen.blit(loading_txt, (WIDTH // 2 - 280, HEIGHT // 2))
        
        # Project to your monitor screen
        scaled_surface = pygame.transform.smoothscale(screen, (NATIVE_WIDTH, NATIVE_HEIGHT))
        real_screen.blit(scaled_surface, (0, 0))
        pygame.display.flip()

        # Check for window exit events even while loading to prevent OS "Not Responding" hangs
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                lighting.on_game_close()             # ← LIGHTING: all lights off before exit
                pygame.quit(); sys.exit()
        
        # Once 1 second passes, safely inject the camera stream
        if now - camera_trigger_time > 1000:
            cap = opencv.init_camera()
            reference_ok_sign = opencv.load_relational_gesture_csv("okhandsign.csv")
            camera_fully_initialized = True
            lighting.init()                          # ← LIGHTING: spooky atmosphere + spotlight on load
            last_move_time = pygame.time.get_ticks()
        
        clock.tick(60)
        continue  # Skip processing the rest of the loop until camera initialization finishes
    


    # Scenery routing mapping
    is_tutorial_scene = game_phase in [PHASE_TUTORIAL, PHASE_TUTORIAL_MP, PHASE_INSTRUCT, PHASE_PREPARE]
    if game_phase in [PHASE_INTRO]:
        screen.fill((10, 8, 20))
    elif game_phase == PHASE_STAGE_CLEAR:
        designs.draw_haunted_house(screen, lightning_active)
    elif is_tutorial_scene:
        designs.draw_library(screen, lightning_active)
    else:
        designs.draw_haunted_house(screen, lightning_active)
        
    # =================================================================
    # === COMPRESSED COMPUTER VISION PIPELINE MATRIX ===
    # =================================================================
    # Tell opencv.py to ONLY run heavy MediaPipe skeleton tracking during PHASE_INSTRUCT
    need_hand_skeleton = (game_phase == PHASE_INSTRUCT)
    
    cv_data = opencv.process_cv_frame(
        cap, 
        list(cursor_pos), 
        WIDTH, 
        HEIGHT, 
        run_skeletal_check=need_hand_skeleton
    )
    
    rgb_frame = None
    hands_obj = None
    tracked_cursor = None
    tracked_cursor_p2 = None
    wrist_pos = None
    is_too_small = False

    if cv_data and cv_data[0]:
        rgb_frame = cv_data[1]        # Crisp RGB frame array
        hands_obj = cv_data[2]        # Contains MediaPipe hand landmarks if requested
        tracked_cursor = cv_data[3]   # Green object tracking position
        wrist_pos = cv_data[4]        # Wrist position mapping pixel coordinates
        is_too_small = cv_data[5]     # Size alert flag

        # === PURPLE OBJECT TRACKING (MULTIPLAYER P2) ===
        if multiplayer_mode and len(cv_data) > 6:
            tracked_cursor_p2 = cv_data[6]

        # === HIGH-SPEED BOUNDARY VALIDATION LOCK ===
        # Initialize visibility tracking states at boot level if not present
        if 'object_was_visible' not in locals() and 'object_was_visible' not in globals():
            global object_was_visible, last_frame_pos
            object_was_visible = False
            last_frame_pos = pygame.math.Vector2(WIDTH // 2, HEIGHT // 2)

        # === FIXED PHASE-AWARE BOUNDARY VALIDATION LOCK (P1 - GREEN) ===
        if tracked_cursor is not None and not is_too_small:
            green_obj_vec = pygame.math.Vector2(tracked_cursor[0], tracked_cursor[1])
            
            # --- OVERRIDE GATE FOR INSTRUCTION SCREEN ---
            if game_phase == PHASE_INSTRUCT:
                target_vector = green_obj_vec
                raw_displacement = target_vector - cursor_vector
                velocity_vector = velocity_vector.lerp(raw_displacement, 0.70)
                cursor_vector = cursor_vector.lerp(target_vector, 0.65)
                last_frame_pos = green_obj_vec
                object_was_visible = True
            
            else:
                # --- STRICT GAMEPLAY MODE (PHASE_TUTORIAL & PHASE_GAMEPLAY) ---
                if not object_was_visible:
                    last_frame_pos = green_obj_vec
                    object_was_visible = True  
                
                frame_to_frame_distance = green_obj_vec.distance_to(last_frame_pos)
                
                if frame_to_frame_distance < 300:
                    target_vector = green_obj_vec
                    raw_displacement = target_vector - cursor_vector
                    velocity_vector = velocity_vector.lerp(raw_displacement, 0.70)
                    cursor_vector = cursor_vector.lerp(target_vector, 0.65)
                    last_frame_pos = pygame.math.Vector2(cursor_vector.x, cursor_vector.y)
                else:
                    velocity_vector *= 0.0
        else:
            object_was_visible = False
            velocity_vector *= 0.0

        # Sync P1 coordinate positions back down to drawing arrays
        cursor_pos[0] = int(cursor_vector.x)
        cursor_pos[1] = int(cursor_vector.y)

        # === P2 CURSOR SMOOTHING (PURPLE OBJECT) ===
        if multiplayer_mode:
            if tracked_cursor_p2 is not None:
                p2_vec = pygame.math.Vector2(tracked_cursor_p2[0], tracked_cursor_p2[1])
                if not object_was_visible_p2:
                    last_frame_pos_p2 = p2_vec
                    object_was_visible_p2 = True
                dist_p2 = p2_vec.distance_to(last_frame_pos_p2)
                if dist_p2 < 300:
                    velocity_vector_p2 = velocity_vector_p2.lerp(p2_vec - cursor_vector_p2, 0.70)
                    cursor_vector_p2 = cursor_vector_p2.lerp(p2_vec, 0.65)
                    last_frame_pos_p2 = pygame.math.Vector2(cursor_vector_p2.x, cursor_vector_p2.y)
                else:
                    velocity_vector_p2 *= 0.0
            else:
                object_was_visible_p2 = False
                velocity_vector_p2 *= 0.0
            cursor_pos_p2[0] = int(cursor_vector_p2.x)
            cursor_pos_p2[1] = int(cursor_vector_p2.y)

    # =================================================================
    # === MULTIPLAYER TRACKING LOCK ENGINE ===
    # Freezes gameplay if either object drops out of camera view.
    # Automatically unfreezes the moment both are visible again.
    # Only active during PHASE_GAMEPLAY when multiplayer_mode is on.
    # =================================================================
    if multiplayer_mode and game_phase == PHASE_GAMEPLAY:
        p1_visible = tracked_cursor is not None and not is_too_small
        p2_visible = tracked_cursor_p2 is not None

        both_visible = p1_visible and p2_visible

        if not both_visible:
            # === LOCK: One or both objects lost ===
            if not mp_tracking_locked:
                # First frame of loss — record when the freeze began
                mp_tracking_locked = True
                mp_lock_start_time = now
                print(f"[TRACKING LOCK] Object lost — game frozen. P1:{p1_visible} P2:{p2_visible}")
            else:
                # Still locked — keep accumulating the frozen debt so the ghost timer
                # doesn't tick down while players can't see what they're doing
                mp_ghost_timer_debt = now - mp_lock_start_time
        else:
            # === UNLOCK: Both objects back in view ===
            if mp_tracking_locked:
                mp_tracking_locked = False
                # Push last_move_time forward by the frozen duration so the ghost
                # doesn't immediately vanish the moment tracking resumes
                last_move_time += mp_ghost_timer_debt
                # Also push start_ticks forward so the game clock doesn't penalise
                # players for time lost while frozen
                start_ticks += mp_ghost_timer_debt
                mp_ghost_timer_debt = 0
                print("[TRACKING LOCK] Both objects recovered — game resumed.")

    # Pygame Native Event Loop Processing
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            lighting.on_game_close()
            pygame.quit(); sys.exit()
        
    # === TOGGLE DETECTOR ===
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_c:  # Press 'C' to hide/show the live camera
                show_debug_camera = not show_debug_camera
                print(f"[UI] Debug camera window visibility set to: {show_debug_camera}")

            if event.key == pygame.K_p:  # Press 'P' to pause/resume
                if game_phase in [PHASE_TUTORIAL, PHASE_TUTORIAL_MP, PHASE_GAMEPLAY]:
                    is_paused = not is_paused
                    if is_paused:
                        pause_start_time = now
                        print("[PAUSE] Game paused.")
                    else:
                        elapsed_pause = now - pause_start_time
                        start_ticks += elapsed_pause
                        last_move_time += elapsed_pause
                        print("[PAUSE] Game resumed.")

            if event.key == pygame.K_s:  # Press 'S' to save a still frame for HSV calibration
                if rgb_frame is not None:
                    import cv2
                    import os
                    import time

                    os.makedirs("calibration_snapshots", exist_ok=True)
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    filename = f"calibration_snapshots/frame_{timestamp}.png"

                    # rgb_frame is in RGB order (used for pygame.surfarray.make_surface),
                    # but cv2.imwrite expects BGR — convert before saving
                    bgr_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
                    cv2.imwrite(filename, bgr_frame)
                    print(f"[CALIBRATION] Saved snapshot → {filename}")
                else:
                    print("[CALIBRATION] No camera frame available to save yet.")
            
            # === DEBUG: STAGE SKIP BYPASS (LEFT = back, RIGHT = forward) ===
            if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                if game_phase in [PHASE_TUTORIAL, PHASE_TUTORIAL_MP, PHASE_INSTRUCT,
                                  PHASE_PREPARE, PHASE_GAMEPLAY, PHASE_STAGE_CLEAR]:
                    direction = 1 if event.key == pygame.K_RIGHT else -1
                    new_stage = max(1, min(3, current_stage + direction))

                    if new_stage != current_stage:
                        current_stage = new_stage
                        score = 0
                        pool_pointer = 0
                        ghost_state = "UP"
                        ghost_y_offset = 0
                        stage_clear_hover = 0
                        stage_passed = False
                        death_sequences = []
                        start_ticks = now
                        last_move_time = now
                        game_phase = PHASE_GAMEPLAY
                        lighting.on_tutorial_start()
                        print(f"[DEBUG] Jumped to stage {current_stage} via hotkey.")

        
        if game_phase == PHASE_GAMEOVER and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q:
                lighting.on_game_close()             # ← LIGHTING: all lights off before exit
                pygame.quit(); sys.exit()
            if event.key == pygame.K_r: 
                score, time_left, start_ticks, current_hole, _ = restart_quit.reset_game()
                tutorial_count = 0; mp_tutorial_count = 0; game_phase = PHASE_INTRO; death_sequences = []
                ghost_state = "UP"; ghost_y_offset = 0; last_move_time = now
                current_stage = 1; stage_clear_hover = 0; stage_passed = False

                total_ghosts_spawned = 0
                total_decoys_spawned = 0
                
                # === RESET POINTER FOR THE NEW GAME ===
                pool_pointer = 0

                # === RESET MULTIPLAYER STATE ON RESTART ===
                multiplayer_mode = True
                cursor_vector_p2 = pygame.math.Vector2(WIDTH // 2, HEIGHT // 2)
                velocity_vector_p2 = pygame.math.Vector2(0, 0)
                cursor_pos_p2[0] = WIDTH // 2
                cursor_pos_p2[1] = HEIGHT // 2
                object_was_visible_p2 = False
                last_frame_pos_p2 = pygame.math.Vector2(WIDTH // 2, HEIGHT // 2)
                mp_tracking_locked = False
                mp_ghost_timer_debt = 0
                lighting.on_game_restart()           # ← LIGHTING: restore spooky + spotlight

    lighting.update()                                # ← LIGHTING: handles all timed effects every frame

    # Phase State Machine Routing Engine
    thumbs_up_active = False
    if game_phase == PHASE_INTRO:
        hover_start_progress = start_button.handle_intro_phase(screen, title_font, ui_font, cursor_pos, cursor_pos_p2, hover_start_progress)
        if hover_start_progress >= start_button.HOVER_TO_START_FRAMES:
            game_phase = PHASE_TUTORIAL_MP
            hover_start_progress = 0
            last_move_time = now

    elif game_phase == PHASE_TUTORIAL and tutorial_count >= 5:
        game_phase = PHASE_INSTRUCT
        lighting.on_thumbsup_check()                 # ← LIGHTING: calm white/blue for gesture

    elif game_phase == PHASE_TUTORIAL_MP and mp_tutorial_count >= 10:
        game_phase = PHASE_INSTRUCT
        lighting.on_thumbsup_check()                 # ← LIGHTING: same for multiplayer path
        
    elif game_phase == PHASE_INSTRUCT:
        # 1. Broad Level Pipeline Check
        if not cv_data:
            print("[PHASE_INSTRUCT] STAGE 1 FAIL: cv_data package is empty or False.")
        elif cv_data[2] is None:
            print("[PHASE_INSTRUCT] STAGE 2 FAIL: Camera works, but MediaPipe sees NO hand.")
        else:
            print("[PHASE_INSTRUCT] STAGE 3 SUCCESS: Hand found! Pulling landmarks...")
            landmarks = cv_data[2].landmark
            
            # Run the matching engine
            if opencv.check_csv_ok_sign(landmarks, reference_ok_sign, threshold=3.0):
                print("[PHASE_INSTRUCT] STAGE 4 SUCCESS: CSV Match accepted!")
                thumbs_up_active = True
            else:
                print("[PHASE_INSTRUCT] STAGE 4 FAIL: Hand geometry does not match your CSV data values.")
        
        if thumbs_up_active:
            config.gesture_hold_progress = min(config.GESTURE_HOLD_TARGET, config.gesture_hold_progress + 3)
            if config.gesture_hold_progress >= config.GESTURE_HOLD_TARGET:
                config.gesture_hold_progress = 0  
                game_phase = PHASE_PREPARE
                ready_timer = now
                lighting.on_thumbsup_accepted()      # ← LIGHTING: restore spooky, lightning on
        else:
            config.gesture_hold_progress = max(0, config.gesture_hold_progress - 2)

    elif game_phase == PHASE_PREPARE and (now - ready_timer) > 5000:
        game_phase = PHASE_GAMEPLAY
        start_ticks = now
        score = 0                # NEW: clear any score accumulated during tutorial hits
        lighting.on_tutorial_start()                 # ← LIGHTING: enable lightning for gameplay

    elif game_phase == PHASE_STAGE_CLEAR:
    # Hover-to-continue button for stage clear screen
    # Either P1 (green) or P2 (purple) crosshair can push the bar forward
        p2_pos_for_hover = cursor_pos_p2 if multiplayer_mode else None
        stage_clear_hover = tutorial.handle_stage_clear_screen(
            screen, ui_font, title_font, cursor_pos, p2_pos_for_hover, score,
            current_stage, stage_passed, STAGE_TARGETS, stage_clear_hover
    )
        if stage_clear_hover >= tutorial.STAGE_HOVER_TARGET:
            current_stage += 1
            score = 0                # Reset score for the new stage
            pool_pointer = 0         # Reset spawn pool for stage 3 decoys
            ghost_state = "UP"
            ghost_y_offset = 0
            stage_clear_hover = 0
            start_ticks = now
            game_phase = PHASE_GAMEPLAY
            lighting.on_tutorial_start()             # ← LIGHTING: re-enable lightning for next stage
            print(f"[STAGE] Advancing to stage {current_stage}")

    # =================================================================
    # === GHOST HIT ENGINE & MOVEMENT MATRIX (STRICT VISIBILITY) ===
    # Skipped entirely while the multiplayer tracking lock is active.
    # =================================================================
    if game_phase in [PHASE_TUTORIAL, PHASE_TUTORIAL_MP, PHASE_GAMEPLAY] and not mp_tracking_locked and not is_paused:
        # 1. Run the Hit Engine Check (Forces clean integer values for pixel-perfect collision)
        int_cursor_pos = [int(cursor_vector.x), int(cursor_vector.y)]
        
        # P1 hit check (green object)
        hit, tutorial_count, score, ghost_state, active_entity_type, death_sequences = gameplay.check_ghost_collisions(
            game_phase, int_cursor_pos, current_hole, ghost_state, ghost_y_offset, 
            tutorial_count, score, death_sequences, now, active_entity_type, True
        )

        # Increment combined MP tutorial counter if P1 landed a hit during MP training
        if hit and game_phase == PHASE_TUTORIAL_MP:
            mp_tutorial_count += 1

        # Decoy hit — full room red flash
        if hit and active_entity_type == "DECOY" and game_phase == PHASE_GAMEPLAY:
            lighting.on_decoy_hit()

        # P2 hit check (purple object) — only if multiplayer on and P1 didn't already land a hit
        if multiplayer_mode and not hit:
            int_cursor_pos_p2 = [int(cursor_vector_p2.x), int(cursor_vector_p2.y)]
            p2_hit, tutorial_count, score, ghost_state, active_entity_type, death_sequences = gameplay.check_ghost_collisions(
                game_phase, int_cursor_pos_p2, current_hole, ghost_state, ghost_y_offset,
                tutorial_count, score, death_sequences, now, active_entity_type, True
            )

            # Increment combined MP tutorial counter if P2 landed a hit during MP training
            if p2_hit and game_phase == PHASE_TUTORIAL_MP:
                mp_tutorial_count += 1

            # P2 decoy hit
            if p2_hit and active_entity_type == "DECOY" and game_phase == PHASE_GAMEPLAY:
                lighting.on_decoy_hit()              # ← LIGHTING: same red flash for P2 decoy hit
        
        # 2. Match Timing & Stage Completion Check
        if game_phase == PHASE_GAMEPLAY:
            seconds_in_game = (now - start_ticks) // 1000
            time_left = max(0, STAGE_DURATION - seconds_in_game)

            lighting.on_countdown(time_left)         # ← LIGHTING: handles 10s shift + per-second flash

            if time_left == 0:
                # Stage time is up — check if target was met
                stage_passed = score >= STAGE_TARGETS[current_stage]
                if current_stage == 3:
                    # Final stage done — go to game over regardless
                    game_phase = PHASE_GAMEOVER
                    if stage_passed:
                        lighting.on_win()            # ← LIGHTING: final win amber gold
                    else:
                        lighting.on_lose()           # ← LIGHTING: final lose doom heartbeat
                else:
                    game_phase = PHASE_STAGE_CLEAR
                    stage_clear_hover = 0
                    if stage_passed:
                        audio.win_pt()         # ← AUDIO: stage win sound effect
                        lighting.on_stage_win(current_stage)   # ← LIGHTING: stage win dark gold
                    else:
                        audio.lose_pt()        # ← AUDIO: stage lose sound effect
                        lighting.on_stage_lose(current_stage)  # ← LIGHTING: stage lose dark red

        # 3. Stage-Aware Move Interval & Positional Shifting
        # Stage 3 also enables decoys via the spawn pool
        move_interval = STAGE_SPEEDS[current_stage]
        config.current_move_interval = move_interval

        old_hole = current_hole

        # Update live positional logic coordinate shifts
        ghost_state, ghost_y_offset, current_hole, last_move_time, active_entity_type = gameplay.update_ghost_movement(
            ghost_state, ghost_y_offset, current_hole, last_move_time, move_interval, now, game_phase, osc_client, active_entity_type, current_stage
        )

        # === NEW: FIRST TUTORIAL GHOST DISPLACEMENT GATE ===
        if game_phase == PHASE_TUTORIAL and tutorial_count == 0 and current_hole != old_hole:
            CENTER_HOLE_INDEX = 0 
            if current_hole == CENTER_HOLE_INDEX:
                current_hole = random.choice([1, 2, 3, 4, 5])

        # 4. === POOL ENFORCEMENT ENGINE ===
        if current_hole != old_hole:
            
            # TUTORIAL PHASES: Strictly spawn regular ghosts for practice
            if game_phase in [PHASE_TUTORIAL, PHASE_TUTORIAL_MP]:
                active_entity_type = "GHOST"
                
            # ACTIVE GAMEPLAY: Stage-aware entity spawning
            else:
                if current_stage < 3:
                    # Stages 1 & 2: ghosts only, no decoys
                    active_entity_type = "GHOST"
                else:
                    # Stage 3: use the fixed spawn pool with decoys
                    if pool_pointer < len(spawn_pool):
                        active_entity_type = spawn_pool[pool_pointer]
                        if active_entity_type == "GHOST":
                            total_ghosts_spawned += 1
                        elif active_entity_type == "DECOY":
                            total_decoys_spawned += 1
                            print(f"[TRACKER] Decoy #{total_decoys_spawned} spawned at index {pool_pointer}")
                        pool_pointer += 1
                    else:
                        ghost_state = "DOWN"
                        active_entity_type = "NONE"

        # === ANTI-REPETITION SAFETY LAYER (stage 3 only) ===
        if game_phase == PHASE_GAMEPLAY and current_stage == 3 and pool_pointer > 0 and pool_pointer <= len(spawn_pool):
            active_entity_type = spawn_pool[pool_pointer - 1]

    # =================================================================
    # === GRAPHICAL LAYOUT LAYERS ===
    # =================================================================
    if game_phase == PHASE_GAMEPLAY:
        for pos in gameplay.hole_positions:
            designs.draw_smooth_ellipse(screen, pos[0], pos[1], 97, 45, (12, 10, 18))
            pygame.gfxdraw.aaellipse(screen, pos[0], pos[1], 105, 52, (55, 50, 70))

    if game_phase in [PHASE_TUTORIAL, PHASE_TUTORIAL_MP, PHASE_GAMEPLAY]:
        if active_entity_type == "DECOY" and game_phase == PHASE_GAMEPLAY:
            designs.draw_jack_o_lantern(screen, current_hole, ghost_y_offset, now)
        else:
            designs.draw_ghost_entity(screen, current_hole, ghost_y_offset, now)

    designs.draw_death_sequence(screen, death_sequences, now)
    for death in death_sequences[:]:
        death["frame"] += 1
        if death["frame"] > 25: death_sequences.remove(death)

    # Draw P1 crosshair (green)
    designs.draw_crosshair(screen, cursor_pos)

    # Draw P2 crosshair (purple) — only when multiplayer is active
    if multiplayer_mode:
        designs.draw_crosshair(screen, cursor_pos_p2, color=(180, 0, 220))

    if game_phase in [PHASE_TUTORIAL, PHASE_TUTORIAL_MP, PHASE_INSTRUCT, PHASE_PREPARE]:
        tutorial.handle_tutorial_rendering(screen, ui_font, title_font, countdown_font, game_phase, tutorial_count, now, locals().get('ready_timer', 0), mp_tutorial_count)
        if game_phase == PHASE_INSTRUCT:
            addons.process_gesture_loading_bar(screen, thumbs_up_active, ui_font)
    elif game_phase == PHASE_GAMEPLAY:
        gameplay.render_gameplay_ui(screen, score, time_left)
        # Stage indicator
        stage_names = {1: "STAGE 1 — CASUAL", 2: "STAGE 2 — FASTER", 3: "STAGE 3 — DANGER"}
        stage_txt = ui_font.render(stage_names[current_stage], True, (220, 200, 255))
        screen.blit(stage_txt, (WIDTH // 2 - stage_txt.get_width() // 2, 20))
        # Target reminder
        target_txt = ui_font.render(f"TARGET: {STAGE_TARGETS[current_stage]} GHOSTS", True, (180, 180, 220))
        screen.blit(target_txt, (WIDTH // 2 - target_txt.get_width() // 2, 62))
        # Multiplayer mode indicator
        if multiplayer_mode:
            mp_txt = ui_font.render("2P CO-OP", True, (180, 0, 220))
            screen.blit(mp_txt, (WIDTH - 260, 20))
    elif game_phase == PHASE_GAMEOVER:
        restart_quit.render_game_over_screen(screen, score)

    # =================================================================
    # === MULTIPLAYER TRACKING LOSS BANNER ===
    # Rendered on top of everything else so it's always visible.
    # Only shown during PHASE_GAMEPLAY when the lock is active.
    # =================================================================
    if multiplayer_mode and mp_tracking_locked and game_phase == PHASE_GAMEPLAY:
        p1_visible = tracked_cursor is not None and not is_too_small
        p2_visible = tracked_cursor_p2 is not None

        # Determine which object(s) are missing for the message
        if not p1_visible and not p2_visible:
            lost_label = "BOTH OBJECTS LOST"
        elif not p1_visible:
            lost_label = "GREEN OBJECT LOST"
        else:
            lost_label = "BLUE OBJECT LOST"

        # Pulsing red banner — sine wave drives the alpha so it breathes urgently
        pulse_alpha = int(180 + math.sin(now * 0.008) * 60)
        banner = pygame.Surface((WIDTH, 110), pygame.SRCALPHA)
        banner.fill((200, 20, 20, min(255, pulse_alpha)))
        screen.blit(banner, (0, HEIGHT // 2 - 55))

        # Primary lost-object label
        lost_txt = title_font.render(lost_label, True, (255, 255, 255))
        lost_rect = lost_txt.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 10))
        screen.blit(lost_txt, lost_rect)

        # Sub-label prompting players to re-enter frame
        sub_txt = ui_font.render("BRING BOTH OBJECTS INTO VIEW TO CONTINUE", True, (255, 200, 200))
        sub_rect = sub_txt.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 42))
        screen.blit(sub_txt, sub_rect)

    # =================================================================
    # === LIVE CAMERA DEBUG WINDOW LAYER (BOTTOM LEFT CORNER) ===
    # =================================================================
    if game_phase in [PHASE_INTRO, PHASE_TUTORIAL, PHASE_TUTORIAL_MP, PHASE_GAMEPLAY, PHASE_INSTRUCT] and rgb_frame is not None and show_debug_camera:
        camera_surface = pygame.surfarray.make_surface(rgb_frame.swapaxes(0, 1))
        
        debug_w, debug_h = 320, 240
        small_camera_preview = pygame.transform.scale(camera_surface, (debug_w, debug_h))
        
        dx = 30
        dy = HEIGHT - debug_h - 50
        
        # Extract the size alert safely from cv_data if it exists
        is_too_small = cv_data[5] if (cv_data and len(cv_data) > 5) else False
        
        if is_too_small:
            border_color = (255, 30, 30)  # Warning Alert Red
            border_thickness = 6          
        else:
            border_color = (30, 25, 40)   # Default Deep Purple
            border_thickness = 4
            
        # Draw the background/border container using our dynamic color
        pygame.draw.rect(
            screen, 
            border_color, 
            (dx - border_thickness, dy - border_thickness, debug_w + (border_thickness * 2), debug_h + (border_thickness * 2)), 
            border_radius=6
        )
        
        # Paste the camera feed over the border background
        screen.blit(small_camera_preview, (dx, dy))
        
        # Update text color to match the warning state
        text_color = (255, 100, 100) if is_too_small else (200, 180, 220)
        debug_txt = ui_font.render("TOO FAR!" if is_too_small else "LIVE FEED", True, text_color)
        debug_txt = pygame.transform.scale(debug_txt, (80, 18))
        screen.blit(debug_txt, (dx + 10, dy + debug_h + 12))

    # Scale the internal virtual surface to match native hardware window
    scaled_surface = pygame.transform.scale(screen, (NATIVE_WIDTH, NATIVE_HEIGHT))
    real_screen.blit(scaled_surface, (0, 0))
    if is_paused:
        designs.draw_pause_overlay(screen, title_font, ui_font)

    pygame.display.flip()
    clock.tick(60)