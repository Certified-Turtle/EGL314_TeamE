# lighting.py
# Handles all GMA3 OSC lighting control
#
# ─────────────────────────────────────────────────────────────────
# WHAT THIS FILE DOES, MATCHED TO main.py's ACTUAL CALLS:
#
#  init()                  - once, after the camera is ready. Sets the
#                            spooky atmosphere and fires "spotlightE"
#                            immediately (no separate intro-lights step).
#  on_tutorial_start()      - tutorial begins / new stage starts. Starts
#                            the round chase sequence (and "goboE" with it).
#  on_thumbsup_check()      - gesture-check screen begins. Full white,
#                            round sequence (and goboE) paused.
#  on_thumbsup_accepted()   - gesture accepted. Restores spooky, resumes
#                            the round sequence (and goboE).
#  on_decoy_hit()           - player hits a decoy. Red flash.
#  on_boss_sequence()       - stage 3, ghost hit count reaches the boss
#                            trigger. Blacks out the game-sequence/win
#                            fixtures and fires "BOSSMAN" once.
#  on_stage_win(stage)      - stage 1 or 2 cleared. Gold pulse.
#  on_win()                 - stage 3 cleared. Bright amber gold pulse.
#  on_game_restart()        - K_r restart. Clears effects, re-arms the
#                            boss trigger guard, restores spooky.
#  on_game_close()          - game exits. Turns everything off.
#  update()                 - every frame. Advances all timed effects.
#
# FIXTURE GROUPS:
#  Game sequence (spooky/decoy hit/round chase): Fixture 702, 704, 802, 804
#  Win effects ONLY (on_stage_win / on_win):      Fixture 301, 401, 701, 801
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
SPOTLIGHT_SEQ = "spotlightE"   # Fired once in init() — stays on until game close
GOBO_SEQ      = "goboE"        # Wall decor — ON only while the round sequence plays
BOSS_SEQ      = "BOSSMAN"      # Fired once by on_boss_sequence()

# =================================================================
# === FIXTURE GROUPS ===
# =================================================================
GAME_FIXTURES = ["Fixture 702", "Fixture 704", "Fixture 802", "Fixture 804"]

# Split into two alternating pairs for the round chase visual
GROUP_1 = ["Fixture 702", "Fixture 704"]
GROUP_2 = ["Fixture 802", "Fixture 804"]

# Win fixtures — used ONLY by on_stage_win() / on_win()
WIN_FIXTURES = ["Fixture 301", "Fixture 401", "Fixture 701", "Fixture 801"]

# Of the win fixtures, these are the ePar ones — flash green for a stage pass,
# since there's no win/lose distinction anymore and green reads as "pass"
EPAR_WIN_FIXTURES  = ["Fixture 301", "Fixture 401", "Fixture 801"]
OTHER_WIN_FIXTURES = ["Fixture 701"]   # MiniPanel — keeps the gold tone

# =================================================================
# === TIMING CONSTANTS ===
# =================================================================
DECOY_FLASH_DURATION_MS = 350
STAGE_WIN_PULSE_COUNT   = 4
STAGE_WIN_PULSE_MS      = 200
SEQUENCE_STEP_MS        = 350

# Colour ranges
RED_MIN,   RED_MAX   = 0, 255
GREEN_MIN, GREEN_MAX = 0, 255
BLUE_MIN,  BLUE_MAX  = 0, 255

# Round chase colours — pink/orange(yellow)/red
ROUND_SEQUENCE = [
    {"group1": (220, 200, 0, 60),  "group2": (70, 20, 35, 20)},   # yellow on group 1
    {"group1": (70, 20, 35, 20),   "group2": (220, 20, 100, 60)}, # pink on group 2
    {"group1": (220, 0, 0, 60),    "group2": (70, 20, 35, 20)},   # red on group 1
    {"group1": (70, 20, 35, 20),   "group2": (70, 20, 35, 20)},   # low breather
]

# =================================================================
# === INTERNAL STATE ===
# =================================================================
_decoy_flash_active      = False
_decoy_flash_trigger_ms  = 0

_stage_win_active        = False
_stage_win_step          = 0
_stage_win_last_ms       = 0
_stage_win_on            = False

_final_win_active        = False
_final_win_step          = 0
_final_win_last_ms       = 0
_final_win_on            = False

_round_sequence_active   = False
_round_sequence_step     = 0
_round_sequence_last_ms  = 0

_gobo_active             = False

_boss_triggered          = False   # Defensive guard - main.py already guards this too


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
    global _gobo_active
    if _gobo_active:
        return
    _gobo_active = True
    _send(f'Go Sequence "{GOBO_SEQ}" Cue 1')
    print(f"[LIGHTING] Gobo sequence '{GOBO_SEQ}' ON.")


def _stop_gobo_sequence():
    global _gobo_active
    if not _gobo_active:
        return
    _gobo_active = False
    _send(f'Off Sequence "{GOBO_SEQ}"')
    print(f"[LIGHTING] Gobo sequence '{GOBO_SEQ}' OFF.")


def _stop_all_effects():
    """Resets every routine effect flag and stops goboE."""
    global _stage_win_active, _final_win_active, _decoy_flash_active
    global _round_sequence_active

    _stage_win_active      = False
    _final_win_active      = False
    _decoy_flash_active    = False
    _round_sequence_active = False

    _stop_gobo_sequence()


def _start_round_sequence():
    global _round_sequence_active, _round_sequence_step, _round_sequence_last_ms
    _round_sequence_active  = True
    _round_sequence_step    = 0
    _round_sequence_last_ms = pygame.time.get_ticks()
    _start_gobo_sequence()
    print("[LIGHTING] Round sequence started.")


# =================================================================
# === ATMOSPHERE SETUPS (game-sequence fixtures only) ===
# =================================================================
def _setup_spooky():
    for fix in GAME_FIXTURES:
        _set_colour(fix, 90, 20, 20); _set_dimmer(fix, 45)
    print("[LIGHTING] Spooky atmosphere set.")


def _setup_thumbsup():
    for fix in GAME_FIXTURES:
        _set_colour(fix, 255, 255, 255); _set_dimmer(fix, 75)
    print("[LIGHTING] Thumbs up atmosphere - full white.")


# =================================================================
# === PUBLIC API — matched to main.py's calls ===
# =================================================================
def init():
    """
    Call ONCE, after the camera is ready.
    Sets spooky atmosphere on the game-sequence fixtures and fires
    spotlightE immediately.
    """
    global _boss_triggered

    _stop_all_effects()
    _boss_triggered = False

    _setup_spooky()
    _send(f'Go Sequence "{SPOTLIGHT_SEQ}" Cue 1')
    print(f"[LIGHTING] Initialised - spooky set, '{SPOTLIGHT_SEQ}' ON.")


def on_tutorial_start():
    """Tutorial begins or new stage starts. Starts round sequence (and goboE with it)."""
    _stop_all_effects()
    _setup_spooky()
    _start_round_sequence()
    print("[LIGHTING] Tutorial/stage started.")


def on_thumbsup_check():
    """Gesture-check screen begins. Full white, round sequence (and goboE) paused."""
    global _round_sequence_active
    _round_sequence_active = False
    _stop_gobo_sequence()
    _setup_thumbsup()
    print("[LIGHTING] Thumbs up check - full white.")


def on_thumbsup_accepted():
    """Gesture accepted. Restore spooky, round sequence (and goboE) resumes."""
    _stop_all_effects()
    _setup_spooky()
    _start_round_sequence()
    print("[LIGHTING] Thumbs up accepted.")


def on_decoy_hit():
    """Player hits a decoy. Red flash on game-sequence fixtures only."""
    global _decoy_flash_active, _decoy_flash_trigger_ms

    if _decoy_flash_active:
        return

    _decoy_flash_active     = True
    _decoy_flash_trigger_ms = pygame.time.get_ticks()

    for fix in GAME_FIXTURES:
        _set_colour(fix, 220, 0, 0); _set_dimmer(fix, 90)

    print("[LIGHTING] DECOY HIT - red flash!")


def on_boss_sequence():
    """
    Call ONCE, when the stage-3 ghost hit count reaches the boss trigger
    (main.py already guards this with its own `boss_triggered` flag, so
    this is safe to call once per playthrough - a local guard here too,
    just in case).

    Blacks out the game-sequence fixtures, win fixtures, and spotlightE,
    pauses the round sequence/goboE, then fires BOSSMAN once.

    NOTE: this is a placeholder cue mapping - swap in whatever your real
    GMA3 "BOSSMAN" sequence/cue actually needs. Nothing here automatically
    restores the atmosphere once PHASE_BOSS ends and main.py drops back
    into PHASE_GAMEPLAY - if you want the round sequence/goboE/spotlight
    to come back after the boss black screen, call on_tutorial_start()
    (or a dedicated restore function) when that happens in main.py.
    """
    global _boss_triggered

    if _boss_triggered:
        return
    _boss_triggered = True

    _stop_all_effects()
    _send(f'Off Sequence "{SPOTLIGHT_SEQ}"')

    for fix in GAME_FIXTURES:
        _set_dimmer(fix, 0)
    for fix in WIN_FIXTURES:
        _set_dimmer(fix, 0)

    _send(f'Go Sequence "{BOSS_SEQ}" Cue 1')
    print(f"[LIGHTING] BOSS SEQUENCE - game lights off, '{BOSS_SEQ}' fired.")


def on_stage_win(stage: int):
    """Stage 1 or 2 cleared (a 'stage pass'). ePar fixtures flash green,
    the MiniPanel win fixture keeps its gold accent."""
    global _stage_win_active, _stage_win_step, _stage_win_on, _stage_win_last_ms

    _stop_all_effects()

    for fix in EPAR_WIN_FIXTURES:
        _set_colour(fix, 0, 200, 0);   _set_dimmer(fix, 80)
    for fix in OTHER_WIN_FIXTURES:
        _set_colour(fix, 160, 120, 0); _set_dimmer(fix, 75)

    _stage_win_active  = True
    _stage_win_step    = 0
    _stage_win_on      = True
    _stage_win_last_ms = pygame.time.get_ticks()
    print(f"[LIGHTING] Stage {stage} passed - ePar green pulse.")


def on_win():
    """Stage 3 cleared. Bright amber gold pulse on win fixtures ONLY."""
    global _final_win_active, _final_win_step, _final_win_on, _final_win_last_ms

    _stop_all_effects()

    for fix in WIN_FIXTURES:
        _set_colour(fix, 200, 130, 0); _set_dimmer(fix, 85)

    _final_win_active  = True
    _final_win_step    = 0
    _final_win_on      = True
    _final_win_last_ms = pygame.time.get_ticks()
    print("[LIGHTING] FINAL WIN - amber gold pulse!")


def on_game_restart():
    """K_r restart. Clears effects, re-arms the boss trigger guard, restores spooky."""
    global _boss_triggered

    _stop_all_effects()
    _boss_triggered = False

    _setup_spooky()
    print("[LIGHTING] Restarted - spooky restored, boss trigger re-armed.")


def on_game_close():
    """Called when the game exits. Turns off spotlightE/goboE and every fixture."""
    _send(f'Off Sequence "{SPOTLIGHT_SEQ}"')
    _send(f'Off Sequence "{GOBO_SEQ}"')

    for fix in GAME_FIXTURES + WIN_FIXTURES:
        _send(f"{fix} At 0")

    print("[LIGHTING] Game closed - all lights off.")


def update():
    """
    Call EVERY FRAME.
    Handles:
      - Decoy hit restore
      - Round chase sequence
      - Stage win pulse
      - Final win pulse
    """
    global _decoy_flash_active
    global _stage_win_active, _stage_win_step, _stage_win_on, _stage_win_last_ms
    global _final_win_active, _final_win_step, _final_win_on, _final_win_last_ms
    global _round_sequence_active, _round_sequence_step, _round_sequence_last_ms

    now = pygame.time.get_ticks()

    # --- Decoy hit restore ---
    if _decoy_flash_active:
        if now - _decoy_flash_trigger_ms > DECOY_FLASH_DURATION_MS:
            _setup_spooky()
            _decoy_flash_active = False
            print("[LIGHTING] Decoy flash over.")

    # --- Round chase sequence ---
    if _round_sequence_active and not _decoy_flash_active:
        if now - _round_sequence_last_ms >= SEQUENCE_STEP_MS:
            _round_sequence_step    = (_round_sequence_step + 1) % len(ROUND_SEQUENCE)
            _round_sequence_last_ms = now
            step = ROUND_SEQUENCE[_round_sequence_step]
            r1, g1, b1, d1 = step["group1"]
            for fix in GROUP_1:
                _set_colour(fix, r1, g1, b1); _set_dimmer(fix, d1)
            r2, g2, b2, d2 = step["group2"]
            for fix in GROUP_2:
                _set_colour(fix, r2, g2, b2); _set_dimmer(fix, d2)

    # --- Stage pass pulse: ePar green, MiniPanel gold ---
    if _stage_win_active:
        if now - _stage_win_last_ms >= STAGE_WIN_PULSE_MS:
            _stage_win_on = not _stage_win_on
            if _stage_win_on:
                for fix in EPAR_WIN_FIXTURES:
                    _set_colour(fix, 0, 200, 0);   _set_dimmer(fix, 80)
                for fix in OTHER_WIN_FIXTURES:
                    _set_colour(fix, 160, 120, 0); _set_dimmer(fix, 75)
            else:
                for fix in EPAR_WIN_FIXTURES:
                    _set_colour(fix, 0, 90, 0);    _set_dimmer(fix, 30)
                for fix in OTHER_WIN_FIXTURES:
                    _set_colour(fix, 70, 50, 0);   _set_dimmer(fix, 28)
            _stage_win_step    += 1
            _stage_win_last_ms  = now
            if _stage_win_step >= STAGE_WIN_PULSE_COUNT * 2:
                _stage_win_active = False
                for fix in EPAR_WIN_FIXTURES:
                    _set_colour(fix, 0, 130, 0);  _set_dimmer(fix, 45)
                for fix in OTHER_WIN_FIXTURES:
                    _set_colour(fix, 100, 70, 0); _set_dimmer(fix, 40)
                print("[LIGHTING] Stage pass pulse complete.")

    # --- Final win amber gold pulse ---
    if _final_win_active:
        if now - _final_win_last_ms >= 300:
            _final_win_on = not _final_win_on
            if _final_win_on:
                for fix in WIN_FIXTURES:
                    _set_colour(fix, 200, 130, 0); _set_dimmer(fix, 85)
            else:
                for fix in WIN_FIXTURES:
                    _set_colour(fix, 100, 65, 0);  _set_dimmer(fix, 38)
            _final_win_step    += 1
            _final_win_last_ms  = now
            if _final_win_step >= 12:
                _final_win_active = False
                for fix in WIN_FIXTURES:
                    _set_colour(fix, 160, 105, 0); _set_dimmer(fix, 65)
                print("[LIGHTING] Final win pulse complete.")