# EGL314
## Whack-A-Ghost OpenCV + MediaPipe Game (POC)  
A fun game developed in python that integrates OpenCV and Mediapipe (Real time hand/colour tracking), GrandMA3 lighting fixtures and wall mounted speakers.

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
| `addons.py` | |
| `audio.py` | |
| `config.py` | |
| `designs.py` | |
| `gameplay.py` | |
| `lighting.py` | |
| `main.py` | |
| `opencv.py` | |
| `oscserver.py` | |
| `requirements.txt` | |
| `restart_quit.py` | |
| `start_button.py`| |
| `tutorial.py` | |
| `webcam_test.py`| |


