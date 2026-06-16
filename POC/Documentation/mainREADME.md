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


