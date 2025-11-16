#!/usr/bin/env python3
"""Quick test for ceiling fan commands"""

import paho.mqtt.client as mqtt
import time
import sys

MQTT_BROKER = "192.168.50.77"
MQTT_USER = "hassio"
MQTT_PASS = "hassio"

def on_message(client, userdata, msg):
    print(f"📨 {msg.topic}: {msg.payload.decode()}")

# Create client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(MQTT_USER, MQTT_PASS)
client.on_message = on_message

print("🔌 Connecting to MQTT...")
client.connect(MQTT_BROKER, 1883, 60)
client.loop_start()

# Subscribe to status topics
client.subscribe("rv/command/#")
time.sleep(1)

if len(sys.argv) < 2:
    print("Usage: python test_ceiling_fan.py LOW|HIGH|OFF")
    sys.exit(1)

speed = sys.argv[1].upper()
print(f"\n🌀 Sending ceiling fan command: {speed}")
client.publish("rv/fan/fan_bedroom_ceiling/set", speed)

time.sleep(3)
client.loop_stop()
client.disconnect()
