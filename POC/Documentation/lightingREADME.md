# lighting.py README

---

This code controls the lighting effects for the "Whack-a-Ghost" game. While `main.py` runs the game logic, `lighting.py` only handles sending commands over the network to the GMA3 lighting console, so the room lights react to what's happening in the game.

We start off with importing the following libraries:

```bash
import pygame
from pythonosc import udp_client
```

### What each library does:

| Library | Function |
| :--- | :--- |
| `import pygame` | Used only for its internal clock, `pygame.time.get_ticks()`. This lets the code track how much time has passed, so it can time things like a 250ms lightning flash or a pulsing win effect. |
| `from pythonosc import udp_client` | Sends short text commands over the network to the GMA3 console, which is the system that actually controls the physical lights. |

## Section 1: Connection Address

```bash
GMA3_IP   = "192.168.254.252"
GMA3_PORT = 8000
GMA3_ADDR = "/gma3/cmd"
```

This is the network address of the lighting console. Every command sent by this file goes to this IP, port, and OSC channel. If the console moves to a different machine, this is the only place that needs to change.

## Section 2: Fixture Assignments

```bash
SPOTLIGHT_FIXTURE   = "Fixture 501"
FLASH_FIXTURE       = "Fixture 503"
WIN_PULSE_FIXTURE   = "Fixture 502"
WIN_SWEEP_FIXTURE   = "Fixture 504"
LOSE_WASH_FIXTURE   = "Fixture 503"
```

These constants map each fixture number to a job, so the rest of the code can refer to fixtures by role instead of by number.

| Fixture | Role |
| :--- | :--- |
| Fixture 501 (ePar 180) | Constant white spotlight kept on the player during gameplay. |
| Fixture 502 (MiniPanelFX) | Pulses white when the player wins. |
| Fixture 503 (Mistral-TC) | Flashes white for in-game lightning, and turns red when the player loses. |
| Fixture 504 (MagicBlade FX) | Sweeps to gold and holds it after a win. |

The file also defines dimmer levels (e.g. `SPOTLIGHT_DIMMER = 100`), timing values (e.g. `FLASH_DURATION_MS = 250`), and valid ranges for pan, tilt, and RGB colour (e.g. `RED_MIN, RED_MAX = 0, 255`), so no command can send a value the hardware can't handle.

## Section 3: Internal State Variables

```bash
_flash_active      = False
_win_active        = False
_win_pulse_step    = 0
_win_pulse_on      = False
_win_last_pulse_ms = 0
_lose_active       = False
```

These variables track the current status of each effect across frames, since effects like a win pulse or lightning flash play out over time rather than instantly. The leading underscore marks them as private — meant to be used only within this file.

## Section 4: Low-Level OSC Helpers

```bash
def _send(message): ...
def _gma3_value(value, v_min, v_max): ...
def _set_attribute(fixture, attribute, value, v_min, v_max): ...
def _set_colour(fixture, r, g, b): ...
```

These functions handle sending commands and aren't called directly by `main.py`.

| Function | Purpose |
| :--- | :--- |
| `_send()` | Opens a connection to the GMA3 console and sends one raw command. If the network fails, it catches the error and prints a warning instead of crashing the game. |
| `_gma3_value()` | Converts a normal value (e.g. a colour from 0–255) into the 0–65535 scale the GMA3 console expects. |
| `_set_attribute()` | Selects a fixture and sets one attribute (like brightness or pan) to a converted value. |
| `_set_colour()` | Calls `_set_attribute()` three times to set red, green, and blue in one line instead of three. |

## Section 5: Public API

These are the functions `main.py` is meant to call directly.

| Function | When it's called | What it does |
| :--- | :--- | :--- |
| `init()` | Once, at game startup. | Clears all effect fixtures to off and turns the spotlight on. |
| `on_game_restart()` | When the player presses `K_r` on the game-over screen. | Clears any lightning, win, or lose effects and restores the spotlight. |
| `on_lightning_flash()` | Once, when in-game lightning triggers. | Flashes Fixture 503 white and starts a timer to know when to turn it off. |
| `on_win()` | Once, when the game ends with a good score. | Starts the gold colour sweep and begins the white pulse pattern. |
| `on_lose()` | Once, when the game ends with a bad score. | Dims the spotlight and washes Fixture 503 in red. |
| `update()` | Every frame, in the main game loop. | Checks timers to turn off the lightning flash and advance the win-pulse animation. |

## Section 6: The `update()` Function

```bash
def update():
    now = pygame.time.get_ticks()
    if _flash_active:
        if now - _flash_trigger_ms > FLASH_DURATION_MS:
            ...
    if _win_active:
        if now - _win_last_pulse_ms >= WIN_PULSE_MS:
            ...
```

Like the main `while True` loop in `main.py`, this function is called roughly 60 times per second. Each call checks whether enough time has passed for the current effect to move to its next step. This lets the lightning flash turn off after exactly 250ms, or the win pulse blink a set number of times, without pausing the rest of the game.