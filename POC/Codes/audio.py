from pythonosc import udp_client
import time

def send_message(client, address):
    try:
        client.send_message(address, 1.0)
        print(f"Sent to REAPER: {address}")
    except Exception as e:
        print("Message not sent:", e)

PI_A_ADDR = "192.168.254.58"
PORT = 8000

client = udp_client.SimpleUDPClient(PI_A_ADDR, PORT)

#Jump to Marker 1
send_message(client, "/action/40161")
#Play
send_message(client, "/action/40073")