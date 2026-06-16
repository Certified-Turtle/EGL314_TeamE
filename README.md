# EGL314
## Whack-A-Ghost OpenCV + MediaPipe Game (POC)  
An interactive game developed in python that integrates OpenCV and Mediapipe (Real time hand/colour tracking), GrandMA3 lighting fixtures and laptop speakers via L-ISA and Reaper.

---


## Setup
---
## 1. Create Conda environment
The Conda environment acts as a dedicated workshop for our 'Whack-a-Ghost' game, ensuring that the specific versions of OpenCV, MediaPipe, and other tools you need are kept isolated so they don't crash or conflict with other projects on your computer.

### Install this in your terminal
```bash
conda create --name <env_name> python=3.10.0
conda activate <env_name>
```
---
## 2. Installing your dependencies
Dependencies are like pre-manufactured parts—like circuit boards or sensors—that you'd buy from a hardware store instead of building them from scratch, allowing our team to focus on designing the game logic rather than reinventing the fundamental tools for vision and input.

## What each dependency does:
| Dependency | Role in the game |
| :--- | :--- |
| `opencv-python` | Handles video capture from your webcam and detects your hand or, in this case colour. |
| `mediapipe` | Detects your hand landmarks in real-time. |
| `numpy` | Performs high-speed math to calculate distances/coordinates. |
| `pyautogui` | Simulates mouse/keyboard actions (e.g., "clicking" on a ghost). |
| `pynput` | Monitors keyboard/mouse input if you need custom hotkeys. |
| `pygrabber` | It helps your computer see all the cameras plugged into it, so you can pick the right one for your game, eg: you have a built-in webcam and a external usb webcam connected to your computer. |
| `python-osc` | Enables communication with other software or hardware via OSC protocols. |

### Create a text file and name it requirements.txt and paste in the following:
```bash
opencv-python
mediapipe==0.10.9
pyautogui
pynput
numpy
pygrabber
python-osc==1.8.1
```
### Install this in your terminal after creating requirements.txt:
``` bash
pip install -r requirements.txt
```

## Game Files
| File | Description |
| :--- | :--- |
| `addons.py` | Handles secondary mechanics: Gesture loading bars, decoy logic, difficulty ramping. |
| `audio.py` | Bridges the game to REAPER via Open Sound Control (OSC) to trigger sounds and transport controls. |
| `config.py` | The central hub where the game's settings, such as screen dimensions, colour codes and difficulty levels are stored. |
| `designs.py` | The visual rendering engine; draws backgrounds, particles, character and UI elements. |
| `gameplay.py` | Manages core game rules: hit detection, movement intervals, scoring and entity states.|
| `lighting.py` | Acts as a DMX/GrandMA3 lighting controller, sending OSC commands for visual effects. |
| `main.py` | This file contains the main .py file that uses each .py file to create the game. |
| `opencv.py` | Processes webcam frames, handles colour tracking and evaluates hand gesture geometry |
| `oscserver.py` | The "Central Router"; receives OSC from the game and forwards it to Audio/Lighting/Spatial systems. |
| `requirements.txt` | This file contains the dependencies mentioned earlier. |
| `restart_quit.py` | Handles end-game state resets and renders the game-over result screen. |
| `start_button.py`| Manages the interaction logic for the game's startup menu. |
| `thumbsup.csv` | Originally meant for thumbs up gestures but configured to recognise an OK sign for easier hand landmark recognition. |
| `tutorial.py` | Renders the instructional and tutorial logic for the game's startup menu | 
| `webcam_test.py`| A standalone tool to verify webcam connectivity. |


 ### [Click here to view the README for each .py file](Documentation/)

## What you'll need:
1. Webcam (Built-in/ external)
2. Laptop monitor/ External monitor
3. A bright green object.
