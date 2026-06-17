# addons.py README

---

This file handles two features for "Whack-a-Ghost": the gesture-calibration loading bar shown before gameplay starts, and the decoy ghost (the one that penalizes the player for whacking it). It reads and writes shared values stored in `config.py` so the rest of the game can react to what's happening here.

```bash
import pygame
import random
import math
import config
```

### What each library does:

| Library | Function |
| :--- | :--- |
| `import pygame` | Used to draw the loading bar rectangles and render text onto the screen. |
| `import random` | Decides whether a decoy spawns on a given cycle, and picks which hole it appears in. |
| `import math` | Calculates the distance between the player's cursor and the decoy's position, to check if the player whacked it. |
| `import config` | Stores shared game state — things like hole positions, timers, and gesture progress — that this file reads from and writes to so other modules stay in sync. |

## Section 1: Gesture Loading Bar

```python
def process_gesture_loading_bar(screen, is_thumbs_up, ui_font):
```

This draws the progress bar shown while the player holds up a thumbs-up gesture to confirm something (likely to start the game). It does this in four steps:

1. Draws a dark grey background track for the bar.
2. Calculates how full the bar should be using `config.gesture_hold_progress / config.GESTURE_HOLD_TARGET`, then draws a green fill rectangle scaled to that percentage.
3. Draws a green border outline around the whole bar.
4. Renders text above the bar showing the percentage, e.g. "CALIBRATING GESTURE: 62%".


## Section 2: Decoy Spawning

```python
def rolls_decoy_spawn(ghost_hole):
```

This is called each time a new ghost spawns, to decide whether a decoy should also appear:

- There's a 45% chance a decoy spawns. If it does, it's placed in a random hole that isn't the same one the ghost just spawned in, its state is set to `"UP"`, and its `decoy_y_offset` is set to 180 (meaning it starts fully hidden below the hole, ready to animate upward).
- If the roll fails (55% of the time), the decoy is set to `"HIDDEN"` with no hole assigned, so it doesn't appear at all.

## Section 3: Decoy Animation and Collision

```python
def process_decoy_logic(cursor_pos):
```

This runs every frame to animate the decoy and check if the player hit it.

If the decoy is `"HIDDEN"` or has no hole assigned, the function does nothing and returns 0 (no score change).

If the decoy is in the `"UP"` state, its `decoy_y_offset` decreases by 45 each frame (popping it up out of the hole) until it reaches 0, fully visible.

If the decoy is in the `"DOWN"` state, its `decoy_y_offset` increases by 90 each frame (retreating back into the hole). Once the offset reaches 180 or more, the decoy is set back to `"HIDDEN"` and the function returns 0.

After updating the animation, the function calculates the decoy's current on-screen position and measures the distance from the cursor to that position using `math.hypot`. If that distance is less than 180 pixels, it counts as a hit: the decoy is switched to `"DOWN"` (triggering the fast retreat) and the function returns -1, which the gameplay logic elsewhere presumably uses as a score penalty.

## Section 4: Dynamic Difficulty

```python
def handle_dynamic_difficulty(gameplay_duration):
```

This gradually increases difficulty as the game goes on, by shortening how long a ghost stays visible before it's swapped out.

Each time `gameplay_duration` passes the next scheduled threshold (`config.next_speed_bump_time`), the ghost movement interval (`config.current_move_interval`) is reduced by 300ms, with a floor of 750ms so ghosts never move impossibly fast. The threshold for the next bump is then pushed forward by `config.speed_bump_interval`, and a message is printed to the console confirming the new speed.

## Function Summary

| Function | Purpose |
| :--- | :--- |
| `process_gesture_loading_bar()` | Draws the progress bar and percentage text for the gesture calibration screen. |
| `rolls_decoy_spawn()` | Rolls a 45% chance to spawn a decoy in a hole different from the ghost's, or hides it otherwise. |
| `process_decoy_logic()` | Animates the decoy popping up and retreating, and checks if the cursor hit it, returning a score penalty if so. |
| `handle_dynamic_difficulty()` | Reduces the ghost movement interval over time to make the game progressively faster. |
