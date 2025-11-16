#!/usr/bin/env python3
"""Verify MQTT discovery messages"""

import paho.mqtt.client as mqtt
import json
import time
import sys

MQTT_BROKER = "192.168.50.77"
MQTT_USER = "hassio"
MQTT_PASS = "hassio"

messages = {}

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"✅ Connected to MQTT")
    # Subscribe to both fan and sensor config topics
    client.subscribe("homeassistant/fan/+/config")
    client.subscribe("homeassistant/sensor/+/config")
    print("📡 Subscribed to discovery topics")

def on_message(client, userdata, msg):
    entity_id = msg.topic.split('/')[2]
    messages[entity_id] = msg.payload.decode()

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(MQTT_USER, MQTT_PASS)
client.on_connect = on_connect
client.on_message = on_message

print(f"🔌 Connecting to {MQTT_BROKER}...")
client.connect(MQTT_BROKER, 1883, 60)
client.loop_start()

print("⏳ Listening for 3 seconds...")
time.sleep(3)

client.loop_stop()
client.disconnect()

# Check ceiling fan
print("\n" + "="*70)
print("CEILING FAN DISCOVERY")
print("="*70)
if 'rv_fan_bedroom_ceiling' in messages:
    payload = json.loads(messages['rv_fan_bedroom_ceiling'])
    print(json.dumps(payload, indent=2))

    # Check for device field
    if 'device' in payload:
        print("\n✅ Device field present:")
        print(json.dumps(payload['device'], indent=2))
    else:
        print("\n❌ Device field MISSING")

    # Check for preset modes
    if 'preset_modes' in payload:
        print(f"\n✅ Preset modes: {payload['preset_modes']}")
    else:
        print("\n❌ Preset modes MISSING")
else:
    print("❌ Ceiling fan discovery message NOT FOUND")

# Check propane tank
print("\n" + "="*70)
print("PROPANE TANK DISCOVERY")
print("="*70)
if 'rv_tank_propane_3' in messages:
    payload = json.loads(messages['rv_tank_propane_3'])
    print(json.dumps(payload, indent=2))

    # Check for device_class
    if 'device_class' in payload:
        print(f"\n❌ device_class still present: {payload['device_class']}")
    else:
        print("\n✅ device_class removed (correct)")
else:
    print("❌ Propane tank discovery message NOT FOUND")

print("\n" + "="*70)
