# oscserver.py
from pythonosc import osc_server, dispatcher, udp_client
import sys

# === 1. UNIVERSAL IP BINDING ===
# "0.0.0.0" forces Windows to use whatever active IP address your network card currently has.
# This prevents crashes when moving between home Wi-Fi and venue routers.
RECEIVER_IP = "192.168.254.58"
RECEIVER_PORT = 2000

print("[INIT] Booting Central Network Router Node...")

# ---- HARDWARE / AV SOFTWARE TARGET CLIENTS ----
try:
    reaper = udp_client.SimpleUDPClient("192.168.254.58", 8000)
    lisa = udp_client.SimpleUDPClient("192.168.254.58", 8880)
    grandma3 = udp_client.SimpleUDPClient("192.168.254.252", 8000)
except Exception as e:
    print(f"[CRITICAL ERROR] Failed to initialize hardware client targets: {e}")
    sys.exit()

# ---- ROUTING MATRIX ENGINE ----
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

# ---- PACKET DISPATCHER CONFIG ----
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