import paho.mqtt.client as mqtt
import time
import os

# MQTT broker configuration
BROKER = "192.168.50.111"
PORT = 1883
TOPIC = "RVC/#"  # Subscribes to all topics
KEEP_ALIVE = 60

# MQTT broker authentication credentials
USERNAME = ""
PASSWORD = ""

# File to log incoming messages
LOG_FILE = "mqtt_messages.log"

# Callback for when the client receives a CONNACK response from the server
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {str(rc)}")
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe(TOPIC)

# Callback for when a PUBLISH message is received from the server
def on_message(client, userdata, msg):
    print(f"Topic: {msg.topic}\nMessage: {str(msg.payload)}")
    with open(LOG_FILE, 'a') as f:
        f.write(f"Time: {time.asctime()} Topic: {msg.topic} Message: {msg.payload}\n")

def on_disconnect(client, userdata, rc):
    print("Client disconnected OK")

def main():
    client = mqtt.Client()

#    client.username_pw_set(USERNAME, PASSWORD)

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    client.connect(BROKER, PORT, KEEP_ALIVE)

    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    client.loop_forever()


if __name__ == "__main__":
    main()
