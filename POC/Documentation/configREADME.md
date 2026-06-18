# config.py

This is the file that stores all shared settings, constants, and global game state variables used across the entire project. Acting as a control panel for game settings, UI layout, computer vision thresholds, game phases and game mechanics.

```bash
WIDTH, HEIGHT = 1920, 1080
```

Defines screen resolution and is used for UI placement and coordinate scaling across the game.

=====================================================================================

```bash
GREEN_LOWER = np.array([35, 100, 100])
GREEN_UPPER = np.array([85, 255, 255])
```

Sets the HSV colour range for what is considered green. A Lower GREEN_LOWER threshold would make it easier to detect darker less saturated shades of green and convorsely a higher threshold for GREEN_UPPER makes easier detection for bright shades of green such as neon green

=====================================================================================

```bash
PHASE_INTRO = -1
PHASE_TUTORIAL = 0
PHASE_INSTRUCT = 1
PHASE_PREPARE = 2
PHASE_GAMEPLAY = 3
PHASE_GAMEOVER = 4
```

These define the different game phases and controls the flow of the game, comparable to a state machine. Each number representing a dfferent state or screen.

=====================================================================================

```bash
HOVER_TO_START_FRAMES = 35
```
This sets that players need to hover over the start button for over 35 frames to activate it.

=====================================================================================

```bash
hole_positions = [(480 + col * 480, 660 + row * 150) for row in range(3) for col in range(3)]
```
Generates a 3 by 3 grid of spawn locations where ghost and Jack-O-Lanterns can spawn.

=====================================================================================

```bash
START_BUTTON_RECT = pygame.Rect(WIDTH//2 - 250, HEIGHT//2 + 80, 500, 160)
```
Defines the start button seen at the start of the game.

=====================================================================================

```bash
gesture_hold_progress = 0
GESTURE_HOLD_TARGET = 60  # Updated: Exactly 3.0 seconds sustained at 60 FPS
```
Creates the loading bar for when detecing the required hand gesture.

=====================================================================================

```bash
decoy_hole = None
decoy_state = "HIDDEN"  # "UP", "DOWN", "HIDDEN"
decoy_y_offset = 180
active_entity_type = "GHOST"  # Tracks whether a "GHOST" or "DECOY" is active in the hole
```

Creates the decoy system allowing for decoy Jack-O-Lanterns to spawn.

=====================================================================================

```bash
current_move_interval = 2200  # Default 2.2 seconds
next_speed_bump_time = 15000   # First shift at 15s (15000ms)
speed_bump_interval = 7000     # Follow-up steps every 7s (7000ms)
speed_multiplier = 1.0         # Current acceleration multiplier step
last_speed_bump_time = 0       # Milestone checker for speed updates
```
This is the code responsible for speeding up the game as the game progresses.
