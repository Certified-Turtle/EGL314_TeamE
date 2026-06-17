# Main.py README

---

This code's purpose is to serve as the central control system for an interactive, gesture controlled "Whack-a-Ghost" game.

It's primary function is to bridge the gap between virtual game logic and physical world interaction. So, instead of running a standalone came, this script coordinates multiple hardware inputs and outputs to create a synchronized and immersive haunted house experience.

We start off with importing the various libraries shown below.

```bash
import pygame
import pygame.gfxdraw
import random
import sys
import os
import math
```

### What each library does:
| Library | Function |
| :--- | :--- |
| `import pygame` | Think of this as the General Contractor. Builds the stage (the window on your screen), shows the actors (ghosts and decoys), listens to the audience (player's input) and manages the music and lighting. |
| `import pygame.gfxdraw` | This would be the artist. The general contractor can build walls, but the artist specialises in making things look smooth and polished, like drawing the rounded holes for the ghosts or decoys to pop out of. |
| `import random | This is the "Chaos Manager" per se. In a classic Whack-a-Mole game, you wouldn't want the ghost to appear in the same spot at the same time every time. So, you would use the Chaos Manager to roll a dice and decide, 'Okay, put the next ghost in hole #5' or 'Trigger a lightning strike now'. |
| `import sys` | This is the "Security Guard". When you want to close the game, the Security Guard makes sure everything is turned off properly so that the computer doesn't get confused or leave 'dangling' files behind. |
| `import os` | This is the "Office Manager". They talk to your computer's operating system to make sure the game knows which screen to use and how to talk to your graphics card to make the images look crisp. |
| `import math` | This is the "Math Teacher". The computer needs to know exactly how far your hand coordinates are from tehe ghost/decoy to decide if you've 'whacked' it. This library does the measuring and geometry calculations. |

Afterwards, we need to import the following:
```bash
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
```
By importing these modules, you reduce the chances of having your main code being thousands of lines long. If you make a mistake in the code, you would have to search through a long list of code to find it.

| Module | Function |
| :--- | :--- |
| `import designs` | Contains all the code for drawing the background, graveyard, even the ghosts themselves. |
| `import opencv` | This handles all the "camera" work. It looks at the raw video feed, finds your hand and figures out where you're pointing. |
| `import start_button` and `import tutorial` | These files manage the "Welcome" screens, the instructions, and the "How-to-play" guide, to ensure the player knows what to do even before the game starts. |
| `import gameplay` | It calculates the game logic. Did the player "whack" a ghost? Did they miss a decoy? What score did they get? This .py file essentially makes the game fair. |
| `import restart_quit` | It handles the clearing of score, resetting the game, or closing the software properly when the player is finished.
| `import addons` | This contains the loading bar for your hand gestures.
| `import config` | This stores the "constants" -- like how fast the ghosts move, the specific colours of the UI etc. |
| `from pythonosc import udp_client` | Used to send wireless messages to other devices on your network. |
| `import lighting` and `import audio` | Takes the commands and translates them into physical actions like flashing the room lights or playing sound effects on a different laptop even. |

## Section 1

This section would be the setup phase. This code standardizes the environment, ensuring the game always runs at a consistent resolution and looks polished, regardless of what hardware you use to run it.

```bash
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
```
This code stores the important information it needs to track, such as the game phases. It stores the IP addresses for the other hardware, like the OSC clients and OSC server. The code also contains the pre-determined list that tells the game the order of ghosts and decoys to spawn. It also keeps track of where the player's hand is and checks if the camera is ready to see the playerm so the game doesn't start until everything is working.

```bash
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
```
This section ensures the hardware is ready.

```bash
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
```

## Section 3

This while True loop is the endless heartbeat of the game. Because it is set to True, it runs continuously, repeating its entire sequence of instructions roughly 60 times every second until you force the program to close. Without this loop, the code would run once from top to bottom and finish, causing the game to close instantly.

Everytime the loop restarts, it performs these 3 vital tasks.

| Task | Purpose |
| :--- | :--- |
| Checks the inputs | It checks the camear to see where the player is pointing and listens for keyboard commands like pressing 'Escape' to quit or 'C' for the camera debug window. |
| Logic | It updates the game by moving the ghosts, checking if the player's hand overlaps with a target, manages the game timer and decides which game phase is currently active. |
| Checks outputs | It triggers physical room effects like sending an OSC signal to flash the room lights and refreshes the display by drawing the latest frame onto the monitor. |

Some control functions include:

| Function | Purpose |
| :--- | :--- |
| `pygame.QUIT` / `K_ESCAPE` | The 'Kill Switch'. This immediately shuts down the program and safely cleans up your camera and network connections. |
| `K_c` | The debug camera toggle. It toggles the small camera window on/off, allowing you to see if the computer vision is still detecting the player correctly.
| `K_r` | (Reset) During the PHASE_GAMEOVER state, this triggers the restart_quit.reset_game(). It wipes the scores, resets the spawn pointers and restarts the room lighting system to clear the previous game session. |


