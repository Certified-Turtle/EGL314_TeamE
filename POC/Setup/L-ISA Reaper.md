# EGL314
## Setup for Reaper L-ISA loopMIDI 
Using Reaper for Audio tracks and L-ISA for surround sound

---

## 1. Install Reaper, L-ISA Controller and loopMIDI

### Click the links below to download software

Reaper: https://www.reaper.fm/download.php

L-ISA: https://www.l-acoustics.com/products/l-isa-controller/

loopMIDI: https://www.tobias-erichsen.de/software/loopmidi.html

---

## 2. Setting up loopMIDI
1. Enter `loopMIDI Port` name for MIDI port

![loopMIDI-named](https://github.com/Certified-Turtle/EGL314_TeamE/blob/main/POC/Setup/Diagram/loopMIDI_named.png)

2. Add the MIDI port

![loopMIDI-add](https://github.com/Certified-Turtle/EGL314_TeamE/blob/main/POC/Setup/Diagram/loopMIDI_add.png)


## 3. Setting up L-ISA Controller
1. Open `Settings`
2. Go to `MIDI` tab

![L-ISA-MIDI](https://github.com/Certified-Turtle/EGL314_TeamE/blob/main/POC/Setup/Diagram/L-ISA_MIDI.png)

3. Make sure your `loopMIDI Port` is setup 

![L-ISA-MIDI-1](https://github.com/Certified-Turtle/EGL314_TeamE/blob/main/POC/Setup/Diagram/L-ISA_MIDI_1.png)

## 4. Setting up Reaper
1. Open Preference window with `ctrl + p`,  under `Audio`, select `Device`
2. Change `Audio System` to `ASIO`, and `ASIO Driver` to `L-ISA Audio Bridge`
3. Set the range of `Inputs` and `Outputs` below

![Reaper-AudioD](https://github.com/Certified-Turtle/EGL314_TeamE/blob/main/POC/Setup/Diagram/Reaper_AudioD.png)

4. Open Preference window with `ctrl + p`, select `MIDI Outputs`
5. The port that you created should appear on the right
6. Ensure that `Enable` and `Clock` are applied
7. Click OK to continue

![Reaper-Moutputs](https://github.com/Certified-Turtle/EGL314_TeamE/blob/main/POC/Setup/Diagram/Reaper_Moutputs.png)

8. Go to `Insert` tab, click on `SMPTE LTC/MTC Timecode Generator`

![Reaper-Timecode](https://github.com/Certified-Turtle/EGL314_TeamE/blob/main/POC/Setup/Diagram/Reaper_Timecode.png)

9. Double click on the `Timecode Generator` and set it to `Send MIDI (MTC)`

![Reaper-Timecode-1](https://github.com/Certified-Turtle/EGL314_TeamE/blob/main/POC/Setup/Diagram/Reaper_Timecode_1.png)

10. Configure the `MIDI Output` to `loopMIDI Port` for the `Timecode Generator`

![Reaper-Output](https://github.com/Certified-Turtle/EGL314_TeamE/blob/main/POC/Setup/Diagram/Reaper_Output.png)