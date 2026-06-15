import pygame
import pygame.gfxdraw
import random
import math

WIDTH, HEIGHT = 1920, 1080

# 1. Define variables globally first
rain_particles = []
fog_particles = []
cached_ghost_surf = None
vortex_scratch_surf = None

# 2. Keep the helper drawing tools here
def draw_smooth_circle(surface, x, y, radius, color):
    pygame.gfxdraw.aacircle(surface, int(x), int(y), int(radius), color)
    pygame.gfxdraw.filled_circle(surface, int(x), int(y), int(radius), color)

def draw_smooth_ellipse(surface, x, y, rx, ry, color):
    pygame.gfxdraw.aaellipse(surface, int(x), int(y), int(rx), int(ry), color)
    pygame.gfxdraw.filled_ellipse(surface, int(x), int(y), int(rx), int(ry), color)

# 3. Use them inside your asset initializer
def init_assets():
    """Call this function ONLY after pygame.display.set_mode has executed."""
    global rain_particles, fog_particles, cached_ghost_surf, vortex_scratch_surf
    
    rain_particles = [{"x": random.randint(0, WIDTH), "y": random.randint(0, HEIGHT), "length": random.randint(22, 37), "speed": random.uniform(7.0, 12.0)} for _ in range(50)]

    fog_particles = []
    for _ in range(8):
        r = random.randint(60, 120)
        f_surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA).convert_alpha()
        draw_smooth_circle(f_surf, r, r, r, (80, 90, 100, 40))
        fog_particles.append({"x": random.randint(0, WIDTH), "y": random.randint(600, HEIGHT), "radius": r, "speed": random.uniform(0.3, 0.9), "surf": f_surf})

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

# --- 4. SCENE DRAWING ENGINES ---
def draw_cemetery(surface, lightning_active):
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
    for r in rain_particles:
        pygame.draw.aaline(surface, rain_color, (r["x"], r["y"]), (r["x"] - (r["length"] * 0.3), r["y"] + r["length"]))
        r["y"] += r["speed"]
        r["x"] -= r["speed"] * 0.3
        if r["y"] > HEIGHT or r["x"] < 0:
            r["y"] = random.randint(-40, 0)
            r["x"] = random.randint(0, WIDTH)

def draw_haunted_house(surface, lightning_active):
    wall_base = (24, 18, 36) if not lightning_active else (210, 215, 255)
    surface.fill(wall_base)
    stripe_color = (15, 10, 24) if not lightning_active else (160, 170, 220)
    for x in range(0, WIDTH, 120):
        pygame.draw.rect(surface, stripe_color, (x, 0, 22, 525))
    window_sky = (10, 8, 20) if not lightning_active else (180, 190, 255)
    pygame.draw.rect(surface, window_sky, (165, 165, 495, 345))
    
    rain_color = (70, 90, 120) if not lightning_active else (255, 255, 255)
    for r in rain_particles:
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
        
    for f in fog_particles:
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

def draw_jack_o_lantern(surface, pos, y_offset, current_ticks):
    """Draws a spooky animated Jack-o'-Lantern decoy using gfxdraw."""
    x, y = pos
    float_anim = math.sin(current_ticks * 0.007) * 22
    y += int(y_offset + float_anim)
    
    # Base Pumpkin (Orange Ellipse layer)
    draw_smooth_ellipse(surface, x, y, 75, 65, (230, 90, 10))
    
    # Stem (Green top handle)
    pygame.draw.lines(surface, (40, 90, 30), False, [(x, y-60), (x+5, y-70), (x+15, y-75)], width=8)
    
    # Carved Glowing Eyes (Triangles)
    pygame.gfxdraw.filled_polygon(surface, [(x-35, y-10), (x-15, y-10), (x-25, y-28)], (255, 200, 0))
    pygame.gfxdraw.aapolygon(surface, [(x-35, y-10), (x-15, y-10), (x-25, y-28)], (255, 200, 0))
    
    pygame.gfxdraw.filled_polygon(surface, [(x+15, y-10), (x+35, y-10), (x+25, y-28)], (255, 200, 0))
    pygame.gfxdraw.aapolygon(surface, [(x+15, y-10), (x+35, y-10), (x+25, y-28)], (255, 200, 0))
    
    # Spooky Jagged Mouth (Polygon cutout)
    mouth_pts = [(x-45, y+10), (x-25, y+25), (x-15, y+15), (x, y+30), (x+15, y+15), (x+25, y+25), (x+45, y+10), (x, y+42)]
    pygame.gfxdraw.filled_polygon(surface, mouth_pts, (255, 200, 0))
    pygame.gfxdraw.aapolygon(surface, mouth_pts, (255, 200, 0))

def draw_spooky_panel(surface, x, y, w, h, base_color, label, value):
    pygame.draw.rect(surface, base_color, (x, y, w, h), border_radius=12)
    pygame.draw.rect(surface, (100, 105, 120), (x, y, w, h), width=4, border_radius=12)
    font = pygame.font.SysFont("Courier New", 63, bold=True)
    txt = font.render(f"{label}:{value}", True, (230, 240, 255))
    surface.blit(txt, (x + 30, y + 45))

def draw_death_sequence(surface, active_deaths, current_ticks):
    # Fallback initialization if it doesn't exist globally
    global vortex_scratch_surf
    if 'vortex_scratch_surf' not in globals():
        vortex_scratch_surf = pygame.Surface((300, 150), pygame.SRCALPHA)

    for death in active_deaths:
        pos = death["pos"]; frame = death["frame"]
        
        # --- PHASE 1: GREEN ENERGY FLASH ---
        if frame <= 6:
            radius = max(1, int(frame * 18)) # Ensure radius is at least 1
            pygame.gfxdraw.aacircle(surface, int(pos[0]), int(pos[1]), radius, (0, 255, 150))
            pygame.draw.circle(surface, (0, 255, 150), (int(pos[0]), int(pos[1])), radius, min(6, radius))
            pygame.draw.aaline(surface, (255, 255, 255), (pos[0]-radius, pos[1]-radius), (pos[0]+radius, pos[1]+radius))
            pygame.draw.aaline(surface, (255, 255, 255), (pos[0]+radius, pos[1]-radius), (pos[0]-radius, pos[1]+radius))
            
        # --- PHASE 2: FLOATING SKULL ---
        if 3 <= frame <= 20:
            up_drift = (frame - 3) * 6; skull_y = pos[1] - up_drift
            draw_smooth_circle(surface, pos[0], skull_y, 27, (230, 220, 255))
            pygame.draw.rect(surface, (230, 220, 255), (pos[0]-15, skull_y+15, 30, 18), border_bottom_left_radius=6, border_bottom_right_radius=6)
            pygame.draw.line(surface, (40, 30, 50), (pos[0]-6, skull_y+24), (pos[0]-6, skull_y+33), 3)
            pygame.draw.line(surface, (40, 30, 50), (pos[0]+6, skull_y+24), (pos[0]+6, skull_y+33), 3)
            draw_smooth_circle(surface, pos[0]-9, skull_y+3, 6, (20, 10, 35))
            draw_smooth_circle(surface, pos[0]+9, skull_y+3, 6, (20, 10, 35))
            
        # --- PHASE 3: PURPLE VORTEX ---
        if 8 <= frame <= 24:
            vortex_frame = frame - 8; width = 135 - (vortex_frame * 6); height = 37 - (vortex_frame * 1.5)
            spin_offset = math.sin(current_ticks * 0.05 + frame) * 22
            if width > 0 and height > 0:
                vortex_scratch_surf.fill((0, 0, 0, 0)) # Clear transparently
                
                # Draw relative to the scratchpad coordinates (150, 75 is the center of our 300x150 scratchpad)
                center_x = 150 + int(spin_offset * 0.3)
                center_y = 75
                draw_smooth_ellipse(vortex_scratch_surf, center_x, center_y, int(width//2), int(height//2), (150, 100, 255, 130))
                
                # Blit the scratchpad centered over the ghost hole position
                surface.blit(vortex_scratch_surf, (pos[0] - 150, pos[1] - int(vortex_frame * 9) - 75))

def draw_crosshair(screen, cursor_pos):
    x, y = cursor_pos
    # Tight, crisp, smaller crosshair lines
    pygame.draw.line(screen, (0, 255, 0), (x - 12, y), (x + 12, y), 2) # Green crosshair
    pygame.draw.line(screen, (0, 255, 0), (x, y - 12), (x, y + 12), 2)
    pygame.draw.circle(screen, (0, 255, 0), (x, y), 3, 1) # Tiny center intersection ring
    pygame.draw.circle(screen, (255, 140, 0), (x, y), 24, 2)

