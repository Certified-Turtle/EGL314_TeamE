import pygame
import numpy as np

# --- WINDOW CONFIGURATION ---
WIDTH, HEIGHT = 1920, 1080

# --- COMPUTER VISION BOUNDS ---
GREEN_LOWER = np.array([35, 100, 100])
GREEN_UPPER = np.array([85, 255, 255])

BLUE_LOWER = np.array([100, 140, 100])
BLUE_UPPER = np.array([120, 255, 255])

# --- SYSTEM GAME STATES ---
PHASE_INTRO = -2
PHASE_MODE_SELECT = -1   # Single/Multiplayer selection screen
PHASE_TUTORIAL = 0
PHASE_INSTRUCT = 1
PHASE_PREPARE = 2
PHASE_GAMEPLAY = 3
PHASE_GAMEOVER = 4
PHASE_TUTORIAL_MP = 5    # Multiplayer combined training session
PHASE_STAGE_CLEAR = 6    # Between-stage screen with score + hover to continue

# --- TRACKERS AND TARGET COORDINATES ---
HOVER_TO_START_FRAMES = 35
hole_positions = [(480 + col * 480, 660 + row * 150) for row in range(3) for col in range(3)]
START_BUTTON_RECT = pygame.Rect(WIDTH//2 - 250, HEIGHT//2 + 80, 500, 160)

# ==========================================================
# ─── ADD-ON FEATURE GLOBAL TRACKERS ───────────────────────
# ==========================================================

# Feature 1: Tutorial Gesture Loading Bar Metrics
gesture_hold_progress = 0
GESTURE_HOLD_TARGET = 60  # Updated: Exactly 3.0 seconds sustained at 60 FPS

# Feature 2: Dynamic Speed Ramping Configs
current_move_interval = 2200  # Default 2.2 seconds
next_speed_bump_time = 15000   # First shift at 15s (15000ms)
speed_bump_interval = 7000     # Follow-up steps every 7s (7000ms)
speed_multiplier = 1.0         # Current acceleration multiplier step
last_speed_bump_time = 0       # Milestone checker for speed updates
