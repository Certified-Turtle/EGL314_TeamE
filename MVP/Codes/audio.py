from pythonosc import udp_client
import time

def send_message(client, address):
    try:
        client.send_message(address, 1.0)
        print(f"Sent to REAPER: {address}")
    except Exception as e:
        print("Message not sent:", e)

PI_A_ADDR = "192.168.254.12"
PORT = 8000

client = udp_client.SimpleUDPClient(PI_A_ADDR, PORT)

send_message(client, "/action/_RSec88256f5cfe129e3c94fe68f3db56f421abafd6")

def mute_tracks():
    send_message(client, "/action/41255")

def decoy_hit():
    send_message(client, "/action/41257")
    send_message(client, "/action/1007")           

def ghost_hit():
    send_message(client, "/action/41256")
    send_message(client, "/action/1007")  

def win_pt():
    send_message(client, "/action/41258")
    send_message(client, "/action/1007")  

def lose_pt():
    send_message(client, "/action/41259")
    send_message(client, "/action/1007")  

def thunder():
    send_message(client, "/action/41260")
    send_message(client, "/action/1007")