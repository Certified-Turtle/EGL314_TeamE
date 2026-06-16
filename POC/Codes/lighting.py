# lighting.py
# Handles all GMA3 OSC lighting control for Haunted Manor: Ghost Hunt
#
# Fixture map:
#   Fixture 1 — ePar 180 8-bit         → Constant white spotlight on player
#   Fixture 2 — MiniPanelFX Extended   → Win pulse effect
#   Fixture 3 — Mistral-TC Extended    → Lightning flash + lose red wash
#   Fixture 4 — MagicBlade FX Extended → Win colour sweep
 
import pygame
from pythonosc import udp_client
 
# =================================================================
# === GMA3 CONNECTION ===
# =================================================================

 
GMA3_IP   = "192.168.254.252"  
GMA3_PORT = 8000
GMA3_ADDR = "/gma3/cmd" 
 
# =================================================================
# === FIXTURE ASSIGNMENT ===
# =================================================================
SPOTLIGHT_FIXTURE   = "Fixture 501"
SPOTLIGHT_DIMMER    = 100
 
FLASH_FIXTURE       = "Fixture 503"
FLASH_DIMMER        = 100
FLASH_DURATION_MS   = 250
 
WIN_PULSE_FIXTURE   = "Fixture 502"
WIN_SWEEP_FIXTURE   = "Fixture 504"
WIN_PULSE_DIMMER    = 100
WIN_SWEEP_DIMMER    = 100
WIN_PULSE_COUNT     = 4
WIN_PULSE_MS        = 300
 
LOSE_WASH_FIXTURE   = "Fixture 503"
LOSE_WASH_DIMMER    = 70
LOSE_SPOTLIGHT_DIM  = 20
 
PAN_MIN,  PAN_MAX  = -315, 315
TILT_MIN, TILT_MAX = -135, 135
RED_MIN,   RED_MAX   = 0, 255
GREEN_MIN, GREEN_MAX = 0, 255
BLUE_MIN,  BLUE_MAX  = 0, 255
 
# =================================================================
# === INTERNAL STATE ===
# =================================================================
_flash_active      = False
_flash_trigger_ms  = 0
_win_active        = False
_win_pulse_step    = 0
_win_pulse_on      = False
_win_last_pulse_ms = 0
_lose_active       = False
 
 
# =================================================================
# === LOW-LEVEL OSC HELPERS ===
# =================================================================
def _send(message: str):
    """Create a fresh OSC client and fire one command to GMA3."""
    try:
        client = udp_client.SimpleUDPClient(GMA3_IP, GMA3_PORT)
        client.send_message(GMA3_ADDR, message)
    except Exception as e:
        print(f"[LIGHTING] OSC send failed: {e}")
 
 
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
    """Call ONCE at game startup. Turns on spotlight, clears all other fixtures."""
    global _flash_active, _win_active, _lose_active
 
    _flash_active = False
    _win_active   = False
    _lose_active  = False
 
    _send(f"{FLASH_FIXTURE} At 0")
    _send(f"{WIN_PULSE_FIXTURE} At 0")
    _send(f"{WIN_SWEEP_FIXTURE} At 0")
 
    _fire_spotlight()
    print("[LIGHTING] Initialised — spotlight on, all effects cleared.")
 
 
def on_game_restart():
    """Call on K_r restart. Clears effects and restores spotlight."""
    global _flash_active, _win_active, _lose_active, _win_pulse_step
 
    _flash_active   = False
    _win_active     = False
    _lose_active    = False
    _win_pulse_step = 0
 
    _send(f"{FLASH_FIXTURE} At 0")
    _send(f"{WIN_PULSE_FIXTURE} At 0")
    _send(f"{WIN_SWEEP_FIXTURE} At 0")
    _send(f"{SPOTLIGHT_FIXTURE} At {SPOTLIGHT_DIMMER}")
 
    print("[LIGHTING] Restarted — all effects cleared, spotlight restored.")
 
 
def on_lightning_flash():
    """Call once when in-game lightning activates. Snaps Mistral-TC to white."""
    global _flash_active, _flash_trigger_ms
 
    if _flash_active:
        return
 
    _flash_active     = True
    _flash_trigger_ms = pygame.time.get_ticks()
 
    _set_colour(FLASH_FIXTURE, 255, 255, 255)
    _send(f"{FLASH_FIXTURE} At {FLASH_DIMMER}")
    print("[LIGHTING] ⚡ Lightning flash!")
 
 
def on_win():
    """Call on game over with good score. MiniPanelFX pulses white, MagicBlade goes gold."""
    global _win_active, _win_pulse_step, _win_pulse_on, _win_last_pulse_ms
 
    _win_active        = True
    _win_pulse_step    = 0
    _win_pulse_on      = True
    _win_last_pulse_ms = pygame.time.get_ticks()
 
    _set_colour(WIN_SWEEP_FIXTURE, 255, 160, 0)    # Gold
    _send(f"{WIN_SWEEP_FIXTURE} At {WIN_SWEEP_DIMMER}")
 
    _set_colour(WIN_PULSE_FIXTURE, 255, 255, 255)  # White
    _send(f"{WIN_PULSE_FIXTURE} At {WIN_PULSE_DIMMER}")
    print("[LIGHTING] 🏆 Win effect started!")
 
 
def on_lose():
    """Call on game over with bad score. Spotlight drops low, Mistral-TC goes red."""
    global _lose_active
 
    _lose_active = True
 
    _send(f"{SPOTLIGHT_FIXTURE} At {LOSE_SPOTLIGHT_DIM}")
    _set_colour(LOSE_WASH_FIXTURE, 220, 0, 0)      # Deep red
    _send(f"{LOSE_WASH_FIXTURE} At {LOSE_WASH_DIMMER}")
    print("[LIGHTING] 💀 Lose effect — spotlight dim, red wash on.")
 
 
def update():
    """Call EVERY FRAME. Handles flash timeout and win pulse animation."""
    global _flash_active, _win_active, _win_pulse_step, _win_pulse_on, _win_last_pulse_ms
 
    now = pygame.time.get_ticks()
 
    # Flash timeout
    if _flash_active:
        if now - _flash_trigger_ms > FLASH_DURATION_MS:
            _send(f"{FLASH_FIXTURE} At 0")
            _flash_active = False
 
    # Win pulse
    if _win_active:
        if now - _win_last_pulse_ms >= WIN_PULSE_MS:
            _win_pulse_on = not _win_pulse_on
            if _win_pulse_on:
                _send(f"{WIN_PULSE_FIXTURE} At {WIN_PULSE_DIMMER}")
            else:
                _send(f"{WIN_PULSE_FIXTURE} At 0")
 
            _win_pulse_step    += 1
            _win_last_pulse_ms  = now
 
            if _win_pulse_step >= WIN_PULSE_COUNT * 2:
                _win_active = False
                _send(f"{WIN_PULSE_FIXTURE} At 0")
                print("[LIGHTING] Win pulse complete — MagicBlade holding gold.")
 
 
# =================================================================
# === PRIVATE HELPERS ===
# =================================================================
def _fire_spotlight():
    _set_colour(SPOTLIGHT_FIXTURE, 255, 255, 255)
    _send(f"{SPOTLIGHT_FIXTURE} At {SPOTLIGHT_DIMMER}")
    print(f"[LIGHTING] Spotlight ON — {SPOTLIGHT_FIXTURE} at {SPOTLIGHT_DIMMER}%")
    
# Test lights
# def _send(message: str):
#     try:
#         client = udp_client.SimpleUDPClient(GMA3_IP, GMA3_PORT)
#         client.send_message(GMA3_ADDR, message)
#         print(f"[LIGHTING SENT] → {message}")  # ← add back temporarily
#     except Exception as e:
#         print(f"[LIGHTING] OSC send failed: {e}")
