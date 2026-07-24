# lighting.py
# Handles all GMA3 OSC lighting control for Haunted Manor: Ghost Hunt
#
# ─────────────────────────────────────────────────────────────────
# FIXTURE OWNERSHIP MAP — what controls what:
#
#  SPOTLIGHT SEQUENCE ("spotlightE") — fired ONCE at init, never touched again:
#    MiniPanel 202, MiniPanel 302, MiniPanel 502, MagicBlade 304
#
#  GOBO SEQUENCE ("goboE") — wall decoration. ON ONLY while the game
#  sequence (round chase) is playing, OFF otherwise. This is the ONLY
#  thing that ever touches the Mistrals — nothing else in this script
#  sends commands to any Mistral fixture:
#    Mistral 103, Mistral 203, Mistral 503, Mistral 603, Mistral 703, Mistral 803
#
#  LIGHTNING — REMOVED. No lightning sequence, no lightning fixtures,
#  no on_lightning_flash(). Mistrals are fully owned by goboE now.
#
#  ALWAYS OFF — never sent any command, ever:
#    ePar 301, ePar 401
#    MiniPanel 402
#    Mistral 303, Mistral 403
#    MagicBlade 404
#
#  GAME SEQUENCE (atmosphere / effects — this script):
#    ePar:       101, 201, 501, 601, 702, 801
#    MiniPanel:  102, 602, 701, 802
#    MagicBlade: 104, 204, 504, 604, 704, 804
# ─────────────────────────────────────────────────────────────────

import pygame
from pythonosc import udp_client

# =================================================================
# === GMA3 CONNECTION — EDIT THESE ===
# =================================================================
GMA3_IP   = "192.168.254.252"
GMA3_PORT = 8080
GMA3_ADDR = "/gma3/cmd"

# =================================================================
# === SEQUENCE NAMES ===
# =================================================================
SPOTLIGHT_SEQ = "spotlightE"   # Fired once at init — stays on until game close
GOBO_SEQ      = "goboE"        # Wall decor — ON only while game sequence is playing

# =================================================================
# === GAME-SEQUENCE FIXTURE GROUPS ===
# Only these fixtures are ever touched by the game atmospheres/effects.
# Mistrals are NOT here — they belong entirely to goboE.
# =================================================================
ALL_EPAR = [
    "Fixture 101", "Fixture 201",
    "Fixture 501", "Fixture 601",
    "Fixture 702", "Fixture 801"
]

ALL_MINIPANEL = [
    "Fixture 102",
    "Fixture 602", "Fixture 701", "Fixture 802"
]

ALL_MAGICBLADE = [
    "Fixture 104", "Fixture 204",
    "Fixture 504", "Fixture 604",
    "Fixture 704", "Fixture 804"
]

# All game-sequence fixtures — used only for game-close shutdown
GAME_FIXTURES = ALL_EPAR + ALL_MINIPANEL + ALL_MAGICBLADE

# Spotlight fixtures — owned by spotlightE, never touched by this script
SPOTLIGHT_FIXTURES = [
    "Fixture 202", "Fixture 302", "Fixture 502", "Fixture 304"
]

# Gobo/wall-decor fixtures — owned entirely by goboE. ALL 6 Mistrals.
GOBO_FIXTURES = [
    "Fixture 103", "Fixture 203", "Fixture 503",
    "Fixture 603", "Fixture 703", "Fixture 803"
]

# =================================================================
# === TIMING CONSTANTS ===
# =================================================================
DECOY_FLASH_DURATION_MS     = 350
STAGE_WIN_PULSE_COUNT       = 4
STAGE_WIN_PULSE_MS          = 200
STAGE_LOSE_PULSE_MS         = 500
COUNTDOWN_FLASH_DURATION_MS = 120

# Colour ranges
RED_MIN,   RED_MAX   = 0, 255
GREEN_MIN, GREEN_MAX = 0, 255
BLUE_MIN,  BLUE_MAX  = 0, 255

# =================================================================
# === INTERNAL STATE ===
# =================================================================
_countdown_triggered     = False
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

_gobo_active              = False   # Tracks whether goboE is currently running

SEQUENCE_STEP_MS = 350
ROUND_SEQUENCE = [
    {"epar": (220, 200, 0, 40), "minipanel": (70, 20, 35, 12), "magicblade": (60, 10, 10, 12)},
    {"epar": (60, 20, 10, 18), "minipanel": (220, 20, 100, 40), "magicblade": (60, 10, 10, 12)},
    {"epar": (60, 20, 10, 18), "minipanel": (70, 20, 35, 12), "magicblade": (220, 0, 0, 42)},
    {"epar": (60, 20, 10, 18), "minipanel": (70, 20, 35, 12), "magicblade": (60, 10, 10, 12)},
]


# =================================================================
# === LOW-LEVEL OSC HELPERS ===
# =================================================================
def _send(message: str):
    try:
        client = udp_client.SimpleUDPClient(GMA3_IP, GMA3_PORT)
        client.send_message(GMA3_ADDR, message)
        print(f"[LIGHTING SENT] -> {message}")
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


def _start_gobo_sequence():
    """Turn on the goboE wall-decor sequence, only if not already running."""
    global _gobo_active
    if _gobo_active:
        return
    _gobo_active = True
    _send(f'Go Sequence "{GOBO_SEQ}" Cue 1')
    print(f"[LIGHTING] Gobo sequence '{GOBO_SEQ}' ON - wall decor running.")


def _stop_gobo_sequence():
    """Turn off the goboE wall-decor sequence, only if currently running."""
    global _gobo_active
    if not _gobo_active:
        return
    _gobo_active = False
    _send(f'Off Sequence "{GOBO_SEQ}"')
    print(f"[LIGHTING] Gobo sequence '{GOBO_SEQ}' OFF - wall decor stopped.")


def _stop_all_effects():
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

    # Game sequence is stopping - gobo (wall decor) stops with it
    _stop_gobo_sequence()


def _start_round_sequence():
    global _round_sequence_active, _round_sequence_step, _round_sequence_last_ms
    _round_sequence_active  = True
    _round_sequence_step    = 0
    _round_sequence_last_ms = pygame.time.get_ticks()

    # Game sequence is starting - gobo (wall decor) starts with it
    _start_gobo_sequence()

    print("[LIGHTING] Round sequence started.")


# =================================================================
# === ATMOSPHERE SETUPS (game-sequence fixtures only - no Mistral) ===
# =================================================================
def _setup_spooky():
    for fix in ALL_EPAR:
        _set_colour(fix, 90, 20, 20);   _set_dimmer(fix, 45)
    for fix in ALL_MINIPANEL:
        _set_colour(fix, 100, 20, 55);  _set_dimmer(fix, 38)
    for fix in ALL_MAGICBLADE:
        _set_colour(fix, 90, 20, 20);   _set_dimmer(fix, 38)
    print("[LIGHTING] Spooky atmosphere set.")


def _setup_countdown():
    for fix in ALL_EPAR:
        _set_colour(fix, 120, 0, 0);    _set_dimmer(fix, 60)
    for fix in ALL_MINIPANEL:
        _set_colour(fix, 100, 0, 0);    _set_dimmer(fix, 55)
    for fix in ALL_MAGICBLADE:
        _set_colour(fix, 150, 0, 0);    _set_dimmer(fix, 55)
    print("[LIGHTING] Countdown atmosphere - blood red.")


def _setup_thumbsup():
    """Pure white for gesture reading. Spotlight and gobo/Mistral fixtures untouched."""
    for fix in ALL_EPAR:
        _set_colour(fix, 255, 255, 255); _set_dimmer(fix, 80)
    for fix in ALL_MINIPANEL:
        _set_colour(fix, 255, 255, 255); _set_dimmer(fix, 75)
    for fix in ALL_MAGICBLADE:
        _set_colour(fix, 255, 255, 255); _set_dimmer(fix, 70)
    print("[LIGHTING] Thumbs up atmosphere - full white.")


# =================================================================
# === PUBLIC API ===
# =================================================================
def init():
    """
    Call ONCE at game startup.
    - Fires the spotlight sequence (stays on until game close, never touched again)
    - Sets spooky atmosphere on game-sequence fixtures only
    - Does NOT touch the Mistrals - goboE only runs while the round sequence plays
    """
    _stop_all_effects()

    # Fire spotlight sequence ONCE - it stays on for the whole session
    _send(f'Go Sequence "{SPOTLIGHT_SEQ}" Cue 1')
    print(f"[LIGHTING] Spotlight sequence '{SPOTLIGHT_SEQ}' fired - stays on until game close.")

    # Set spooky on game-sequence fixtures only
    _setup_spooky()
    print("[LIGHTING] Initialised.")


def on_tutorial_start():
    """Tutorial begins or new stage starts. Starts round sequence (and goboE with it)."""
    _stop_all_effects()

    _setup_spooky()
    _start_round_sequence()
    print("[LIGHTING] Tutorial/stage started.")


def on_thumbsup_check():
    """PHASE_INSTRUCT starts. Full white, round sequence (and goboE) paused."""
    global _round_sequence_active
    _round_sequence_active = False
    _stop_gobo_sequence()

    _setup_thumbsup()
    print("[LIGHTING] Thumbs up check - full white.")


def on_thumbsup_accepted():
    """Thumbs up registered. Restore spooky, round sequence (and goboE) resumes."""
    _stop_all_effects()

    _setup_spooky()
    _start_round_sequence()
    print("[LIGHTING] Thumbs up accepted - spooky + round sequence restored.")


def on_decoy_hit():
    """Player hits a decoy. Full room red slam on game-sequence fixtures only."""
    global _decoy_flash_active, _decoy_flash_trigger_ms

    if _decoy_flash_active:
        return

    _decoy_flash_active     = True
    _decoy_flash_trigger_ms = pygame.time.get_ticks()

    for fix in ALL_EPAR:
        _set_colour(fix, 220, 0, 0);    _set_dimmer(fix, 90)
    for fix in ALL_MINIPANEL:
        _set_colour(fix, 200, 0, 0);    _set_dimmer(fix, 85)
    for fix in ALL_MAGICBLADE:
        _set_colour(fix, 220, 0, 0);    _set_dimmer(fix, 80)

    print("[LIGHTING] DECOY HIT - red slam!")


def on_countdown(time_left: int):
    """Call every frame during gameplay. Handles red shift at 10s and per-second flash.
    Stops the round sequence (and goboE) when countdown begins."""
    global _countdown_triggered, _in_countdown
    global _countdown_flash_active, _countdown_flash_ms, _last_countdown_second
    global _round_sequence_active

    if not _countdown_triggered and time_left <= 10:
        _countdown_triggered   = True
        _in_countdown          = True
        _round_sequence_active = False
        _stop_gobo_sequence()
        _setup_countdown()
        print("[LIGHTING] Countdown - blood red!")

    if _in_countdown and 1 <= time_left <= 10:
        if time_left != _last_countdown_second:
            _last_countdown_second  = time_left
            _countdown_flash_active = True
            _countdown_flash_ms     = pygame.time.get_ticks()

            for fix in ALL_EPAR:
                _set_colour(fix, 240, 0, 0);    _set_dimmer(fix, 100)
            for fix in ALL_MINIPANEL:
                _set_colour(fix, 220, 0, 0);    _set_dimmer(fix, 95)

            print(f"[LIGHTING] Countdown flash - {time_left}s!")


def on_stage_win(stage: int):
    """Stage 1 or 2 cleared. Gold pulse on game-sequence fixtures."""
    global _stage_win_active, _stage_win_step, _stage_win_on, _stage_win_last_ms

    _stop_all_effects()

    for fix in ALL_EPAR:
        _set_colour(fix, 20, 15, 0);    _set_dimmer(fix, 10)
    for fix in ALL_MINIPANEL:
        _set_colour(fix, 140, 110, 0);  _set_dimmer(fix, 65)
    for fix in ALL_MAGICBLADE:
        _set_colour(fix, 160, 120, 0);  _set_dimmer(fix, 75)

    _stage_win_active  = True
    _stage_win_step    = 0
    _stage_win_on      = True
    _stage_win_last_ms = pygame.time.get_ticks()
    print(f"[LIGHTING] Stage {stage} cleared - gold pulse.")


def on_stage_lose(stage: int):
    """Stage 1 or 2 failed. Dark red slow pulse."""
    global _stage_lose_active, _stage_lose_on, _stage_lose_last_ms

    _stop_all_effects()

    for fix in ALL_EPAR:
        _set_colour(fix, 70, 0, 0);     _set_dimmer(fix, 35)
    for fix in ALL_MINIPANEL:
        _set_colour(fix, 60, 0, 0);     _set_dimmer(fix, 30)
    for fix in ALL_MAGICBLADE:
        _set_colour(fix, 100, 0, 0);    _set_dimmer(fix, 38)

    _stage_lose_active  = True
    _stage_lose_on      = True
    _stage_lose_last_ms = pygame.time.get_ticks()
    print(f"[LIGHTING] Stage {stage} failed - dark red pulse.")


def on_win():
    """Final win after stage 3. Bright amber gold pulse."""
    global _final_win_active, _final_win_step, _final_win_on, _final_win_last_ms

    _stop_all_effects()

    for fix in ALL_EPAR:
        _set_dimmer(fix, 0)
    for fix in ALL_MINIPANEL:
        _set_colour(fix, 180, 120, 0);  _set_dimmer(fix, 85)
    for fix in ALL_MAGICBLADE:
        _set_colour(fix, 200, 130, 0);  _set_dimmer(fix, 85)

    _final_win_active  = True
    _final_win_step    = 0
    _final_win_on      = True
    _final_win_last_ms = pygame.time.get_ticks()
    print("[LIGHTING] FINAL WIN - amber gold pulse!")


def on_lose():
    """Final lose after stage 3. Dark red everywhere, MagicBlade heartbeat."""
    global _final_lose_active, _final_lose_on, _final_lose_last_ms

    _stop_all_effects()

    for fix in ALL_EPAR:
        _set_colour(fix, 60, 0, 0);     _set_dimmer(fix, 28)
    for fix in ALL_MINIPANEL:
        _set_colour(fix, 50, 0, 0);     _set_dimmer(fix, 22)
    for fix in ALL_MAGICBLADE:
        _set_colour(fix, 90, 0, 0);     _set_dimmer(fix, 32)

    _final_lose_active  = True
    _final_lose_on      = True
    _final_lose_last_ms = pygame.time.get_ticks()
    print("[LIGHTING] FINAL LOSE - doom heartbeat.")


def on_game_restart():
    """K_r restart. Clears effects, restores spooky. Spotlights untouched, goboE stops."""
    _stop_all_effects()

    _setup_spooky()
    print("[LIGHTING] Restarted - spooky restored. Spotlights still on.")


def on_game_close():
    """
    Called when the game exits.
    Stops both GMA3 sequences and turns off all fixtures.
    This is the ONLY place spotlights (and goboE) are turned off.
    """
    # Stop GMA3 sequences
    _send(f'Off Sequence "{SPOTLIGHT_SEQ}"')
    _send(f'Off Sequence "{GOBO_SEQ}"')

    # Turn off all game-sequence fixtures
    for fix in GAME_FIXTURES:
        _send(f"{fix} At 0")

    # Also turn off spotlight and gobo/Mistral fixtures explicitly
    for fix in SPOTLIGHT_FIXTURES + GOBO_FIXTURES:
        _send(f"{fix} At 0")

    print("[LIGHTING] Game closed - all lights off.")


def update():
    """
    Call EVERY FRAME.
    Handles:
      - Decoy hit restore
      - Countdown per-second flash cutoff
      - Round chase sequence
      - Stage win/lose pulses
      - Final win/lose pulses
    """
    global _decoy_flash_active
    global _countdown_flash_active
    global _stage_win_active, _stage_win_step, _stage_win_on, _stage_win_last_ms
    global _stage_lose_active, _stage_lose_on, _stage_lose_last_ms
    global _final_win_active, _final_win_step, _final_win_on, _final_win_last_ms
    global _final_lose_active, _final_lose_on, _final_lose_last_ms
    global _round_sequence_active, _round_sequence_step, _round_sequence_last_ms

    now = pygame.time.get_ticks()

    # --- Decoy hit restore ---
    if _decoy_flash_active:
        if now - _decoy_flash_trigger_ms > DECOY_FLASH_DURATION_MS:
            if _in_countdown:
                _setup_countdown()
            else:
                _setup_spooky()
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

    # --- Round chase sequence ---
    if _round_sequence_active and not _decoy_flash_active:
        if now - _round_sequence_last_ms >= SEQUENCE_STEP_MS:
            _round_sequence_step    = (_round_sequence_step + 1) % len(ROUND_SEQUENCE)
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

    # --- Stage win gold pulse ---
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
                print("[LIGHTING] Final win pulse complete.")

    # --- Final lose heartbeat ---
    if _final_lose_active:
        if now - _final_lose_last_ms >= 700:
            _final_lose_on = not _final_lose_on
            dimmer = 60 if _final_lose_on else 15
            for fix in ALL_MAGICBLADE:
                _set_colour(fix, 100, 0, 0);    _set_dimmer(fix, dimmer)
            _final_lose_last_ms = now