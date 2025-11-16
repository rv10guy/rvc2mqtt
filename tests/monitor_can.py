#!/usr/bin/env python3
"""
Simple CAN Bus Monitor
Displays CAN messages in real-time to analyze light control commands
"""

import can
import time
from datetime import datetime

CAN_HOST = "192.168.50.103"
CAN_PORT = 3333

def format_can_message(msg):
    """Format CAN message for display"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    can_id = f"{msg.arbitration_id:08X}"
    data_hex = ''.join(f'{b:02X}' for b in msg.data)

    # Decode extended ID for RV-C
    dgn = (msg.arbitration_id >> 8) & 0x1FFFF
    priority = (msg.arbitration_id >> 26) & 0x7
    source = msg.arbitration_id & 0xFF

    return f"{timestamp} | ID:{can_id} | DGN:{dgn:05X} | Src:{source:02X} | Data:{data_hex}"

def is_light_message(msg):
    """Check if message is light-related (DGN 1FEDB)"""
    dgn = (msg.arbitration_id >> 8) & 0x1FFFF
    return dgn == 0x1FEDB

def main():
    print("=" * 80)
    print("  CAN Bus Monitor - Light Control Analysis")
    print("=" * 80)
    print("\nConnecting to CAN bus...")

    try:
        bus = can.interface.Bus(
            interface='slcan',
            channel=f'socket://{CAN_HOST}:{CAN_PORT}',
            bitrate=250000
        )
        print(f"✅ Connected to {CAN_HOST}:{CAN_PORT}")
        print("\n🔍 Monitoring CAN bus (press Ctrl+C to stop)...")
        print("💡 LIGHT MESSAGES will be highlighted\n")
        print("-" * 80)

        message_count = 0
        light_message_count = 0

        while True:
            msg = bus.recv(timeout=1.0)
            if msg is None:
                continue

            message_count += 1
            is_light = is_light_message(msg)

            if is_light:
                light_message_count += 1
                print(f"💡 LIGHT: {format_can_message(msg)}")

                # Decode light command details
                instance = msg.data[0]
                command = msg.data[1]
                brightness = msg.data[2]

                cmd_names = {
                    0x00: "OFF (delay off)",
                    0x03: "OFF (immediate)",
                    0x04: "ON (restore previous)",
                    0xC8: "ON (100%)",
                    0x15: "RAMP STOP",
                }

                cmd_str = cmd_names.get(command, f"UNKNOWN({command:02X})")
                print(f"         → Instance:{instance} Command:{cmd_str} Brightness:{brightness}")
                print()
            else:
                # Show non-light messages more compactly
                if message_count % 10 == 0:  # Show every 10th message
                    print(f"    {format_can_message(msg)}")

    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print(f"  Monitoring stopped")
        print(f"  Total messages: {message_count}")
        print(f"  Light messages: {light_message_count}")
        print("=" * 80)
        bus.shutdown()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
