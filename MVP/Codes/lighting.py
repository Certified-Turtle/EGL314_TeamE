# lighting.py
# Handles all GMA3 OSC lighting control
#
# ─────────────────────────────────────────────────────────────────
# GAME FLOW / FIXTURE OWNERSHIP MAP:
#
#  1. Script launches -> init() fires "mainfacelights" AND "Player Position"
#     together.
#
#  2. Team presses 'O' -> on_intro_transition() turns OFF BOTH
#     "mainfacelights" and "Player Position", and turns ON "spotlightE".
#     Locked - none of this fires again this session.
#
#  3. Game sequence (tutorial/rounds) -> on_tutorial_start() /
#     on_thumbsup_accepted() turn ON "goboE" AND "gameseqE" together.
#     These two sequences own Fixture 701 (MiniPanel), 703 (Mistral),
#     802 (MiniPanel), 803 (Mistral) ENTIRELY - this script NEVER sends
#     a single command to any of those four fixtures.
#
#  4. Passing-stage lights - the ePars (702, 801, 301, 401) are used
#     ONLY by on_stage_win() / on_win(), nothing else touches them.
#
#  5. Fixture 704 and 804 (MagicBlade) are free-use - this script uses
#     them for the spooky ambience, gesture-check white, and decoy hit
#     flash.
#
#  6. Game exits -> on_game_close() turns everything off.
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
MAIN_FACE_SEQ  = "mainfacelights"   # Pre-game explanation, off on 'O'
PLAYER_POS_SEQ = "Player Position"  # Pre-game, on with mainfacelights, off on 'O'
SPOTLIGHT_SEQ  = "spotlightE"       # Fired once via 'O', stays on until game close
GOBO_SEQ       = "goboE"            # Game sequence — on only while playing
GAMESEQ_SEQ    = "gameseqE"         # Game sequence — on only while playing, alongside goboE

# =================================================================
# === FIXTURE GROUPS ===
# =================================================================
# Owned ENTIRELY by goboE/gameseqE — never touched directly by this script
SEQUENCE_OWNED_FIXTURES = ["Fixture 701", "Fixture 703", "Fixture 802", "Fixture 803"]

# ePars — passing-stage lights ONLY (on_stage_win / on_win)
PASS_FIXTURES = ["Fixture 702", "Fixture 801", "Fixture 301", "Fixture 401"]

# MagicBlade — free-use. Spooky ambience, gesture-check white, decoy hit flash.
FREE_FIXTURES = ["Fixture 704", "Fixture 804"]

# =================================================================
# === TIMING CONSTANTS ===
# =================================================================
DECOY_FLASH_DURATION_MS = 350
STAGE_WIN_PULSE_COUNT   = 4
STAGE_WIN_PULSE_MS      = 200

# Colour ranges
RED_MIN,   RED_MAX   = 0, 255
GREEN_MIN, GREEN_MAX = 0, 255
BLUE_MIN,  BLUE_MAX  = 0, 255

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

_game_sequence_active    = False   # True while goboE + gameseqE are on

_main_face_active        = False
_player_pos_active       = False
_intro_transitioned      = False   # Once True, mainfacelights/Player Position lock off


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


def _start_game_sequence():
    """Turn on goboE + gameseqE together, only if not already running."""
    global _game_sequence_active
    if _game_sequence_active:
        return
    _game_sequence_active = True
    _send(f'Go Sequence "{GOBO_SEQ}" Cue 1')
    _send(f'Go Sequence "{GAMESEQ_SEQ}" Cue 1')
    print(f"[LIGHTING] '{GOBO_SEQ}' + '{GAMESEQ_SEQ}' ON.")


def _stop_game_sequence():
    """Turn off goboE + gameseqE together, only if currently running."""
    global _game_sequence_active
    if not _game_sequence_active:
        return
    _game_sequence_active = False
    _send(f'Off Sequence "{GOBO_SEQ}"')
    _send(f'Off Sequence "{GAMESEQ_SEQ}"')
    print(f"[LIGHTING] '{GOBO_SEQ}' + '{GAMESEQ_SEQ}' OFF.")


def _stop_all_effects():
    """Resets every routine effect flag and stops the game sequence."""
    global _stage_win_active, _final_win_active, _decoy_flash_active

    _stage_win_active   = False
    _final_win_active   = False
    _decoy_flash_active = False

    _stop_game_sequence()


# =================================================================
# === ATMOSPHERE SETUPS (free-use MagicBlade fixtures only) ===
# =================================================================
def _setup_spooky():
    for fix in FREE_FIXTURES:
        _set_colour(fix, 90, 20, 20); _set_dimmer(fix, 45)
    print("[LIGHTING] Spooky atmosphere set.")


def _setup_thumbsup():
    for fix in FREE_FIXTURES:
        _set_colour(fix, 255, 255, 255); _set_dimmer(fix, 75)
    print("[LIGHTING] Thumbs up atmosphere - full white.")


# =================================================================
# === PUBLIC API ===
# =================================================================
def init():
    """
    Call ONCE at game startup.
    Fires "mainfacelights" AND "Player Position" together for the pre-game
    explanation, and sets the spooky ambience on the free-use fixtures.
    """
    global _main_face_active, _player_pos_active, _intro_transitioned

    _stop_all_effects()
    _intro_transitioned = False

    _send(f'Go Sequence "{MAIN_FACE_SEQ}" Cue 1')
    _send(f'Go Sequence "{PLAYER_POS_SEQ}" Cue 1')
    _main_face_active  = True
    _player_pos_active = True
    print(f"[LIGHTING] '{MAIN_FACE_SEQ}' + '{PLAYER_POS_SEQ}' fired for the pre-game explanation.")

    _setup_spooky()
    print("[LIGHTING] Initialised.")


def on_intro_transition():
    """
    Call ONCE, when the team presses 'O' after explaining the game.
    Turns OFF BOTH "mainfacelights" and "Player Position", and turns ON
    "spotlightE". Locked - calling this again does nothing.
    """
    global _main_face_active, _player_pos_active, _intro_transitioned

    if _intro_transitioned:
        return
    _intro_transitioned = True

    if _main_face_active:
        _send(f'Off Sequence "{MAIN_FACE_SEQ}"')
        _main_face_active = False
    if _player_pos_active:
        _send(f'Off Sequence "{PLAYER_POS_SEQ}"')
        _player_pos_active = False

    _send(f'Go Sequence "{SPOTLIGHT_SEQ}" Cue 1')
    print(f"[LIGHTING] '{MAIN_FACE_SEQ}' + '{PLAYER_POS_SEQ}' OFF, '{SPOTLIGHT_SEQ}' ON - locked.")


def on_tutorial_start():
    """Tutorial begins or new stage starts. Starts goboE + gameseqE together."""
    _stop_all_effects()
    _setup_spooky()
    _start_game_sequence()
    print("[LIGHTING] Tutorial/stage started.")


def on_thumbsup_check():
    """Gesture-check screen begins. Full white, game sequence paused."""
    _stop_game_sequence()
    _setup_thumbsup()
    print("[LIGHTING] Thumbs up check - full white.")


def on_thumbsup_accepted():
    """Gesture accepted. Restore spooky, game sequence resumes."""
    _stop_all_effects()
    _setup_spooky()
    _start_game_sequence()
    print("[LIGHTING] Thumbs up accepted.")


def on_decoy_hit():
    """Player hits a decoy. Red flash on the free-use fixtures only."""
    global _decoy_flash_active, _decoy_flash_trigger_ms

    if _decoy_flash_active:
        return

    _decoy_flash_active     = True
    _decoy_flash_trigger_ms = pygame.time.get_ticks()

    for fix in FREE_FIXTURES:
        _set_colour(fix, 220, 0, 0); _set_dimmer(fix, 90)

    print("[LIGHTING] DECOY HIT - red flash!")


def on_stage_win(stage: int):
    """Stage 1 or 2 cleared (a 'stage pass'). Green pulse on the ePar
    passing-stage fixtures ONLY."""
    global _stage_win_active, _stage_win_step, _stage_win_on, _stage_win_last_ms

    _stop_all_effects()

    for fix in PASS_FIXTURES:
        _set_colour(fix, 0, 200, 0); _set_dimmer(fix, 80)

    _stage_win_active  = True
    _stage_win_step    = 0
    _stage_win_on      = True
    _stage_win_last_ms = pygame.time.get_ticks()
    print(f"[LIGHTING] Stage {stage} passed - ePar green pulse.")


def on_win():
    """Stage 3 cleared. Bright green pulse on the ePar passing-stage fixtures ONLY."""
    global _final_win_active, _final_win_step, _final_win_on, _final_win_last_ms

    _stop_all_effects()

    for fix in PASS_FIXTURES:
        _set_colour(fix, 0, 255, 0); _set_dimmer(fix, 95)

    _final_win_active  = True
    _final_win_step    = 0
    _final_win_on      = True
    _final_win_last_ms = pygame.time.get_ticks()
    print("[LIGHTING] FINAL WIN - bright ePar green pulse!")


def on_game_restart():
    """K_r restart. Clears effects, restores spooky. mainfacelights/Player
    Position/spotlightE are untouched - the intro handoff stays locked."""
    _stop_all_effects()
    _setup_spooky()
    print("[LIGHTING] Restarted - spooky restored.")


def on_game_close():
    """Called when the game exits. Turns everything off."""
    _send(f'Off Sequence "{MAIN_FACE_SEQ}"')
    _send(f'Off Sequence "{PLAYER_POS_SEQ}"')
    _send(f'Off Sequence "{SPOTLIGHT_SEQ}"')
    _send(f'Off Sequence "{GOBO_SEQ}"')
    _send(f'Off Sequence "{GAMESEQ_SEQ}"')

    for fix in PASS_FIXTURES + FREE_FIXTURES:
        _send(f"{fix} At 0")

    print("[LIGHTING] Game closed - all lights off.")


def update():
    """
    Call EVERY FRAME.
    Handles:
      - Decoy hit restore
      - Stage win pulse
      - Final win pulse
    """
    global _decoy_flash_active
    global _stage_win_active, _stage_win_step, _stage_win_on, _stage_win_last_ms
    global _final_win_active, _final_win_step, _final_win_on, _final_win_last_ms

    now = pygame.time.get_ticks()

    # --- Decoy hit restore ---
    if _decoy_flash_active:
        if now - _decoy_flash_trigger_ms > DECOY_FLASH_DURATION_MS:
            _setup_spooky()
            _decoy_flash_active = False
            print("[LIGHTING] Decoy flash over.")

    # --- Stage pass pulse (ePar green) ---
    if _stage_win_active:
        if now - _stage_win_last_ms >= STAGE_WIN_PULSE_MS:
            _stage_win_on = not _stage_win_on
            if _stage_win_on:
                for fix in PASS_FIXTURES:
                    _set_colour(fix, 0, 200, 0); _set_dimmer(fix, 80)
            else:
                for fix in PASS_FIXTURES:
                    _set_colour(fix, 0, 90, 0);  _set_dimmer(fix, 30)
            _stage_win_step    += 1
            _stage_win_last_ms  = now
            if _stage_win_step >= STAGE_WIN_PULSE_COUNT * 2:
                _stage_win_active = False
                for fix in PASS_FIXTURES:
                    _set_colour(fix, 0, 130, 0); _set_dimmer(fix, 45)
                print("[LIGHTING] Stage pass pulse complete.")

    # --- Final win pulse (ePar bright green) ---
    if _final_win_active:
        if now - _final_win_last_ms >= 300:
            _final_win_on = not _final_win_on
            if _final_win_on:
                for fix in PASS_FIXTURES:
                    _set_colour(fix, 0, 255, 0); _set_dimmer(fix, 95)
            else:
                for fix in PASS_FIXTURES:
                    _set_colour(fix, 0, 100, 0); _set_dimmer(fix, 38)
            _final_win_step    += 1
            _final_win_last_ms  = now
            if _final_win_step >= 12:
                _final_win_active = False
                for fix in PASS_FIXTURES:
                    _set_colour(fix, 0, 160, 0); _set_dimmer(fix, 65)
                print("[LIGHTING] Final win pulse complete.")