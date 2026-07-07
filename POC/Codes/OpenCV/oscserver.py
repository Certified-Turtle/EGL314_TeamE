# central_router.py
from pythonosc import osc_server, dispatcher, udp_client

# The IP of the computer running THIS server script, and the port it listens on
RECEIVER_IP = "192.168.254.58"
RECEIVER_PORT = 2000

print("[INIT] Booting Central Network Router Node...")

# ---- HARDWARE / AV SOFTWARE TARGET CLIENTS ----
# These point out to your team's respective production setups
reaper = udp_client.SimpleUDPClient("192.168.254.12", 8000)
grandma3 = udp_client.SimpleUDPClient("192.168.254.252", 8080)
lisa = udp_client.SimpleUDPClient("192.168.254.192", 8880)

def forward_all(address, *args):
    if len(args) < 1: return
    value = args[-1]
    
    sending_software = "UNKNOWN"
    try:
        # 1. AUDIO LAYER ROUTING (Reaper)
        if "action" in address.lower() or "vol" in address.lower() or "play" in address.lower():
            sending_software = "REAPER"
            reaper.send_message(address, value)
            
        # 2. LIGHTING LAYER ROUTING (grandMA3)
        elif any(x in address.lower() for x in ["ma3", "fad", "light", "bright", "maxpy", "fixture", "col", "rgb", "pan", "tilt", "gobo", "beam", "strobe"]):
            sending_software = "MA3"
            grandma3.send_message(address, value)
            
        # 3. SPATIAL AUDIO / INTERACTIVE LAYER ROUTING (LISA)
        elif "ext/src" in address.lower() or "lisa" in address.lower() or "pos" in address.lower():
            sending_software = "LISA"
            lisa.send_message(address, value)
            
        # 4. FALLBACK LOGGING
        else:
            sending_software = "UNMAPPED_PORT"

        # Consolidated debug log statement (Cleaned up unreachable code bug)
        print(f"[{sending_software}] Routed: {address} -> Value: {value}")
        
    except Exception as e:
        print(f"[NET ERROR] Failed to route address {address}: {e}")

# ---- PACKET DISPATCHER CONFIG ----
disp = dispatcher.Dispatcher()
disp.set_default_handler(forward_all)

# ---- NETWORK SOCKET SPIN-UP ----
# Threads incoming connections so multiple clients can hit it simultaneously
server = osc_server.ThreadingOSCUDPServer(
    (RECEIVER_IP, RECEIVER_PORT), disp
)

print(f"[SUCCESS] Central Router Online! Listening on {server.server_address}")
print("Leave this terminal window open in the background.")

# Enters an isolated infinite monitoring loop listening for packets
server.serve_forever()