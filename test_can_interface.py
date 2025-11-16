#!/usr/bin/env python3
"""
Test different CAN interface types to find the right one for the device
"""

import can
import time
import socket

CAN_HOST = "192.168.50.103"
CAN_PORT = 3333

print("=" * 70)
print("  CAN Interface Type Detection")
print("=" * 70)

# First, test raw socket connection
print("\n1. Testing raw TCP socket connection...")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((CAN_HOST, CAN_PORT))
    print(f"   ✅ TCP connection successful to {CAN_HOST}:{CAN_PORT}")

    # Try to read any initial data
    sock.settimeout(2)
    try:
        data = sock.recv(1024)
        if data:
            print(f"   📨 Received initial data: {data[:50]}")
        else:
            print("   ℹ️  No initial data received")
    except socket.timeout:
        print("   ℹ️  No initial data (timeout)")

    sock.close()
except Exception as e:
    print(f"   ❌ TCP connection failed: {e}")
    exit(1)

# Test different CAN interface types
interfaces_to_try = [
    {
        'name': 'SLCAN (Serial Line CAN)',
        'interface': 'slcan',
        'kwargs': {
            'channel': f'socket://{CAN_HOST}:{CAN_PORT}',
            'bitrate': 250000
        }
    },
    {
        'name': 'SLCAN (no flow control)',
        'interface': 'slcan',
        'kwargs': {
            'channel': f'socket://{CAN_HOST}:{CAN_PORT}',
            'bitrate': 250000,
            'rtscts': False
        }
    },
    {
        'name': 'SLCAN (with ttyUSB)',
        'interface': 'slcan',
        'kwargs': {
            'channel': f'socket://{CAN_HOST}:{CAN_PORT}',
            'bitrate': 250000,
            'ttyBaudrate': 115200
        }
    },
    {
        'name': 'SocketCAN',
        'interface': 'socketcan',
        'kwargs': {
            'channel': f'{CAN_HOST}:{CAN_PORT}'
        }
    },
]

print("\n2. Testing CAN interface types...\n")

for test in interfaces_to_try:
    print(f"   Testing: {test['name']}")
    print(f"      Interface: {test['interface']}")
    print(f"      Config: {test['kwargs']}")

    try:
        bus = can.interface.Bus(
            interface=test['interface'],
            **test['kwargs']
        )
        print(f"      ✅ SUCCESS! Connected with {test['name']}")
        print(f"      Bus info: {bus}")

        # Try to read a message
        print("      Attempting to read CAN message (5 sec timeout)...")
        msg = bus.recv(timeout=5)
        if msg:
            print(f"      📨 Received CAN message: ID={msg.arbitration_id:08X}, Data={msg.data.hex()}")
        else:
            print("      ℹ️  No messages received (may be normal if bus is quiet)")

        bus.shutdown()
        print(f"\n   ✅ {test['name']} WORKS!\n")
        print("=" * 70)
        print(f"  SOLUTION FOUND: Use interface='{test['interface']}'")
        print(f"  Config: {test['kwargs']}")
        print("=" * 70)
        break

    except can.exceptions.CanInitializationError as e:
        print(f"      ❌ Initialization failed: {e}")
    except Exception as e:
        print(f"      ❌ Error: {type(e).__name__}: {e}")

    print()

else:
    print("\n" + "=" * 70)
    print("  ❌ None of the standard interfaces worked")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Check what type of CAN-to-network device you have")
    print("  2. Check if it requires specific initialization commands")
    print("  3. Verify it's configured for SLCAN protocol")
    print("  4. Try connecting with the manufacturer's software to confirm it works")
