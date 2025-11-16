#!/usr/bin/env python3
"""Test Phase 2 with real configured entity"""

import paho.mqtt.client as mqtt
import time
import json

MQTT_BROKER = "192.168.50.77"
MQTT_USER = "hassio"
MQTT_PASS = "hassio"

responses = []

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"✅ Connected to MQTT broker")
    client.subscribe("rv/command/status")
    client.subscribe("rv/command/error")
    print("📡 Subscribed to command feedback topics\n")

def on_message(client, userdata, msg):
    global responses
    payload = json.loads(msg.payload.decode())
    responses.append((msg.topic, payload))

    if "status" in msg.topic:
        print(f"✅ SUCCESS: {payload.get('entity_id')} - {payload.get('action')} = {payload.get('value')}")
        print(f"   Latency: {payload.get('latency_ms')}ms")
        if 'can_frames' in payload:
            print(f"   CAN Frames sent: {len(payload.get('can_frames', []))}")
    else:
        print(f"❌ ERROR: {payload.get('error_code')} - {payload.get('error_message')}")

def main():
    print("=" * 70)
    print("  Phase 2 Real Entity Test - HVAC Control")
    print("=" * 70 + "\n")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_start()
    time.sleep(2)

    # Test climate control commands
    print("🌡️  Test 1: Set HVAC mode to HEAT")
    client.publish("rv/climate/hvac_front/mode/set", "heat")
    time.sleep(2)

    print("\n🌡️  Test 2: Set temperature to 72°F")
    client.publish("rv/climate/hvac_front/temperature/set", "72")
    time.sleep(2)

    print("\n🌡️  Test 3: Set fan to AUTO")
    client.publish("rv/climate/hvac_front/fan_mode/set", "auto")
    time.sleep(2)

    print("\n🌡️  Test 4: Invalid temperature (too low) - should be rejected")
    client.publish("rv/climate/hvac_front/temperature/set", "30")
    time.sleep(2)

    print("\n" + "=" * 70)
    print(f"  Test Complete - {len(responses)} responses received")
    print("=" * 70)

    client.loop_stop()
    client.disconnect()

if __name__ == '__main__':
    main()
