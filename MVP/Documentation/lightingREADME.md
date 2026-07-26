# lighting.py README

---

This code controls the lighting effects for the ghost-hunting game. While `main.py` runs the game logic, `lighting.py` only handles sending commands over the network to the GMA3 lighting console, so the room lights react to what's happening in the game.

We start off with importing the following libraries:

```bash
import pygame
from pythonosc import udp_client
```

### What each library does:

| Library | Function |
| :--- | :--- |
| `import pygame` | Used only for its internal clock, `pygame.time.get_ticks()`. This lets the code track how much time has passed, so it can time things like a decoy-hit flash or a pulsing win effect. |
| `from pythonosc import udp_client` | Sends short text commands over the network to the GMA3 console, which is the system that actually controls the physical lights. |

## Section 1: GMA3 Sequences & Fixture Ownership

Rather than controlling every fixture attribute by hand, this file leans on two sequences programmed directly into the GMA3 console, and only reaches for individual fixture commands on the remaining fixtures it's responsible for.

```bash
SPOTLIGHT_SEQ = "spotlightE"
GOBO_SEQ      = "goboE"
```

| Owner | Fixtures | Behaviour |
| :--- | :--- | :--- |
| `spotlightE` sequence | MiniPanel 202, MiniPanel 302, MiniPanel 502, MagicBlade 304 | Fired **once** in `init()`. Stays on for the entire game session and is never touched again until `on_game_close()`. |
| `goboE` sequence | Mistral 103, 203, 503, 603, 703, 803 (all six Mistrals) | Wall-decoration sequence. Turned **on** whenever the round chase sequence starts, and **off** whenever it stops (countdown, stage win/lose, gesture check, restart, etc). This is the *only* thing in the file that ever touches a Mistral fixture. |
| This script directly | ePar 101, 201, 501, 601, 702, 801; MiniPanel 102, 602, 701, 802; MagicBlade 104, 204, 504, 604, 704, 804 | The "game sequence" fixtures — everything the atmosphere/effect functions below actually set colour and dimmer values on. |
| Always off | ePar 301, 401; MiniPanel 402; Mistral 303, 403; MagicBlade 404 | Never sent a single command by this file, at any point. |

There used to be a separate in-game lightning effect and a `LIGHTNING_SEQ`/`on_lightning_flash()` pair driving the 103/203/503/603 Mistrals directly — that's been removed. Those fixtures are now owned exclusively by `goboE`.

The file also defines timing constants (e.g. `DECOY_FLASH_DURATION_MS = 350`) and valid ranges for RGB colour (e.g. `RED_MIN, RED_MAX = 0, 255`), so no command can send a value the hardware can't handle.

## Section 2: Internal State Variables

```bash
_decoy_flash_active      = False
_stage_win_active        = False
_stage_lose_active       = False
_final_win_active        = False
_final_lose_active       = False
_countdown_flash_active  = False
_round_sequence_active   = False
_gobo_active              = False
```

These variables (and a handful of matching timer/step variables like `_stage_win_last_ms` or `_round_sequence_step`) track the current status of each effect across frames, since effects like a stage-win pulse or the round colour chase play out over time rather than instantly. `_gobo_active` specifically tracks whether the `goboE` sequence is currently running, so it's only ever started or stopped once rather than spammed every frame. The leading underscore marks all of these as private — meant to be used only within this file.

## Section 3: Low-Level OSC Helpers

```bash
def _send(message): ...
def _gma3_value(value, v_min, v_max): ...
def _set_attribute(fixture, attribute, value, v_min, v_max): ...
def _set_colour(fixture, r, g, b): ...
def _set_dimmer(fixture, percent): ...
def _set_group_colour(fixtures, r, g, b, dimmer): ...
def _start_gobo_sequence(): ...
def _stop_gobo_sequence(): ...
def _start_round_sequence(): ...
def _stop_all_effects(): ...
def _setup_spooky(): ...
def _setup_countdown(): ...
def _setup_thumbsup(): ...
```

These functions handle sending commands and setting up atmospheres, and aren't called directly by `main.py`.

| Function | Purpose |
| :--- | :--- |
| `_send()` | Opens a connection to the GMA3 console and sends one raw command. If the network fails, it catches the error and prints a warning instead of crashing the game. |
| `_gma3_value()` | Converts a normal value (e.g. a colour from 0–255) into the 0–65535 scale the GMA3 console expects. |
| `_set_attribute()` | Selects a fixture and sets one attribute (like brightness or colour) to a converted value. |
| `_set_colour()` | Calls `_set_attribute()` three times to set red, green, and blue in one line instead of three. |
| `_set_dimmer()` | Sets a single fixture's brightness directly (e.g. `"Fixture 101 At 45"`). |
| `_set_group_colour()` | Applies the same colour and dimmer to a whole list of fixtures in one call. |
| `_start_gobo_sequence()` / `_stop_gobo_sequence()` | Fire the `goboE` sequence on/off, guarded by `_gobo_active` so it's never re-triggered while already running (or stopped while already off). |
| `_start_round_sequence()` | Kicks off the round colour-chase timer and starts `goboE` alongside it. |
| `_stop_all_effects()` | Resets every effect's active flag back to `False` (win/lose pulses, countdown, decoy flash, round sequence) and stops `goboE` since the round sequence is ending. |
| `_setup_spooky()` / `_setup_countdown()` / `_setup_thumbsup()` | Push a fixed colour/dimmer look onto the game-sequence fixtures (ePar, MiniPanel, MagicBlade) for each atmosphere: dim red spooky ambience, blood-red countdown, and full white for the gesture-check screen. |

## Section 4: Public API

These are the functions `main.py` is meant to call directly.

| Function | When it's called | What it does |
| :--- | :--- | :--- |
| `init()` | Once, at game startup. | Fires `spotlightE` (stays on for the whole session) and sets the spooky atmosphere on the game-sequence fixtures. |
| `on_tutorial_start()` | Tutorial begins, or a new stage starts. | Resets effects, restores the spooky atmosphere, and starts the round chase sequence (which also starts `goboE`). |
| `on_thumbsup_check()` | The gesture-check screen begins. | Switches to full white on the game-sequence fixtures and pauses the round sequence (stopping `goboE`). |
| `on_thumbsup_accepted()` | The player's gesture is accepted. | Restores the spooky atmosphere and restarts the round sequence (and `goboE`). |
| `on_decoy_hit()` | The player hits a decoy. | Slams the game-sequence fixtures to a bright red for a short flash. |
| `on_countdown(time_left)` | Every frame during gameplay. | Switches to the blood-red countdown look once 10 seconds remain (stopping the round sequence and `goboE`), and flashes brighter on each new second. |
| `on_stage_win(stage)` | A stage (1 or 2) is cleared. | Starts a gold pulse on the game-sequence fixtures. |
| `on_stage_lose(stage)` | A stage (1 or 2) is failed. | Starts a slow dark-red pulse. |
| `on_win()` | The game ends with a passing final score. | Starts a bright amber-gold pulse. |
| `on_lose()` | The game ends with a failing final score. | Starts a dark red heartbeat pulse on MagicBlade. |
| `on_game_restart()` | The player presses `K_r` on the game-over screen. | Clears all effects and restores the spooky atmosphere. The spotlight sequence is left untouched — it keeps running. |
| `on_game_close()` | Once, when the game exits. | Stops both `spotlightE` and `goboE`, and turns off every fixture this file knows about — the only place spotlights are ever switched off. |
| `update()` | Every frame, in the main game loop. | Advances every timed effect below. |

## Section 5: The `update()` Function

```bash
def update():
    now = pygame.time.get_ticks()
    if _decoy_flash_active:
        if now - _decoy_flash_trigger_ms > DECOY_FLASH_DURATION_MS:
            ...
    if _round_sequence_active and not _decoy_flash_active:
        if now - _round_sequence_last_ms >= SEQUENCE_STEP_MS:
            ...
    if _stage_win_active:
        if now - _stage_win_last_ms >= STAGE_WIN_PULSE_MS:
            ...
```

Like the main `while True` loop in `main.py`, this function is called roughly 60 times per second. Each call checks whether enough time has passed for the current effect to move to its next step, without pausing the rest of the game. Specifically, `update()` is responsible for:

- **Decoy hit restore** — reverting back to spooky (or countdown red, if the timer's already inside the last 10 seconds) once the decoy flash duration has elapsed.
- **Countdown per-second flash cutoff** — dropping back down after each second's brighter flash.
- **Round chase sequence** — stepping through `ROUND_SEQUENCE` every `SEQUENCE_STEP_MS` to cycle the game-sequence fixtures through their colours.
- **Stage win / stage lose pulses** — alternating brightness a fixed number of times before settling on a held colour.
- **Final win / final lose pulses** — the same pattern, used for the end-of-game result.

Note that `goboE` itself isn't advanced here — it's a self-contained GMA3 sequence, so once it's told to go or stop (from `_start_round_sequence()` / `_stop_all_effects()` / `on_countdown()`), the console handles its own timing.