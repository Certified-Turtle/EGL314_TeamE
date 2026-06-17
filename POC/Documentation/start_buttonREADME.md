# start_button.py README

---

This file draws and runs the intro screen for "Haunted Manor: Ghost Hunt" — the title screen the player sees before anything else, where they hover the crosshair over a button to begin.

```python
import pygame
import designs
```

### What each library does:

| Library | Function |
| :--- | :--- |
| `import pygame` | Used to draw the title screen, the button, and detect whether the cursor is hovering over it. |
| `import designs` | Used to draw the crosshair on screen at the player's current cursor position. |

## Section 1: Constants

```python
WIDTH, HEIGHT = 1920, 1080
START_BUTTON_RECT = pygame.Rect(WIDTH//2 - 250, HEIGHT//2 + 80, 500, 160)
HOVER_TO_START_FRAMES = 35
```

`WIDTH` and `HEIGHT` define the screen size this layout is built for. `START_BUTTON_RECT` is the button's position and size — a 500x160 box centered horizontally and placed slightly below the vertical middle of the screen. `HOVER_TO_START_FRAMES` sets how many frames the player needs to keep hovering over the button before it triggers — at 35 frames, that's roughly half a second at 60 FPS.

## Section 2: `handle_intro_phase()`

```python
def handle_intro_phase(screen, title_font, ui_font, cursor_pos, hover_progress):
```

This function runs every frame while the game is on the intro screen, and is responsible for drawing the whole screen and tracking how close the player is to starting the game.

It takes in the current cursor position and the current `hover_progress` value (carried over from the previous frame), and returns the updated `hover_progress` so the caller can pass it back in next frame.

Step by step, it:

1. Fills the screen with a dark background colour.
2. Draws the title text ("WHACK-A-GHOST SYSTEM") and an instruction line telling the player to move the crosshair over the button.
3. Checks if the cursor is currently inside `START_BUTTON_RECT`. If it is, `hover_progress` increases by 1. If not, it decreases by 2 (down to a minimum of 0) — so moving away drains progress faster than hovering builds it.
4. Calculates how much of the button should be filled in, based on `hover_progress` as a fraction of `HOVER_TO_START_FRAMES`, and draws the button: a background box, the proportional green fill, and a green border on top.
5. Swaps the button's label text between "START WHACKING!" and "INITIATING..." once `hover_progress` reaches the threshold, as a signal to the player that the hold has registered.
6. Draws the crosshair at the cursor's position by calling `designs.draw_crosshair()`.

Note that this function only draws the screen and tracks hover progress — it doesn't itself decide when to transition to the next game phase. That decision (checking if the returned `hover_progress` has reached `HOVER_TO_START_FRAMES`) must happen wherever this function is called from, likely in `main.py`.

## Function Summary

| Function | Purpose |
| :--- | :--- |
| `handle_intro_phase()` | Draws the title screen and start button, tracks how long the cursor has hovered over the button, and returns the updated hover progress. |
