# tutorial.py README

---

This code generates the tutorial phase for the main game

## Section 1: Imports and Screen Setup

Imports pygame for rendering graphics and text and sets game resolution
Sets the game resolution:

```python
import pygame

WIDTH, HEIGHT = 1920, 1080
```

---

## Section 2: Tutorial Rendering

This function controls what the player sees during tutorial and pre-game phases

```python
def handle_tutorial_rendering(screen, ui_font, title_font, countdown_font, phase, tutorial_count, now, ready_timer):
```

---

## Section 3: Tutorial Gameplay

Basic training scene

```python
if phase == -0:  # PHASE_TUTORIAL
```

### 3.1 Instruction Text

This code displays the instructions "USE YOUR GREEN OBJECT..."

```python
t1 = ui_font.render(...)
```

### 3.2 Progress Counter

Shows tutorial progress on how many traning ghosts have been hit, the goal being 5

```python
t2 = ui_font.render(...)
```

### 3.3 Centering on Screen

Centers text horizontally near the top of the screen

```python
screen.blit(i1, (WIDTH // 2 - t1.get_width() // 2, 60))
```

The same applies to `i1`, `i2`, `i3`, `i4` and `i5`


## Section 4: Transition Screen

This is a transition screen after tutorial completion

```python
elif phase == 1:  # PHASE_INSTRUCT
```

### 4.1 Dark Overlay Background

Creates a dark transulcent layer, making the gameplay less visible so easier to see the instructions

```python
dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA).convert_alpha()
dim.fill((10, 8, 20, 130))
screen.blit(dim, (0, 0))
```

### 4.2 Instruction Text Blocks

Each line explains game rules
These explains:  
Time limit  
Win condition  
Penalty  
Difficulty scaling

```python
i1 = title_font.render("TUTORIAL COMPLETE...", True, (255, 215, 0))
i2 = ui_font.render("You have 30 seconds...", ...)
i3 = ui_font.render("Level Clear Target...", ...)
i4 = ui_font.render("WARNING: Avoid decoys...", ...)
i5 = ui_font.render("HINT: Pace yourself...", ...)
```

### 4.3 Continue Prompt

Waits for user gesture input (using OpenCV, MediaPipe)

```
i6 = title_font.render("SHOW AN OK SIGN TO CONTINUE", ...)
```

### 4.4 Centered Layout System

Centers all text

```python
screen.blit(i2, (WIDTH // 2 - i2.get_width() // 2, 350))
```

## Section 5: Countdown

This is the final countdown before gameplay starts

```python
elif phase == 2:  # PHASE_PREPARE
```

### 5.1 Second Dark Overlay

```python
dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA).convert_alpha()
dim.fill((15, 10, 25, 130))
screen.blit(dim, (0, 0))
```

### 5.2 Countdown Calculation

This code creates a 5 second countdown

```python
seconds_remaining = max(1, 5 - (now - ready_timer) // 1000)
```

### 5.3 “Get Ready” Text

Big warning message that signals gameplay start

```python
p_text = title_font.render("GET READY!", True, (255, 69, 0))
```

### 5.4 Countdown Number

This code generates a big countdown timer

```python
c_text = countdown_font.render(str(seconds_remaining), True, (255, 255, 255))
```

### 5.5 Centered Placement

Centers all the elements

```python
screen.blit(p_text, (WIDTH // 2 - p_text.get_width() // 2, HEIGHT // 2 - 210))
screen.blit(c_text, (WIDTH // 2 - c_text.get_width() // 2, HEIGHT // 2 - 30))
```
