#!/usr/bin/env python3
"""Check MQTT discovery messages"""

import paho.mqtt.client as mqtt
import json
import time

MQTT_BROKER = "192.168.50.77"
MQTT_USER = "hassio"
MQTT_PASS = "hassio"

messages = []

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"✅ Connected to MQTT")
    client.subscribe("homeassistant/fan/+/config")
    print("📡 Subscribed to homeassistant/fan/+/config")

def on_message(client, userdata, msg):
    print(f"\n📨 Topic: {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode())
        print(json.dumps(payload, indent=2))
    except:
        print(f"Raw: {msg.payload.decode()}")
    messages.append(msg)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(MQTT_USER, MQTT_PASS)
client.on_connect = on_connect
client.on_message = on_message

print(f"🔌 Connecting to {MQTT_BROKER}...")
client.connect(MQTT_BROKER, 1883, 60)
client.loop_start()

print("⏳ Listening for 5 seconds...")
time.sleep(5)

if not messages:
    print("\n⚠️  No fan discovery messages found!")
    print("This means the fan entity is not being published to MQTT.")

client.loop_stop()
client.disconnect()
