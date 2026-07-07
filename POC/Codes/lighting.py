# lighting.py
# Handles all GMA3 OSC lighting control for Haunted Manor: Ghost Hunt
# FULLY HARDCODED — no GMA3 sequences needed at all
#
# All fixtures controlled directly from Python:
#   ePar 180:    101, 201, 301, 401, 501, 601, 702, 801
#   MiniPanel:   102, 202, 302, 402, 502, 602, 701, 802
#   Mistral:     103, 203, 303, 403, 503, 603, 703, 803
#   MagicBlade:  104, 204, 304, 404, 504, 604, 704, 804

import pygame
import time
from pythonosc import udp_client

# =================================================================
# === GMA3 CONNECTION — EDIT THESE ===
# =================================================================
GMA3_IP   = "192.168.254.252"
GMA3_PORT = 8080
GMA3_ADDR = "/gma3/cmd"

# =================================================================
# === FIXTURE GROUPS ===
# =================================================================
ALL_EPAR = [
    "Fixture 101", "Fixture 201", "Fixture 301", "Fixture 401",
    "Fixture 501", "Fixture 601", "Fixture 702", "Fixture 801"
]

ALL_MINIPANEL = [
    "Fixture 102", "Fixture 202", "Fixture 302", "Fixture 402",
    "Fixture 502", "Fixture 602", "Fixture 701", "Fixture 802"
]

ALL_MISTRAL = [
    "Fixture 103", "Fixture 203", "Fixture 303", "Fixture 403",
    "Fixture 503", "Fixture 603", "Fixture 703", "Fixture 803"
]

ALL_MAGICBLADE = [
    "Fixture 104", "Fixture 204", "Fixture 304", "Fixture 404",
    "Fixture 504", "Fixture 604", "Fixture 704", "Fixture 804"
]

ALL_FIXTURES = ALL_EPAR + ALL_MINIPANEL + ALL_MISTRAL + ALL_MAGICBLADE

# Lightning uses all Mistrals for maximum room flash
FLASH_FIXTURES    = ALL_MISTRAL
FLASH_DIMMER      = 100
FLASH_DURATION_MS = 200

# Decoy hit flash duration
DECOY_FLASH_DURATION_MS = 400

# Win pulse settings
WIN_PULSE_COUNT = 6
WIN_PULSE_MS    = 250

# Pan/Tilt ranges
PAN_MIN,  PAN_MAX  = -315, 315
TILT_MIN, TILT_MAX = -135, 135

# Zoom/Focus ranges
ZOOM_MIN,  ZOOM_MAX  = 0, 100
FOCUS_MIN, FOCUS_MAX = 0, 100

# Colour ranges
RED_MIN,   RED_MAX   = 0, 255
GREEN_MIN, GREEN_MAX = 0, 255
BLUE_MIN,  BLUE_MAX  = 0, 255

# =================================================================
# === INTERNAL STATE ===
# =================================================================
_lightning_enabled      = False
_countdown_triggered    = False
_flash_active           = False
_flash_trigger_ms       = 0
_decoy_flash_active     = False
_decoy_flash_trigger_ms = 0
_win_pulse_active       = False
_win_pulse_step         = 0
_win_pulse_last_ms      = 0
_win_pulse_on           = False
_lose_pulse_active      = False
_lose_pulse_step        = 0
_lose_pulse_last_ms     = 0
_lose_pulse_on          = False
_in_countdown           = False


# =================================================================
# === LOW-LEVEL OSC HELPERS ===
# =================================================================
def _send(message: str):
    try:
        client = udp_client.SimpleUDPClient(GMA3_IP, GMA3_PORT)
        client.send_message(GMA3_ADDR, message)
        print(f"[LIGHTING SENT] → {message}")
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


def _set_dimmer(fixture: str, percent: int):
    _send(f"{fixture} At {percent}")


def _set_group_colour(fixtures: list, r: int, g: int, b: int, dimmer: int):
    for fix in fixtures:
        _set_colour(fix, r, g, b)
        _set_dimmer(fix, dimmer)


def _set_mistral_pan_tilt(fixture: str, pan: float, tilt: float):
    _set_attribute(fixture, "pan",  pan,  PAN_MIN,  PAN_MAX)
    _set_attribute(fixture, "tilt", tilt, TILT_MIN, TILT_MAX)


def _set_all_mistrals_position(pan: float, tilt: float):
    for fix in ALL_MISTRAL:
        _set_mistral_pan_tilt(fix, pan, tilt)


# =================================================================
# === ATMOSPHERE SETUPS ===
# =================================================================
def _setup_spooky():
    """
    Full room spooky atmosphere — all 32 fixtures active.

    ePar:       alternating deep purple and dark teal
    MiniPanel:  dim green moonlight wash
    Mistral:    left side cold blue, right side deep purple, spread wide
    MagicBlade: alternating amber and purple, low glow
    """
    # ePar — alternate purple/teal
    purple_epars = ["Fixture 101", "Fixture 301", "Fixture 501", "Fixture 801"]
    teal_epars   = ["Fixture 201", "Fixture 401", "Fixture 601", "Fixture 702"]
    for fix in purple_epars:
        _set_colour(fix, 80, 0, 120);  _set_dimmer(fix, 60)
    for fix in teal_epars:
        _set_colour(fix, 0, 80, 100);  _set_dimmer(fix, 55)

    # MiniPanel — dim green moonlight
    _set_group_colour(ALL_MINIPANEL, 0, 80, 40, 50)

    # Mistral — left side blue, right side purple, spread wide
    left_mistrals  = ["Fixture 103", "Fixture 303", "Fixture 503", "Fixture 703"]
    right_mistrals = ["Fixture 203", "Fixture 403", "Fixture 603", "Fixture 803"]
    for fix in left_mistrals:
        _set_colour(fix, 0, 60, 180);  _set_dimmer(fix, 70)
        _set_mistral_pan_tilt(fix, -45, 30)
    for fix in right_mistrals:
        _set_colour(fix, 60, 0, 160);  _set_dimmer(fix, 70)
        _set_mistral_pan_tilt(fix, 45, 30)

    # MagicBlade — alternating amber/purple low glow
    amber_blades  = ["Fixture 104", "Fixture 304", "Fixture 504", "Fixture 704"]
    purple_blades = ["Fixture 204", "Fixture 404", "Fixture 604", "Fixture 804"]
    for fix in amber_blades:
        _set_colour(fix, 120, 50, 0);  _set_dimmer(fix, 40)
    for fix in purple_blades:
        _set_colour(fix, 80, 0, 100);  _set_dimmer(fix, 40)

    print("[LIGHTING] Spooky atmosphere set across all 32 fixtures.")


def _setup_countdown():
    """
    Tense red atmosphere — all fixtures shift to red, Mistrals face players.
    """
    _set_group_colour(ALL_EPAR,       200, 0, 0, 80)
    _set_group_colour(ALL_MINIPANEL,  180, 0, 0, 70)
    _set_group_colour(ALL_MISTRAL,    220, 0, 0, 100)
    _set_group_colour(ALL_MAGICBLADE, 220, 0, 0, 90)
    _set_all_mistrals_position(0, 0)    # All face straight at players
    print("[LIGHTING] Countdown atmosphere — all red, Mistrals facing players.")


def _setup_thumbsup():
    """
    Calm white/blue for gesture reading — all fixtures soft and bright.
    """
    _set_group_colour(ALL_EPAR,       200, 200, 255, 70)
    _set_group_colour(ALL_MINIPANEL,  180, 180, 255, 60)
    _set_group_colour(ALL_MISTRAL,    255, 255, 255, 50)
    _set_group_colour(ALL_MAGICBLADE, 150, 150, 200, 50)
    _set_all_mistrals_position(0, 20)   # Gently face players
    print("[LIGHTING] Thumbs up atmosphere — all calm white/blue.")


# =================================================================
# === PUBLIC API ===
# =================================================================
def init():
    """
    Call ONCE at game startup after camera initialises.
    Sets spooky atmosphere across all 32 fixtures.
    """
    global _lightning_enabled, _countdown_triggered, _flash_active
    global _decoy_flash_active, _win_pulse_active, _lose_pulse_active
    global _in_countdown

    _lightning_enabled   = False
    _countdown_triggered = False
    _flash_active        = False
    _decoy_flash_active  = False
    _win_pulse_active    = False
    _lose_pulse_active   = False
    _in_countdown        = False

    _setup_spooky()
    print("[LIGHTING] Initialised.")


def on_tutorial_start():
    """Call when start button pressed. Enables lightning."""
    global _lightning_enabled, _countdown_triggered, _in_countdown

    _lightning_enabled   = True
    _countdown_triggered = False
    _in_countdown        = False

    print("[LIGHTING] Tutorial started — lightning enabled.")


def on_thumbsup_check():
    """Call when PHASE_INSTRUCT starts. Calm white/blue, lightning off."""
    global _lightning_enabled, _flash_active

    _lightning_enabled = False
    _flash_active      = False

    _setup_thumbsup()

    # Cut all Mistrals used for lightning
    for fix in FLASH_FIXTURES:
        _set_dimmer(fix, 0)

    print("[LIGHTING] Thumbs up check — calm atmosphere.")


def on_thumbsup_accepted():
    """Call when thumbs up registered. Restore spooky, re-enable lightning."""
    global _lightning_enabled, _countdown_triggered, _in_countdown

    _lightning_enabled   = True
    _countdown_triggered = False
    _in_countdown        = False

    _setup_spooky()
    print("[LIGHTING] Thumbs up accepted — spooky restored, lightning on.")


def on_lightning_flash():
    """
    Call when in-game lightning activates.
    ALL Mistrals snap to full white — maximum room flash.
    update() cuts them after FLASH_DURATION_MS.
    """
    global _flash_active, _flash_trigger_ms

    if not _lightning_enabled:
        return
    if _flash_active:
        return

    _flash_active     = True
    _flash_trigger_ms = pygame.time.get_ticks()

    for fix in FLASH_FIXTURES:
        _set_colour(fix, 255, 255, 255)
        _set_dimmer(fix, FLASH_DIMMER)
        _set_attribute(fix, "Zoom",  100, ZOOM_MIN,  ZOOM_MAX)
        _set_attribute(fix, "Focus", 100, FOCUS_MIN, FOCUS_MAX)

    print(f"[LIGHTING] ⚡ Lightning ON — all {len(FLASH_FIXTURES)} Mistrals!")


def on_decoy_hit():
    """
    Call when player hits a decoy.
    FULL ROOM slams red. All Mistrals face players.
    update() restores atmosphere after DECOY_FLASH_DURATION_MS.
    """
    global _decoy_flash_active, _decoy_flash_trigger_ms

    if _decoy_flash_active:
        return

    _decoy_flash_active     = True
    _decoy_flash_trigger_ms = pygame.time.get_ticks()

    _set_group_colour(ALL_EPAR,       255, 0, 0, 100)
    _set_group_colour(ALL_MINIPANEL,  255, 0, 0, 100)
    _set_group_colour(ALL_MISTRAL,    255, 0, 0, 100)
    _set_group_colour(ALL_MAGICBLADE, 255, 0, 0, 100)
    _set_all_mistrals_position(0, 0)

    print("[LIGHTING] 🎃 DECOY HIT — full room red!")


def on_countdown():
    """
    Call when 10 seconds remain.
    All fixtures shift to tense red. Fires once only.
    """
    global _countdown_triggered, _in_countdown

    if _countdown_triggered:
        return

    _countdown_triggered = True
    _in_countdown        = True

    _setup_countdown()
    print("[LIGHTING] ⏱ Countdown — all fixtures red!")


def on_win():
    """
    Call on game over with good score.
    Full room celebration:
      ePar      → bright white
      MiniPanel → gold flood
      Mistral   → fan out left/right yellow
      MagicBlade → gold full brightness
    Then pulses the whole room in update().
    """
    global _lightning_enabled, _flash_active, _decoy_flash_active
    global _win_pulse_active, _win_pulse_step, _win_pulse_on, _win_pulse_last_ms
    global _lose_pulse_active

    _lightning_enabled  = False
    _flash_active       = False
    _decoy_flash_active = False
    _lose_pulse_active  = False

    # Cut all Mistrals first
    for fix in FLASH_FIXTURES:
        _set_dimmer(fix, 0)

    # ePar — bright white
    _set_group_colour(ALL_EPAR, 255, 255, 255, 100)

    # MiniPanel — gold
    _set_group_colour(ALL_MINIPANEL, 255, 200, 0, 100)

    # Mistral — fan out left and right, yellow
    left_mistrals  = ["Fixture 103", "Fixture 303", "Fixture 503", "Fixture 703"]
    right_mistrals = ["Fixture 203", "Fixture 403", "Fixture 603", "Fixture 803"]
    for fix in left_mistrals:
        _set_colour(fix, 255, 220, 0);  _set_dimmer(fix, 100)
        _set_mistral_pan_tilt(fix, -90, 20)
    for fix in right_mistrals:
        _set_colour(fix, 255, 220, 0);  _set_dimmer(fix, 100)
        _set_mistral_pan_tilt(fix, 90, 20)

    # MagicBlade — gold
    _set_group_colour(ALL_MAGICBLADE, 255, 160, 0, 100)

    # Start win pulse in update()
    _win_pulse_active    = True
    _win_pulse_step      = 0
    _win_pulse_on        = True
    _win_pulse_last_ms   = pygame.time.get_ticks()

    print("[LIGHTING] 🏆 WIN — full room celebration started!")


def on_lose():
    """
    Call on game over with bad score.
    Full room doom:
      ePar      → dark red low
      MiniPanel → very dark red
      Mistral   → all tilt to floor, deep red
      MagicBlade → deep red slow heartbeat pulse in update()
    """
    global _lightning_enabled, _flash_active, _decoy_flash_active
    global _lose_pulse_active, _lose_pulse_step, _lose_pulse_on, _lose_pulse_last_ms
    global _win_pulse_active

    _lightning_enabled  = False
    _flash_active       = False
    _decoy_flash_active = False
    _win_pulse_active   = False

    for fix in FLASH_FIXTURES:
        _set_dimmer(fix, 0)

    # ePar — dark red
    _set_group_colour(ALL_EPAR, 150, 0, 0, 50)

    # MiniPanel — very dark red
    _set_group_colour(ALL_MINIPANEL, 120, 0, 0, 40)

    # Mistral — tilt to floor, deep red
    _set_group_colour(ALL_MISTRAL, 180, 0, 0, 80)
    _set_all_mistrals_position(0, -60)

    # MagicBlade — deep red, will pulse slowly in update()
    _set_group_colour(ALL_MAGICBLADE, 200, 0, 0, 60)

    # Start lose heartbeat pulse
    _lose_pulse_active   = True
    _lose_pulse_step     = 0
    _lose_pulse_on       = True
    _lose_pulse_last_ms  = pygame.time.get_ticks()

    print("[LIGHTING] 💀 LOSE — full room doom!")


def on_game_restart():
    """
    Call on K_r restart. Resets everything, restores spooky atmosphere.
    """
    global _lightning_enabled, _countdown_triggered, _flash_active
    global _decoy_flash_active, _win_pulse_active, _lose_pulse_active
    global _in_countdown

    _lightning_enabled   = False
    _countdown_triggered = False
    _flash_active        = False
    _decoy_flash_active  = False
    _win_pulse_active    = False
    _lose_pulse_active   = False
    _in_countdown        = False

    for fix in FLASH_FIXTURES:
        _set_dimmer(fix, 0)

    _setup_spooky()
    print("[LIGHTING] Restarted — all fixtures back to spooky.")


def update():
    """
    Call EVERY FRAME.
    Handles:
      - Lightning cutoff after FLASH_DURATION_MS
      - Decoy hit restore after DECOY_FLASH_DURATION_MS
      - Win celebration pulse (ePar + MiniPanel strobe)
      - Lose heartbeat pulse (MagicBlade slow throb)
    """
    global _flash_active, _decoy_flash_active
    global _win_pulse_active, _win_pulse_step, _win_pulse_on, _win_pulse_last_ms
    global _lose_pulse_active, _lose_pulse_step, _lose_pulse_on, _lose_pulse_last_ms

    now = pygame.time.get_ticks()

    # --- Lightning cutoff ---
    if _flash_active:
        if now - _flash_trigger_ms > FLASH_DURATION_MS:
            for fix in FLASH_FIXTURES:
                _set_dimmer(fix, 0)
            _flash_active = False
            print("[LIGHTING] ⚡ Lightning OFF")

    # --- Decoy hit restore ---
    if _decoy_flash_active:
        if now - _decoy_flash_trigger_ms > DECOY_FLASH_DURATION_MS:
            if _in_countdown:
                _setup_countdown()
            else:
                _setup_spooky()
            _decoy_flash_active = False
            print("[LIGHTING] Decoy flash over — atmosphere restored.")

    # --- Win celebration pulse ---
    # ePar and MiniPanel strobe white/gold alternately
    if _win_pulse_active:
        if now - _win_pulse_last_ms >= WIN_PULSE_MS:
            _win_pulse_on = not _win_pulse_on

            if _win_pulse_on:
                _set_group_colour(ALL_EPAR,      255, 255, 255, 100)  # White
                _set_group_colour(ALL_MINIPANEL, 255, 200,   0, 100)  # Gold
            else:
                _set_group_colour(ALL_EPAR,      255, 200,   0,  60)  # Dim gold
                _set_group_colour(ALL_MINIPANEL, 255, 255, 255,  60)  # Dim white

            _win_pulse_step    += 1
            _win_pulse_last_ms  = now

            if _win_pulse_step >= WIN_PULSE_COUNT * 2:
                _win_pulse_active = False
                # Hold final gold look
                _set_group_colour(ALL_EPAR,      255, 220,   0, 100)
                _set_group_colour(ALL_MINIPANEL, 255, 160,   0, 100)
                print("[LIGHTING] Win pulse complete — holding gold.")

    # --- Lose heartbeat pulse ---
    # MagicBlade throbs red slowly like a heartbeat
    if _lose_pulse_active:
        if now - _lose_pulse_last_ms >= 600:    # Slow heartbeat
            _lose_pulse_on = not _lose_pulse_on

            if _lose_pulse_on:
                _set_group_colour(ALL_MAGICBLADE, 220, 0, 0, 80)   # Bright red
            else:
                _set_group_colour(ALL_MAGICBLADE, 100, 0, 0, 20)   # Very dim red

            _lose_pulse_last_ms = now
            # Lose pulse keeps going until restart — no step limit


# =================================================================
# === TEST BLOCK — DELETE AFTER TESTING ===
# =================================================================
if __name__ == "__main__":
    import time
    import random
    pygame.init()

    print("=== FULL ROOM HARDCODED LIGHTING TEST ===")
    print(f"Sending to {GMA3_IP}:{GMA3_PORT}")
    print(f"Controlling {len(ALL_FIXTURES)} fixtures total")
    print()

    print("1. Init — all fixtures spooky atmosphere...")
    init()
    time.sleep(3)

    print("2. Tutorial start — lightning enabled...")
    on_tutorial_start()

    start = time.time()
    while time.time() - start < 15:
        remaining = 30 - (time.time() - start)
        print(f"Time left: {remaining:.0f}s")

        if random.random() < 0.4:
            on_lightning_flash()
            time.sleep(FLASH_DURATION_MS / 1000)
            for fix in FLASH_FIXTURES:
                _set_dimmer(fix, 0)
            _flash_active = False

        if random.random() < 0.2:
            on_decoy_hit()
            time.sleep(DECOY_FLASH_DURATION_MS / 1000)
            _setup_spooky()
            _decoy_flash_active = False

        time.sleep(0.8)

    print()
    print("3. Countdown — full room red...")
    on_countdown()

    start = time.time()
    while time.time() - start < 10:
        remaining = 10 - (time.time() - start)
        print(f"Time left: {remaining:.0f}s")

        if random.random() < 0.6:
            on_lightning_flash()
            time.sleep(FLASH_DURATION_MS / 1000)
            for fix in FLASH_FIXTURES:
                _set_dimmer(fix, 0)
            _flash_active = False

        time.sleep(0.8)

    print()
    print("4. WIN — full room celebration!")
    on_win()
    time.sleep(6)

    print()
    print("5. Restart...")
    on_game_restart()
    time.sleep(3)

    print()
    print("6. LOSE — full room doom + heartbeat!")
    on_tutorial_start()
    time.sleep(1)
    on_lose()
    time.sleep(6)

    print()
    print("=== TEST COMPLETE — delete test block when done ===")