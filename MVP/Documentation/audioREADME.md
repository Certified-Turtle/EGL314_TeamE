# audio.py README



This code `audio.py` controls the audio effects for the ghost-hunting game

We start off with importing the following library:

```bash
from pythonosc import udp_client
```

### What this library does:

| Library | Function |
| :--- | :--- |
| `from pythonosc import udp_client` | Sends short text commands over the network to the audio laptop. |

## Section 1: Create a custom script in Reaper

Since we are creating a custom command, we will need to upload it into Reaper later

For this project, we work with other groups, team E uses tracks 29, 30, 31 and 32 in Reaper.

We need to create a custom ReaScript that mutes all tracks (other groups) and unmute our own tracks.
Save the LUA code below.

```lua
-- Mute all tracks, then unmute tracks 29, 30, 31, 32
reaper.Undo_BeginBlock()
local total = reaper.CountTracks(0)
-- Mute every track
for i = 0, total - 1 do
  local tr = reaper.GetTrack(0, i)
  if tr then
    reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", 1)
  end
end
-- Unmute tracks 29, 30, 31, 32 (UI numbers -> 0-based: 28..31)
for _, ui_num in ipairs({29, 30, 31, 32}) do
  local idx = ui_num - 1
  if idx < total then
    local tr = reaper.GetTrack(0, idx)
    if tr then
      reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", 0)
    end
  else
    reaper.ShowConsoleMsg(string.format(
      "Track %d does not exist (project has %d tracks).\n", ui_num, total))
  end
end
reaper.Undo_EndBlock("Mute all, unmute 29-32", -1)
```

## Section 2: Uploading ReaScript to Reaper

Now, we need to upload the ReaScript to get the command ID so that we can put it in the `audio.py`

On your keyboard, press `Shift` and `?` at the same time, this window will appear. 

![reascript1](https://github.com/Certified-Turtle/EGL314_TeamE/blob/main/MVP/Documentation/Images/reascript1.png)

Next, click on `New Action`, and then `Load ReaScript...`

![reascript2](https://github.com/Certified-Turtle/EGL314_TeamE/blob/main/MVP/Documentation/Images/reascript2.png)

To find the Command ID, just search the ReaScript name, in this case `trackControl` at the top, right click on the command, and click on `Copy selected action command ID`

![reascript3](https://github.com/Certified-Turtle/EGL314_TeamE/blob/main/MVP/Documentation/Images/reascript3.png)

Now with the action command, you can complete the code line (replace the action with your own Command ID)

```python
send_message(client, "/action/_RSec88256f5cfe129e3c94fe68f3db56f421abafd6")
```