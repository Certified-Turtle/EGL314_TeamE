# oscserver.py README

This python script acts as an OSC (Open Sound Control) Router. It sits between various controllers and the softwares (Reaper, GrandMA3, L-ISA), automatically directing incoming network messages to the correct destination based on the content of the message "address".

We start off by installing pythonosc and sys.

```bash
from pythonosc import osc_server, dispatcher, udp_client
import sys
```

These 2 lines would be replaced with your OWN computer's IP address and port number.

```bash
RECEIVER_IP = "192.168.254.58"
RECEIVER_PORT = 2000
```

This chunk of code is responsivble for establishing the outgoing network connections to the specific softwares you want to control. By creating these ```bash SimpleUDPClient``` objects, you essentially direct the code at specific destinations on your network so it knows wheree to send messages later. Remember to update the various IP addresses and port number with the respective computer's IP and port number. These port numbers can be found in the respective software.

```bash
# ---- HARDWARE / AV SOFTWARE TARGET CLIENTS ----
try:
    reaper = udp_client.SimpleUDPClient("192.168.254.58", 8000)
    lisa = udp_client.SimpleUDPClient("192.168.254.58", 8880)
    grandma3 = udp_client.SimpleUDPClient("192.168.254.252", 8000)
except Exception as e:
    print(f"[CRITICAL ERROR] Failed to initialize hardware client targets: {e}")
    sys.exit()
```

This function below. ```bash forward_all```, is the router of the OSC server. Every time the server receives an  OSC message from any device, this function is triggered to inspect that message and decide which piece of softawre needs to receive it.

```bash
def forward_all(address, *args):
    if len(args) < 1: return
    value = args[-1]
    
    sending_software = "UNKNOWN"
    try:
        # 1. AUDIO LAYER ROUTING (Reaper) - EXPANDED KEYWORDS
        if any(x in address.lower() for x in ["action", "vol", "play", "stop", "sample", "frame", "time", "beat"]):
            sending_software = "REAPER"
            reaper.send_message(address, value)
            
        # 2. LIGHTING LAYER ROUTING (grandMA3)
        elif any(x in address.lower() for x in ["ma3", "fad", "light", "bright", "maxpy", "fixture", "col", "rgb", "pan", "tilt", "gobo", "beam", "strobe"]):
            sending_software = "MA3"
            grandma3.send_message(address, value)
            
        # 3. SPATIAL AUDIO / INTERACTIVE LAYER ROUTING (LISA)
        elif "ext/src" in address.lower() or "lisa" in address.lower() or "pos" in address.lower() or "track" in address.lower() or "master" in address.lower():
            sending_software = "LISA"
            lisa.send_message(address, value)
            
        # 4. FALLBACK LOGGING
        else:
            sending_software = "UNMAPPED_PORT"

        # === LIVE REHEARSAL TERMINAL FILTER ===
        # Blocks high-frequency timeline packets from flooding your view
        high_frequency_paths = ["/time", "/sample", "/frame", "/beat"]
        if any(path in address.lower() for path in high_frequency_paths):
            return  

        # Clean, discrete interaction log
        print(f"[{sending_software}] Routed: {address} -> Value: {value}")
        
    except Exception as e:
        print(f"[NET ERROR] Failed to route address {address}: {e}")
```

This section of the code handles the infrastructure setup. It initializes the 'receiving' part of the code and runs indefinitely so it can process incoming network traffic in real time.

```bash
disp = dispatcher.Dispatcher()
disp.set_default_handler(forward_all)

# ---- NETWORK SOCKET SPIN-UP & BLOCKING PROTECTION ----
try:
    server = osc_server.ThreadingOSCUDPServer(
        (RECEIVER_IP, RECEIVER_PORT), disp
    )
    print(f"[SUCCESS] Central Router Online! Listening on port {RECEIVER_PORT}")
    print("Leave this terminal window open in the background.\n" + "="*50)
    
    # CRITICAL: This method locks the execution thread open forever. 
    server.serve_forever()

except Exception as e:
    print(f"\n[CRITICAL CRASH] Server failed to lock onto network sockets! Reason: {e}")
    print("\nTroubleshooting Checks:")
    print("1. Is another terminal or background process already using Port 2000?")
    print("2. Are you connected to an active network card/switch interface?")
    input("\nPress ENTER to acknowledge error and exit...")
```