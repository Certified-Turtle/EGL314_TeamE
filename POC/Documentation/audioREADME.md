# audio.py README

---

This code runs the audio part of the game

## Section 1: Imports (setting up tools)

`pythonosc.udp_client` is used to send OSC (Open Sound Control) messages over a network using UDP.  
`time` is used to create delays before the next line of code runs.

This section loads the tools the script needs:
```python
from pythonosc import udp_client
import time
```

---

## Section 2: Message-sending function (core communication logic)

This function is responsible for sending commands to REAPER.

It takes:
client: the OSC connection
address: the OSC command like `/action/40161` (Marker 1)

What it does step-by-step:

Sends an OSC message with value 1.0 to the given address
Prints a confirmation message if successful
If anything goes wrong (network issue, wrong IP, etc.), it catches the error and prints `"Message not sent"`

```python
def send_message(client, address):
    try:
        client.send_message(address, 1.0)
        print(f"Sent to REAPER: {address}")
    except Exception as e:
        print("Message not sent:", e)
```

---

## Section 3: Network setup (targeting REAPER)

`PI_A_ADDR` is the IP address of the machine running REAPER  
`PORT = 8000` is the UDP port REAPER is listening on for OSC commands

```python
PI_A_ADDR = "192.168.254.58"
PORT = 8000
```

---

## Section 4: Creating the OSC client (connection setup)

This creates the actual OSC sender.

```python
client = udp_client.SimpleUDPClient(PI_A_ADDR, PORT)
```

It prepares a UDP client that knows: where to send messages (IP) and which port to use

After this, `client.send_message()` becomes usable for sending commands

---

## Section 5: Sending REAPER commands

This action tells REAPER to jump to Marker 1

```python
send_message(client, "/action/40161")
```

This tells REAPER to start playing the project

```python
send_message(client, "/action/40073")
```

This causes the code to stop for 40 seconds (configurable by changing the number)

```python
time.sleep(40)
```

This tells REAPER to stop the playback completely

```python
send_message(client, "/action/1016")
```

The full action list can be found under REAPER software, Actions > Show action list...
