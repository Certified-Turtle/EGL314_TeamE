import cv2
import numpy as np
import pygame
import pygame.gfxdraw
import random
import sys
import math
import csv
from collections import defaultdict
import mediapipe as mp
from pythonosc import udp_client
import os

# --- 1. NETWORK & SHOW CONTROL INITIALIZATION ---
# Forces local-only video mode safely without requiring RPI2_IP or OSC_PORT variables
osc_client = None
print("[INFO] Running in safe, local-only offline mode.")

# --- 2. GAME WINDOW INITIALIZATION ---
os.environ['SDL_RENDER_SCALE_QUALITY'] = 'linear'  
pygame.init()
WIDTH, HEIGHT = 1920, 1080
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED | pygame.DOUBLEBUF)
pygame.display.set_caption("Haunted Manor: Ghost Hunt 1080p Edition")
clock = pygame.time.Clock()
pygame.font.init()

ui_font = pygame.font.SysFont("Courier New", 36, bold=True)
title_font = pygame.font.SysFont("Courier New", 68, bold=True)
countdown_font = pygame.font.SysFont("Courier New", 180, bold=True)

# --- 3. COMPUTER VISION & MEDIAPIPE SETUP ---
def init_camera():
    # Scan indices 0 through 3 to find whichever port your USB webcam landed on
    for index in [0, 1, 2, 3]:
        print(f"[INFO] Testing camera port index {index}...")
        test_cap = cv2.VideoCapture(index)
        if test_cap.isOpened():
            success, test_frame = test_cap.read()
            if success and test_frame is not None:
                print(f"[SUCCESS] Active webcam locked onto index {index}")
                # Set your target hardware dimensions on the working camera port
                test_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                test_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                return test_cap
            test_cap.release()

    print("[CRITICAL ERROR] No functional webcam stream detected on indices 0-3.")
    print("[FIX] Ensure your USB webcam is physically plugged in and permissions are granted.")
    pygame.quit()
    sys.exit()

 # Run the scanner and assign the working port to your primary camera variable
cap = init_camera()

GREEN_LOWER = np.array([35, 100, 100])
GREEN_UPPER = np.array([85, 255, 255])

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.5)

# --- 4. RELATIONAL CSV DATA PARSING ENGINE ---
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
    if not reference_samples:
        return (live_landmarks[4].y < live_landmarks[3].y and 
                live_landmarks[8].y > live_landmarks[6].y and 
                live_landmarks[12].y > live_landmarks[10].y)

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

reference_thumbs_up = load_relational_gesture_csv("thumbsup.csv")

# --- 5. GAME STATES & CONFIGURATION ---
PHASE_INTRO = -1
PHASE_TUTORIAL = 0
PHASE_INSTRUCT = 1
PHASE_PREPARE = 2
PHASE_GAMEPLAY = 3
PHASE_GAMEOVER = 4

game_phase = PHASE_INTRO  
tutorial_count = 0
score = 0
time_left = 30
ready_timer = 0
start_ticks = 0

# --- START BUTTON INTERACTION METRICS ---
START_BUTTON_RECT = pygame.Rect(WIDTH//2 - 250, HEIGHT//2 + 80, 500, 160)
hover_start_progress = 0
HOVER_TO_START_FRAMES = 35

# --- 6. CACHED ENVIRONMENTAL GRAPHICS ---
def draw_smooth_circle(surface, x, y, radius, color):
    pygame.gfxdraw.aacircle(surface, int(x), int(y), int(radius), color)
    pygame.gfxdraw.filled_circle(surface, int(x), int(y), int(radius), color)

def draw_smooth_ellipse(surface, x, y, rx, ry, color):
    pygame.gfxdraw.aaellipse(surface, int(x), int(y), int(rx), int(ry), color)
    pygame.gfxdraw.filled_ellipse(surface, int(x), int(y), int(rx), int(ry), color)

rain_particles = [{"x": random.randint(0, WIDTH), "y": random.randint(0, HEIGHT), "length": random.randint(22, 37), "speed": random.uniform(7.0, 12.0)} for _ in range(50)]

fog_particles = []
for _ in range(8):
    r = random.randint(60, 120)
    f_surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA).convert_alpha()
    draw_smooth_circle(f_surf, r, r, r, (80, 90, 100, 40))
    fog_particles.append({
        "x": random.randint(0, WIDTH), 
        "y": random.randint(600, HEIGHT), 
        "radius": r, 
        "speed": random.uniform(0.3, 0.9),
        "surf": f_surf
    })

cached_ghost_surf = pygame.Surface((300, 400), pygame.SRCALPHA).convert_alpha()
draw_smooth_ellipse(cached_ghost_surf, 150, 180, 80, 110, (200, 235, 255, 180))
draw_smooth_circle(cached_ghost_surf, 150, 110, 80, (200, 235, 255, 180))
draw_smooth_circle(cached_ghost_surf, 120, 110, 15, (255, 10, 80, 230))
draw_smooth_circle(cached_ghost_surf, 180, 110, 15, (255, 10, 80, 230))
draw_smooth_circle(cached_ghost_surf, 120, 110, 5, (0, 0, 0, 255))
draw_smooth_circle(cached_ghost_surf, 180, 110, 5, (0, 0, 0, 255))
_ripples = [(70, 260), (95, 310), (125, 260), (155, 310), (185, 260), (215, 310), (230, 260)]
pygame.gfxdraw.filled_polygon(cached_ghost_surf, _ripples, (200, 235, 255, 180))
pygame.gfxdraw.aapolygon(cached_ghost_surf, _ripples, (200, 235, 255, 180))

vortex_scratch_surf = pygame.Surface((240, 90), pygame.SRCALPHA).convert_alpha()

# --- 7. SCENE DRAWING ENGINES ---
def draw_cemetery(surface, rain_list, lightning_active):
    sky_color = (48, 56, 78) if not lightning_active else (210, 220, 255)
    surface.fill(sky_color)
    
    hill1_color = (36, 46, 62) if not lightning_active else (150, 160, 185)
    hill2_color = (32, 50, 45) if not lightning_active else (130, 145, 135)
    ground_color = (45, 62, 48) if not lightning_active else (110, 135, 115)
    house_color = (22, 24, 30) if not lightning_active else (70, 75, 85)
    tree_color = (55, 46, 40) if not lightning_active else (105, 95, 88)
    ts_color = (120, 125, 135) if not lightning_active else (200, 205, 215)
    
    h1_pts = [(0, 600), (200, 490), (410, 445), (650, 480), (950, 600), (950, 1080), (0, 1080)]
    pygame.gfxdraw.filled_polygon(surface, h1_pts, hill1_color)
    pygame.gfxdraw.aapolygon(surface, h1_pts, hill1_color)
    
    pygame.draw.polygon(surface, house_color, [(350, 448), (355, 370), (465, 365), (470, 448)])
    pygame.draw.polygon(surface, house_color, [(330, 373), (405, 290), (485, 367)])
    pygame.draw.polygon(surface, house_color, [(435, 330), (433, 255), (455, 260), (455, 330)])
    win_color = (235, 210, 120) if not lightning_active else (255, 255, 255)
    pygame.draw.rect(surface, win_color, (380, 395, 20, 25))
    pygame.draw.rect(surface, (10, 12, 15), (380, 395, 20, 25), width=3)
    
    h2_pts = [(550, 600), (900, 530), (1200, 500), (1500, 540), (1920, 600), (1920, 1080), (550, 1080)]
    pygame.gfxdraw.filled_polygon(surface, h2_pts, hill2_color)
    pygame.gfxdraw.aapolygon(surface, h2_pts, hill2_color)
    
    pygame.draw.rect(surface, ground_color, (0, 600, WIDTH, HEIGHT - 600))
    
    pygame.draw.polygon(surface, tree_color, [(1650, 620), (1700, 350), (1740, 350), (1790, 620)])
    pygame.draw.line(surface, tree_color, (1710, 380), (1560, 240), width=16)
    pygame.draw.line(surface, tree_color, (1560, 240), (1440, 220), width=9)
    pygame.draw.line(surface, tree_color, (1560, 240), (1510, 140), width=7)
    pygame.draw.line(surface, tree_color, (1730, 360), (1880, 220), width=14)
    pygame.draw.line(surface, tree_color, (1880, 220), (1990, 210), width=8)
    pygame.draw.line(surface, tree_color, (1720, 350), (1730, 160), width=11)
    pygame.draw.line(surface, tree_color, (1730, 160), (1660, 80), width=6)

    ts_positions = [(200, 630), (550, 670), (850, 620), (1150, 650), (1450, 640)]
    for tx, ty in ts_positions:
        pygame.draw.rect(surface, ts_color, (tx - 35, ty - 70, 70, 90), border_top_left_radius=30, border_top_right_radius=30)
        shadow = (65, 70, 80)
        pygame.draw.line(surface, shadow, (tx, ty - 50), (tx, ty - 15), width=4)
        pygame.draw.line(surface, shadow, (tx - 15, ty - 38), (tx + 15, ty - 38), width=4)

    rain_color = (95, 115, 145) if not lightning_active else (255, 255, 255)
    for r in rain_list:
        pygame.draw.aaline(surface, rain_color, (r["x"], r["y"]), (r["x"] - (r["length"] * 0.3), r["y"] + r["length"]))
        r["y"] += r["speed"]
        r["x"] -= r["speed"] * 0.3
        if r["y"] > HEIGHT or r["x"] < 0:
            r["y"] = random.randint(-40, 0)
            r["x"] = random.randint(0, WIDTH)

def draw_haunted_house(surface, rain_list, fog_list, lightning_active):
    wall_base = (24, 18, 36) if not lightning_active else (210, 215, 255)
    surface.fill(wall_base)
    stripe_color = (15, 10, 24) if not lightning_active else (160, 170, 220)
    for x in range(0, WIDTH, 120):
        pygame.draw.rect(surface, stripe_color, (x, 0, 22, 525))
    window_sky = (10, 8, 20) if not lightning_active else (180, 190, 255)
    pygame.draw.rect(surface, window_sky, (165, 165, 495, 345))
    
    rain_color = (70, 90, 120) if not lightning_active else (255, 255, 255)
    for r in rain_list:
        pygame.draw.aaline(surface, rain_color, (r["x"], r["y"]), (r["x"] - (r["length"] * 0.3), r["y"] + r["length"]))
        r["y"] += r["speed"]; r["x"] -= r["speed"] * 0.3
        if r["y"] > 502 or r["x"] < 172: 
            r["y"] = 165
            r["x"] = random.randint(195, 660)
        
    frame_color = (40, 35, 50) if not lightning_active else (120, 125, 160)
    pygame.draw.rect(surface, frame_color, (150, 150, 525, 375), width=22)
    pygame.draw.line(surface, frame_color, (412, 165), (412, 510), width=12)
    pygame.draw.line(surface, frame_color, (165, 337), (660, 337), width=12)
    floor_color = (45, 35, 30) if not lightning_active else (100, 90, 85)
    pygame.draw.rect(surface, floor_color, (0, 525, WIDTH, 555))
    for x in range(0, WIDTH, 90):
        pygame.draw.line(surface, (25, 18, 15) if not lightning_active else (60, 50, 45), (x, 525), (x, HEIGHT), width=3)
        
    for f in fog_list:
        surface.blit(f["surf"], (int(f["x"] - f["radius"]), int(f["y"] - f["radius"])))
        f["x"] += f["speed"]
        if f["x"] - f["radius"] > WIDTH: f["x"] = -f["radius"]

def draw_ghost_entity(surface, pos, y_offset, current_ticks):
    x, y = pos
    float_anim = math.sin(current_ticks * 0.007) * 22
    y += int(y_offset + float_anim)
    surface.set_clip(pygame.Rect(0, 0, WIDTH, y - y_offset + 60))
    surface.blit(cached_ghost_surf, (x - 150, y - 150))
    surface.set_clip(None)

def draw_spooky_panel(surface, x, y, w, h, base_color, label, value):
    pygame.draw.rect(surface, base_color, (x, y, w, h), border_radius=12)
    pygame.draw.rect(surface, (100, 105, 120), (x, y, w, h), width=4, border_radius=12)
    font = pygame.font.SysFont("Courier New", 63, bold=True)
    txt = font.render(f"{label}:{value}", True, (230, 240, 255))
    surface.blit(txt, (x + 30, y + 45))

def draw_death_sequence(surface, active_deaths, current_ticks):
    for death in active_deaths:
        pos = death["pos"]; frame = death["frame"]
        if frame <= 6:
            radius = frame * 18
            pygame.gfxdraw.aacircle(surface, int(pos[0]), int(pos[1]), int(radius), (0, 255, 150))
            pygame.draw.circle(surface, (0, 255, 150), pos, radius, 6)
            pygame.draw.aaline(surface, (255, 255, 255), (pos[0]-radius, pos[1]-radius), (pos[0]+radius, pos[1]+radius))
            pygame.draw.aaline(surface, (255, 255, 255), (pos[0]+radius, pos[1]-radius), (pos[0]-radius, pos[1]+radius))
        if 3 <= frame <= 20:
            up_drift = (frame - 3) * 6; skull_y = pos[1] - up_drift
            draw_smooth_circle(surface, pos[0], skull_y, 27, (230, 220, 255))
            pygame.draw.rect(surface, (230, 220, 255), (pos[0]-15, skull_y+15, 30, 18), border_bottom_left_radius=6, border_bottom_right_radius=6)
            pygame.draw.line(surface, (40, 30, 50), (pos[0]-6, skull_y+24), (pos[0]-6, skull_y+33), 3)
            pygame.draw.line(surface, (40, 30, 50), (pos[0]+6, skull_y+24), (pos[0]+6, skull_y+33), 3)
            draw_smooth_circle(surface, pos[0]-9, skull_y+3, 6, (20, 10, 35))
            draw_smooth_circle(surface, pos[0]+9, skull_y+3, 6, (20, 10, 35))
        if 8 <= frame <= 24:
            vortex_frame = frame - 8; width = 135 - (vortex_frame * 6); height = 37 - (vortex_frame * 1.5)
            spin_offset = math.sin(current_ticks * 0.05 + frame) * 22
            if width > 0 and height > 0:
                vortex_scratch_surf.fill((0, 0, 0, 0))
                draw_smooth_ellipse(vortex_scratch_surf, 120 + int(spin_offset*0.3), 45, int(width//2), int(height//2), (150, 100, 255, 130))
                surface.blit(vortex_scratch_surf, (pos[0] - 120, pos[1] - int(vortex_frame * 9) - 15))

# --- 8. TARGET HOLE PLACEMENT ENGINE ---
hole_positions = [(480 + col * 480, 660 + row * 150) for row in range(3) for col in range(3)]

def reset_game():
    return 0, 30, pygame.time.get_ticks(), random.choice(hole_positions), False

score, time_left, start_ticks, current_hole, game_over = reset_game()
cursor_pos = [WIDTH//2, HEIGHT//2]
last_move_time, ghost_y_offset, ghost_state, death_sequences = pygame.time.get_ticks(), 0, "UP", []

lightning_active, lightning_trigger_time, lightning_duration = False, 0, 0

# --- 9. SYSTEM ENGINE LOOP ---
while True:
    now = pygame.time.get_ticks()
    
    if lightning_active:
        if now - lightning_trigger_time > lightning_duration: lightning_active = False
    else:
        if random.random() < (0.005 if time_left > 10 else 0.025):
            lightning_active = True
            lightning_trigger_time = now
            lightning_duration = random.randint(80, 220)

    # Background Routing Engine
    is_tutorial_phase = game_phase in [PHASE_TUTORIAL, PHASE_INSTRUCT, PHASE_PREPARE]
    if game_phase == PHASE_INTRO:
        screen.fill((10, 8, 20))
    elif is_tutorial_phase:
        draw_cemetery(screen, rain_particles, lightning_active)
    else:
        draw_haunted_house(screen, rain_particles, fog_particles, lightning_active)
    
    success, frame = cap.read()
    if not success or frame is None: 
        continue  # <--- Changed from 'break' to 'continue' to prevent closing
        
    frame = cv2.flip(frame, 1) 
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # MediaPipe processes frames strictly during PHASE_INSTRUCT mode now
    hand_results = None
    if game_phase == PHASE_INSTRUCT:
        hand_results = hands.process(rgb_frame)
    
    mask = cv2.inRange(hsv_frame, GREEN_LOWER, GREEN_UPPER)
    moments = cv2.moments(mask)
    if moments["m00"] > 400: 
        cursor_pos[0] = int(int(moments["m10"] / moments["m00"]) * (WIDTH / 640))
        cursor_pos[1] = int(int(moments["m01"] / moments["m00"]) * (HEIGHT / 480))

    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            pygame.quit(); sys.exit()
        if game_phase == PHASE_GAMEOVER and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q: pygame.quit(); sys.exit()
            if event.key == pygame.K_r: 
                score, time_left, start_ticks, current_hole, _ = reset_game()
                tutorial_count = 0; game_phase = PHASE_INTRO; death_sequences = []
                ghost_state = "UP"; ghost_y_offset = 0; last_move_time = now
                # Safe hardware guard check added below
                if osc_client is not None: 
                    osc_client.send_message("/game/restart", 1)

    # --- INTRO BUTTON PROCESSING INTERFACE BLOCK ---
    if game_phase == PHASE_INTRO:
        intro_title = title_font.render("WHACK-A-GHOST SYSTEM", True, (0, 255, 180))
        screen.blit(intro_title, intro_title.get_rect(center=(WIDTH//2, HEIGHT//2 - 180)))
        
        # Hover guidance documentation text labels
        guide_txt = ui_font.render("MOVE THE CROSSHAIR OVER THE BUTTON TO START", True, (170, 185, 200))
        screen.blit(guide_txt, guide_txt.get_rect(center=(WIDTH//2, HEIGHT//2 - 60)))
        
        # 1. Evaluate spatial color cursor coordinate intersection
        mouse_x, mouse_y = cursor_pos
        hovering = START_BUTTON_RECT.collidepoint(mouse_x, mouse_y)
        
        # 2. Progress bar increments based exclusively on crosshair alignment
        if hovering:
            hover_start_progress += 1
        else:
            hover_start_progress = max(0, hover_start_progress - 2)
            
        # Draw Start Button Graphical Assets
        fill_width = int((hover_start_progress / HOVER_TO_START_FRAMES) * START_BUTTON_RECT.width)
        pygame.draw.rect(screen, (40, 40, 60), START_BUTTON_RECT, border_radius=14)
        if fill_width > 0:
            pygame.draw.rect(screen, (0, 255, 180), (START_BUTTON_RECT.x, START_BUTTON_RECT.y, fill_width, START_BUTTON_RECT.height), border_radius=14)
        pygame.draw.rect(screen, (0, 255, 180), START_BUTTON_RECT, width=4, border_radius=14)
        
        # Compute Dynamic String Label States
        btn_label = "START EXORCISM" if hover_start_progress < HOVER_TO_START_FRAMES else "INITIATING..."
        btn_text = ui_font.render(btn_label, True, (230, 240, 255))
        screen.blit(btn_text, btn_text.get_rect(center=START_BUTTON_RECT.center))
        
        # Draw active crosshair sight overlay above background configurations
        pygame.gfxdraw.aacircle(screen, cursor_pos[0], cursor_pos[1], 52, (255, 69, 0))
        pygame.draw.circle(screen, (255, 69, 0), (cursor_pos[0], cursor_pos[1]), 52, 4)
        pygame.draw.aaline(screen, (0, 255, 180), (cursor_pos[0]-30, cursor_pos[1]), (cursor_pos[0]+30, cursor_pos[1]))
        pygame.draw.aaline(screen, (0, 255, 180), (cursor_pos[0], cursor_pos[1]-30), (cursor_pos[0], cursor_pos[1]+30))
        
        if hover_start_progress >= HOVER_TO_START_FRAMES:
            game_phase = PHASE_TUTORIAL
            hover_start_progress = 0
            last_move_time = now 
            
        pygame.display.flip()
        clock.tick(60)
        continue

    # --- STATE CONTROLLERS ---
    if game_phase == PHASE_TUTORIAL and tutorial_count >= 5:
        game_phase = PHASE_INSTRUCT
        
    elif game_phase == PHASE_INSTRUCT and hand_results and hand_results.multi_hand_landmarks:
        for hand_landmarks in hand_results.multi_hand_landmarks:
            if check_csv_thumbs_up(hand_landmarks.landmark, reference_thumbs_up, threshold=0.35):
                game_phase = PHASE_PREPARE
                ready_timer = now
                
    elif game_phase == PHASE_PREPARE and (now - ready_timer) > 5000:
        game_phase = PHASE_GAMEPLAY
        start_ticks = now

    # --- COLLISION HIT DETECTION CORE ---
    if game_phase in [PHASE_TUTORIAL, PHASE_GAMEPLAY] and ghost_state == "UP" and ghost_y_offset < 60:
        ghost_core_pos = (current_hole[0], current_hole[1] - 45 + ghost_y_offset)
        if math.hypot(cursor_pos[0] - ghost_core_pos[0], cursor_pos[1] - ghost_core_pos[1]) < 180: 
            if game_phase == PHASE_TUTORIAL: tutorial_count += 1
            else: score += 1
            death_sequences.append({"pos": list(ghost_core_pos), "frame": 0})
            ghost_state = "DOWN"
            last_move_time = now 
    # --- MOVEMENT PACING ENGINE ---
    if game_phase in [PHASE_TUTORIAL, PHASE_GAMEPLAY]:
        move_interval = 2200  
        
        if game_phase == PHASE_GAMEPLAY:
            time_left = max(0, 30 - (now - start_ticks) // 1000)
            if time_left == 0:
                game_phase = PHASE_GAMEOVER


        if ghost_state == "DOWN":
            ghost_y_offset += 30
            if ghost_y_offset >= 180:
                ghost_y_offset, ghost_state = 180, "HIDDEN"
                current_hole = random.choice([h for h in hole_positions if h != current_hole])
        elif ghost_state == "HIDDEN":
            ghost_state = "UP"
            last_move_time = now 
        elif ghost_state == "UP":
            if ghost_y_offset > 0: ghost_y_offset -= 30
            else: ghost_y_offset = 0
            
            if now - last_move_time > move_interval:
                ghost_state = "DOWN"
                last_move_time = now
                # Safe hardware guard check added below
                if game_phase == PHASE_GAMEPLAY and osc_client is not None: 
                    osc_client.send_message("/ghost/miss", 1)

    # Plot holes out conditionally based on active scenery state
    if not is_tutorial_phase:
        for pos in hole_positions:
            draw_smooth_ellipse(screen, pos[0], pos[1], 97, 45, (12, 10, 18))
            pygame.gfxdraw.aaellipse(screen, pos[0], pos[1], 105, 52, (55, 50, 70))

    # Draw active floating entities
    if game_phase in [PHASE_TUTORIAL, PHASE_GAMEPLAY]:
        draw_ghost_entity(screen, current_hole, ghost_y_offset, now)

    # Render Active Animations
    draw_death_sequence(screen, death_sequences, now)
    for death in death_sequences[:]:
        death["frame"] += 1
        if death["frame"] > 25: death_sequences.remove(death)

    # Crosshair Reticle
    pygame.gfxdraw.aacircle(screen, cursor_pos[0], cursor_pos[1], 52, (255, 69, 0))
    pygame.draw.circle(screen, (255, 69, 0), (cursor_pos[0], cursor_pos[1]), 52, 4)
    pygame.draw.aaline(screen, (0, 255, 180), (cursor_pos[0]-30, cursor_pos[1]), (cursor_pos[0]+30, cursor_pos[1]))
    pygame.draw.aaline(screen, (0, 255, 180), (cursor_pos[0], cursor_pos[1]-30), (cursor_pos[0], cursor_pos[1]+30))

    # --- SCENE RENDERING PIPELINE ---
    if game_phase == PHASE_TUTORIAL:
        t1 = ui_font.render("USE YOUR GREEN OBJECT TO MOVE THE CROSSHAIR OVER THE GHOST TO REGISTER A HIT.", True, (255, 230, 150))
        t2 = ui_font.render(f"TRAINING GHOSTS BANISHED: {tutorial_count}/5", True, (180, 255, 200))
        screen.blit(t1, (WIDTH // 2 - t1.get_width() // 2, 60))
        screen.blit(t2, (WIDTH // 2 - t2.get_width() // 2, 128))

    elif game_phase == PHASE_INSTRUCT:
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA).convert_alpha()
        dim.fill((10, 8, 20, 130)); screen.blit(dim, (0, 0)) 
        i1 = title_font.render("TUTORIAL COMPLETE - PHASE TWO ENGAGED", True, (255, 215, 0))
        i2 = ui_font.render("-> You have 30 seconds to clear as many ghosts as possible.", True, (240, 240, 255))
        i3 = ui_font.render("-> Level Clear Target: 15 ghosts minimum required to purge.", True, (240, 240, 255))
        i4 = title_font.render("RAISE A THUMBS UP WITH EITHER HAND TO BEGIN", True, (0, 255, 150))
        screen.blit(i1, (WIDTH // 2 - i1.get_width() // 2, 240))
        screen.blit(i2, (WIDTH // 2 - i2.get_width() // 2, 420))
        screen.blit(i3, (WIDTH // 2 - i3.get_width() // 2, 510))
        screen.blit(i4, (WIDTH // 2 - i4.get_width() // 2, 720))

    elif game_phase == PHASE_PREPARE:
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA).convert_alpha()
        dim.fill((15, 10, 25, 130)); screen.blit(dim, (0, 0)) 
        seconds_remaining = max(1, 5 - (now - ready_timer) // 1000)
        p_text = title_font.render("GET READY!", True, (255, 69, 0))
        c_text = countdown_font.render(str(seconds_remaining), True, (255, 255, 255))
        screen.blit(p_text, (WIDTH // 2 - p_text.get_width() // 2, HEIGHT // 2 - 210))
        screen.blit(c_text, (WIDTH // 2 - c_text.get_width() // 2, HEIGHT // 2 - 30))

    elif game_phase == PHASE_GAMEPLAY:
        # Safe hardware guard check added below
        if osc_client is not None: 
            osc_client.send_message("/tempo/bpm", 100.0)
        draw_spooky_panel(screen, 60, 60, 480, 150, (20, 30, 25), "CAPTURED", f"{score:02d}")
        draw_spooky_panel(screen, WIDTH - 540, 60, 480, 150, (40, 15, 20), "TIME REM", f"{time_left:02d}s")

    elif game_phase == PHASE_GAMEOVER:
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA).convert_alpha()
        dim.fill((5, 5, 12, 240)); screen.blit(dim, (0, 0))
        f1, f2 = pygame.font.SysFont("Courier New", 150, bold=True), pygame.font.SysFont("Courier New", 60, bold=True)
        title_str = "CLEARED!" if score >= 15 else "GAME!"
        title_surf = f1.render(title_str, True, (200, 255, 220) if score >= 15 else (220, 40, 60))
        score_surf = f2.render(f"SPIRITS BANISHED: {score} (Target: 15)", True, (255, 215, 0))
        menu_surf  = f2.render("PRESS [R] TO RE-ENTER OR [Q] TO LEAVE", True, (160, 165, 180))
        screen.blit(title_surf, title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 150)))
        screen.blit(score_surf, score_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30)))
        screen.blit(menu_surf, menu_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 180)))

    pygame.display.flip()
    clock.tick(60)