import math
import random
import pygame
import designs

WIDTH, HEIGHT = 1920, 1080
hole_positions = [(480 + col * 480, 660 + row * 150) for row in range(3) for col in range(3)]

def check_ghost_collisions(game_phase, cursor_pos, current_hole, ghost_state, ghost_y_offset, tutorial_count, score, death_sequences, now, active_entity_type, is_striking):
    # FIX: Ensure we don't process collisions if the entity isn't fully surfaced
    if ghost_state != "UP" or current_hole is None:
        return False, tutorial_count, score, ghost_state, active_entity_type, death_sequences

    if isinstance(current_hole, (tuple, list)):
        hole_x, hole_y = current_hole[0], current_hole[1]
    else:
        hole_x, hole_y = hole_positions[current_hole]
        
    ghost_current_x = hole_x
    ghost_current_y = hole_y - ghost_y_offset

    # =================================================================
    # === ADJUSTED: PERFECT CROSSHAIR-SPAN HITBOX MATRIX ===
    # =================================================================
    # Shift the target calculation center up to match the chest/face mass of the sprite
    target_center_x = ghost_current_x
    target_center_y = ghost_current_y - 80 

    # FIXED: Expanded the boundaries so that the cross lines extending out
    # from your cursor center safely trigger a hit when overlapping the asset.
    RADIUS_X = 110  # Widened horizontally from 65 -> 110
    RADIUS_Y = 140  # Tallened vertically from 110 -> 140

    # Calculate exact distance offset
    dx = cursor_pos[0] - target_center_x
    dy = cursor_pos[1] - target_center_y
    
    # Elliptical collision boundary calculation
    is_inside_hitbox = ((dx ** 2) / (RADIUS_X ** 2)) + ((dy ** 2) / (RADIUS_Y ** 2)) <= 1.0

    if is_inside_hitbox:
        # Strike verification gates
        if active_entity_type == "DECOY":
            if not is_striking:
                return False, tutorial_count, score, ghost_state, active_entity_type, death_sequences
        else:
            if not is_striking:
                return False, tutorial_count, score, ghost_state, active_entity_type, death_sequences

        print(f"[CLEAN STRIKE] {active_entity_type} whacked perfectly!")
        
        # Determine score outcomes based on game phase context
        # FIXED: Enforce phase 0 (PHASE_TUTORIAL) or active gameplay routing smoothly
        if game_phase == 0:  # PHASE_TUTORIAL
            tutorial_count += 1
        else:                # PHASE_GAMEPLAY
            score = score + 1 if active_entity_type == "GHOST" else max(0, score - 1)
            
        ghost_state = "DOWN"
        
        # Append particle effect dictionary metadata securely
        death_sequences.append({
            "pos": (ghost_current_x, ghost_current_y),
            "frame": 0,
            "type": active_entity_type
        })
        
        return True, tutorial_count, score, ghost_state, active_entity_type, death_sequences

    return False, tutorial_count, score, ghost_state, active_entity_type, death_sequences

def update_ghost_movement(ghost_state, ghost_y_offset, current_hole, last_move_time, move_interval, now, game_phase, osc_client, active_entity_type):
    new_state = ghost_state
    new_offset = ghost_y_offset
    new_hole = current_hole
    new_move_time = last_move_time
    new_entity_type = active_entity_type

    if ghost_state == "DOWN":
        # ---> FEATURE FIX: If it's a DECOY, drop it down instantly (180) instead of animating slowly
        if active_entity_type == "DECOY":
            new_offset = 180
        else:
            new_offset += 30
            
        if new_offset >= 180:
            new_offset, new_state = 180, "HIDDEN"
            new_hole = random.choice([h for h in hole_positions if h != current_hole])
            
    elif ghost_state == "HIDDEN":
        new_state = "UP"
        new_move_time = now 
        new_entity_type = "DECOY" if random.random() < 0.70 else "GHOST" # Increased spawn rate to 35% as requested!
        
    elif ghost_state == "UP":
        if new_offset > 0: 
            # Decoys pop up quickly, regular ghosts pop up at standard speed
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
    designs.draw_spooky_panel(screen, 60, 60, 480, 150, (20, 30, 25), "CAPTURED", f"{score:02d}")
    designs.draw_spooky_panel(screen, WIDTH - 540, 60, 480, 150, (40, 15, 20), "TIME REM", f"{time_left:02d}s")

def render_speed_warning(screen, ui_font, title_font, now, speed_warning_start_ticks, width=1920):
    """Renders a pulsing red warning bar and countdown overlay for the upcoming speed surge."""
    # 1. Calculate remaining warning seconds (counting down from 5 to 1)
    elapsed_warning_ms = now - speed_warning_start_ticks
    warning_countdown = max(1, 5 - (elapsed_warning_ms // 1000))
    
    # 2. Create a semi-transparent warning backdrop bar
    warning_bar = pygame.Surface((width, 90), pygame.SRCALPHA)
    
    # Pulsing red animation background using sine wave math
    pulse_alpha = int(80 + math.sin(now * 0.01) * 40) 
    warning_bar.fill((200, 30, 30, pulse_alpha))
    screen.blit(warning_bar, (0, 120))
    
    # 3. Construct text strings
    alert_text = ui_font.render("ALERT: GHOST ACTIVITY RISING IN", True, (255, 220, 220))
    timer_text = title_font.render(f"{warning_countdown}", True, (255, 50, 50))
    
    # 4. Blit text elements centered neatly inside our presentation bar
    screen.blit(alert_text, (width // 2 - 380, 145))
    screen.blit(timer_text, (width // 2 + 340, 130))