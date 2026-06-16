# addons.py
import pygame
import random
import math
import config

def process_gesture_loading_bar(screen, is_thumbs_up, ui_font):
    """Renders the visual elements of the progress bar based on current configuration values."""
    bar_w, bar_h = 500, 40
    bx = config.WIDTH // 2 - bar_w // 2
    by = 820
    
    # Background Track
    pygame.draw.rect(screen, (40, 40, 50), (bx, by, bar_w, bar_h), border_radius=8)
    
    # Render Active Progress Fill based on global configuration memory state
    fill_pct = config.gesture_hold_progress / config.GESTURE_HOLD_TARGET
    if fill_pct > 0:
        pygame.draw.rect(screen, (0, 255, 150), (bx, by, int(bar_w * fill_pct), bar_h), border_radius=8)
        
    # Border Outline
    pygame.draw.rect(screen, (0, 255, 150), (bx, by, bar_w, bar_h), width=3, border_radius=8)

    # Percentage Calibration text layout matrix helper
    txt = ui_font.render(f"CALIBRATING GESTURE: {int(fill_pct * 100)}%", True, (230, 240, 255))
    screen.blit(txt, txt.get_rect(center=(config.WIDTH // 2, by - 25)))

def rolls_decoy_spawn(ghost_hole):
    """Rolls a probability matrix chance to spawn a penalty decoy."""
    if random.random() < 0.45:  # Controlled 45% spawn chance
        config.decoy_hole = random.choice([h for h in config.hole_positions if h != ghost_hole])
        config.decoy_state = "UP"
        config.decoy_y_offset = 180
    else:
        config.decoy_state = "HIDDEN"
        config.decoy_hole = None

def process_decoy_logic(cursor_pos):
    """Animates the backend decoy states and calculates scoring penalties on collision."""
    if config.decoy_state == "HIDDEN" or config.decoy_hole is None:
        return 0

    if config.decoy_state == "UP":
        if config.decoy_y_offset > 0: 
            config.decoy_y_offset -= 45  # Pops up quickly (4 frames)
        else:
            config.decoy_y_offset = 0
            
    elif config.decoy_state == "DOWN":
        # ---> INCREASE THIS TO 90 OR 180 TO MAKE IT RETREAT INSTANTLY <---
        config.decoy_y_offset += 90  
        
        if config.decoy_y_offset >= 180:
            config.decoy_state = "HIDDEN"
            config.decoy_hole = None
            return 0

    # Calculate current target math coordinates
    dx, dy = config.decoy_hole[0], config.decoy_hole[1] - 45 + config.decoy_y_offset
    
    # Evaluate Crosshair Intersection
    if math.hypot(cursor_pos[0] - dx, cursor_pos[1] - dy) < 180:
        config.decoy_state = "DOWN"  # Triggers the fast retreat path configured above
        return -1  
    return 0

def handle_dynamic_difficulty(gameplay_duration):
    """Scales ghost visibility windows down over runtime milestones."""
    if gameplay_duration > config.next_speed_bump_time:
        config.current_move_interval = max(750, config.current_move_interval - 300) 
        
        if config.next_speed_bump_time == 15000:
            config.next_speed_bump_time = 15000 + config.speed_bump_interval
        else:
            config.next_speed_bump_time += config.speed_bump_interval
        print(f"[ DIFFICULTY BUMP ] New Speed Window Locked: {config.current_move_interval}ms")