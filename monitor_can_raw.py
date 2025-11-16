#!/usr/bin/env python3
"""
Simple CAN Bus Monitor using raw TCP socket
Works alongside rvc2mqtt by reading SLCAN frames directly from TCP
"""

import socket
import time
from datetime import datetime
import sys

CAN_HOST = "192.168.50.103"
CAN_PORT = 3333

def parse_slcan_frame(line):
    """Parse SLCAN format frame (e.g., 'T19FEDB63801FFC800FF00FFFF')"""
    line = line.strip()
    if not line:
        return None

    # Standard SLCAN format: T<8-digit ID><N><data bytes>\r
    # T = extended frame
    # t = standard frame
    if not (line.startswith('T') or line.startswith('t')):
        return None

    try:
        is_extended = line.startswith('T')
        if is_extended:
            # Extended frame: T + 8 hex digits for ID
            can_id_hex = line[1:9]
            dlc = int(line[9])
            data_hex = line[10:10+dlc*2]
        else:
            # Standard frame: t + 3 hex digits for ID
            can_id_hex = line[1:4]
            dlc = int(line[4])
            data_hex = line[5:5+dlc*2]

        can_id = int(can_id_hex, 16)
        data = bytes.fromhex(data_hex)

        return {
            'id': can_id,
            'data': data,
            'is_extended': is_extended
        }
    except (ValueError, IndexError) as e:
        return None

def format_can_message(msg):
    """Format CAN message for display"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    can_id = msg['id']
    can_id_str = f"{can_id:08X}"
    data_hex = ''.join(f'{b:02X}' for b in msg['data'])

    # Decode extended ID for RV-C
    if msg['is_extended']:
        dgn = (can_id >> 8) & 0x1FFFF
        priority = (can_id >> 26) & 0x7
        source = can_id & 0xFF
        return f"{timestamp} | ID:{can_id_str} | DGN:{dgn:05X} | Src:{source:02X} | Data:{data_hex}"
    else:
        return f"{timestamp} | ID:{can_id_str} | Data:{data_hex}"

def is_light_message(msg):
    """Check if message is light-related (DGN 1FEDB)"""
    if not msg['is_extended']:
        return False
    dgn = (msg['id'] >> 8) & 0x1FFFF
    return dgn == 0x1FEDB

def decode_light_command(data):
    """Decode light command details"""
    if len(data) < 3:
        return "INCOMPLETE"

    instance = data[0]
    command = data[1]
    brightness = data[2]

    cmd_names = {
        0x00: "OFF (delay off)",
        0x03: "OFF (immediate)",
        0x04: "ON (restore previous)",
        0xC8: "ON (100%)",
        0x15: "RAMP STOP",
    }

    cmd_str = cmd_names.get(command, f"UNKNOWN({command:02X})")
    return f"Instance:{instance} Command:{cmd_str} Brightness:{brightness}"

def main():
    print("=" * 80)
    print("  CAN Bus Monitor - Light Control Analysis (Raw Socket)")
    print("=" * 80)
    print("\nConnecting to CAN device...")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((CAN_HOST, CAN_PORT))
        print(f"✅ Connected to {CAN_HOST}:{CAN_PORT}")
        print("\n🔍 Monitoring CAN bus (press Ctrl+C to stop)...")
        print("💡 LIGHT MESSAGES will be highlighted\n")
        print("-" * 80)
        sys.stdout.flush()

        buffer = ""
        message_count = 0
        light_message_count = 0

        while True:
            # Read data from socket
            data = sock.recv(1024)
            if not data:
                print("Connection closed by device")
                break

            # Add to buffer and process complete lines
            buffer += data.decode('ascii', errors='ignore')
            lines = buffer.split('\r')
            buffer = lines[-1]  # Keep incomplete line in buffer

            for line in lines[:-1]:
                msg = parse_slcan_frame(line)
                if msg is None:
                    continue

                message_count += 1
                is_light = is_light_message(msg)

                if is_light:
                    light_message_count += 1
                    print(f"💡 LIGHT: {format_can_message(msg)}")
                    details = decode_light_command(msg['data'])
                    print(f"         → {details}")
                    print()
                    sys.stdout.flush()
                elif message_count % 20 == 0:  # Show every 20th non-light message
                    print(f"    {format_can_message(msg)}")
                    sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print(f"  Monitoring stopped")
        print(f"  Total messages: {message_count}")
        print(f"  Light messages: {light_message_count}")
        print("=" * 80)
        sock.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
