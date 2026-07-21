# lighting.py
# Handles all GMA3 OSC lighting control for Haunted Manor: Ghost Hunt
# FULLY HARDCODED — no GMA3 sequences needed
#
# Fixture groups:
#   ePar 180:    101, 201, 301, 401, 501, 601, 702, 801
#   MiniPanel:   102, 202, 302, 402, 502, 602, 701, 802
#   Mistral:     103, 203, 303, 403, 503, 603, 703, 803  ← all used for lightning
#   MagicBlade:  104, 204, 304, 404, 504, 604, 704, 804  ← effects, colour only
#
# Spotlights (pan/tilt hardcoded, always on):
#   MiniPanel 502 — pan -71.26,  tilt -27.53, 100% white
#   MiniPanel 202 — pan -140.56, tilt -11.78, 100% white

import pygame
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
    "Fixture 101", "Fixture 201", "Fixture 501", "Fixture 601", "Fixture 702", "Fixture 801"
]

# All MiniPanels EXCEPT the two spotlights (502 and 202)
ALL_MINIPANEL = [
    "Fixture 102", "Fixture 602", "Fixture 701", "Fixture 802"
]

# All Mistrals — all used for lightning
ALL_MISTRAL = [
    "Fixture 103", "Fixture 203", "Fixture 503", "Fixture 603", "Fixture 703", "Fixture 803"
]

ALL_MAGICBLADE = [
    "Fixture 104", "Fixture 204", "Fixture 504", "Fixture 604", "Fixture 704", "Fixture 804"
]

ALL_FIXTURES = ALL_EPAR + ALL_MINIPANEL + ["Fixture 202", "Fixture 502"] + ALL_MISTRAL + ALL_MAGICBLADE

# Spotlights — MiniPanel 502 and 202, white, pan/tilt hardcoded, always on
SPOTLIGHT_A      = "Fixture 502"
SPOTLIGHT_A_PAN  = -71.26
SPOTLIGHT_A_TILT = -27.53

SPOTLIGHT_B      = "Fixture 202"
SPOTLIGHT_B_PAN  = -140.56
SPOTLIGHT_B_TILT = -11.78

SPOTLIGHT_DIMMER = 35


# Lightning — ALL Mistrals
FLASH_FIXTURES    = ALL_MISTRAL
FLASH_DIMMER      = 25
FLASH_DURATION_MS = 150

# Only these 4 Mistrals actually flash, each at a hardcoded pan/tilt.
# Any other Mistral (i.e. 703, 803) is forced off during lightning.
FLASH_POSITIONS = {
    "Fixture 103": (-155, 125),
    "Fixture 203": (-155, 125),
    "Fixture 503": (155, 125),
    "Fixture 603": (155, 125),
}
FLASH_OFF_FIXTURES = [fix for fix in ALL_MISTRAL if fix not in FLASH_POSITIONS]

# Decoy hit flash duration
DECOY_FLASH_DURATION_MS = 350

# Stage win pulse
STAGE_WIN_PULSE_COUNT = 4
STAGE_WIN_PULSE_MS    = 200

# Stage lose pulse interval
STAGE_LOSE_PULSE_MS = 500

# Countdown flash per second duration
COUNTDOWN_FLASH_DURATION_MS = 120

# Pan/Tilt ranges (for spotlights only)
PAN_MIN,  PAN_MAX  = -315, 315
TILT_MIN, TILT_MAX = -135, 135

FOCUS_MIN, FOCUS_MAX = 0, 100
FLASH_FOCUS = 100

# Colour ranges
RED_MIN,   RED_MAX   = 0, 255
GREEN_MIN, GREEN_MAX = 0, 255
BLUE_MIN,  BLUE_MAX  = 0, 255

# =================================================================
# === ROUND SEQUENCE (hardcoded colour chase) ===
# One single sequence, reused for all 3 rounds. Runs continuously
# during gameplay (started on_tutorial_start / on_thumbsup_accepted,
# stopped on countdown / decoy-hit-safe / stage end / restart).
# Mistrals are left untouched — they're reserved for lightning flashes.
# Spotlights (502 / 202) are NOT touched by this — they stay fixed at
# their hardcoded pan/tilt the whole time, per _fire_spotlights().
# =================================================================
SEQUENCE_STEP_MS = 350  # how long each step holds before moving to the next

# Each step = (epar_rgb+dim, minipanel_rgb+dim, magicblade_rgb+dim)
ROUND_SEQUENCE = [
    # step 0: ePar bright
    {"epar": (60, 30, 130, 80), "minipanel": (20, 35, 20, 25), "magicblade": (60, 10, 10, 25)},
    # step 1: MiniPanel bright
    {"epar": (35, 25, 75, 35), "minipanel": (25, 90, 25, 80), "magicblade": (60, 10, 10, 25)},
    # step 2: MagicBlade bright
    {"epar": (35, 25, 75, 35), "minipanel": (20, 35, 20, 25), "magicblade": (130, 25, 25, 85)},
    # step 3: all low (breath before repeating)
    {"epar": (35, 25, 75, 35), "minipanel": (20, 35, 20, 25), "magicblade": (60, 10, 10, 25)},
]

# =================================================================
# === INTERNAL STATE ===
# =================================================================
_lightning_enabled       = False
_countdown_triggered     = False
_flash_active            = False
_flash_trigger_ms        = 0
_decoy_flash_active      = False
_decoy_flash_trigger_ms  = 0
_in_countdown            = False

_stage_win_active        = False
_stage_win_step          = 0
_stage_win_last_ms       = 0
_stage_win_on            = False

_stage_lose_active       = False
_stage_lose_on           = False
_stage_lose_last_ms      = 0

_final_win_active        = False
_final_win_step          = 0
_final_win_last_ms       = 0
_final_win_on            = False

_final_lose_active       = False
_final_lose_on           = False
_final_lose_last_ms      = 0

_countdown_flash_active  = False
_countdown_flash_ms      = 0
_last_countdown_second   = -1

_round_sequence_active   = False
_round_sequence_step     = 0
_round_sequence_last_ms  = 0


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


def _all_lights_off():
    """Turn off every single fixture — used on game close."""
    for fix in ALL_FIXTURES:
        _send(f"{fix} At 0")
    print("[LIGHTING] All lights off.")


def _fire_spotlights():
    """
    Bring up both MiniPanel spotlights at their hardcoded pan/tilt.
    White, 100% brightness. ONLY these two fixtures have pan/tilt set by Python.
    """
    _set_colour(SPOTLIGHT_A, 255, 255, 255)
    _set_dimmer(SPOTLIGHT_A, SPOTLIGHT_DIMMER)
    _set_attribute(SPOTLIGHT_A, "pan",  SPOTLIGHT_A_PAN,  PAN_MIN, PAN_MAX)
    _set_attribute(SPOTLIGHT_A, "tilt", SPOTLIGHT_A_TILT, TILT_MIN, TILT_MAX)

    _set_colour(SPOTLIGHT_B, 255, 255, 255)
    _set_dimmer(SPOTLIGHT_B, SPOTLIGHT_DIMMER)
    _set_attribute(SPOTLIGHT_B, "pan",  SPOTLIGHT_B_PAN,  PAN_MIN, PAN_MAX)
    _set_attribute(SPOTLIGHT_B, "tilt", SPOTLIGHT_B_TILT, TILT_MIN, TILT_MAX)

    # Fixture 601 turns on/color-cycles alongside the spotlights (console-side
    # effect, not driven by this script) — force it off every time spotlights fire.
    _set_dimmer("Fixture 601", 0)

    print(f"[LIGHTING] Spotlights ON — {SPOTLIGHT_A} and {SPOTLIGHT_B} white, Fixture 601 forced off")


def _stop_all_effects():
    """Clear all running win/lose/pulse/sequence effects and their state."""
    global _stage_win_active, _stage_lose_active
    global _final_win_active, _final_lose_active
    global _decoy_flash_active, _countdown_triggered
    global _in_countdown, _countdown_flash_active, _last_countdown_second
    global _round_sequence_active

    _stage_win_active       = False
    _stage_lose_active      = False
    _final_win_active       = False
    _final_lose_active      = False
    _decoy_flash_active     = False
    _countdown_triggered    = False
    _in_countdown           = False
    _countdown_flash_active = False
    _last_countdown_second  = -1
    _round_sequence_active  = False


def _start_round_sequence():
    """Kick off the hardcoded chase/sweep sequence used during every round."""
    global _round_sequence_active, _round_sequence_step, _round_sequence_last_ms
    _round_sequence_active  = True
    _round_sequence_step    = 0
    _round_sequence_last_ms = pygame.time.get_ticks()
    print("[LIGHTING] Round sequence started.")


# =================================================================
# === ATMOSPHERE SETUPS ===
# =================================================================
def _setup_spooky():
    """
    Dimmed spooky atmosphere. No pan/tilt — GMA3 controls Mistral positions.
    Spotlights (502, 202) excluded — handled by _fire_spotlights().

    ePar:       dark charcoal blue-grey, very low
    MiniPanel:  deep olive green, very dim (excludes spotlights)
    Mistral:    cold steel blue, low
    MagicBlade: dark rust/maroon, low
    """
    for fix in ALL_EPAR:
        _set_colour(fix, 45, 45, 90);   _set_dimmer(fix, 45)

    for fix in ALL_MINIPANEL:
        _set_colour(fix, 35, 70, 35);   _set_dimmer(fix, 38)

    for fix in ALL_MISTRAL:
        _set_colour(fix, 35, 50, 120);  _set_dimmer(fix, 50)

    for fix in ALL_MAGICBLADE:
        _set_colour(fix, 90, 20, 20);   _set_dimmer(fix, 38)

    print("[LIGHTING] Spooky atmosphere set.")


def _setup_countdown():
    """Last 10 seconds — deep blood red. No pan/tilt. Spotlights stay white."""
    for fix in ALL_EPAR:
        _set_colour(fix, 120, 0, 0);    _set_dimmer(fix, 60)

    for fix in ALL_MINIPANEL:
        _set_colour(fix, 100, 0, 0);    _set_dimmer(fix, 55)

    for fix in ALL_MISTRAL:
        _set_colour(fix, 170, 0, 0);    _set_dimmer(fix, 75)

    for fix in ALL_MAGICBLADE:
        _set_colour(fix, 150, 0, 0);    _set_dimmer(fix, 55)

    print("[LIGHTING] Countdown atmosphere — blood red.")


def _setup_thumbsup():
    """Calm cool white for gesture reading. No pan/tilt. Spotlights stay."""
    for fix in ALL_EPAR:
        _set_colour(fix, 140, 140, 180); _set_dimmer(fix, 65)

    for fix in ALL_MINIPANEL:
        _set_colour(fix, 120, 120, 160); _set_dimmer(fix, 60)

    for fix in ALL_MISTRAL:
        _set_colour(fix, 200, 200, 230); _set_dimmer(fix, 60)

    for fix in ALL_MAGICBLADE:
        _set_colour(fix, 120, 120, 160); _set_dimmer(fix, 50)

    print("[LIGHTING] Thumbs up atmosphere — cool white/blue.")


# =================================================================
# === PUBLIC API ===
# =================================================================
def init():
    """Call ONCE at game startup. Sets spooky atmosphere and fires spotlights."""
    global _lightning_enabled, _flash_active

    _lightning_enabled = False
    _flash_active      = False
    _stop_all_effects()

    _setup_spooky()
    _fire_spotlights()
    print("[LIGHTING] Initialised.")


def on_tutorial_start():
    """Call when tutorial begins or a new stage starts. Enables lightning,
    clears effects, and kicks off the round chase/sweep sequence."""
    global _lightning_enabled

    _lightning_enabled = True
    _stop_all_effects()

    _setup_spooky()
    _fire_spotlights()
    _start_round_sequence()
    print("[LIGHTING] Tutorial/stage started — lightning enabled, sequence running.")


def on_thumbsup_check():
    """Call when PHASE_INSTRUCT starts. Calm atmosphere, lightning off, sequence paused."""
    global _lightning_enabled, _flash_active, _round_sequence_active

    _lightning_enabled    = False
    _flash_active         = False
    _round_sequence_active = False

    _setup_thumbsup()

    for fix in FLASH_FIXTURES:
        _set_dimmer(fix, 0)

    print("[LIGHTING] Thumbs up check.")


def on_thumbsup_accepted():
    """Call when thumbs up registered. Restore spooky, lightning on, sequence resumes."""
    global _lightning_enabled

    _lightning_enabled = True
    _stop_all_effects()

    _setup_spooky()
    _fire_spotlights()
    _start_round_sequence()
    print("[LIGHTING] Thumbs up accepted — spooky restored, lightning + sequence on.")


def on_lightning_flash():
    """
    Call when in-game lightning activates.
    Only the 4 hardcoded Mistrals (103, 203, 503, 603) snap white at their
    fixed pan/tilt positions. Any other Mistral (703, 803) is forced off.
    update() cuts after FLASH_DURATION_MS.
    """
    global _flash_active, _flash_trigger_ms

    if not _lightning_enabled:
        return
    if _flash_active:
        return

    _flash_active     = True
    _flash_trigger_ms = pygame.time.get_ticks()

    for fix, (pan, tilt) in FLASH_POSITIONS.items():
        _set_attribute(fix, "pan",  pan,  PAN_MIN, PAN_MAX)
        _set_attribute(fix, "tilt", tilt, TILT_MIN, TILT_MAX)
        _set_attribute(fix, "focus", FLASH_FOCUS, FOCUS_MIN, FOCUS_MAX)
        _set_colour(fix, 255, 255, 255)
        _set_dimmer(fix, FLASH_DIMMER)

    for fix in FLASH_OFF_FIXTURES:
        _set_dimmer(fix, 0)

    print("[LIGHTING] ⚡ Lightning ON!")


def on_decoy_hit():
    """
    Call when player hits a decoy.
    Full room deep red. No pan/tilt. Spotlights stay white.
    update() restores after DECOY_FLASH_DURATION_MS (sequence resumes on its own).
    """
    global _decoy_flash_active, _decoy_flash_trigger_ms

    if _decoy_flash_active:
        return

    _decoy_flash_active     = True
    _decoy_flash_trigger_ms = pygame.time.get_ticks()

    for fix in ALL_EPAR:
        _set_colour(fix, 220, 0, 0);    _set_dimmer(fix, 90)
    for fix in ALL_MINIPANEL:
        _set_colour(fix, 200, 0, 0);    _set_dimmer(fix, 85)
    for fix in ALL_MISTRAL:
        _set_colour(fix, 240, 0, 0);    _set_dimmer(fix, 95)
    for fix in ALL_MAGICBLADE:
        _set_colour(fix, 220, 0, 0);    _set_dimmer(fix, 80)

    print("[LIGHTING] 🎃 DECOY HIT — red slam!")


def on_countdown(time_left: int):
    """
    Call every frame during gameplay, passing time_left.
    Handles initial red shift at 10s (stops the round sequence for a clean
    blood-red look) and per-second flash sync.
    """
    global _countdown_triggered, _in_countdown
    global _countdown_flash_active, _countdown_flash_ms, _last_countdown_second
    global _round_sequence_active

    if not _countdown_triggered and time_left <= 10:
        _countdown_triggered  = True
        _in_countdown         = True
        _round_sequence_active = False
        _setup_countdown()
        print("[LIGHTING] ⏱ Countdown — blood red! (sequence paused)")

    if _in_countdown and 1 <= time_left <= 10:
        if time_left != _last_countdown_second:
            _last_countdown_second  = time_left
            _countdown_flash_active = True
            _countdown_flash_ms     = pygame.time.get_ticks()

            for fix in ALL_EPAR:
                _set_colour(fix, 240, 0, 0);    _set_dimmer(fix, 100)
            for fix in ALL_MINIPANEL:
                _set_colour(fix, 220, 0, 0);    _set_dimmer(fix, 95)

            print(f"[LIGHTING] ⚡ Countdown flash — {time_left}s!")


def on_stage_win(stage: int):
    """
    Call when stage 1 or 2 cleared with passing score.
    Bright gold pulse on MiniPanel + MagicBlade. No ePars. No pan/tilt.
    """
    global _lightning_enabled, _flash_active
    global _stage_win_active, _stage_win_step, _stage_win_on, _stage_win_last_ms

    _lightning_enabled = False
    _flash_active      = False
    _stop_all_effects()

    for fix in FLASH_FIXTURES:
        _set_dimmer(fix, 0)

    for fix in ALL_EPAR:
        _set_colour(fix, 20, 15, 0);    _set_dimmer(fix, 10)
    for fix in ALL_MINIPANEL:
        _set_colour(fix, 140, 110, 0);  _set_dimmer(fix, 65)
    for fix in ALL_MISTRAL:
        _set_colour(fix, 60, 40, 0);    _set_dimmer(fix, 30)
    for fix in ALL_MAGICBLADE:
        _set_colour(fix, 160, 120, 0);  _set_dimmer(fix, 75)

    _stage_win_active  = True
    _stage_win_step    = 0
    _stage_win_on      = True
    _stage_win_last_ms = pygame.time.get_ticks()

    print(f"[LIGHTING] Stage {stage} cleared — bright gold pulse.")


def on_stage_lose(stage: int):
    """
    Call when stage 1 or 2 ends without passing score.
    Dark red slow pulse on MagicBlade. No pan/tilt.
    """
    global _lightning_enabled, _flash_active
    global _stage_lose_active, _stage_lose_on, _stage_lose_last_ms

    _lightning_enabled = False
    _flash_active      = False
    _stop_all_effects()

    for fix in FLASH_FIXTURES:
        _set_dimmer(fix, 0)

    for fix in ALL_EPAR:
        _set_colour(fix, 70, 0, 0);     _set_dimmer(fix, 35)
    for fix in ALL_MINIPANEL:
        _set_colour(fix, 60, 0, 0);     _set_dimmer(fix, 30)
    for fix in ALL_MISTRAL:
        _set_colour(fix, 90, 0, 0);     _set_dimmer(fix, 40)
    for fix in ALL_MAGICBLADE:
        _set_colour(fix, 100, 0, 0);    _set_dimmer(fix, 38)

    _stage_lose_active  = True
    _stage_lose_on      = True
    _stage_lose_last_ms = pygame.time.get_ticks()

    print(f"[LIGHTING] Stage {stage} failed — dark red slow pulse.")


def on_win():
    """
    Final win (after stage 3).
    Bright amber gold on MiniPanel + MagicBlade. No ePars. No pan/tilt. Spotlights stay.
    """
    global _lightning_enabled, _flash_active
    global _final_win_active, _final_win_step, _final_win_on, _final_win_last_ms

    _lightning_enabled = False
    _flash_active      = False
    _stop_all_effects()

    for fix in FLASH_FIXTURES:
        _set_dimmer(fix, 0)

    for fix in ALL_EPAR:
        _set_dimmer(fix, 0)
    for fix in ALL_MINIPANEL:
        _set_colour(fix, 180, 120, 0);  _set_dimmer(fix, 85)
    for fix in ALL_MISTRAL:
        _set_colour(fix, 150, 90, 0);   _set_dimmer(fix, 70)
    for fix in ALL_MAGICBLADE:
        _set_colour(fix, 200, 130, 0);  _set_dimmer(fix, 85)

    _final_win_active  = True
    _final_win_step    = 0
    _final_win_on      = True
    _final_win_last_ms = pygame.time.get_ticks()

    print("[LIGHTING] 🏆 FINAL WIN — bright amber gold pulse!")


def on_lose():
    """
    Final lose (after stage 3).
    Dark red everywhere, MagicBlade heartbeat. No pan/tilt. Spotlights stay.
    """
    global _lightning_enabled, _flash_active
    global _final_lose_active, _final_lose_on, _final_lose_last_ms

    _lightning_enabled = False
    _flash_active      = False
    _stop_all_effects()

    for fix in FLASH_FIXTURES:
        _set_dimmer(fix, 0)

    for fix in ALL_EPAR:
        _set_colour(fix, 60, 0, 0);     _set_dimmer(fix, 28)
    for fix in ALL_MINIPANEL:
        _set_colour(fix, 50, 0, 0);     _set_dimmer(fix, 22)
    for fix in ALL_MISTRAL:
        _set_colour(fix, 80, 0, 0);     _set_dimmer(fix, 35)
    for fix in ALL_MAGICBLADE:
        _set_colour(fix, 90, 0, 0);     _set_dimmer(fix, 32)

    _final_lose_active  = True
    _final_lose_on      = True
    _final_lose_last_ms = pygame.time.get_ticks()

    print("[LIGHTING] 💀 FINAL LOSE — doom heartbeat.")


def on_game_restart():
    """Call on K_r restart. Stops all effects, restores spooky + spotlights."""
    global _lightning_enabled, _flash_active

    _lightning_enabled = False
    _flash_active      = False
    _stop_all_effects()

    for fix in FLASH_FIXTURES:
        _set_dimmer(fix, 0)

    _setup_spooky()
    _fire_spotlights()
    print("[LIGHTING] Restarted — spooky + spotlights restored.")


def on_game_close():
    """Call when the game exits. Turns off every single fixture."""
    _all_lights_off()
    print("[LIGHTING] Game closed — all lights off.")


def update():
    """
    Call EVERY FRAME.
    Handles all timed effects:
      - Round chase/sweep sequence
      - Lightning cutoff
      - Decoy hit restore
      - Countdown per-second flash cutoff
      - Stage win gold pulse
      - Stage lose slow red pulse
      - Final win amber gold pulse
      - Final lose heartbeat
    """
    global _flash_active, _decoy_flash_active
    global _countdown_flash_active
    global _stage_win_active, _stage_win_step, _stage_win_on, _stage_win_last_ms
    global _stage_lose_active, _stage_lose_on, _stage_lose_last_ms
    global _final_win_active, _final_win_step, _final_win_on, _final_win_last_ms
    global _final_lose_active, _final_lose_on, _final_lose_last_ms
    global _round_sequence_active, _round_sequence_step, _round_sequence_last_ms

    now = pygame.time.get_ticks()

    # --- Round chase/sweep sequence ---
    if _round_sequence_active and not _decoy_flash_active:
        if now - _round_sequence_last_ms >= SEQUENCE_STEP_MS:
            _round_sequence_step   = (_round_sequence_step + 1) % len(ROUND_SEQUENCE)
            _round_sequence_last_ms = now

            step = ROUND_SEQUENCE[_round_sequence_step]

            er, eg, eb, ed = step["epar"]
            for fix in ALL_EPAR:
                _set_colour(fix, er, eg, eb); _set_dimmer(fix, ed)

            mr, mg, mb, md = step["minipanel"]
            for fix in ALL_MINIPANEL:
                _set_colour(fix, mr, mg, mb); _set_dimmer(fix, md)

            gr, gg, gb, gd = step["magicblade"]
            for fix in ALL_MAGICBLADE:
                _set_colour(fix, gr, gg, gb); _set_dimmer(fix, gd)

            # Safety net: re-pin the spotlights to white every step in case
            # a console-side cue/group overlap is sneaking other colours in.
            _fire_spotlights()

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
            _fire_spotlights()
            _decoy_flash_active = False
            print("[LIGHTING] Decoy flash over.")

    # --- Countdown per-second flash cutoff ---
    if _countdown_flash_active:
        if now - _countdown_flash_ms > COUNTDOWN_FLASH_DURATION_MS:
            for fix in ALL_EPAR:
                _set_colour(fix, 120, 0, 0);    _set_dimmer(fix, 60)
            for fix in ALL_MINIPANEL:
                _set_colour(fix, 100, 0, 0);    _set_dimmer(fix, 55)
            _countdown_flash_active = False

    # --- Stage win bright gold pulse ---
    if _stage_win_active:
        if now - _stage_win_last_ms >= STAGE_WIN_PULSE_MS:
            _stage_win_on = not _stage_win_on
            if _stage_win_on:
                for fix in ALL_MINIPANEL:
                    _set_colour(fix, 140, 110, 0);  _set_dimmer(fix, 65)
                for fix in ALL_MAGICBLADE:
                    _set_colour(fix, 160, 120, 0);  _set_dimmer(fix, 75)
            else:
                for fix in ALL_MINIPANEL:
                    _set_colour(fix, 60, 45, 0);    _set_dimmer(fix, 25)
                for fix in ALL_MAGICBLADE:
                    _set_colour(fix, 75, 50, 0);    _set_dimmer(fix, 28)

            _stage_win_step    += 1
            _stage_win_last_ms  = now

            if _stage_win_step >= STAGE_WIN_PULSE_COUNT * 2:
                _stage_win_active = False
                for fix in ALL_MINIPANEL:
                    _set_colour(fix, 90, 65, 0);    _set_dimmer(fix, 38)
                for fix in ALL_MAGICBLADE:
                    _set_colour(fix, 100, 70, 0);   _set_dimmer(fix, 40)
                print("[LIGHTING] Stage win pulse complete.")

    # --- Stage lose slow red pulse ---
    if _stage_lose_active:
        if now - _stage_lose_last_ms >= STAGE_LOSE_PULSE_MS:
            _stage_lose_on = not _stage_lose_on
            dimmer = 60 if _stage_lose_on else 15
            for fix in ALL_MAGICBLADE:
                _set_colour(fix, 100, 0, 0);    _set_dimmer(fix, dimmer)
            _stage_lose_last_ms = now

    # --- Final win amber gold pulse ---
    if _final_win_active:
        if now - _final_win_last_ms >= 300:
            _final_win_on = not _final_win_on
            if _final_win_on:
                for fix in ALL_MINIPANEL:
                    _set_colour(fix, 180, 120, 0);  _set_dimmer(fix, 85)
                for fix in ALL_MAGICBLADE:
                    _set_colour(fix, 200, 130, 0);  _set_dimmer(fix, 85)
            else:
                for fix in ALL_MINIPANEL:
                    _set_colour(fix, 90, 60, 0);    _set_dimmer(fix, 40)
                for fix in ALL_MAGICBLADE:
                    _set_colour(fix, 100, 65, 0);   _set_dimmer(fix, 38)

            _final_win_step    += 1
            _final_win_last_ms  = now

            if _final_win_step >= 12:
                _final_win_active = False
                for fix in ALL_MINIPANEL:
                    _set_colour(fix, 150, 100, 0);  _set_dimmer(fix, 65)
                for fix in ALL_MAGICBLADE:
                    _set_colour(fix, 160, 105, 0);  _set_dimmer(fix, 65)
                print("[LIGHTING] Final win pulse complete — holding amber.")

    # --- Final lose heartbeat ---
    if _final_lose_active:
        if now - _final_lose_last_ms >= 700:
            _final_lose_on = not _final_lose_on
            dimmer = 60 if _final_lose_on else 15
            for fix in ALL_MAGICBLADE:
                _set_colour(fix, 100, 0, 0);    _set_dimmer(fix, dimmer)
            _final_lose_last_ms = now


# # =================================================================
# # === TEST BLOCK — DELETE AFTER TESTING ===
# # =================================================================
# if __name__ == "__main__":
#     import time
#     import random
#     pygame.init()

#     print("=== FULL LIGHTING TEST ===")
#     print(f"Sending to {GMA3_IP}:{GMA3_PORT}")
#     print()

#     print("1. Init — spooky + spotlights (502 and 202)...")
#     init()
#     time.sleep(3)

#     print("2. Tutorial start — lightning + round sequence enabled...")
#     on_tutorial_start()

#     start = time.time()
#     while time.time() - start < 10:
#         remaining = 30 - (time.time() - start)
#         print(f"Time left: {remaining:.0f}s")
#         update()
#         if random.random() < 0.4:
#             on_lightning_flash()
#             time.sleep(FLASH_DURATION_MS / 1000)
#             for fix in FLASH_FIXTURES:
#                 _set_dimmer(fix, 0)
#             _flash_active = False
#         if random.random() < 0.2:
#             on_decoy_hit()
#             time.sleep(DECOY_FLASH_DURATION_MS / 1000)
#             _setup_spooky(); _fire_spotlights()
#             _decoy_flash_active = False
#         time.sleep(0.8)

#     print()
#     print("3. Countdown — 10 to 1...")
#     for t in range(10, 0, -1):
#         on_countdown(t)
#         time.sleep(1)

#     print()
#     print("4. Stage 1 WIN...")
#     on_stage_win(1)
#     time.sleep(4)

#     print()
#     print("5. New round starts — effects clear, spooky + sequence restore...")
#     on_tutorial_start()
#     time.sleep(2)

#     print()
#     print("6. Stage 2 LOSE...")
#     on_stage_lose(2)
#     time.sleep(4)

#     print()
#     print("7. FINAL WIN...")
#     on_win()
#     time.sleep(6)

#     print()
#     print("8. Restart...")
#     on_game_restart()
#     time.sleep(3)

#     print()
#     print("9. FINAL LOSE + heartbeat...")
#     on_tutorial_start()
#     time.sleep(1)
#     on_lose()
#     time.sleep(6)

#     print()
#     print("10. Game close — all lights off...")
#     on_game_close()

#     print()
#     print("=== TEST COMPLETE — delete test block when done ===")