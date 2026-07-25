import math
import random
import time
from xmlrpc import client
import pygame
from audio import send_message
import designs
import audio

WIDTH, HEIGHT = 1920, 1080
hole_positions = [(480 + col * 480, 660 + row * 150) for row in range(3) for col in range(3)]

def check_ghost_collisions(game_phase, cursor_pos, current_hole, ghost_state, ghost_y_offset, tutorial_count, score, death_sequences, now, active_entity_type, is_striking):
    if ghost_state != "UP" or current_hole is None:
        return False, tutorial_count, score, ghost_state, active_entity_type, death_sequences

    if isinstance(current_hole, (tuple, list)):
        hole_x, hole_y = current_hole[0], current_hole[1]
    else:
        hole_x, hole_y = hole_positions[current_hole]
        
    ghost_current_x = hole_x
    ghost_current_y = hole_y - ghost_y_offset

    target_center_x = ghost_current_x
    target_center_y = ghost_current_y - 80 

    RADIUS_X = 110
    RADIUS_Y = 140

    dx = cursor_pos[0] - target_center_x
    dy = cursor_pos[1] - target_center_y
    
    is_inside_hitbox = ((dx ** 2) / (RADIUS_X ** 2)) + ((dy ** 2) / (RADIUS_Y ** 2)) <= 1.0

    if is_inside_hitbox:
        if active_entity_type == "DECOY":
            audio.decoy_hit()
            if not is_striking:
                return False, tutorial_count, score, ghost_state, active_entity_type, death_sequences
        else:
            audio.ghost_hit()
            if not is_striking:
                return False, tutorial_count, score, ghost_state, active_entity_type, death_sequences

        print(f"[CLEAN SWEEP] {active_entity_type} Swept perfectly!")
        
        # === FIXED: was only checking `game_phase == 0` (PHASE_TUTORIAL), which
        # missed PHASE_TUTORIAL_MP (== 5) entirely. That meant every multiplayer
        # tutorial hit fell through to the `else` branch and incremented `score`
        # by mistake, so stage 1 started already carrying leftover tutorial points
        # (exactly matching the 10-hit multiplayer tutorial requirement).
        if game_phase in (0, 5):  # PHASE_TUTORIAL or PHASE_TUTORIAL_MP
            tutorial_count += 1
        else:                     # PHASE_GAMEPLAY
            score = score + 1 if active_entity_type == "GHOST" else max(0, score - 1)
            
        ghost_state = "DOWN"
        
        death_sequences.append({
            "pos": (ghost_current_x, ghost_current_y),
            "frame": 0,
            "type": active_entity_type
        })
        
        return True, tutorial_count, score, ghost_state, active_entity_type, death_sequences

    return False, tutorial_count, score, ghost_state, active_entity_type, death_sequences

def update_ghost_movement(ghost_state, ghost_y_offset, current_hole, last_move_time, move_interval, now, game_phase, osc_client, active_entity_type, current_stage=3):
    new_state = ghost_state
    new_offset = ghost_y_offset
    new_hole = current_hole
    new_move_time = last_move_time
    new_entity_type = active_entity_type

    if ghost_state == "DOWN":
        if active_entity_type == "DECOY":
            new_offset = 180
        else:
            new_offset += 30
            
        if new_offset >= 180:
            new_offset, new_state = 180, "HIDDEN"

            # Minimum distance spawn — next hole must be at least 500px away
            MIN_SPAWN_DISTANCE = 500
            far_holes = [
                h for h in hole_positions
                if h != current_hole and
                ((h[0] - current_hole[0])**2 + (h[1] - current_hole[1])**2) ** 0.5 >= MIN_SPAWN_DISTANCE
            ]
            new_hole = random.choice(far_holes if far_holes else [h for h in hole_positions if h != current_hole])
            
    elif ghost_state == "HIDDEN":
        new_state = "UP"
        new_move_time = now
        # Only assign DECOY in stage 3 — stages 1 and 2 are ghosts only
        if current_stage >= 3:
            new_entity_type = "DECOY" if random.random() < 0.70 else "GHOST"
        else:
            new_entity_type = "GHOST"
        
    elif ghost_state == "UP":
        if new_offset > 0: 
            new_offset -= 90 if active_entity_type == "DECOY" else 30
        else: 
            new_offset = 0
        
        if now - last_move_time > move_interval:
            new_state = "DOWN"
            new_move_time = now
            if game_phase == 3 and osc_client is not None and new_entity_type == "GHOST": 
                osc_client.send_message("/ghost/miss", 1)

    return new_state, new_offset, new_hole, new_move_time, new_entity_type

def render_gameplay_ui(screen, score, time_left):
    designs.draw_spooky_panel(screen, 60, 60, 480, 150, (20, 30, 25), "SWEPT", f"{score:02d}")
    designs.draw_spooky_panel(screen, WIDTH - 540, 60, 480, 150, (40, 15, 20), "TIME REM", f"{time_left:02d}s")

def render_speed_warning(screen, ui_font, title_font, now, speed_warning_start_ticks, width=1920):
    elapsed_warning_ms = now - speed_warning_start_ticks
    warning_countdown = max(1, 5 - (elapsed_warning_ms // 1000))
    warning_bar = pygame.Surface((width, 90), pygame.SRCALPHA)
    pulse_alpha = int(80 + math.sin(now * 0.01) * 40) 
    warning_bar.fill((200, 30, 30, pulse_alpha))
    screen.blit(warning_bar, (0, 120))
    alert_text = ui_font.render("ALERT: PHANTOM ACTIVITY RISING IN", True, (255, 220, 220))
    timer_text = title_font.render(f"{warning_countdown}", True, (255, 50, 50))
    screen.blit(alert_text, (width // 2 - 380, 145))
    screen.blit(timer_text, (width // 2 + 340, 130))