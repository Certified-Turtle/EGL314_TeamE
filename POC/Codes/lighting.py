# lighting.py
# Handles all GMA3 OSC lighting control for Haunted Manor: Ghost Hunt
#
# GMA3 Sequence: "TeamE"
#   Cue 1 — gameseq    → Main 30sec round lighting (runs continuously, never stopped)
#   Cue 2 — 10sec      → Last 10 second countdown flash
#   Cue 3 — PASS       → Win effect
#   Cue 4 — FAIL       → Lose effect
#
# Lightning — handled directly via fixtures 203, 303, 403, 503
#   Python controls ON/OFF timing, no cue needed

import pygame
from pythonosc import udp_client

# =================================================================
# === GMA3 CONNECTION — EDIT THESE ===
# =================================================================
GMA3_IP   = "192.168.254.252"
GMA3_PORT = 8000
GMA3_ADDR = "/gma3/cmd"

# =================================================================
# === SEQUENCE CONFIG ===
# =================================================================
SEQ_NAME      = "TeamE"
CUE_GAMESEQ   = 1
CUE_COUNTDOWN = 2
CUE_PASS      = 3
CUE_FAIL      = 4

# =================================================================
# === LIGHTNING FIXTURE CONFIG ===
# =================================================================
FLASH_FIXTURES    = ["Fixture 203", "Fixture 303", "Fixture 403", "Fixture 503"]
FLASH_DIMMER      = 100
FLASH_DURATION_MS = 200     # How long the flash stays on in milliseconds

# Zoom and focus ranges
ZOOM_MIN,  ZOOM_MAX  = 0, 100
FOCUS_MIN, FOCUS_MAX = 0, 100

# Colour ranges
RED_MIN,   RED_MAX   = 0, 255
GREEN_MIN, GREEN_MAX = 0, 255
BLUE_MIN,  BLUE_MAX  = 0, 255

# =================================================================
# === INTERNAL STATE ===
# =================================================================
_lightning_enabled   = False        # Only active during tutorial + gameplay
_countdown_triggered = False        # Ensures 10sec cue only fires once
_flash_active        = False        # Tracks if lightning is currently on
_flash_trigger_ms    = 0            # When the flash started
_current_cue         = CUE_GAMESEQ  # Tracks which sequence cue is playing


# =================================================================
# === LOW-LEVEL OSC HELPERS ===
# =================================================================
def _send(message: str):
    """Create a fresh OSC client and fire one command to GMA3."""
    try:
        client = udp_client.SimpleUDPClient(GMA3_IP, GMA3_PORT)
        client.send_message(GMA3_ADDR, message)
        print(f"[LIGHTING SENT] → {message}")
    except Exception as e:
        print(f"[LIGHTING] OSC send failed: {e}")


def _go(cue: int):
    """Fire a specific cue in the TeamE sequence."""
    _send(f'Go Sequence "{SEQ_NAME}" Cue {cue}')


def _gma3_value(value: float, v_min: float, v_max: float) -> int:
    value = max(min(value, v_max), v_min)
    return int(round((value - v_min) * 65535 / (v_max - v_min)))


def _set_attribute(fixture: str, attribute: str, value: float, v_min: float, v_max: float):
    gma_val = _gma3_value(value, v_min, v_max)
    _send(fixture)
    _send(f"Attribute '{attribute}' At Absolute Decimal16 {gma_val}")


def _set_colour(fixture: str, r: int, g: int, b: int):
    _set_attribute(fixture, "ColorRGB_R", r, RED_MIN,   RED_MAX)
    _set_attribute(fixture, "ColorRGB_G", g, GREEN_MIN, GREEN_MAX)
    _set_attribute(fixture, "ColorRGB_B", b, BLUE_MIN,  BLUE_MAX)


# =================================================================
# === PUBLIC API ===
# =================================================================
def init():
    """
    Call ONCE at game startup after camera initialises.
    Starts gameseq immediately and turns off all lightning fixtures.
    """
    global _lightning_enabled, _countdown_triggered, _flash_active, _current_cue

    _lightning_enabled   = False
    _countdown_triggered = False
    _flash_active        = False
    _current_cue         = CUE_GAMESEQ

    # Start gameseq immediately — runs continuously from here
    _go(CUE_GAMESEQ)

    # Make sure all lightning fixtures are off
    for fix in FLASH_FIXTURES:
        _send(f"{fix} At 0")

    print("[LIGHTING] Initialised — gameseq running, waiting for tutorial.")


def on_tutorial_start():
    """
    Call when start button is pressed and tutorial begins.
    Enables lightning — gameseq is already running.
    """
    global _lightning_enabled, _countdown_triggered, _current_cue

    _lightning_enabled   = True
    _countdown_triggered = False
    _current_cue         = CUE_GAMESEQ

    print(f"[LIGHTING] Tutorial started — lightning enabled, gameseq continues.")


def on_thumbsup_check():
    """
    Call when PHASE_INSTRUCT starts (checking thumbs up gesture).
    Disables lightning only — gameseq keeps running.
    """
    global _lightning_enabled, _flash_active

    _lightning_enabled = False
    _flash_active      = False

    # Cut lightning fixtures but leave sequence running
    for fix in FLASH_FIXTURES:
        _send(f"{fix} At 0")

    print("[LIGHTING] Thumbs up check — lightning off, gameseq continues.")


def on_thumbsup_accepted():
    """
    Call when thumbs up is registered and game is about to start.
    Re-enables lightning — gameseq is already running.
    """
    global _lightning_enabled, _countdown_triggered, _current_cue

    _lightning_enabled   = True
    _countdown_triggered = False
    _current_cue         = CUE_GAMESEQ

    print(f"[LIGHTING] Thumbs up accepted — lightning re-enabled, gameseq continues.")


def on_lightning_flash():
    """
    Call once when in-game lightning activates.
    Snaps all 4 fixtures to full white at max zoom and focus.
    update() cuts them off after FLASH_DURATION_MS.
    Only works if lightning is enabled.
    """
    global _flash_active, _flash_trigger_ms

    if not _lightning_enabled:
        return
    if _flash_active:               # Don't stack flashes
        return

    _flash_active     = True
    _flash_trigger_ms = pygame.time.get_ticks()

    for fix in FLASH_FIXTURES:
        _set_colour(fix, 255, 255, 255)                              # Pure white
        _send(f"{fix} At {FLASH_DIMMER}")                            # Full brightness
        _set_attribute(fix, "Zoom",  100, ZOOM_MIN,  ZOOM_MAX)      # Max zoom
        _set_attribute(fix, "Focus", 100, FOCUS_MIN, FOCUS_MAX)     # Max focus

    print(f"[LIGHTING] ⚡ Lightning ON — {len(FLASH_FIXTURES)} fixtures!")


def on_countdown():
    """
    Call when 10 seconds remain.
    Fires Cue 2 (10sec) once only.
    """
    global _countdown_triggered, _current_cue

    if _countdown_triggered:
        return

    _countdown_triggered = True
    _current_cue         = CUE_COUNTDOWN

    _go(CUE_COUNTDOWN)
    print(f"[LIGHTING] ⏱ Cue {CUE_COUNTDOWN} (10sec countdown) fired!")


def on_win():
    """
    Call on game over with good score.
    Cuts lightning and fires Cue 3 (PASS).
    """
    global _lightning_enabled, _flash_active, _current_cue

    _lightning_enabled = False
    _flash_active      = False
    _current_cue       = CUE_PASS

    for fix in FLASH_FIXTURES:
        _send(f"{fix} At 0")

    _go(CUE_PASS)
    print(f"[LIGHTING] 🏆 Cue {CUE_PASS} (PASS) fired!")


def on_lose():
    """
    Call on game over with bad score.
    Cuts lightning and fires Cue 4 (FAIL).
    """
    global _lightning_enabled, _flash_active, _current_cue

    _lightning_enabled = False
    _flash_active      = False
    _current_cue       = CUE_FAIL

    for fix in FLASH_FIXTURES:
        _send(f"{fix} At 0")

    _go(CUE_FAIL)
    print(f"[LIGHTING] 💀 Cue {CUE_FAIL} (FAIL) fired!")


def on_game_restart():
    """
    Call on K_r restart.
    Resets lightning state — gameseq keeps running.
    """
    global _lightning_enabled, _countdown_triggered, _flash_active, _current_cue

    _lightning_enabled   = False
    _countdown_triggered = False
    _flash_active        = False
    _current_cue         = CUE_GAMESEQ

    # Cut lightning fixtures, restart gameseq
    for fix in FLASH_FIXTURES:
        _send(f"{fix} At 0")

    _go(CUE_GAMESEQ)
    print("[LIGHTING] Restarted — back to gameseq, waiting for tutorial.")


def update():
    """
    Call EVERY FRAME in the main game loop.
    Cuts all lightning fixtures off after FLASH_DURATION_MS.
    """
    global _flash_active

    now = pygame.time.get_ticks()

    if _flash_active:
        if now - _flash_trigger_ms > FLASH_DURATION_MS:
            for fix in FLASH_FIXTURES:
                _send(f"{fix} At 0")
            _flash_active = False
            print("[LIGHTING] ⚡ Lightning OFF")


# # =================================================================
# # === TEST BLOCK — DELETE AFTER TESTING ===
# # =================================================================
# if __name__ == "__main__":
#     import time
#     import random
#     pygame.init()

#     print("=== TIMING + LIGHTNING TEST ===")
#     print(f"Sending to {GMA3_IP}:{GMA3_PORT}")
#     print()

#     print("Starting — gameseq running continuously...")
#     init()
#     on_tutorial_start()

#     start = time.time()
#     while time.time() - start < 20:
#         remaining = 30 - (time.time() - start)
#         print(f"Time left: {remaining:.0f} seconds")

#         if random.random() < 0.4:
#             on_lightning_flash()
#             time.sleep(FLASH_DURATION_MS / 1000)
#             for fix in FLASH_FIXTURES:
#                 _send(f"{fix} At 0")
#             _flash_active = False
#             print("[LIGHTING] ⚡ Lightning OFF")

#         time.sleep(0.8)

#     print()
#     print("10 seconds left — firing countdown cue...")
#     on_countdown()

#     start = time.time()
#     while time.time() - start < 10:
#         remaining = 10 - (time.time() - start)
#         print(f"Time left: {remaining:.0f} seconds")

#         if random.random() < 0.6:
#             on_lightning_flash()
#             time.sleep(FLASH_DURATION_MS / 1000)
#             for fix in FLASH_FIXTURES:
#                 _send(f"{fix} At 0")
#             _flash_active = False
#             print("[LIGHTING] ⚡ Lightning OFF")

#         time.sleep(0.8)

#     print()
#     print("Time up! Firing PASS...")
#     on_win()
#     time.sleep(3)

#     print()
#     print("=== TEST COMPLETE — delete the test block when done ===")