# restart_quit.py README

This is the code responsible for creating the restart and quit button that appears at the end of the game.

The code starts by importing the following:

```bash
import pygame
import random
```

This imports the pygame library which creates the game, handles the graphics and fonts etc. While random imports Python's built-in random module, which allows random selections.

```bash
WIDTH, HEIGHT = 1920, 1080
hole_positions = [(480 + col * 480, 660 + row * 150) for row in range(3) for col in range(3)]
```

This creates the varibles WIDTH and HEIGHT respresenting the screen. 
hole_positions are the holes that appear in gameplay.

(These are not the main functions of this file.)

# Main functions

```bash
def reset_game():
    # Returns score, time_left, start_ticks, current_hole, game_over
    return 0, 30, pygame.time.get_ticks(), random.choice(hole_positions), False
```

This function returns all game varibles to their starting values, whenever the player restarts a game via the start button.

"0" Sets player score to 0, 

"30" resets timer back to 30 seconds, 

"pygame.time.get_ticks()" records time in miliseconds since pygame started and is used as a reference starting point for the countdown timer,

"random.choice(hole_positions)" determines the spawn point of the first ghost on restart and 

"False" sets the game over flag to false, indicating the game is currently not game over.


As for the next block:

```bash
def render_game_over_screen(screen, score):
    WIDTH, HEIGHT = screen.get_size()
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA).convert_alpha()
    dim.fill((5, 5, 12, 240)); screen.blit(dim, (0, 0))
    
    f1, f2 = pygame.font.SysFont("Courier New", 150, bold=True), pygame.font.SysFont("Courier New", 60, bold=True)
    title_str = "CLEARED!" if score >= 15 else "GAME!"
    title_surf = f1.render(title_str, True, (200, 255, 220) if score >= 15 else (220, 40, 60))
    score_surf = f2.render(f"SPIRITS BANISHED: {score} (Target: 15)", True, (255, 215, 0))
    menu_surf  = f2.render("PRESS [R] TO RE-ENTER OR [Q] TO LEAVE", True, (160, 165, 180))
    
    screen.blit(title_surf, title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 150)))
    screen.blit(score_surf, score_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30)))
    screen.blit(menu_surf, menu_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 180)))
```
This defines defines the game over screen when the game ends.

Breaking it down:

```bash
WIDTH, HEIGHT = screen.get_size()
```

Gets the screen dimensions.

```bash
dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA).convert_alpha()
dim.fill((5, 5, 12, 240)); screen.blit(dim, (0, 0))
```

Creates a semi-transparent dark layer that covers the game screen. This dims the background and helps the game over text stand out, creating a clearer visual transition between gameplay and the game over screen.

```bash
f1, f2 = pygame.font.SysFont("Courier New", 150, bold=True), pygame.font.SysFont("Courier New", 60, bold=True)
```

Creates 2 fonts, 1 for the big game over text and one for the smaller instructions below.

```bash
title_str = "CLEARED!" if score >= 15 else "GAME!"
```

Determines what displays at the end. If the win condition of 15 points is met, the messsage "CLEARED!" is displayed, if not, "GAME!" is displayed.

```bash
title_surf = f1.render(title_str, True, (200, 255, 220) if score >= 15 else (220, 40, 60))
score_surf = f2.render(f"SPIRITS BANISHED: {score} (Target: 15)", True, (255, 215, 0))
menu_surf  = f2.render("PRESS [R] TO RE-ENTER OR [Q] TO LEAVE", True, (160, 165, 180))
```

Creates 3 text surface layers

1 for the title message, score message and menu instructions respectively.

Finally 

```bash
screen.blit(title_surf, title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 150)))
screen.blit(score_surf, score_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30)))
screen.blit(menu_surf, menu_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 180)))
```

This function places all text elements in the center of the screen, with the game over title near the top of the game over screen, the score below the title and the instructions below the score.
