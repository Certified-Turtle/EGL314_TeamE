# lighting.py
# Handles all GMA3 OSC lighting control
#
# ─────────────────────────────────────────────────────────────────
# FIXTURE OWNERSHIP MAP — what controls what:
#
#  GAME SEQUENCE (atmosphere/effects — this script's normal loop):
#    Fixture 702, Fixture 704, Fixture 802, Fixture 804
#
#  WIN/LOSE EFFECTS — used ONLY by on_stage_win/on_stage_lose/on_win/on_lose,
#  never touched by anything else (not spooky, not countdown, not decoy hit,
#  not the round chase):
#    Fixture 301, Fixture 401, Fixture 701, Fixture 801
#
#  SPOTLIGHT SEQUENCE ("spotlightE") — toggled by the 'O' key via
#  on_spotlight_toggle(). Pressing it clears everything (round sequence,
#  goboE, game-sequence fixtures) THEN fires spotlightE.
#
#  GOBO SEQUENCE ("goboE") — wall decoration. ON ONLY while the game
#  sequence (round chase) is playing, OFF otherwise.
#
#  BOSS ENDGAME CASCADE — triggered once, when the ghost counter hits 8
#  during round 3 (see trigger_boss_sequence()):
#    1. Everything above (spotlightE, goboE, game-sequence fixtures,
#       win/lose fixtures) turns off immediately.
#    2. "Zone A" -> "Zone B" -> "Zone C" -> "Zone D" turn off one by one,
#       1 second apart.
#    3. One more second later, "BOSS MAN" turns on and STAYS ON —
#       including after the game process exits. on_game_close() no
#       longer clears any lights, specifically so BOSS MAN persists.
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
SPOTLIGHT_SEQ = "spotlightE"
GOBO_SEQ      = "goboE"
ZONE_SEQS     = ["Zone A", "Zone B", "Zone C", "Zone D"]
BOSS_SEQ      = "BOSS MAN"

# =================================================================
# === FIXTURE GROUPS ===
# =================================================================
# Game-sequence fixtures — spooky/countdown/decoy hit/round chase only
GAME_FIXTURES = ["Fixture 702", "Fixture 704", "Fixture 802", "Fixture 804"]

# Split into two alternating pairs for the round chase visual
GROUP_1 = ["Fixture 702", "Fixture 704"]
GROUP_2 = ["Fixture 802", "Fixture 804"]

# Win/lose fixtures — used ONLY by the four win/lose functions below
WIN_LOSE_FIXTURES = ["Fixture 301", "Fixture 401", "Fixture 701", "Fixture 801"]

# =================================================================
# === TIMING CONSTANTS ===
# =================================================================
DECOY_FLASH_DURATION_MS     = 350
STAGE_WIN_PULSE_COUNT       = 4
STAGE_WIN_PULSE_MS          = 200
STAGE_LOSE_PULSE_MS         = 500
COUNTDOWN_FLASH_DURATION_MS = 120
SEQUENCE_STEP_MS            = 350
BOSS_STEP_MS                = 1000   # 1 second between each zone/boss step

# Colour ranges
RED_MIN,   RED_MAX   = 0, 255
GREEN_MIN, GREEN_MAX = 0, 255
BLUE_MIN,  BLUE_MAX  = 0, 255

# Round chase colours — pink/orange(yellow)/red only
ROUND_SEQUENCE = [
    {"group1": (220, 200, 0, 60),  "group2": (70, 20, 35, 20)},   # yellow on group 1
    {"group1": (70, 20, 35, 20),   "group2": (220, 20, 100, 60)}, # pink on group 2
    {"group1": (220, 0, 0, 60),    "group2": (70, 20, 35, 20)},   # red on group 1
    {"group1": (70, 20, 35, 20),   "group2": (70, 20, 35, 20)},   # low breather
]

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

_gobo_active             = False

_boss_triggered          = False   # One-time guard - boss cascade only ever fires once per game
_boss_sequence_active    = False   # True while the Zone A->B->C->D->BOSS MAN cascade is ticking
_boss_step               = 0
_boss_last_ms            = 0


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
    """Resets every routine effect flag. Does NOT touch the boss cascade state."""
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


def _setup_countdown():
    for fix in GAME_FIXTURES:
        _set_colour(fix, 150, 0, 0); _set_dimmer(fix, 60)
    print("[LIGHTING] Countdown atmosphere - blood red.")


def _setup_thumbsup():
    for fix in GAME_FIXTURES:
        _set_colour(fix, 255, 255, 255); _set_dimmer(fix, 75)
    print("[LIGHTING] Thumbs up atmosphere - full white.")


# =================================================================
# === PUBLIC API ===
# =================================================================
def init():
    """
    Call ONCE at game startup.
    - Resets all effect state, including the boss cascade guard for a fresh session
    - Sets spooky atmosphere on the 4 game-sequence fixtures only
    - Does NOT fire spotlightE (only 'O' does that) or goboE (only the round
      sequence does that)
    """
    global _boss_triggered, _boss_sequence_active, _boss_step

    _stop_all_effects()
    _boss_triggered       = False
    _boss_sequence_active = False
    _boss_step            = 0

    _setup_spooky()
    print("[LIGHTING] Initialised.")


def on_spotlight_toggle():
    """
    Call when 'O' is pressed.
    Clears everything (round sequence, goboE, game-sequence fixtures) THEN
    fires spotlightE. Does not touch win/lose fixtures, zones, or BOSS MAN.
    """
    _stop_all_effects()

    for fix in GAME_FIXTURES:
        _set_dimmer(fix, 0)

    _send(f'Go Sequence "{SPOTLIGHT_SEQ}" Cue 1')
    print(f"[LIGHTING] Cleared everything - '{SPOTLIGHT_SEQ}' ON.")


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
    print("[LIGHTING] Thumbs up accepted.")


def on_decoy_hit():
    """Player hits a decoy. Red slam on game-sequence fixtures only."""
    global _decoy_flash_active, _decoy_flash_trigger_ms

    if _decoy_flash_active:
        return

    _decoy_flash_active     = True
    _decoy_flash_trigger_ms = pygame.time.get_ticks()

    for fix in GAME_FIXTURES:
        _set_colour(fix, 220, 0, 0); _set_dimmer(fix, 90)

    print("[LIGHTING] DECOY HIT - red slam!")


def on_countdown(time_left: int):
    """Call every frame during gameplay. Red shift at 10s (stops round sequence/goboE),
    plus a brighter flash each second."""
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

            for fix in GAME_FIXTURES:
                _set_colour(fix, 240, 0, 0); _set_dimmer(fix, 100)

            print(f"[LIGHTING] Countdown flash - {time_left}s!")


def on_stage_win(stage: int):
    """Stage 1 or 2 cleared. Gold pulse on win/lose fixtures ONLY."""
    global _stage_win_active, _stage_win_step, _stage_win_on, _stage_win_last_ms

    _stop_all_effects()

    for fix in WIN_LOSE_FIXTURES:
        _set_colour(fix, 160, 120, 0); _set_dimmer(fix, 75)

    _stage_win_active  = True
    _stage_win_step    = 0
    _stage_win_on      = True
    _stage_win_last_ms = pygame.time.get_ticks()
    print(f"[LIGHTING] Stage {stage} cleared - gold pulse.")


def on_stage_lose(stage: int):
    """Stage 1 or 2 failed. Dark red slow pulse on win/lose fixtures ONLY."""
    global _stage_lose_active, _stage_lose_on, _stage_lose_last_ms

    _stop_all_effects()

    for fix in WIN_LOSE_FIXTURES:
        _set_colour(fix, 90, 0, 0); _set_dimmer(fix, 38)

    _stage_lose_active  = True
    _stage_lose_on      = True
    _stage_lose_last_ms = pygame.time.get_ticks()
    print(f"[LIGHTING] Stage {stage} failed - dark red pulse.")


def on_win():
    """Final win after stage 3. Bright amber gold pulse on win/lose fixtures ONLY."""
    global _final_win_active, _final_win_step, _final_win_on, _final_win_last_ms

    _stop_all_effects()

    for fix in WIN_LOSE_FIXTURES:
        _set_colour(fix, 200, 130, 0); _set_dimmer(fix, 85)

    _final_win_active  = True
    _final_win_step    = 0
    _final_win_on      = True
    _final_win_last_ms = pygame.time.get_ticks()
    print("[LIGHTING] FINAL WIN - amber gold pulse!")


def on_lose():
    """Final lose after stage 3. Dark red heartbeat on win/lose fixtures ONLY."""
    global _final_lose_active, _final_lose_on, _final_lose_last_ms

    _stop_all_effects()

    for fix in WIN_LOSE_FIXTURES:
        _set_colour(fix, 90, 0, 0); _set_dimmer(fix, 32)

    _final_lose_active  = True
    _final_lose_on      = True
    _final_lose_last_ms = pygame.time.get_ticks()
    print("[LIGHTING] FINAL LOSE - doom heartbeat.")


def on_game_restart():
    """K_r restart. Clears routine effects, restores spooky, re-arms the boss trigger."""
    global _boss_triggered, _boss_sequence_active, _boss_step

    _stop_all_effects()
    _boss_triggered       = False
    _boss_sequence_active = False
    _boss_step            = 0

    _setup_spooky()
    print("[LIGHTING] Restarted - spooky restored, boss trigger re-armed.")


def trigger_boss_sequence():
    """
    Call ONCE, when the ghost counter hits 8 during round 3.
    Safe to call more than once - after the first call this does nothing.

    1. Turns off spotlightE, goboE, game-sequence fixtures, and win/lose fixtures.
    2. Turns off Zone A immediately, then Zone B/C/D one at a time, 1 second apart.
    3. One more second after Zone D, fires BOSS MAN - which stays on permanently,
       including after the game process exits (on_game_close() no longer clears it).
    """
    global _boss_triggered, _boss_sequence_active, _boss_step, _boss_last_ms

    if _boss_triggered:
        return
    _boss_triggered = True

    # 1. Everything mentioned above, off
    _stop_all_effects()
    _send(f'Off Sequence "{SPOTLIGHT_SEQ}"')

    for fix in GAME_FIXTURES:
        _set_dimmer(fix, 0)
    for fix in WIN_LOSE_FIXTURES:
        _set_dimmer(fix, 0)

    # 2. Zone A off immediately, B/C/D handled in update() at 1s intervals
    _send(f'Off Sequence "{ZONE_SEQS[0]}"')

    _boss_sequence_active = True
    _boss_step            = 0
    _boss_last_ms          = pygame.time.get_ticks()

    print("[LIGHTING] BOSS TRIGGER - all lights off, Zone A down, cascade starting.")


def on_game_close():
    """
    Called when the game exits.
    Intentionally does NOT turn anything off - BOSS MAN (and whatever else is
    running) must persist after the game process ends.
    """
    print("[LIGHTING] Game closed - lights intentionally left as-is (BOSS MAN persists).")


def update():
    """
    Call EVERY FRAME.
    Handles:
      - Decoy hit restore
      - Countdown per-second flash cutoff
      - Round chase sequence
      - Stage win/lose pulses
      - Final win/lose pulses
      - Boss cascade (Zone B/C/D off, then BOSS MAN on)
    """
    global _decoy_flash_active
    global _countdown_flash_active
    global _stage_win_active, _stage_win_step, _stage_win_on, _stage_win_last_ms
    global _stage_lose_active, _stage_lose_on, _stage_lose_last_ms
    global _final_win_active, _final_win_step, _final_win_on, _final_win_last_ms
    global _final_lose_active, _final_lose_on, _final_lose_last_ms
    global _round_sequence_active, _round_sequence_step, _round_sequence_last_ms
    global _boss_sequence_active, _boss_step, _boss_last_ms

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
            for fix in GAME_FIXTURES:
                _set_colour(fix, 150, 0, 0); _set_dimmer(fix, 60)
            _countdown_flash_active = False

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

    # --- Stage win gold pulse ---
    if _stage_win_active:
        if now - _stage_win_last_ms >= STAGE_WIN_PULSE_MS:
            _stage_win_on = not _stage_win_on
            if _stage_win_on:
                for fix in WIN_LOSE_FIXTURES:
                    _set_colour(fix, 160, 120, 0); _set_dimmer(fix, 75)
            else:
                for fix in WIN_LOSE_FIXTURES:
                    _set_colour(fix, 70, 50, 0);   _set_dimmer(fix, 28)
            _stage_win_step    += 1
            _stage_win_last_ms  = now
            if _stage_win_step >= STAGE_WIN_PULSE_COUNT * 2:
                _stage_win_active = False
                for fix in WIN_LOSE_FIXTURES:
                    _set_colour(fix, 100, 70, 0); _set_dimmer(fix, 40)
                print("[LIGHTING] Stage win pulse complete.")

    # --- Stage lose slow red pulse ---
    if _stage_lose_active:
        if now - _stage_lose_last_ms >= STAGE_LOSE_PULSE_MS:
            _stage_lose_on = not _stage_lose_on
            dimmer = 55 if _stage_lose_on else 15
            for fix in WIN_LOSE_FIXTURES:
                _set_colour(fix, 100, 0, 0); _set_dimmer(fix, dimmer)
            _stage_lose_last_ms = now

    # --- Final win amber gold pulse ---
    if _final_win_active:
        if now - _final_win_last_ms >= 300:
            _final_win_on = not _final_win_on
            if _final_win_on:
                for fix in WIN_LOSE_FIXTURES:
                    _set_colour(fix, 200, 130, 0); _set_dimmer(fix, 85)
            else:
                for fix in WIN_LOSE_FIXTURES:
                    _set_colour(fix, 100, 65, 0);  _set_dimmer(fix, 38)
            _final_win_step    += 1
            _final_win_last_ms  = now
            if _final_win_step >= 12:
                _final_win_active = False
                for fix in WIN_LOSE_FIXTURES:
                    _set_colour(fix, 160, 105, 0); _set_dimmer(fix, 65)
                print("[LIGHTING] Final win pulse complete.")

    # --- Final lose heartbeat ---
    if _final_lose_active:
        if now - _final_lose_last_ms >= 700:
            _final_lose_on = not _final_lose_on
            dimmer = 55 if _final_lose_on else 12
            for fix in WIN_LOSE_FIXTURES:
                _set_colour(fix, 100, 0, 0); _set_dimmer(fix, dimmer)
            _final_lose_last_ms = now

    # --- Boss cascade: Zone B -> Zone C -> Zone D -> BOSS MAN, 1s apart ---
    if _boss_sequence_active:
        if now - _boss_last_ms >= BOSS_STEP_MS:
            _boss_step  += 1
            _boss_last_ms = now

            if _boss_step == 1:
                _send(f'Off Sequence "{ZONE_SEQS[1]}"')
                print("[LIGHTING] Zone B off.")
            elif _boss_step == 2:
                _send(f'Off Sequence "{ZONE_SEQS[2]}"')
                print("[LIGHTING] Zone C off.")
            elif _boss_step == 3:
                _send(f'Off Sequence "{ZONE_SEQS[3]}"')
                print("[LIGHTING] Zone D off.")
            elif _boss_step == 4:
                _send(f'Go Sequence "{BOSS_SEQ}" Cue 1')
                _boss_sequence_active = False
                print(f"[LIGHTING] '{BOSS_SEQ}' ON - stays on permanently.")