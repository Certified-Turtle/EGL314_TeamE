import pygame
import pygame.gfxdraw
import random
import math

WIDTH, HEIGHT = 1920, 1080

# 1. Define variables globally first
rain_particles = []
fog_particles = []
cached_ghost_surf = None
ghost_variants = {}  # NEW: color-variant ghost surfaces (red/blue/green auras)
vortex_scratch_surf = None

# === LIBRARY SCENE globals ===
dust_motes = []
fire_embers = []
_library_books_cache = None

# === LIGHTNING TINT VARIETY (NEW) ===
lightning_tints = {
    "blue":  (180, 190, 255),
    "red":   (255, 170, 170),
    "green": (180, 255, 190),
}
_current_lightning_tint = "blue"  # can be changed externally, e.g. per stage


def set_lightning_tint(name):
    """Call this from gameplay.py to change the lightning flash color
    (e.g. per stage: set_lightning_tint('red'))."""
    global _current_lightning_tint
    if name in lightning_tints:
        _current_lightning_tint = name


def _tint():
    return lightning_tints.get(_current_lightning_tint, lightning_tints["blue"])


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
    global rain_particles, fog_particles, cached_ghost_surf, vortex_scratch_surf, ghost_variants

    rain_particles = [{"x": random.randint(0, WIDTH), "y": random.randint(0, HEIGHT), "length": random.randint(22, 37), "speed": random.uniform(7.0, 12.0)} for _ in range(50)]

    fog_particles = []
    for _ in range(8):
        r = random.randint(60, 120)
        f_surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA).convert_alpha()
        draw_smooth_circle(f_surf, r, r, r, (80, 90, 100, 40))
        fog_particles.append({"x": random.randint(0, WIDTH), "y": random.randint(600, HEIGHT), "radius": r, "speed": random.uniform(0.3, 0.9), "surf": f_surf})

    cached_ghost_surf = build_ghost_surf((200, 235, 255))  # default blue-white ghost

    # NEW: pre-built color variants matching tracked object colors (green/purple/orange)
    # and the requested red/blue/green palette.
    ghost_variants = {
        "default": cached_ghost_surf,
        "red":     build_ghost_surf((235, 70, 70)),
        "blue":    build_ghost_surf((90, 150, 235)),
        "green":   build_ghost_surf((90, 215, 130)),
    }

    vortex_scratch_surf = pygame.Surface((240, 90), pygame.SRCALPHA).convert_alpha()

    # NEW: library-specific particles
    init_library_assets()


def build_ghost_surf(aura_color):
    """Builds a ghost sprite surface tinted with the given aura_color (r,g,b).
    Eyes stay red for contrast regardless of aura color."""
    surf = pygame.Surface((300, 400), pygame.SRCALPHA).convert_alpha()
    draw_smooth_ellipse(surf, 150, 180, 80, 110, (*aura_color, 180))
    draw_smooth_circle(surf, 150, 110, 80, (*aura_color, 180))
    draw_smooth_circle(surf, 120, 110, 15, (255, 10, 80, 230))
    draw_smooth_circle(surf, 180, 110, 15, (255, 10, 80, 230))
    draw_smooth_circle(surf, 120, 110, 5, (0, 0, 0, 255))
    draw_smooth_circle(surf, 180, 110, 5, (0, 0, 0, 255))
    _ripples = [(70, 260), (95, 310), (125, 260), (155, 310), (185, 260), (215, 310), (230, 260)]
    pygame.gfxdraw.filled_polygon(surf, _ripples, (*aura_color, 180))
    pygame.gfxdraw.aapolygon(surf, _ripples, (*aura_color, 180))
    return surf


def init_library_assets():
    """Populates library-specific particles (dust motes + fireplace embers).
    Called automatically from init_assets(), no need to call this separately."""
    global dust_motes, fire_embers
    dust_motes = [{"x": random.randint(0, WIDTH), "y": random.randint(0, HEIGHT),
                   "speed": random.uniform(0.2, 0.6), "drift": random.uniform(-0.3, 0.3),
                   "r": random.randint(2, 4)} for _ in range(40)]
    fire_embers = [{"x": 0, "y": 0, "speed": random.uniform(0.8, 2.2),
                    "drift": random.uniform(-0.4, 0.4), "life": random.uniform(0, 1),
                    "r": random.randint(2, 4)} for _ in range(22)]


# --- 4. SCENE DRAWING ENGINES ---
def draw_haunted_house(surface, lightning_active):
    tint = _tint()
    wall_base = (24, 18, 36) if not lightning_active else tint
    surface.fill(wall_base)
    stripe_color = (15, 10, 24) if not lightning_active else tuple(max(0, c - 50) for c in tint)
    for x in range(0, WIDTH, 120):
        pygame.draw.rect(surface, stripe_color, (x, 0, 22, 525))
    window_sky = (10, 8, 20) if not lightning_active else tuple(min(255, c + 30) for c in tint)
    pygame.draw.rect(surface, window_sky, (165, 165, 495, 345))

    rain_color = (70, 90, 120) if not lightning_active else (255, 255, 255)
    for r in rain_particles:
        pygame.draw.aaline(surface, rain_color, (r["x"], r["y"]), (r["x"] - (r["length"] * 0.3), r["y"] + r["length"]))
        r["y"] += r["speed"]; r["x"] -= r["speed"] * 0.3
        if r["y"] > 502 or r["x"] < 172:
            r["y"] = 165
            r["x"] = random.randint(195, 660)

    frame_color = (40, 35, 50) if not lightning_active else tuple(max(0, c - 90) for c in tint)
    pygame.draw.rect(surface, frame_color, (150, 150, 525, 375), width=22)
    pygame.draw.line(surface, frame_color, (412, 165), (412, 510), width=12)
    pygame.draw.line(surface, frame_color, (165, 337), (660, 337), width=12)
    floor_color = (45, 35, 30) if not lightning_active else tuple(max(0, c - 60) for c in tint)
    pygame.draw.rect(surface, floor_color, (0, 525, WIDTH, 555))
    for x in range(0, WIDTH, 90):
        pygame.draw.line(surface, (25, 18, 15) if not lightning_active else tuple(max(0, c - 100) for c in tint), (x, 525), (x, HEIGHT), width=3)

    for f in fog_particles:
        surface.blit(f["surf"], (int(f["x"] - f["radius"]), int(f["y"] - f["radius"])))
        f["x"] += f["speed"]
        if f["x"] - f["radius"] > WIDTH: f["x"] = -f["radius"]


# =================================================================
# === LIBRARY / STUDY SCENE ===
# =================================================================
def _generate_library_books(book_colors):
    """Builds a fixed list of book rectangles/colors ONCE, so they don't
    re-randomize (and therefore flicker) every single frame."""
    books = []
    for side_x in (0, WIDTH - 420):
        for shelf_y in range(140, 820, 130):
            bx = side_x + 15
            while bx < side_x + 400:
                bw = random.choice([14, 18, 22])
                bh = random.randint(90, 115)
                color = random.choice(book_colors)
                books.append((bx, shelf_y, bw, bh, color))
                bx += bw + 3
    return books


def draw_stained_glass(surface, x, y, w, h, current_ticks, lightning_active):
    """NEW: Stained-glass window with red / blue / green panes and lead lines.
    Adds a soft colored glow that pulses gently and flares brighter during lightning."""
    panel_colors = [(190, 35, 35), (35, 70, 190), (35, 150, 70)]  # red, blue, green
    pygame.draw.rect(surface, (18, 13, 9), (x - 12, y - 12, w + 24, h + 24), border_radius=8)  # outer frame

    pulse = 0.85 + 0.15 * math.sin(current_ticks * 0.003)
    if lightning_active:
        pulse = 1.3

    panel_w = w // len(panel_colors)
    for i, color in enumerate(panel_colors):
        glow_color = tuple(min(255, int(c * pulse)) for c in color)
        pygame.draw.rect(surface, glow_color, (x + i * panel_w, y, panel_w - 4, h))
        # simple diamond lattice pattern per pane for a stained-glass feel
        cx = x + i * panel_w + panel_w // 2
        cy = y + h // 2
        light_edge = tuple(min(255, c + 60) for c in glow_color)
        pygame.draw.line(surface, light_edge, (cx, y + 8), (x + i * panel_w + panel_w - 8, cy), 2)
        pygame.draw.line(surface, light_edge, (cx, y + 8), (x + i * panel_w + 8, cy), 2)
        pygame.draw.line(surface, light_edge, (cx, y + h - 8), (x + i * panel_w + panel_w - 8, cy), 2)
        pygame.draw.line(surface, light_edge, (cx, y + h - 8), (x + i * panel_w + 8, cy), 2)

    # lead lines between panes and around the border
    for i in range(1, len(panel_colors)):
        pygame.draw.line(surface, (12, 12, 12), (x + i * panel_w, y), (x + i * panel_w, y + h), 5)
    pygame.draw.rect(surface, (12, 12, 12), (x, y, w, h), width=5)


def draw_wall_sconces(surface, current_ticks):
    """NEW: Small flickering red / blue / green candle sconces scattered on the walls."""
    sconce_positions = [
        (55, 260, (210, 55, 55)),
        (WIDTH - 55, 420, (55, 95, 210)),
        (55, 640, (55, 190, 90)),
        (WIDTH - 55, 780, (210, 55, 55)),
    ]
    for x, y, color in sconce_positions:
        flicker = 1.0 + 0.18 * math.sin(current_ticks * 0.02 + x * 0.01)
        # small wall bracket
        pygame.draw.rect(surface, (30, 22, 16), (x - 6, y + 10, 12, 22))
        # glow halo
        glow_surf = pygame.Surface((80, 80), pygame.SRCALPHA)
        draw_smooth_circle(glow_surf, 40, 40, int(26 * flicker), (*color, 70))
        surface.blit(glow_surf, (x - 40, y - 40))
        # flame core
        draw_smooth_circle(surface, x, y, int(9 * flicker), color)
        draw_smooth_circle(surface, x, y, int(4 * flicker), (255, 240, 210))


def _draw_realistic_fire(surface, cx, base_y):
    """Layered, animated fireplace flame — multiple flickering tongues,
    a soft glow, and rising embers, instead of a single static blob."""
    t = pygame.time.get_ticks()

    glow_pulse = 0.85 + 0.15 * math.sin(t * 0.006)
    glow_surf = pygame.Surface((420, 300), pygame.SRCALPHA)
    draw_smooth_ellipse(glow_surf, 210, 220, int(190 * glow_pulse), int(150 * glow_pulse), (255, 140, 40, 55))
    surface.blit(glow_surf, (cx - 210, base_y - 220))

    tongue_defs = [
        (0,   95, 1.00, (200, 40, 10)),
        (35,  80, 1.35, (220, 60, 10)),
        (-18, 70, 0.85, (255, 110, 20)),
        (18,  70, 1.15, (255, 120, 20)),
        (0,   55, 1.55, (255, 200, 60)),
    ]
    for dx, height, phase, color in tongue_defs:
        wobble = math.sin(t * 0.012 * phase + dx) * 10
        sway = math.sin(t * 0.004 * phase) * 6
        tip_x = cx + dx + sway + wobble
        base_l = cx + dx - 26
        base_r = cx + dx + 26
        mid_l = cx + dx - 14 + wobble * 0.5
        mid_r = cx + dx + 14 - wobble * 0.5
        flame_pts = [
            (base_l, base_y), (base_r, base_y),
            (mid_r, base_y - height * 0.55),
            (tip_x, base_y - height),
            (mid_l, base_y - height * 0.55),
        ]
        pygame.gfxdraw.filled_polygon(surface, [(int(x), int(y)) for x, y in flame_pts], color)
        pygame.gfxdraw.aapolygon(surface, [(int(x), int(y)) for x, y in flame_pts], color)

    for e in fire_embers:
        e["life"] -= 0.012
        if e["life"] <= 0:
            e["life"] = 1.0
            e["x"] = cx + random.randint(-40, 40)
            e["y"] = base_y - 20
            e["speed"] = random.uniform(0.8, 2.2)
            e["drift"] = random.uniform(-0.4, 0.4)
        e["y"] -= e["speed"]
        e["x"] += e["drift"]
        alpha = max(0, int(255 * e["life"]))
        ember_color = (255, 160, 40, alpha)
        ember_surf = pygame.Surface((10, 10), pygame.SRCALPHA)
        draw_smooth_circle(ember_surf, 5, 5, e["r"], ember_color)
        surface.blit(ember_surf, (int(e["x"] - 5), int(e["y"] - 5)))


def draw_library(surface, lightning_active):
    global _library_books_cache

    current_ticks = pygame.time.get_ticks()
    tint = _tint()

    wall_color = (26, 18, 14) if not lightning_active else tint
    surface.fill(wall_color)

    # Floor-to-ceiling bookshelves left and right
    shelf_color = (40, 26, 16) if not lightning_active else tuple(min(255, c + 20) for c in tint)
    book_colors_dim = [(80, 30, 30), (30, 60, 40), (60, 45, 20), (35, 35, 70), (70, 55, 20)]

    if _library_books_cache is None:
        _library_books_cache = _generate_library_books(book_colors_dim)

    for side_x in (0, WIDTH - 420):
        pygame.draw.rect(surface, shelf_color, (side_x, 100, 420, 780))
        for shelf_y in range(140, 820, 130):
            pygame.draw.rect(surface, (20, 13, 9) if not lightning_active else tuple(max(0, c - 40) for c in tint), (side_x, shelf_y, 420, 14))

    for (bx, shelf_y, bw, bh, base_color) in _library_books_cache:
        if lightning_active:
            color = tuple(min(255, c + 110) for c in base_color)
        else:
            color = base_color
        pygame.draw.rect(surface, color, (bx, shelf_y - bh, bw, bh))

    # NEW: Stained-glass window, upper wall between the shelves
    draw_stained_glass(surface, WIDTH // 2 - 210, 90, 420, 260, current_ticks, lightning_active)

    # NEW: Wall sconces (red/blue/green candle flames) along both shelving walls
    draw_wall_sconces(surface, current_ticks)

    # Large dusty globe on a stand, center-left
    globe_color = (70, 90, 70) if not lightning_active else (150, 180, 150)
    draw_smooth_circle(surface, 640, 760, 70, globe_color)
    pygame.draw.arc(surface, (30, 40, 30), (570, 690, 140, 140), 0.3, 2.8, 3)
    pygame.draw.line(surface, (50, 35, 20), (640, 830), (640, 900), width=8)
    pygame.draw.rect(surface, (50, 35, 20), (600, 895, 80, 16))

    # Fireplace, center, casting warm glow
    fp_color = (35, 28, 24) if not lightning_active else (150, 135, 125)
    pygame.draw.rect(surface, fp_color, (WIDTH // 2 - 160, 480, 320, 340), border_radius=10)
    pygame.draw.rect(surface, (10, 8, 8), (WIDTH // 2 - 110, 620, 220, 200))
    _draw_realistic_fire(surface, WIDTH // 2, 815)
    pygame.draw.rect(surface, (25, 20, 16), (WIDTH // 2 - 140, 460, 280, 24))

    # High-backed armchair in front of the fire
    chair_color = (60, 20, 20) if not lightning_active else (170, 90, 90)
    pygame.draw.rect(surface, chair_color, (WIDTH // 2 - 260, 780, 140, 220), border_top_left_radius=30, border_top_right_radius=30)
    pygame.draw.rect(surface, chair_color, (WIDTH // 2 - 260, 950, 140, 40))

    # Grandfather clock, right side
    clock_x = WIDTH - 560
    clock_color = (45, 30, 18) if not lightning_active else (160, 140, 115)
    pygame.draw.rect(surface, clock_color, (clock_x, 260, 100, 560), border_top_left_radius=20, border_top_right_radius=20)
    draw_smooth_circle(surface, clock_x + 50, 340, 42, (230, 220, 200))
    pygame.draw.line(surface, (10, 10, 10), (clock_x + 50, 340), (clock_x + 50, 310), width=3)
    pygame.draw.line(surface, (10, 10, 10), (clock_x + 50, 340), (clock_x + 72, 350), width=3)

    # Wooden floorboards
    floor_color = (30, 22, 15) if not lightning_active else (140, 125, 105)
    pygame.draw.rect(surface, floor_color, (0, 900, WIDTH, HEIGHT - 900))
    for x in range(0, WIDTH, 110):
        pygame.draw.line(surface, (15, 10, 6) if not lightning_active else (100, 90, 75), (x, 900), (x, HEIGHT), width=3)

    # Dust motes drifting in firelight
    for m in dust_motes:
        draw_smooth_circle(surface, m["x"], m["y"], m["r"], (200, 190, 160, 120) if not lightning_active else (255, 255, 240))
        m["y"] -= m["speed"]
        m["x"] += m["drift"]
        if m["y"] < 0:
            m["y"] = HEIGHT
            m["x"] = random.randint(0, WIDTH)


def draw_ghost_entity(surface, pos, y_offset, current_ticks, variant="default"):
    """variant can be 'default', 'red', 'blue', or 'green' to match tracked
    object colors from gameplay.py (e.g. green/purple/orange tracking)."""
    x, y = pos
    ghost_surf = ghost_variants.get(variant, cached_ghost_surf)
    float_anim = math.sin(current_ticks * 0.007) * 22
    y += int(y_offset + float_anim)
    surface.set_clip(pygame.Rect(0, 0, WIDTH, y - y_offset + 60))
    surface.blit(ghost_surf, (x - 150, y - 150))
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

def draw_crosshair(screen, cursor_pos, color=(0, 255, 0)):
    x, y = cursor_pos
    # Tight, crisp, smaller crosshair lines
    pygame.draw.line(screen, color, (x - 12, y), (x + 12, y), 2) # Crosshair (P1 defaults to green)
    pygame.draw.line(screen, color, (x, y - 12), (x, y + 12), 2)
    pygame.draw.circle(screen, color, (x, y), 3, 1) # Tiny center intersection ring
    pygame.draw.circle(screen, (255, 140, 0), (x, y), 24, 2)

def draw_pause_overlay(surface, title_font, ui_font):
    """Dims the frozen scene and shows a PAUSED message with resume instructions."""
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((5, 5, 10, 180))
    surface.blit(dim, (0, 0))

    pause_txt = title_font.render("PAUSED", True, (0, 255, 180))
    pause_rect = pause_txt.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30))
    surface.blit(pause_txt, pause_rect)

    resume_txt = ui_font.render("PRESS  [P]  TO RESUME", True, (200, 210, 230))
    resume_rect = resume_txt.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
    surface.blit(resume_txt, resume_rect)