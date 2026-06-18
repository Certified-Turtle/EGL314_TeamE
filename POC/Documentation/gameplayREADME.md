# gameplay.py README

---

## Section 1: Imports and Global Setup

```python
import math
import random
import pygame
import designs
```

This section loads the tools used:  
`math` is used for smooth animations  
`random` is used for random ghost and decoy behavior  
`pygame` handles rendering, surfaces, and game loop graphics  
`designs` is the custom module for drawing UI elements

---

## Section 2: Screen and Game Layout Configuration


`WIDTH` and `HEIGHT` defines the resolution of the game window
`hole_positions` generates a 3x3 grid of hole positions

```python
WIDTH, HEIGHT = 1920, 1080
hole_positions = [(480 + col * 480, 660 + row * 150) for row in range(3) for col in range(3)]
```

3 rows × 3 columns = 9 total holes  
Each hole has an (x, y) coordinate and is used as spawn locations for ghosts and decoys

So this becomes the whackable target grid

---

## Section 3: Collision Detection System

This function determines whether the player successfully “hits” a ghost

```python
def check_ghost_collisions(...)
```

### 3.1 Early Exit Conditions

```python
if ghost_state != "UP" or current_hole is None:
    return False, ...
```

The function immediately stops if:
The ghost is not fully visible `"UP"`, or there is no active hole which prevents invalid or unfair hits

### 3.2 Determining Ghost Position

```python
if isinstance(current_hole, (tuple, list)):
    hole_x, hole_y = current_hole[0], current_hole[1]
else:
    hole_x, hole_y = hole_positions[current_hole]
```

Coordinates index into the predefined grid `hole_positions`

ghost_current_x = hole_x  
ghost_current_y = hole_y - ghost_y_offset

Calculates the ghost’s actual on-screen position

### 3.3 Hitbox Adjustment

This shifts hit detection upward, which aligns hitbox with the ghost’s head, not the bottom

```python
target_center_y = ghost_current_y - 80
```

Define an oval hitbox for the ghost

```python
RADIUS_X = 110
RADIUS_Y = 140
```

### 3.4 Collision

Getting coordinates for the cursor

```python
dx = cursor_pos[0] - target_center_x
dy = cursor_pos[1] - target_center_y
```

This code measures distance between cursor and ghost center

```python
is_inside_hitbox = ((dx ** 2) / (RADIUS_X ** 2)) + ((dy ** 2) / (RADIUS_Y ** 2)) <= 1.0
```

If result ≤ 1 means that cursor is inside hit area  
If > 1 means miss

### 3.5 Strike Validation

This part is to confirm that the hit is valid

```python
if is_inside_hitbox:
    if active_entity_type == "DECOY":
        if not is_striking:
            return False, tutorial_count, score, ghost_state, active_entity_type, death_sequences
    else:
        if not is_striking:
            return False, tutorial_count, score, ghost_state, active_entity_type, death_sequences
```

### 3.6 Successful Hit Handling

This line logs a successful hit.

```python
print(f"[CLEAN STRIKE] {active_entity_type} whacked perfectly!")
```

### 3.7 Scoring Logic

In tutorial mode, increment tutorial progress

```python
if game_phase == 0:
    tutorial_count += 1
```

Get 1 point by hitting the ghost  
Lose 1 when devoy hit
```python
else:
    score = score + 1 if active_entity_type == "GHOST" else max(0, score - 1)
```

### 3.8 Death Effect

Adds effect where the ghost or decoy dies

```python
death_sequences.append({
    "pos": (ghost_current_x, ghost_current_y),
    "frame": 0,
    "type": active_entity_type
})
```

### 3.9 Return Updated Game State

This line returns updated game state after a successful hit

```python
return True, tutorial_count, score, ghost_state, active_entity_type, death_sequences
```

---

## Section 4: Ghost Movement

This function controls how the ghost come up and down, disappear and respawn
```python
  def update_ghost_movement(...)
```

### 4.1 Copying States

Creates copies so original values aren’t overwritten mid-calculation

```python
new_state = ghost_state
new_offset = ghost_y_offset
```

### 4.2 `DOWN` State

Ghost is going back into the hole.

```python
if ghost_state == "DOWN":
```

Decoys instantly goes down without animation

```python
if active_entity_type == "DECOY":
    new_offset = 180
```

Ghosts while go down gradually

```python
else:
    new_offset += 30
```

### 4.3 Transition to Hidden

```python
if new_offset >= 180:
```
When fully hidden:

Reset position of the ghost  
and choose a new hole while ensuring that ghosts do not reappear in same hole

```python
new_hole = random.choice([h for h in hole_positions if h != current_hole])
```

### 4.4 `HIDDEN` State

Ghost is not visible.

```python
elif ghost_state == "HIDDEN":
```

This spawns the decoy (70% or the ghost 30%)

```python
new_entity_type = "DECOY" if random.random() < 0.70 else "GHOST"
```

### 4.5 `UP` State (rising behavior)

Ghost is emerging.
```python
elif ghost_state == "UP":
```
Decoys will rise up faster (90) than ghosts (30)

```python
new_offset -= 90 if active_entity_type == "DECOY" else 30
```

### 4.6 Ghost Time Limit

If the ghost stays for too long, it will drop automatically

```python
if now - last_move_time > move_interval:
```
Sends an OSC signal when player misses a ghost late into the game

```python
if game_phase == 3 and osc_client is not None and new_entity_type == "GHOST":
    osc_client.send_message("/ghost/miss", 1)
```

## Section 5: Gameplay UI Rendering

This draws the Ui panels

```python
def render_gameplay_ui(...)
  designs.draw_spooky_panel(...)
````

## Section 6: Speed Warning Overlay

This shows a countdown warning before difficulty increases

```python
def render_speed_warning(...)
```

### 6.1 Countdown Calculation

Counts down from 5 to 1

```python
elapsed_warning_ms = now - speed_warning_start_ticks
warning_countdown = max(1, 5 - (elapsed_warning_ms // 1000))
```

### 6.2 Flashing Red Background

Uses sine wave to create pulsing effect from imported library `math`

```python
pulse_alpha = int(80 + math.sin(now * 0.01) * 40)
```

Makes dynamic warning bar with red translucent overlay

```python
warning_bar.fill((200, 30, 30, pulse_alpha))
```

### 6.3 Text Rendering

This creates a warning message and a countdown timer

```python
alert_text = ui_font.render(...)
timer_text = title_font.render(...)
```

### 6.4 Drawing to Screen

This plaves the warning bar at the top, and the text over it in the center

```python
screen.blit(...)
```
