# designs,py README

This code is a modular Pygame rendering engine designed to create a haunted themed visual interface. Itfocuses on drawing stylized, animated graphics like the ghosts and jack-o-lanterns and the atmospheric effects, rather than handling the game logic.

We start the code by importing the following libraries.

```bash
import pygame
import pygame.gfxdraw
import random
import math
```

This defines the resolution of the game window.

```bash
WIDTH, HEIGHT = 1920, 1080
```

This code initializes the global state containers that acts as the 'memory' for the visual engine. By declaring these at the top of the code, it creates variables  that can be accessed, modified, or cleared by any of the drawing functions throughout the lifetime of the program.

```bash
rain_particles = []
fog_particles = []
cached_ghost_surf = None
vortex_scratch_surf = None
```

These functions are custom 'wrappers' degisned to fix a common limitation in standard pygame drawing, which is pixelation. By default, Pygame's standard ```bash pygame.draw.circle``` or ```bash pygame.draw.ellipse``` functions can look jagged or 'blocky' because they do not use anti-aliasing (smoothing). These functions solve that by using the ```bash pygame.gfxdraw``` library to blend the edges of your shapes into the background.

```bash
def draw_smooth_circle(surface, x, y, radius, color):
    pygame.gfxdraw.aacircle(surface, int(x), int(y), int(radius), color)
    pygame.gfxdraw.filled_circle(surface, int(x), int(y), int(radius), color)

def draw_smooth_ellipse(surface, x, y, rx, ry, color):
    pygame.gfxdraw.aaellipse(surface, int(x), int(y), int(rx), int(ry), color)
    pygame.gfxdraw.filled_ellipse(surface, int(x), int(y), int(rx), int(ry), color)
```

The ```bash init_assets()``` function serves as the factory for your visual elements. It populates the global lists and surface variables you defined earlier, essentially 'preparing the scene' before the main game loop begins. It also initializes the rain and fog throughout the game

```bash
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
```

This code is pre-rendering complex visual assets onto their own 'off-screen' surfaces. This is a common performance optimization in Pygame used to draw complex objects once, and then simply 'stamp' them onto the screen later.

```bash
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
```

This code draws the cemetery background, tombstones and the dead tree.

[Cemetery](EGL314_TeamE/POC/Images/CemeteryBackground.jpg)