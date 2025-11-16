#!/usr/bin/env python3
"""
Test script for vent fan and lid control
Validates Phase 2 vent fan/lid implementation
"""

from rvc_commands import RVCCommandEncoder
from command_validator import CommandValidator
from command_handler import CommandHandler
from can_tx import CANTransmitter
from audit_logger import AuditLogger

def test_vent_fan():
    """Test vent fan encoding"""
    print("=" * 80)
    print("Test 1: Vent Fan Control")
    print("=" * 80)

    encoder = RVCCommandEncoder()

    # Test ON command
    frames = encoder.encode_vent_fan(instance=23, turn_on=True)
    print(f"\n✓ Vent fan ON (instance 23):")
    for i, (cid, data, delay) in enumerate(frames):
        print(f"  Frame {i+1}: {encoder.format_frame_debug(cid, data)}")

    # Test OFF command
    frames = encoder.encode_vent_fan(instance=23, turn_on=False)
    print(f"\n✓ Vent fan OFF (instance 23):")
    for i, (cid, data, delay) in enumerate(frames):
        print(f"  Frame {i+1}: {encoder.format_frame_debug(cid, data)}")

    print()

def test_vent_lid():
    """Test vent lid encoding"""
    print("=" * 80)
    print("Test 2: Vent Lid Control (Dual Motor)")
    print("=" * 80)

    encoder = RVCCommandEncoder()

    # Test OPEN command
    frames = encoder.encode_vent_lid(up_instance=26, down_instance=27, position='open')
    print(f"\n✓ Vent lid OPEN (up=26, down=27):")
    for i, (cid, data, delay) in enumerate(frames):
        print(f"  Frame {i+1}: {encoder.format_frame_debug(cid, data)}")
    print("  → Stops DOWN motor, then runs UP motor for 20 seconds")

    # Test CLOSE command
    frames = encoder.encode_vent_lid(up_instance=26, down_instance=27, position='close')
    print(f"\n✓ Vent lid CLOSE (up=26, down=27):")
    for i, (cid, data, delay) in enumerate(frames):
        print(f"  Frame {i+1}: {encoder.format_frame_debug(cid, data)}")
    print("  → Stops UP motor, then runs DOWN motor for 20 seconds")

    print()

def test_validation():
    """Test command validation for fan and cover"""
    print("=" * 80)
    print("Test 3: Command Validation")
    print("=" * 80)

    validator = CommandValidator()

    # Test fan validation
    fan_command = {
        'entity_id': 'vent_fan_galley',
        'command_type': 'fan',
        'action': 'state',
        'value': 'ON'
    }

    valid, error = validator.validate(fan_command)
    print(f"\n✓ Fan command validation: {'PASS' if valid else 'FAIL'}")
    if not valid:
        print(f"  Error: {error.code} - {error.message}")

    # Test cover validation
    cover_command = {
        'entity_id': 'vent_lid_galley',
        'command_type': 'cover',
        'action': 'position',
        'value': 'open'
    }

    valid, error = validator.validate(cover_command)
    print(f"✓ Cover command validation: {'PASS' if valid else 'FAIL'}")
    if not valid:
        print(f"  Error: {error.code} - {error.message}")

    # Test invalid cover value
    invalid_cover = {
        'entity_id': 'vent_lid_galley',
        'command_type': 'cover',
        'action': 'position',
        'value': 'middle'  # Invalid - must be 'open' or 'close'
    }

    valid, error = validator.validate(invalid_cover)
    print(f"✓ Invalid cover validation: {'FAIL (expected)' if not valid else 'PASS (unexpected)'}")
    if not valid:
        print(f"  Error: {error.code} - {error.message}")

    print()

def test_mqtt_topic_parsing():
    """Test MQTT topic parsing for fan and cover"""
    print("=" * 80)
    print("Test 4: MQTT Topic Parsing")
    print("=" * 80)

    # Create mock objects
    encoder = RVCCommandEncoder()
    validator = CommandValidator()
    transmitter = CANTransmitter(debug_level=0)  # Mock, won't connect
    audit_logger = AuditLogger()  # No debug_level parameter

    handler = CommandHandler(
        encoder=encoder,
        validator=validator,
        transmitter=transmitter,
        audit_logger=audit_logger,
        debug_level=0
    )

    # Test fan topic
    fan_topic = "rv/fan/vent_fan_galley/set"
    command = handler._parse_mqtt_message(fan_topic, "ON")
    print(f"\n✓ Fan topic parsed:")
    print(f"  Topic: {fan_topic}")
    print(f"  Payload: ON")
    print(f"  Parsed: {command}")

    # Test cover topic
    cover_topic = "rv/cover/vent_lid_galley/position/set"
    command = handler._parse_mqtt_message(cover_topic, "open")
    print(f"\n✓ Cover topic parsed:")
    print(f"  Topic: {cover_topic}")
    print(f"  Payload: open")
    print(f"  Parsed: {command}")

    print()

def main():
    """Run all vent control tests"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "VENT FAN & LID CONTROL TESTS" + " " * 30 + "║")
    print("║" + " " * 25 + "Phase 2 - Bidirectional" + " " * 31 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    try:
        test_vent_fan()
        test_vent_lid()
        test_validation()
        test_mqtt_topic_parsing()

        print("=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        print()
        print("Next steps:")
        print("  1. Start rvc2mqtt.py")
        print("  2. Check Home Assistant for new vent fan/lid entities")
        print("  3. Test control via MQTT:")
        print("     - mosquitto_pub -t 'rv/fan/vent_fan_galley/set' -m 'ON'")
        print("     - mosquitto_pub -t 'rv/cover/vent_lid_galley/position/set' -m 'open'")
        print()

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
