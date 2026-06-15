import pygame
import pygame.gfxdraw
import random
import sys
import os
import math

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

# =================================================================
# === 1. CONFIGURATION STAGE & PERFORMANCE CANVAS RESCALING ===
# =================================================================
print("[INFO] Running in safe, local-only offline mode.")

os.environ['SDL_RENDER_SCALE_QUALITY'] = 'linear'  # Forces GPU to smooth textures cleanly
pygame.init()

# Automatically grab your monitor's native dimensions on boot
monitor_info = pygame.display.Info()
NATIVE_WIDTH = monitor_info.current_w
NATIVE_HEIGHT = monitor_info.current_h

# Lock your internal gameplay boundaries to a stable 1080p profile
WIDTH, HEIGHT = 1920, 1080

# Build the borderless window container across the native screen pixels
real_screen = pygame.display.set_mode(
    (NATIVE_WIDTH, NATIVE_HEIGHT), 
    pygame.NOFRAME | pygame.DOUBLEBUF
)

# Instantiate the virtual canvas surface that all your modules draw onto
screen = pygame.Surface((WIDTH, HEIGHT))

# Create a dedicated transparent scratchpad surface for the vortex death animations
designs.vortex_scratch_surf = pygame.Surface((300, 150), pygame.SRCALPHA)

pygame.display.set_caption("Haunted Manor: Ghost Hunt")
clock = pygame.time.Clock()

active_entity_type = "GHOST"   # "GHOST" or "DECOY"
speed_multiplier = 1.0
last_speed_bump_time = 0       # Monitors game speed step changes
# Speed warning configuration variables
speed_warning_active = False
speed_warning_start_ticks = 0

designs.init_assets()

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

game_phase = PHASE_INTRO  
tutorial_count = 0
hover_start_progress = 0

score, time_left, start_ticks, current_hole, game_over = restart_quit.reset_game()
last_move_time = pygame.time.get_ticks()
ghost_y_offset = 0
ghost_state = "UP"
death_sequences = []

# ---- CENTRAL NETWORKING TARGETS ----
# Point these directly out to your Central Router machine (IP: 192.168.254.58, Port: 2000)
ROUTER_IP = "192.168.254.58"
ROUTER_PORT = 2000
show_router_client = udp_client.SimpleUDPClient(ROUTER_IP, ROUTER_PORT)

LIGHTING_LAPTOP_IP = "192.168.254.252"
lighting_sender = udp_client.SimpleUDPClient(LIGHTING_LAPTOP_IP, 8000)

REAPER_LAPTOP_IP = "192.168.254.111"
reaper_sender = udp_client.SimpleUDPClient(REAPER_LAPTOP_IP, 8000)

total_ghosts_spawned = 0
total_decoys_spawned = 0
show_debug_camera = True
ready_timer = 0  # Pre-declared to enforce proper local scope memory layout

# === CONTROLLED SPAWN POOL ===
spawn_pool = [
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",   # Decoy 1 (Index 6)
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",   # Decoy 2 (Index 13)
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",   # Decoy 3 (Index 20)
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",   # Decoy 4 (Index 27)
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",   # Decoy 5 (Index 34)
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",   # Decoy 6 (Index 41)
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "DECOY",   # Decoy 7 (Index 48)
    "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST", "GHOST",   # Clean Run to finish (49-55)
    "GHOST"                                                          # Final element (56)
]
pool_pointer = 0

lightning_active, lightning_trigger_time, lightning_duration = False, 0, 0

cursor_vector = pygame.math.Vector2(WIDTH // 2, HEIGHT // 2)
velocity_vector = pygame.math.Vector2(0, 0)
cursor_pos = [int(cursor_vector.x), int(cursor_vector.y)]

cap = None
reference_ok_sign = None  
camera_fully_initialized = False
camera_trigger_time = None  

# --- 3. MAIN RUNTIME LOOP ---
while True:
    now = pygame.time.get_ticks()

    # === ASYNCHRONOUS CAMERA DELAY ENGINE ===
    if not camera_fully_initialized:
        if camera_trigger_time is None:
            camera_trigger_time = now
        
        screen.fill((10, 8, 20))
        loading_txt = ui_font.render("Loading Whack-A-Ghost...", True, (100, 90, 120))
        screen.blit(loading_txt, (WIDTH // 2 - 280, HEIGHT // 2))
        
        scaled_surface = pygame.transform.smoothscale(screen, (NATIVE_WIDTH, NATIVE_HEIGHT))
        real_screen.blit(scaled_surface, (0, 0))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit(); sys.exit()
        
        if now - camera_trigger_time > 1000:
            cap = opencv.init_camera()
            reference_ok_sign = opencv.load_relational_gesture_csv("thumbsup.csv")
            camera_fully_initialized = True
            lighting.init()
            last_move_time = pygame.time.get_ticks()
        
        clock.tick(60)
        continue  
    
    # Atmospheric Lightning Engine Context
    if lightning_active:
        if now - lightning_trigger_time > lightning_duration: lightning_active = False
    else:
        if random.random() < (0.005 if time_left > 10 else 0.025):
            lightning_active = True
            lightning_trigger_time = now
            lightning_duration = random.randint(80, 220)
            lighting.on_lightning_flash()

    # Scenery routing mapping
    is_tutorial_scene = game_phase in [PHASE_TUTORIAL, PHASE_INSTRUCT, PHASE_PREPARE]
    if game_phase == PHASE_INTRO:
        screen.fill((10, 8, 20))
    elif is_tutorial_scene:
        designs.draw_cemetery(screen, lightning_active)
    else:
        designs.draw_haunted_house(screen, lightning_active)
        
    # =================================================================
    # === COMPRESSED COMPUTER VISION PIPELINE MATRIX ===
    # =================================================================
    need_hand_skeleton = (game_phase == PHASE_INSTRUCT)
    
    cv_data = opencv.process_cv_frame(
        cap, 
        list(cursor_pos), 
        WIDTH, 
        HEIGHT, 
        run_skeletal_check=need_hand_skeleton
    )
    
    rgb_frame = None
    tracked_cursor = None
    is_too_small = False

    if cv_data and cv_data[0]:
        rgb_frame = cv_data[1]        
        tracked_cursor = cv_data[3]   
        is_too_small = cv_data[5]     

        if 'object_was_visible' not in locals() and 'object_was_visible' not in globals():
            global object_was_visible, last_frame_pos
            object_was_visible = False
            last_frame_pos = pygame.math.Vector2(WIDTH // 2, HEIGHT // 2)

        if tracked_cursor is not None and not is_too_small:
            green_obj_vec = pygame.math.Vector2(tracked_cursor[0], tracked_cursor[1])
            
            if game_phase == PHASE_INSTRUCT:
                target_vector = green_obj_vec
                velocity_vector = velocity_vector.lerp(target_vector - cursor_vector, 0.70)
                cursor_vector = cursor_vector.lerp(target_vector, 0.65)
                last_frame_pos = green_obj_vec
                object_was_visible = True
            else:
                if not object_was_visible:
                    last_frame_pos = green_obj_vec
                    object_was_visible = True  
                
                if green_obj_vec.distance_to(last_frame_pos) < 300:
                    target_vector = green_obj_vec
                    velocity_vector = velocity_vector.lerp(target_vector - cursor_vector, 0.70)
                    cursor_vector = cursor_vector.lerp(target_vector, 0.65)
                    last_frame_pos = pygame.math.Vector2(cursor_vector.x, cursor_vector.y)
                else:
                    velocity_vector *= 0.0
        else:
            object_was_visible = False
            velocity_vector *= 0.0

        cursor_pos[0] = int(cursor_vector.x)
        cursor_pos[1] = int(cursor_vector.y)

    # Pygame Native Event Loop Processing
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            pygame.quit(); sys.exit()
            
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_c:  
                show_debug_camera = not show_debug_camera
                print(f"[UI] Debug camera window visibility set to: {show_debug_camera}")
        
        if game_phase == PHASE_GAMEOVER and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q: pygame.quit(); sys.exit()
            if event.key == pygame.K_r: 
                score, time_left, start_ticks, current_hole, _ = restart_quit.reset_game()
                tutorial_count = 0; game_phase = PHASE_INTRO; death_sequences = []
                ghost_state = "UP"; ghost_y_offset = 0; last_move_time = now
                total_ghosts_spawned = 0
                total_decoys_spawned = 0
                pool_pointer = 0
                lighting.on_game_restart()

    lighting.update()

    # Phase State Machine Routing Engine
    thumbs_up_active = False
    if game_phase == PHASE_INTRO:
        hover_start_progress = start_button.handle_intro_phase(screen, title_font, ui_font, cursor_pos, hover_start_progress)
        if hover_start_progress >= start_button.HOVER_TO_START_FRAMES:
            game_phase = PHASE_TUTORIAL
            hover_start_progress = 0
            last_move_time = now

    elif game_phase == PHASE_TUTORIAL and tutorial_count >= 5:
        game_phase = PHASE_INSTRUCT
        
    elif game_phase == PHASE_INSTRUCT:
        if not cv_data:
            pass
        elif cv_data[2] is None:
            pass
        else:
            landmarks = cv_data[2].landmark
            if opencv.check_csv_ok_sign(landmarks, reference_ok_sign, threshold=3.0):
                thumbs_up_active = True
        
        if thumbs_up_active:
            config.gesture_hold_progress = min(config.GESTURE_HOLD_TARGET, config.gesture_hold_progress + 3)
            if config.gesture_hold_progress >= config.GESTURE_HOLD_TARGET:
                config.gesture_hold_progress = 0  
                game_phase = PHASE_PREPARE
                ready_timer = now
        else:
            config.gesture_hold_progress = max(0, config.gesture_hold_progress - 2)

    elif game_phase == PHASE_PREPARE and (now - ready_timer) > 5000:
        game_phase = PHASE_GAMEPLAY
        start_ticks = now

    # =================================================================
    # === GHOST HIT ENGINE & MOVEMENT MATRIX ===
    # =================================================================
    if game_phase in [PHASE_TUTORIAL, PHASE_GAMEPLAY]:
        int_cursor_pos = [int(cursor_vector.x), int(cursor_vector.y)]
        
        hit, tutorial_count, score, ghost_state, active_entity_type, death_sequences = gameplay.check_ghost_collisions(
            game_phase, int_cursor_pos, current_hole, ghost_state, ghost_y_offset, 
            tutorial_count, score, death_sequences, now, active_entity_type, True
        )
        
        if game_phase == PHASE_GAMEPLAY:
            seconds_in_game = (now - start_ticks) // 1000
            
            if seconds_in_game >= 10 and seconds_in_game < 15 and not speed_warning_active and last_speed_bump_time == 0:
                speed_warning_active = True
                speed_warning_start_ticks = now

            if seconds_in_game < 15:
                speed_multiplier = 1.0
            elif seconds_in_game >= 15 and last_speed_bump_time == 0:
                speed_multiplier = 2.0  
                last_speed_bump_time = 15
                speed_warning_active = False  

            time_left = max(0, 30 - seconds_in_game)
            if time_left == 0: 
                game_phase = PHASE_GAMEOVER
                if score >= 15:
                    lighting.on_win()
                else:
                    lighting.on_lose()

        move_interval = int(1300 / speed_multiplier)
        config.current_move_interval = move_interval
        old_hole = current_hole

        # UPDATED: Passing show_router_client instead of dead osc_client variable
        ghost_state, ghost_y_offset, current_hole, last_move_time, active_entity_type = gameplay.update_ghost_movement(
            ghost_state, ghost_y_offset, current_hole, last_move_time, move_interval, now, game_phase, show_router_client, active_entity_type
        )

        if game_phase == PHASE_TUTORIAL and tutorial_count == 0 and current_hole != old_hole:
            CENTER_HOLE_INDEX = 0 
            if current_hole == CENTER_HOLE_INDEX:
                current_hole = random.choice([1, 2, 3, 4, 5])

        if current_hole != old_hole:
            if game_phase == PHASE_TUTORIAL:
                active_entity_type = "GHOST"
            else:
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

        if game_phase == PHASE_GAMEPLAY and pool_pointer > 0 and pool_pointer <= len(spawn_pool):
            active_entity_type = spawn_pool[pool_pointer - 1]

    # =================================================================
    # === GRAPHICAL LAYOUT LAYERS ===
    # =================================================================
    if game_phase == PHASE_GAMEPLAY:
        for pos in gameplay.hole_positions:
            designs.draw_smooth_ellipse(screen, pos[0], pos[1], 97, 45, (12, 10, 18))
            pygame.gfxdraw.aaellipse(screen, pos[0], pos[1], 105, 52, (55, 50, 70))

    if game_phase in [PHASE_TUTORIAL, PHASE_GAMEPLAY]:
        if active_entity_type == "DECOY" and game_phase == PHASE_GAMEPLAY:
            designs.draw_jack_o_lantern(screen, current_hole, ghost_y_offset, now)
        else:
            designs.draw_ghost_entity(screen, current_hole, ghost_y_offset, now)

    designs.draw_death_sequence(screen, death_sequences, now)
    for death in death_sequences[:]:
        death["frame"] += 1
        if death["frame"] > 25: death_sequences.remove(death)

    designs.draw_crosshair(screen, cursor_pos)

    if game_phase in [PHASE_TUTORIAL, PHASE_INSTRUCT, PHASE_PREPARE]:
        tutorial.handle_tutorial_rendering(screen, ui_font, title_font, countdown_font, game_phase, tutorial_count, now, ready_timer)
        if game_phase == PHASE_INSTRUCT:
            addons.process_gesture_loading_bar(screen, thumbs_up_active, ui_font)
    elif game_phase == PHASE_GAMEPLAY:
        gameplay.render_gameplay_ui(screen, score, time_left)
        if speed_warning_active:
            gameplay.render_speed_warning(screen, ui_font, title_font, now, speed_warning_start_ticks, WIDTH)
    elif game_phase == PHASE_GAMEOVER:
        restart_quit.render_game_over_screen(screen, score)

    # === LIVE CAMERA DEBUG WINDOW LAYER ===
    if game_phase in [PHASE_INTRO, PHASE_TUTORIAL, PHASE_GAMEPLAY, PHASE_INSTRUCT] and rgb_frame is not None and show_debug_camera:
        camera_surface = pygame.surfarray.make_surface(rgb_frame.swapaxes(0, 1))
        debug_w, debug_h = 320, 240
        small_camera_preview = pygame.transform.scale(camera_surface, (debug_w, debug_h))
        
        dx = 30
        dy = HEIGHT - debug_h - 50
        is_too_small = cv_data[5] if (cv_data and len(cv_data) > 5) else False
        
        border_color = (255, 30, 30) if is_too_small else (30, 25, 40)
        border_thickness = 6 if is_too_small else 4
            
        pygame.draw.rect(
            screen, 
            border_color, 
            (dx - border_thickness, dy - border_thickness, debug_w + (border_thickness * 2), debug_h + (border_thickness * 2)), 
            border_radius=6
        )
        screen.blit(small_camera_preview, (dx, dy))
        
        text_color = (255, 100, 100) if is_too_small else (200, 180, 220)
        debug_txt = ui_font.render("TOO FAR!" if is_too_small else "LIVE FEED", True, text_color)
        debug_txt = pygame.transform.scale(debug_txt, (80, 18))
        screen.blit(debug_txt, (dx + 10, dy + debug_h + 12))

    # Scale to match native monitor dimensions layout cleanly
    scaled_surface = pygame.transform.scale(screen, (NATIVE_WIDTH, NATIVE_HEIGHT))
    real_screen.blit(scaled_surface, (0, 0))

    pygame.display.flip()
    clock.tick(60)