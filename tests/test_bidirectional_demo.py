#!/usr/bin/env python3
"""
Demonstration of Phase 2 Bidirectional Control

This script demonstrates the command flow without requiring actual
MQTT or CAN bus connections.
"""

import time
from command_handler import CommandHandler
from rvc_commands import RVCCommandEncoder
from command_validator import CommandValidator
from audit_logger import AuditLogger


class MockCANTransmitter:
    """Mock CAN transmitter that simulates successful transmission"""

    def __init__(self):
        self.frames_sent = []
        self.connected = False

    def connect(self):
        print("📡 [CAN] Connected to CAN bus (simulated)")
        self.connected = True
        return True, None

    def send_frames(self, frames):
        """Simulate sending frames to CAN bus"""
        if not self.connected:
            return False, "Not connected to CAN bus"

        self.frames_sent.extend(frames)

        # Simulate frames being sent
        for i, (can_id, data, delay) in enumerate(frames):
            data_hex = ''.join(f'{b:02X}' for b in data)
            print(f"  📤 Frame {i+1}: ID={can_id:08X} Data={data_hex}", end='')
            if delay > 0:
                print(f" (delay={delay}ms)")
            else:
                print()

        return True, None


class MockHADiscovery:
    """Mock HA Discovery with test entities"""

    def __init__(self):
        self.entities = [
            {'entity_id': 'ceiling_light', 'instance': 1, 'entity_type': 'light'},
            {'entity_id': 'hvac_front', 'instance': 1, 'entity_type': 'climate'},
            {'entity_id': 'water_pump', 'instance': 3, 'entity_type': 'switch'},
        ]


def print_header(text):
    """Print section header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def demo_light_control(handler):
    """Demonstrate light control"""
    print_header("Light Control Demo")

    # Turn on ceiling light
    print("💡 Command: Turn ON ceiling light")
    success = handler.process_mqtt_command('rv/light/ceiling_light/set', 'ON')
    if success:
        print("✅ Command succeeded\n")
    else:
        print("❌ Command failed\n")

    time.sleep(1)

    # Set brightness to 75%
    print("💡 Command: Set ceiling light brightness to 75%")
    success = handler.process_mqtt_command('rv/light/ceiling_light/brightness/set', '75')
    if success:
        print("✅ Command succeeded\n")
    else:
        print("❌ Command failed\n")

    time.sleep(1)

    # Turn off
    print("💡 Command: Turn OFF ceiling light")
    success = handler.process_mqtt_command('rv/light/ceiling_light/set', 'OFF')
    if success:
        print("✅ Command succeeded\n")
    else:
        print("❌ Command failed\n")


def demo_climate_control(handler):
    """Demonstrate climate control"""
    print_header("Climate Control Demo")

    # Set mode to heat
    print("🌡️  Command: Set HVAC to HEAT mode")
    success = handler.process_mqtt_command('rv/climate/hvac_front/mode/set', 'heat')
    if success:
        print("✅ Command succeeded\n")
    else:
        print("❌ Command failed\n")

    time.sleep(1)

    # Set temperature
    print("🌡️  Command: Set temperature to 72°F")
    success = handler.process_mqtt_command('rv/climate/hvac_front/temperature/set', '72')
    if success:
        print("✅ Command succeeded\n")
    else:
        print("❌ Command failed\n")

    time.sleep(1)

    # Set fan mode
    print("🌡️  Command: Set fan to AUTO")
    success = handler.process_mqtt_command('rv/climate/hvac_front/fan_mode/set', 'auto')
    if success:
        print("✅ Command succeeded\n")
    else:
        print("❌ Command failed\n")


def demo_switch_control(handler):
    """Demonstrate switch control"""
    print_header("Switch Control Demo")

    # Turn on water pump
    print("🔌 Command: Turn ON water pump")
    success = handler.process_mqtt_command('rv/switch/water_pump/set', 'ON')
    if success:
        print("✅ Command succeeded\n")
    else:
        print("❌ Command failed\n")

    time.sleep(1)

    # Turn off water pump
    print("🔌 Command: Turn OFF water pump")
    success = handler.process_mqtt_command('rv/switch/water_pump/set', 'OFF')
    if success:
        print("✅ Command succeeded\n")
    else:
        print("❌ Command failed\n")


def demo_validation_errors(handler):
    """Demonstrate validation error handling"""
    print_header("Validation & Error Handling Demo")

    # Invalid brightness (too high)
    print("❌ Command: Set brightness to 150 (invalid - too high)")
    success = handler.process_mqtt_command('rv/light/ceiling_light/brightness/set', '150')
    if not success:
        print("✅ Correctly rejected invalid command\n")
    else:
        print("❌ Should have been rejected\n")

    time.sleep(1)

    # Invalid temperature (too low)
    print("❌ Command: Set temperature to 30°F (invalid - too low)")
    success = handler.process_mqtt_command('rv/climate/hvac_front/temperature/set', '30')
    if not success:
        print("✅ Correctly rejected invalid command\n")
    else:
        print("❌ Should have been rejected\n")


def main():
    """Run bidirectional control demonstration"""

    print("\n" + "🚐" * 35)
    print("  RVC2MQTT Phase 2 - Bidirectional Control Demonstration")
    print("🚐" * 35)

    print("\n📋 Initializing Phase 2 components...")

    # Create components
    encoder = RVCCommandEncoder(source_address=99)
    print("  ✅ RV-C Command Encoder initialized")

    validator = CommandValidator(config={
        'security_enabled': True,
        'rate_limit_enabled': True,
        'global_commands_per_second': 10,
        'entity_commands_per_second': 2,
        'entity_cooldown_ms': 500,
        'denylist': [],
        'allowlist': [],
        'allowed_commands': ['light', 'climate', 'switch']
    })
    print("  ✅ Command Validator initialized")

    transmitter = MockCANTransmitter()
    transmitter.connect()
    print("  ✅ CAN Transmitter initialized")

    audit_logger = AuditLogger(
        log_file='logs/demo_audit.log',
        console_output=False
    )
    print("  ✅ Audit Logger initialized")

    ha_discovery = MockHADiscovery()
    print("  ✅ HA Discovery initialized")

    handler = CommandHandler(
        encoder=encoder,
        validator=validator,
        transmitter=transmitter,
        audit_logger=audit_logger,
        ha_discovery=ha_discovery,
        mqtt_client=None,
        debug_level=0
    )
    print("  ✅ Command Handler initialized")

    print("\n✨ Phase 2 Ready! Starting demonstrations...")

    # Run demonstrations
    demo_light_control(handler)
    demo_climate_control(handler)
    demo_switch_control(handler)
    demo_validation_errors(handler)

    # Show statistics
    print_header("Command Statistics")
    stats = handler.get_stats()
    print(f"  Total Commands:        {stats['total_commands']}")
    print(f"  Successful:            {stats['successful_commands']}")
    print(f"  Validation Failures:   {stats['validation_failures']}")
    print(f"  Transmission Failures: {stats['transmission_failures']}")
    print(f"  Success Rate:          {stats['success_rate']}%")
    print()

    print_header("Total CAN Frames Transmitted")
    print(f"  {len(transmitter.frames_sent)} frames sent to CAN bus")
    print()

    print("=" * 70)
    print("  ✅ Phase 2 Bidirectional Control Demo Complete!")
    print("=" * 70)
    print("\n📚 Next Steps:")
    print("  - Review docs/COMMAND_FORMAT.md for full command reference")
    print("  - Check docs/HA_AUTOMATION_EXAMPLES.md for automation ideas")
    print("  - View logs/demo_audit.log for complete audit trail")
    print("  - Deploy to RV by configuring rvc2mqtt.ini with your MQTT/CAN settings")
    print()


if __name__ == '__main__':
    main()
