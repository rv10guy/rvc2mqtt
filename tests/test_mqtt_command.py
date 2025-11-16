#!/usr/bin/env python3
"""Test sending MQTT commands to rvc2mqtt Phase 2"""

import paho.mqtt.client as mqtt
import time
import sys

# MQTT broker from config
MQTT_BROKER = "192.168.50.77"
MQTT_USER = "hassio"
MQTT_PASS = "hassio"

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"✅ Connected to MQTT broker: {MQTT_BROKER}")

    # Subscribe to command status and error topics
    client.subscribe("rv/command/status")
    client.subscribe("rv/command/error")
    print("📡 Subscribed to rv/command/status and rv/command/error")

def on_message(client, userdata, msg):
    print(f"\n📨 Received on {msg.topic}:")
    print(f"   {msg.payload.decode()}")

def send_test_command(client):
    """Send a test light command"""
    print("\n💡 Sending test command: Turn ON ceiling light")
    client.publish("rv/light/ceiling_light/set", "ON")
    print("   Published to rv/light/ceiling_light/set: ON")

    time.sleep(2)

    print("\n💡 Sending test command: Set brightness to 50%")
    client.publish("rv/light/ceiling_light/brightness/set", "50")
    print("   Published to rv/light/ceiling_light/brightness/set: 50")

def main():
    print("=" * 70)
    print("  Testing Phase 2 MQTT Commands")
    print("=" * 70)

    # Create MQTT client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        print(f"\n🔌 Connecting to MQTT broker at {MQTT_BROKER}...")
        client.connect(MQTT_BROKER, 1883, 60)

        # Start network loop
        client.loop_start()

        # Wait for connection
        time.sleep(2)

        # Send test commands
        send_test_command(client)

        # Wait for responses
        print("\n⏳ Waiting for command responses (10 seconds)...")
        time.sleep(10)

        print("\n✅ Test complete!")

        client.loop_stop()
        client.disconnect()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
