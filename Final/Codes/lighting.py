# lighting.py
# Handles all GMA3 OSC lighting control
#
# ─────────────────────────────────────────────────────────────────
# GAME FLOW / FIXTURE OWNERSHIP MAP:
#
#  1. Script launches -> init() fires "Player Position" Cue 7 AND
#     "main face lights" together.
#
#  2. Team presses 'O' -> on_intro_transition() turns "Player Position"
#     and "main face lights" OFF and turns "spotlightE" ON. Both are
#     LOCKED off after this and can never turn on again this session
#     (until a restart).
#
#  3. Tutorial starts, then rounds 1-3 play -> "goboE" and "gameseqE"
#     fire together and run the whole time gameplay is active (paused
#     during the thumbs-up check, resumed once accepted). These two
#     sequences own Fixture 701 (Minipanel), 703 (Mistral), 802
#     (Minipanel), 803 (Mistral) ENTIRELY — this script never sends
#     direct colour/dimmer commands to those four fixtures, ever.
#
#     Meanwhile the ePars — Fixture 702, 801, 301, 401 — are reserved
#     as "passing stage" lights: they only light up for stage win/lose
#     and the final win/lose pulses, nothing else.
#
#     The two Magic Blades — Fixture 704 and 804 — are this script's
#     free-use fixtures for atmosphere/decoy-hit flashing, with one
#     constraint: they must always stay a reddish-pink hue. Only their
#     dimmer level changes, never their colour.
#
#  4. Round 3, 8th ghost hit -> trigger_boss_sequence() fires ONCE:
#       - Turns OFF only the lights THIS SCRIPT uses: "Player Position"
#         and "main face lights" (safety, in case somehow still on),
#         "spotlightE", "goboE", "gameseqE", the ePars, and the Magic
#         Blades. Fixture 701/703/802/803 are never touched directly —
#         stopping goboE/gameseqE is what takes them dark.
#       - Fires "BOSSMAN", which stays on. BOSSMAN drives everything
#         itself from that point — this script sends nothing else.
#
#  5. Game exits -> on_game_close() intentionally does NOTHING, so
#     BOSSMAN (or whatever else is running) stays on after the process
#     ends.
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
PLAYER_POSITION_SEQ = "Player Position"   # Fired at Cue 7 on init(), off after 'O'
MAIN_FACE_SEQ       = "main face lights"  # Pre-game explanation, off after 'O'
SPOTLIGHT_SEQ       = "spotlightE"        # Fired once via 'O', stays on until boss trigger/close
GOBO_SEQ            = "goboE"             # Runs alongside gameseqE during active gameplay
GAMESEQ_SEQ         = "gameseqE"          # Runs alongside goboE during active gameplay
BOSS_SEQ            = "BOSS MAN"           # Fired once at the endgame trigger — self-contained

# =================================================================
# === FIXTURE GROUPS ===
# =================================================================
# Owned ENTIRELY by goboE/gameseqE — this script only ever fires or
# stops those two sequences. No direct _set_colour/_set_dimmer calls
# are ever made against these fixtures.
GAMESEQ_OWNED_FIXTURES = ["Fixture 701", "Fixture 703", "Fixture 802", "Fixture 803"]

# ePars — "passing stage" lights. Reserved for stage win/lose and the
# final win/lose pulses only.
EPAR_FIXTURES = ["Fixture 702", "Fixture 801", "Fixture 301", "Fixture 401"]

# Magic Blades — free-use fixtures for atmosphere/decoy flashing.
# Colour must always stay reddish-pink; only dimmer level changes.
MAGIC_BLADE_FIXTURES = ["Fixture 704", "Fixture 804"]
REDDISH_PINK = (220, 20, 90)

# =================================================================
# === TIMING CONSTANTS ===
# =================================================================
DECOY_FLASH_DURATION_MS     = 350
STAGE_WIN_PULSE_COUNT       = 4
STAGE_WIN_PULSE_MS          = 200
STAGE_LOSE_PULSE_MS         = 500
COUNTDOWN_FLASH_DURATION_MS = 120
GAMESEQ_PULSE_STEP_MS       = 350

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

# Drives the Magic Blades' gentle alternating pulse while gameplay is active
_gameseq_pulse_active     = False
_gameseq_pulse_step       = 0
_gameseq_pulse_last_ms    = 0

_gameseq_active           = False   # Whether goboE + gameseqE are currently running

_main_face_active         = False   # Tracks whether "main face lights" is currently on
_player_position_active   = False   # Tracks whether "Player Position" is currently on
_intro_transitioned       = False   # Once True, main face/Player Position can NEVER turn on again

_boss_triggered           = False   # One-time guard - boss trigger only ever fires once per game


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
    _set_attribute(fixture, "ColorRGB_R", r, 0, 255)
    _set_attribute(fixture, "ColorRGB_G", g, 0, 255)
    _set_attribute(fixture, "ColorRGB_B", b, 0, 255)


def _set_dimmer(fixture: str, percent: int):
    _send(f"{fixture} At {percent}")


def _set_magic_blades(dimmer: int):
    """Sets both Magic Blades to the fixed reddish-pink hue at the given
    dimmer level. This is the ONLY way this script should touch Fixture
    704/804's colour — always REDDISH_PINK, only dimmer varies."""
    for fix in MAGIC_BLADE_FIXTURES:
        _set_colour(fix, *REDDISH_PINK)
        _set_dimmer(fix, dimmer)


def _start_gameseq_lighting():
    """Fires goboE + gameseqE together and starts the Magic Blade pulse.
    Fixture 701/703/802/803 are owned entirely by these two sequences
    from here on — never touched directly by this script."""
    global _gameseq_active, _gameseq_pulse_active, _gameseq_pulse_step, _gameseq_pulse_last_ms
    if _gameseq_active:
        return
    _gameseq_active = True
    _send(f'Go Sequence "{GOBO_SEQ}" Cue 1')
    _send(f'Go Sequence "{GAMESEQ_SEQ}" Cue 1')

    _gameseq_pulse_active  = True
    _gameseq_pulse_step    = 0
    _gameseq_pulse_last_ms = pygame.time.get_ticks()
    _set_magic_blades(45)  # baseline reddish-pink idle level
    print(f"[LIGHTING] '{GOBO_SEQ}' + '{GAMESEQ_SEQ}' ON, Magic Blade pulse started.")


def _stop_gameseq_lighting():
    global _gameseq_active, _gameseq_pulse_active
    if not _gameseq_active:
        return
    _gameseq_active = False
    _gameseq_pulse_active = False
    _send(f'Off Sequence "{GOBO_SEQ}"')
    _send(f'Off Sequence "{GAMESEQ_SEQ}"')
    print(f"[LIGHTING] '{GOBO_SEQ}' + '{GAMESEQ_SEQ}' OFF, Magic Blade pulse stopped.")


def _stop_all_effects():
    """Resets every routine effect flag. Does NOT touch the boss trigger state."""
    global _stage_win_active, _stage_lose_active
    global _final_win_active, _final_lose_active
    global _decoy_flash_active, _countdown_triggered
    global _in_countdown, _countdown_flash_active, _last_countdown_second
    global _gameseq_pulse_active

    _stage_win_active       = False
    _stage_lose_active      = False
    _final_win_active       = False
    _final_lose_active      = False
    _decoy_flash_active     = False
    _countdown_triggered    = False
    _in_countdown           = False
    _countdown_flash_active = False
    _last_countdown_second  = -1

    _stop_gameseq_lighting()


# =================================================================
# === PUBLIC API ===
# =================================================================
def init():
    """
    Call ONCE at game startup.
    - Fires "Player Position" Cue 7 AND "main face lights" together
    - Resets all effect state, including the boss trigger guard for a fresh session
    - Does NOT start goboE/gameseqE or the Magic Blade pulse yet - that
      begins when the tutorial/gameplay starts
    """
    global _main_face_active, _player_position_active, _intro_transitioned, _boss_triggered

    _stop_all_effects()
    _intro_transitioned = False
    _boss_triggered      = False

    _send(f'Go Sequence "{PLAYER_POSITION_SEQ}" Cue 7')
    _player_position_active = True

    _send(f'Go Sequence "{MAIN_FACE_SEQ}" Cue 1')
    _main_face_active = True

    print(f"[LIGHTING] '{PLAYER_POSITION_SEQ}' Cue 7 + '{MAIN_FACE_SEQ}' fired for the pre-game explanation.")
    print("[LIGHTING] Initialised.")


def on_intro_transition():
    """
    Call ONCE, when the team presses 'O' after explaining the game.
    Turns OFF "Player Position" and "main face lights", turns ON "spotlightE".
    Safe to call more than once - after the first call, both are locked
    off and calling this again does nothing.
    """
    global _main_face_active, _player_position_active, _intro_transitioned

    if _intro_transitioned:
        return

    _intro_transitioned = True

    if _player_position_active:
        _send(f'Off Sequence "{PLAYER_POSITION_SEQ}"')
        _player_position_active = False

    if _main_face_active:
        _send(f'Off Sequence "{MAIN_FACE_SEQ}"')
        _main_face_active = False

    _send(f'Go Sequence "{SPOTLIGHT_SEQ}" Cue 1')
    print(f"[LIGHTING] '{PLAYER_POSITION_SEQ}' + '{MAIN_FACE_SEQ}' OFF, '{SPOTLIGHT_SEQ}' ON - locked for rest of game.")


def on_tutorial_start():
    """Tutorial begins or new stage starts. Starts goboE + gameseqE and the Magic Blade pulse."""
    _stop_all_effects()
    _start_gameseq_lighting()
    print("[LIGHTING] Tutorial/stage started.")


def on_thumbsup_check():
    """PHASE_INSTRUCT starts. goboE/gameseqE and the Magic Blade pulse pause.
    (Magic Blades stay at their current reddish-pink level rather than
    switching to white — their colour is never allowed to change.)"""
    _stop_gameseq_lighting()
    print("[LIGHTING] Thumbs up check - gameseq paused.")


def on_thumbsup_accepted():
    """Thumbs up registered. goboE/gameseqE and the Magic Blade pulse resume."""
    _stop_all_effects()
    _start_gameseq_lighting()
    print("[LIGHTING] Thumbs up accepted.")


def on_decoy_hit():
    """Player hits a decoy. Reddish-pink brightness spike on the Magic Blades only —
    the only fixtures this script is free to flash."""
    global _decoy_flash_active, _decoy_flash_trigger_ms

    if _decoy_flash_active:
        return

    _decoy_flash_active     = True
    _decoy_flash_trigger_ms = pygame.time.get_ticks()

    _set_magic_blades(95)

    print("[LIGHTING] DECOY HIT - Magic Blade reddish-pink flash!")


def on_countdown(time_left: int):
    """Currently unused by main.py (stages are score-based, not timer-based),
    kept for API compatibility. If ever called: pauses goboE/gameseqE and
    brightens the Magic Blades, still staying reddish-pink."""
    global _countdown_triggered, _in_countdown
    global _countdown_flash_active, _countdown_flash_ms, _last_countdown_second

    if not _countdown_triggered and time_left <= 10:
        _countdown_triggered = True
        _in_countdown        = True
        _stop_gameseq_lighting()
        _set_magic_blades(60)
        print("[LIGHTING] Countdown - Magic Blades brightened.")

    if _in_countdown and 1 <= time_left <= 10:
        if time_left != _last_countdown_second:
            _last_countdown_second  = time_left
            _countdown_flash_active = True
            _countdown_flash_ms     = pygame.time.get_ticks()
            _set_magic_blades(100)
            print(f"[LIGHTING] Countdown flash - {time_left}s!")


def on_stage_win(stage: int):
    """Stage 1 or 2 cleared. Gold pulse on the ePars ONLY."""
    global _stage_win_active, _stage_win_step, _stage_win_on, _stage_win_last_ms

    _stop_all_effects()

    for fix in EPAR_FIXTURES:
        _set_colour(fix, 160, 120, 0); _set_dimmer(fix, 75)

    _stage_win_active  = True
    _stage_win_step    = 0
    _stage_win_on      = True
    _stage_win_last_ms = pygame.time.get_ticks()
    print(f"[LIGHTING] Stage {stage} cleared - gold pulse.")


def on_stage_lose(stage: int):
    """Stage 1 or 2 failed. Dark red slow pulse on the ePars ONLY."""
    global _stage_lose_active, _stage_lose_on, _stage_lose_last_ms

    _stop_all_effects()

    for fix in EPAR_FIXTURES:
        _set_colour(fix, 90, 0, 0); _set_dimmer(fix, 38)

    _stage_lose_active  = True
    _stage_lose_on      = True
    _stage_lose_last_ms = pygame.time.get_ticks()
    print(f"[LIGHTING] Stage {stage} failed - dark red pulse.")


def on_win():
    """Final win after stage 3. Bright amber gold pulse on the ePars ONLY."""
    global _final_win_active, _final_win_step, _final_win_on, _final_win_last_ms

    _stop_all_effects()

    for fix in EPAR_FIXTURES:
        _set_colour(fix, 200, 130, 0); _set_dimmer(fix, 85)

    _final_win_active  = True
    _final_win_step    = 0
    _final_win_on      = True
    _final_win_last_ms = pygame.time.get_ticks()
    print("[LIGHTING] FINAL WIN - amber gold pulse!")


def on_lose():
    """Final lose after stage 3. Dark red heartbeat on the ePars ONLY."""
    global _final_lose_active, _final_lose_on, _final_lose_last_ms

    _stop_all_effects()

    for fix in EPAR_FIXTURES:
        _set_colour(fix, 90, 0, 0); _set_dimmer(fix, 32)

    _final_lose_active  = True
    _final_lose_on      = True
    _final_lose_last_ms = pygame.time.get_ticks()
    print("[LIGHTING] FINAL LOSE - doom heartbeat.")


def on_game_restart():
    """K_r restart. Returns to the pre-game state: clears routine effects,
    re-fires Player Position + main face lights, re-arms the intro-transition
    lock and the boss trigger."""
    global _boss_triggered, _intro_transitioned
    global _main_face_active, _player_position_active

    _stop_all_effects()
    _boss_triggered      = False
    _intro_transitioned  = False

    _send(f'Off Sequence "{SPOTLIGHT_SEQ}"')

    _send(f'Go Sequence "{PLAYER_POSITION_SEQ}" Cue 7')
    _player_position_active = True
    _send(f'Go Sequence "{MAIN_FACE_SEQ}" Cue 1')
    _main_face_active = True

    print("[LIGHTING] Restarted - Player Position + main face lights restored, boss trigger re-armed.")


def trigger_boss_sequence():
    """
    Call ONCE, when stage 3 hits its 8th ghost hit.
    Safe to call more than once - after the first call this does nothing.

    Turns off ONLY the lights this script uses (Player Position, main face
    lights, spotlightE, goboE, gameseqE, the ePars, the Magic Blades) -
    Fixture 701/703/802/803 are never touched directly, they just go dark
    when goboE/gameseqE stop. Then fires BOSSMAN, which stays on and
    handles everything itself from that point.
    """
    global _boss_triggered, _main_face_active, _player_position_active

    if _boss_triggered:
        return
    _boss_triggered = True

    # Turn off only the lights this script owns
    _stop_all_effects()

    if _player_position_active:
        _send(f'Off Sequence "{PLAYER_POSITION_SEQ}"')
        _player_position_active = False
    if _main_face_active:
        _send(f'Off Sequence "{MAIN_FACE_SEQ}"')
        _main_face_active = False
    _send(f'Off Sequence "{SPOTLIGHT_SEQ}"')

    for fix in EPAR_FIXTURES:
        _set_dimmer(fix, 0)
    _set_magic_blades(0)

    # BOSSMAN handles everything itself from here - just fire it and leave it on
    _send(f'Go Sequence "{BOSS_SEQ}" Cue 1')

    print(f"[LIGHTING] BOSS TRIGGER - script-owned lights off, '{BOSS_SEQ}' ON (self-contained from here).")


def on_game_close():
    """
    Called when the game exits.
    Intentionally does NOT turn anything off - BOSSMAN (and whatever else
    is running, including goboE/gameseqE if the game was closed mid-round)
    must persist after the game process ends.
    """
    print("[LIGHTING] Game closed - lights intentionally left as-is.")


def update():
    """
    Call EVERY FRAME.
    Handles:
      - Decoy hit restore (Magic Blades)
      - Countdown per-second flash cutoff (Magic Blades, currently unused)
      - Magic Blade gameseq pulse (alternates gently between the two blades)
      - Stage win/lose pulses (ePars)
      - Final win/lose pulses (ePars)
    """
    global _decoy_flash_active
    global _countdown_flash_active
    global _stage_win_active, _stage_win_step, _stage_win_on, _stage_win_last_ms
    global _stage_lose_active, _stage_lose_on, _stage_lose_last_ms
    global _final_win_active, _final_win_step, _final_win_on, _final_win_last_ms
    global _final_lose_active, _final_lose_on, _final_lose_last_ms
    global _gameseq_pulse_active, _gameseq_pulse_step, _gameseq_pulse_last_ms

    now = pygame.time.get_ticks()

    # --- Decoy hit restore (back to baseline reddish-pink idle level) ---
    if _decoy_flash_active:
        if now - _decoy_flash_trigger_ms > DECOY_FLASH_DURATION_MS:
            _set_magic_blades(45)
            _decoy_flash_active = False
            print("[LIGHTING] Decoy flash over.")

    # --- Countdown per-second flash cutoff (Magic Blades, currently unused) ---
    if _countdown_flash_active:
        if now - _countdown_flash_ms > COUNTDOWN_FLASH_DURATION_MS:
            _set_magic_blades(60)
            _countdown_flash_active = False

    # --- Magic Blade gameseq pulse: gentle alternating reddish-pink chase ---
    if _gameseq_pulse_active and not _decoy_flash_active:
        if now - _gameseq_pulse_last_ms >= GAMESEQ_PULSE_STEP_MS:
            _gameseq_pulse_step   = (_gameseq_pulse_step + 1) % 2
            _gameseq_pulse_last_ms = now
            lead_fix, lag_fix = (MAGIC_BLADE_FIXTURES if _gameseq_pulse_step == 0
                                  else list(reversed(MAGIC_BLADE_FIXTURES)))
            _set_colour(lead_fix, *REDDISH_PINK); _set_dimmer(lead_fix, 65)
            _set_colour(lag_fix, *REDDISH_PINK);  _set_dimmer(lag_fix, 30)

    # --- Stage win gold pulse (ePars) ---
    if _stage_win_active:
        if now - _stage_win_last_ms >= STAGE_WIN_PULSE_MS:
            _stage_win_on = not _stage_win_on
            if _stage_win_on:
                for fix in EPAR_FIXTURES:
                    _set_colour(fix, 160, 120, 0); _set_dimmer(fix, 75)
            else:
                for fix in EPAR_FIXTURES:
                    _set_colour(fix, 70, 50, 0);   _set_dimmer(fix, 28)
            _stage_win_step    += 1
            _stage_win_last_ms  = now
            if _stage_win_step >= STAGE_WIN_PULSE_COUNT * 2:
                _stage_win_active = False
                for fix in EPAR_FIXTURES:
                    _set_colour(fix, 100, 70, 0); _set_dimmer(fix, 40)
                print("[LIGHTING] Stage win pulse complete.")

    # --- Stage lose slow red pulse (ePars) ---
    if _stage_lose_active:
        if now - _stage_lose_last_ms >= STAGE_LOSE_PULSE_MS:
            _stage_lose_on = not _stage_lose_on
            dimmer = 55 if _stage_lose_on else 15
            for fix in EPAR_FIXTURES:
                _set_colour(fix, 100, 0, 0); _set_dimmer(fix, dimmer)
            _stage_lose_last_ms = now

    # --- Final win amber gold pulse (ePars) ---
    if _final_win_active:
        if now - _final_win_last_ms >= 300:
            _final_win_on = not _final_win_on
            if _final_win_on:
                for fix in EPAR_FIXTURES:
                    _set_colour(fix, 200, 130, 0); _set_dimmer(fix, 85)
            else:
                for fix in EPAR_FIXTURES:
                    _set_colour(fix, 100, 65, 0);  _set_dimmer(fix, 38)
            _final_win_step    += 1
            _final_win_last_ms  = now
            if _final_win_step >= 12:
                _final_win_active = False
                for fix in EPAR_FIXTURES:
                    _set_colour(fix, 160, 105, 0); _set_dimmer(fix, 65)
                print("[LIGHTING] Final win pulse complete.")

    # --- Final lose heartbeat (ePars) ---
    if _final_lose_active:
        if now - _final_lose_last_ms >= 700:
            _final_lose_on = not _final_lose_on
            dimmer = 55 if _final_lose_on else 12
            for fix in EPAR_FIXTURES:
                _set_colour(fix, 100, 0, 0); _set_dimmer(fix, dimmer)
            _final_lose_last_ms = now
