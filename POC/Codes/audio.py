from pythonosc import udp_client
import time
import gameplay

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
#End
time.sleep(40)
send_message(client, "/action/1016")


if gameplay.is_inside_hitbox:
    # Strike verification gates
    if gameplay.active_entity_type == "DECOY":
        if not gameplay.is_striking:
            send_message(client, "/action/40162")
            time.sleep(1)
            send_message(client, "/action/1016")
    else:
        if not gameplay.is_striking:
            send_message(client, "/action/40161")
            time.sleep(1)
            send_message(client, "/action/1016")

if gameplay.tutorial_count == 15:
    send_message(client, "/action/40163")
    time.sleep(3)
    send_message(client, "/action/1016")

if gameplay.score == 15:
    send_message(client, "/action/40163")
    time.sleep(3)
    send_message(client, "/action/1016")
else:
    send_message(client, "/action/40164")
    time.sleep(2)
    send_message(client, "/action/1016")