# lighting.py
# Handles all GMA3 OSC lighting control
#
# ─────────────────────────────────────────────────────────────────
# FIXTURE OWNERSHIP MAP:
#
#  GMA3 SEQUENCES (never touch these fixtures in Python):
#    "spotlightE"      → spotlights, fired once at init, off at game close
#    "Player Position" → fired at init, OFF when thumbsup check begins
#    "mainfacelights"  → fired at init, OFF when thumbsup check begins
#    "goboE"           → fired at tutorial start, owns Fixture 701, 703, 802, 803
#    "gameseqE"        → fired at tutorial start, owns Fixture 701, 703, 802, 803
#
#  PYTHON-CONTROLLED FIXTURES ONLY:
#    Stage pass lights:  ePar 702, 801, 301, 401
#    Free effects:       MagicBlade 704, 804
#
#  ALWAYS OFF (never touched):
#    Everything else not listed above
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
SPOTLIGHT_SEQ       = "spotlightE"       # Fired once at init — stays on until game close
PLAYER_POS_SEQ      = "Player Position"  # Fired at init — off when thumbsup check begins
FACE_LIGHTS_SEQ     = "mainfacelights"   # Fired at init — off when thumbsup check begins
GOBO_SEQ            = "goboE"            # Fired at tutorial start — owns 701, 703, 802, 803
GAMESEQ_SEQ         = "gameseqE"         # Fired at tutorial start — owns 701, 703, 802, 803
BOSS_SEQ            = "BOSSMAN"          # Fired once by on_boss_sequence()

# =================================================================
# === PYTHON-CONTROLLED FIXTURE GROUPS ===
# =================================================================

# Stage pass lights — ePars, used ONLY for win effects
EPAR_PASS = [
    "Fixture 702", "Fixture 801",
    "Fixture 301", "Fixture 401"
]

# Free effect fixtures — MagicBlade, used for ambient/decoy/effects
MAGICBLADE = ["Fixture 704", "Fixture 804"]

# All python-controlled fixtures combined (for game close)
ALL_PYTHON_FIXTURES = EPAR_PASS + MAGICBLADE

# =================================================================
# === TIMING CONSTANTS ===
# =================================================================
DECOY_FLASH_DURATION_MS = 350
STAGE_WIN_PULSE_COUNT   = 4
STAGE_WIN_PULSE_MS      = 200
MAGICBLADE_STEP_MS      = 400   # MagicBlade ambient pulse during gameplay

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

_magicblade_pulse_active = False
_magicblade_pulse_on     = False
_magicblade_pulse_ms     = 0

_boss_triggered          = False
_player_pos_on           = False   # Tracks whether Player Position + mainfacelights are on


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


def _stop_all_effects():
    """Resets all effect flags. Does NOT touch sequences — call sequence
    off commands explicitly where needed."""
    global _stage_win_active, _final_win_active
    global _decoy_flash_active, _magicblade_pulse_active

    _stage_win_active        = False
    _final_win_active        = False
    _decoy_flash_active      = False
    _magicblade_pulse_active = False


# =================================================================
# === ATMOSPHERE HELPERS ===
# =================================================================
def _set_magicblade_spooky():
    """MagicBlade ambient — dark rust during gameplay."""
    for fix in MAGICBLADE:
        _set_colour(fix, 80, 15, 5)
        _set_dimmer(fix, 30)


def _set_magicblade_white():
    """MagicBlade full white — for thumbsup check."""
    for fix in MAGICBLADE:
        _set_colour(fix, 255, 255, 255)
        _set_dimmer(fix, 70)


def _set_epar_pass_off():
    """Turn off all stage pass ePars."""
    for fix in EPAR_PASS:
        _set_dimmer(fix, 0)


# =================================================================
# === PUBLIC API ===
# =================================================================
def init():
    """
    Call ONCE after camera is ready.
    - Fires spotlightE (stays on until game close)
    - Fires Player Position and mainfacelights (on until thumbsup check)
    - Sets MagicBlade to spooky
    - ePar pass lights start off
    """
    global _boss_triggered, _player_pos_on

    _stop_all_effects()
    _boss_triggered  = False
    _player_pos_on   = True

    # GMA3 sequences
    _send(f'Go Sequence "{SPOTLIGHT_SEQ}" Cue 1')
    _send(f'Go Sequence "{PLAYER_POS_SEQ}" Cue 1')
    _send(f'Go Sequence "{FACE_LIGHTS_SEQ}" Cue 1')

    # Python fixtures
    _set_magicblade_spooky()
    _set_epar_pass_off()

    print(f"[LIGHTING] Initialised — '{SPOTLIGHT_SEQ}', '{PLAYER_POS_SEQ}', '{FACE_LIGHTS_SEQ}' ON.")


def on_tutorial_start():
    """
    Tutorial begins or new stage starts.
    - Fires goboE and gameseqE (own fixtures 701, 703, 802, 803 — never touched here)
    - MagicBlade starts ambient pulse
    - ePar pass lights off (not yet earned)
    """
    global _magicblade_pulse_active, _magicblade_pulse_ms, _magicblade_pulse_on

    _stop_all_effects()

    # Fire game sequences
    _send(f'Go Sequence "{GOBO_SEQ}" Cue 1')
    _send(f'Go Sequence "{GAMESEQ_SEQ}" Cue 1')

    # MagicBlade ambient pulse during gameplay
    _magicblade_pulse_active = True
    _magicblade_pulse_on     = True
    _magicblade_pulse_ms     = pygame.time.get_ticks()
    _set_magicblade_spooky()

    # ePar pass lights off
    _set_epar_pass_off()

    print(f"[LIGHTING] Tutorial started — '{GOBO_SEQ}' + '{GAMESEQ_SEQ}' ON, MagicBlade pulsing.")


def on_thumbsup_check():
    """
    'o' gesture / PHASE_INSTRUCT begins.
    - Turns OFF Player Position and mainfacelights
    - Turns OFF goboE and gameseqE
    - MagicBlade goes full white
    - ePar pass lights off
    """
    global _player_pos_on, _magicblade_pulse_active

    _stop_all_effects()
    _magicblade_pulse_active = False
    _player_pos_on           = False

    # Turn off intro + game sequences
    _send(f'Off Sequence "{PLAYER_POS_SEQ}"')
    _send(f'Off Sequence "{FACE_LIGHTS_SEQ}"')
    _send(f'Off Sequence "{GOBO_SEQ}"')
    _send(f'Off Sequence "{GAMESEQ_SEQ}"')

    # MagicBlade white
    _set_magicblade_white()

    # ePar pass lights off
    _set_epar_pass_off()

    print(f"[LIGHTING] Thumbs up check — '{PLAYER_POS_SEQ}' + '{FACE_LIGHTS_SEQ}' OFF, full white.")


def on_thumbsup_accepted():
    """
    Gesture accepted. Restores spooky MagicBlade.
    goboE and gameseqE will be fired again by on_tutorial_start()
    when PHASE_PREPARE ends and gameplay begins.
    """
    global _magicblade_pulse_active

    _stop_all_effects()
    _magicblade_pulse_active = False

    _set_magicblade_spooky()
    _set_epar_pass_off()

    print("[LIGHTING] Thumbs up accepted — spooky MagicBlade restored.")


def on_decoy_hit():
    """Player hits a decoy. MagicBlade slams red. update() restores after flash."""
    global _decoy_flash_active, _decoy_flash_trigger_ms

    if _decoy_flash_active:
        return

    _decoy_flash_active     = True
    _decoy_flash_trigger_ms = pygame.time.get_ticks()

    for fix in MAGICBLADE:
        _set_colour(fix, 220, 0, 0)
        _set_dimmer(fix, 100)

    print("[LIGHTING] DECOY HIT — MagicBlade red flash!")


def on_stage_win(stage: int):
    """
    Stage 1 or 2 cleared.
    ePar pass lights flash green. MagicBlade goes gold.
    goboE and gameseqE stay running — not touched.
    """
    global _stage_win_active, _stage_win_step, _stage_win_on, _stage_win_last_ms
    global _magicblade_pulse_active

    _stop_all_effects()
    _magicblade_pulse_active = False

    # ePar pass — green flash
    for fix in EPAR_PASS:
        _set_colour(fix, 0, 200, 0)
        _set_dimmer(fix, 80)

    # MagicBlade — gold
    for fix in MAGICBLADE:
        _set_colour(fix, 160, 120, 0)
        _set_dimmer(fix, 75)

    _stage_win_active  = True
    _stage_win_step    = 0
    _stage_win_on      = True
    _stage_win_last_ms = pygame.time.get_ticks()

    print(f"[LIGHTING] Stage {stage} passed — ePar green, MagicBlade gold.")


def on_win():
    """
    Stage 3 cleared — final win.
    ePar pass lights bright gold. MagicBlade bright amber pulse.
    goboE and gameseqE stopped.
    """
    global _final_win_active, _final_win_step, _final_win_on, _final_win_last_ms
    global _magicblade_pulse_active

    _stop_all_effects()
    _magicblade_pulse_active = False

    # Stop game sequences
    _send(f'Off Sequence "{GOBO_SEQ}"')
    _send(f'Off Sequence "{GAMESEQ_SEQ}"')

    # ePar pass — bright gold
    for fix in EPAR_PASS:
        _set_colour(fix, 220, 160, 0)
        _set_dimmer(fix, 100)

    # MagicBlade — bright amber
    for fix in MAGICBLADE:
        _set_colour(fix, 200, 130, 0)
        _set_dimmer(fix, 85)

    _final_win_active  = True
    _final_win_step    = 0
    _final_win_on      = True
    _final_win_last_ms = pygame.time.get_ticks()

    print("[LIGHTING] FINAL WIN — ePar gold, MagicBlade amber pulse!")


def on_boss_sequence():
    """
    Stage 3 boss trigger.
    Blacks out python fixtures, stops game sequences, fires BOSSMAN.
    """
    global _boss_triggered, _magicblade_pulse_active

    if _boss_triggered:
        return
    _boss_triggered          = True
    _magicblade_pulse_active = False

    _stop_all_effects()

    # Stop game sequences
    _send(f'Off Sequence "{GOBO_SEQ}"')
    _send(f'Off Sequence "{GAMESEQ_SEQ}"')
    _send(f'Off Sequence "{SPOTLIGHT_SEQ}"')

    # Black out python fixtures
    for fix in ALL_PYTHON_FIXTURES:
        _set_dimmer(fix, 0)

    # Fire boss sequence
    _send(f'Go Sequence "{BOSS_SEQ}" Cue 1')

    print(f"[LIGHTING] BOSS SEQUENCE — all game lights off, '{BOSS_SEQ}' fired.")


def on_game_restart():
    """K_r restart. Clears all effects, re-arms boss trigger, restores spooky MagicBlade."""
    global _boss_triggered, _magicblade_pulse_active

    _stop_all_effects()
    _boss_triggered          = False
    _magicblade_pulse_active = False

    # Stop game sequences
    _send(f'Off Sequence "{GOBO_SEQ}"')
    _send(f'Off Sequence "{GAMESEQ_SEQ}"')

    # Restore python fixtures
    _set_magicblade_spooky()
    _set_epar_pass_off()

    print("[LIGHTING] Restarted — spooky restored, boss trigger re-armed.")


def on_game_close():
    """Game exits. Stops all sequences and turns off every python-controlled fixture."""
    _send(f'Off Sequence "{SPOTLIGHT_SEQ}"')
    _send(f'Off Sequence "{PLAYER_POS_SEQ}"')
    _send(f'Off Sequence "{FACE_LIGHTS_SEQ}"')
    _send(f'Off Sequence "{GOBO_SEQ}"')
    _send(f'Off Sequence "{GAMESEQ_SEQ}"')
    _send(f'Off Sequence "{BOSS_SEQ}"')

    for fix in ALL_PYTHON_FIXTURES:
        _send(f"{fix} At 0")

    print("[LIGHTING] Game closed — all lights off.")


def update():
    """
    Call EVERY FRAME.
    Handles:
      - Decoy hit MagicBlade restore
      - MagicBlade ambient pulse during gameplay
      - Stage win ePar green pulse
      - Final win amber gold pulse
    """
    global _decoy_flash_active
    global _stage_win_active, _stage_win_step, _stage_win_on, _stage_win_last_ms
    global _final_win_active, _final_win_step, _final_win_on, _final_win_last_ms
    global _magicblade_pulse_active, _magicblade_pulse_on, _magicblade_pulse_ms

    now = pygame.time.get_ticks()

    # --- Decoy hit restore ---
    if _decoy_flash_active:
        if now - _decoy_flash_trigger_ms > DECOY_FLASH_DURATION_MS:
            _set_magicblade_spooky()
            _decoy_flash_active = False
            print("[LIGHTING] Decoy flash over — MagicBlade restored.")

    # --- MagicBlade ambient pulse during gameplay ---
    if _magicblade_pulse_active and not _decoy_flash_active:
        if now - _magicblade_pulse_ms >= MAGICBLADE_STEP_MS:
            _magicblade_pulse_on = not _magicblade_pulse_on
            if _magicblade_pulse_on:
                for fix in MAGICBLADE:
                    _set_colour(fix, 90, 20, 5)
                    _set_dimmer(fix, 40)
            else:
                for fix in MAGICBLADE:
                    _set_colour(fix, 50, 10, 2)
                    _set_dimmer(fix, 18)
            _magicblade_pulse_ms = now

    # --- Stage win ePar green pulse ---
    if _stage_win_active:
        if now - _stage_win_last_ms >= STAGE_WIN_PULSE_MS:
            _stage_win_on = not _stage_win_on
            if _stage_win_on:
                for fix in EPAR_PASS:
                    _set_colour(fix, 0, 200, 0)
                    _set_dimmer(fix, 80)
                for fix in MAGICBLADE:
                    _set_colour(fix, 160, 120, 0)
                    _set_dimmer(fix, 75)
            else:
                for fix in EPAR_PASS:
                    _set_colour(fix, 0, 80, 0)
                    _set_dimmer(fix, 25)
                for fix in MAGICBLADE:
                    _set_colour(fix, 70, 50, 0)
                    _set_dimmer(fix, 28)

            _stage_win_step    += 1
            _stage_win_last_ms  = now

            if _stage_win_step >= STAGE_WIN_PULSE_COUNT * 2:
                _stage_win_active = False
                for fix in EPAR_PASS:
                    _set_colour(fix, 0, 120, 0)
                    _set_dimmer(fix, 40)
                for fix in MAGICBLADE:
                    _set_colour(fix, 100, 70, 0)
                    _set_dimmer(fix, 40)
                print("[LIGHTING] Stage win pulse complete — holding green.")

    # --- Final win amber gold pulse ---
    if _final_win_active:
        if now - _final_win_last_ms >= 300:
            _final_win_on = not _final_win_on
            if _final_win_on:
                for fix in EPAR_PASS:
                    _set_colour(fix, 220, 160, 0)
                    _set_dimmer(fix, 100)
                for fix in MAGICBLADE:
                    _set_colour(fix, 200, 130, 0)
                    _set_dimmer(fix, 85)
            else:
                for fix in EPAR_PASS:
                    _set_colour(fix, 100, 70, 0)
                    _set_dimmer(fix, 40)
                for fix in MAGICBLADE:
                    _set_colour(fix, 90, 55, 0)
                    _set_dimmer(fix, 35)

            _final_win_step    += 1
            _final_win_last_ms  = now

            if _final_win_step >= 12:
                _final_win_active = False
                for fix in EPAR_PASS:
                    _set_colour(fix, 160, 110, 0)
                    _set_dimmer(fix, 70)
                for fix in MAGICBLADE:
                    _set_colour(fix, 150, 95, 0)
                    _set_dimmer(fix, 65)
                print("[LIGHTING] Final win pulse complete — holding amber.")