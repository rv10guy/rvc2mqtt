#!/usr/bin/env python3
"""
MQTT Command Handler

Orchestrates the complete command processing flow:
MQTT → Parse → Validate → Encode → Transmit → Audit → Acknowledge

Integrates all Phase 2 components into a unified command processor.

Phase 2: Bidirectional Communication
"""

import time
import json
import re
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

# Phase 2 components
from rvc_commands import RVCCommandEncoder
from command_validator import CommandValidator, ValidationError
from audit_logger import AuditLogger

# CAN transmitter (optional for testing)
try:
    from can_tx import CANTransmitter
except ImportError:
    CANTransmitter = None  # Not available in test environment


class CommandHandler:
    """
    Unified command handler for MQTT → CAN flow

    Responsibilities:
    - Parse MQTT command messages
    - Validate commands
    - Encode to RV-C frames
    - Transmit to CAN bus
    - Log to audit trail
    - Publish acknowledgments
    """

    def __init__(self,
                 encoder: RVCCommandEncoder,
                 validator: CommandValidator,
                 transmitter: CANTransmitter,
                 audit_logger: AuditLogger,
                 ha_discovery=None,
                 mqtt_client=None,
                 debug_level: int = 0):
        """
        Initialize command handler

        Args:
            encoder: RVCCommandEncoder instance
            validator: CommandValidator instance
            transmitter: CANTransmitter instance
            audit_logger: AuditLogger instance
            ha_discovery: HADiscovery instance (for entity lookup)
            mqtt_client: MQTT client for publishing acknowledgments
            debug_level: Debug output level
        """
        self.encoder = encoder
        self.validator = validator
        self.transmitter = transmitter
        self.audit_logger = audit_logger
        self.ha_discovery = ha_discovery
        self.mqtt_client = mqtt_client
        self.debug_level = debug_level

        # Statistics
        self.stats = {
            'total_commands': 0,
            'successful_commands': 0,
            'validation_failures': 0,
            'transmission_failures': 0,
            'encoding_failures': 0,
        }

    # =========================================================================
    # Main Command Processing
    # =========================================================================

    def process_mqtt_command(self, topic: str, payload: str) -> bool:
        """
        Process MQTT command message

        Args:
            topic: MQTT topic (e.g., "rv/light/ceiling/set")
            payload: MQTT payload (e.g., "ON" or "75")

        Returns:
            True if command processed successfully, False otherwise

        Flow:
            1. Parse topic and payload
            2. Validate command
            3. Encode to RV-C frames
            4. Transmit frames
            5. Log and acknowledge
        """
        start_time = time.time()
        self.stats['total_commands'] += 1

        try:
            # Step 1: Parse MQTT message
            command = self._parse_mqtt_message(topic, payload)
            if not command:
                return False

            # Step 2: Log command attempt
            cmd_id = self.audit_logger.log_command_attempt(command, source='mqtt')

            if self.debug_level > 0:
                print(f"[CMD {cmd_id}] Processing: {command.get('entity_id')} "
                      f"({command.get('command_type')}) = {command.get('value')}")

            # Step 3: Validate command
            valid, error = self.validator.validate(command)
            if not valid:
                self.stats['validation_failures'] += 1
                self.audit_logger.log_validation_failure(
                    cmd_id, command, error.code, error.message, error.field
                )
                self._publish_error(command, error.code, error.message)
                return False

            # Step 4: Encode command to RV-C frames
            try:
                frames = self._encode_command(command)
                if not frames:
                    self.stats['encoding_failures'] += 1
                    self.audit_logger.log_transmission_failure(
                        cmd_id, command, "Failed to encode command"
                    )
                    self._publish_error(command, 'E100', 'Encoding failed')
                    return False
            except Exception as e:
                self.stats['encoding_failures'] += 1
                self.audit_logger.log_transmission_failure(
                    cmd_id, command, f"Encoding error: {e}"
                )
                self._publish_error(command, 'E100', f'Encoding error: {e}')
                return False

            # Step 5: Transmit frames
            success, tx_error = self.transmitter.send_frames(frames)
            if not success:
                self.stats['transmission_failures'] += 1
                frame_strs = [self._format_frame(f[0], f[1]) for f in frames]
                self.audit_logger.log_transmission_failure(
                    cmd_id, command, tx_error, frame_strs
                )
                self._publish_error(command, 'E101', tx_error)
                return False

            # Step 6: Success - log and acknowledge
            latency_ms = (time.time() - start_time) * 1000
            self.stats['successful_commands'] += 1
            frame_strs = [self._format_frame(f[0], f[1]) for f in frames]
            self.audit_logger.log_command_success(cmd_id, command, frame_strs, latency_ms)
            self._publish_success(command, latency_ms)

            if self.debug_level > 0:
                print(f"[CMD {cmd_id}] Success: {len(frames)} frames in {latency_ms:.1f}ms")

            return True

        except Exception as e:
            if self.debug_level > 0:
                print(f"[CMD] Unexpected error: {e}")
            self._publish_error({'entity_id': 'unknown'}, 'E999', f'Unexpected error: {e}')
            return False

    # =========================================================================
    # MQTT Message Parsing
    # =========================================================================

    def _parse_mqtt_message(self, topic: str, payload: str) -> Optional[Dict[str, Any]]:
        """
        Parse MQTT topic and payload into command dictionary

        Topic formats:
            rv/light/{entity_id}/set                -> state command
            rv/light/{entity_id}/brightness/set     -> brightness command
            rv/climate/{entity_id}/mode/set         -> mode command
            rv/climate/{entity_id}/temperature/set  -> temperature command
            rv/climate/{entity_id}/fan_mode/set     -> fan mode command
            rv/switch/{entity_id}/set               -> switch command

        Args:
            topic: MQTT topic
            payload: MQTT payload

        Returns:
            Command dictionary or None if parsing fails
        """
        # Parse topic pattern: rv/{entity_type}/{entity_id}/{action}/set
        pattern = r'^rv/(light|climate|switch)/([^/]+)/([^/]+)(?:/set)?$'
        match = re.match(pattern, topic)

        if not match:
            if self.debug_level > 0:
                print(f"Invalid topic format: {topic}")
            return None

        entity_type = match.group(1)
        entity_id = match.group(2)
        action_or_set = match.group(3)

        # Determine action based on topic structure
        if action_or_set == 'set':
            # Simple format: rv/light/ceiling/set
            action = 'state'
        elif action_or_set == 'brightness':
            # Brightness: rv/light/ceiling/brightness/set
            action = 'brightness'
        elif action_or_set in ['mode', 'temperature', 'fan_mode']:
            # Climate actions: rv/climate/hvac_front/mode/set
            action = action_or_set
        else:
            if self.debug_level > 0:
                print(f"Unknown action: {action_or_set}")
            return None

        # Parse payload based on action
        try:
            if action in ['state']:
                # ON/OFF commands
                value = payload.strip().upper()
            elif action == 'brightness':
                # Numeric brightness (0-100)
                value = int(payload.strip())
            elif action == 'temperature':
                # Numeric temperature
                value = float(payload.strip())
            elif action in ['mode', 'fan_mode']:
                # String mode values
                value = payload.strip().lower()
            else:
                value = payload.strip()
        except (ValueError, AttributeError) as e:
            if self.debug_level > 0:
                print(f"Failed to parse payload '{payload}': {e}")
            return None

        # Build command dictionary
        command = {
            'entity_id': entity_id,
            'command_type': entity_type,
            'action': action,
            'value': value
        }

        return command

    # =========================================================================
    # Command Encoding
    # =========================================================================

    def _encode_command(self, command: Dict[str, Any]) -> Optional[List[Tuple[int, List[int], int]]]:
        """
        Encode command to RV-C CAN frames

        Args:
            command: Command dictionary

        Returns:
            List of (can_id, data_bytes, delay_ms) tuples or None if encoding fails
        """
        # Get instance ID from entity mapping
        instance = self._get_instance_id(command['entity_id'])
        if instance is None:
            if self.debug_level > 0:
                print(f"No instance mapping for entity: {command['entity_id']}")
            return None

        command_type = command['command_type']
        action = command.get('action', 'state')
        value = command['value']

        try:
            # Route to appropriate encoder based on command type
            if command_type == 'light':
                if action == 'brightness':
                    return self.encoder.encode_light_brightness(instance, value)
                else:
                    # ON/OFF
                    turn_on = (value == 'ON')
                    return self.encoder.encode_light_on_off(instance, turn_on)

            elif command_type == 'climate':
                if action == 'mode':
                    return self.encoder.encode_climate_mode(instance, value)
                elif action == 'temperature':
                    return self.encoder.encode_climate_temperature(instance, value)
                elif action == 'fan_mode':
                    return self.encoder.encode_climate_fan_mode(instance, value)

            elif command_type == 'switch':
                # ON/OFF
                turn_on = (value == 'ON')
                return self.encoder.encode_switch_on_off(instance, turn_on)

            else:
                if self.debug_level > 0:
                    print(f"Unknown command type: {command_type}")
                return None

        except Exception as e:
            if self.debug_level > 0:
                print(f"Encoding error: {e}")
            raise

    def _get_instance_id(self, entity_id: str) -> Optional[int]:
        """
        Get RV-C instance ID for entity

        Args:
            entity_id: Entity ID from HA

        Returns:
            Instance ID or None if not found
        """
        if not self.ha_discovery:
            # If no HA discovery, try to extract instance from entity_id
            # Format: light_ceiling_1 -> instance 1
            match = re.search(r'_(\d+)$', entity_id)
            if match:
                return int(match.group(1))
            return 1  # Default to instance 1

        # Look up entity in HA discovery mapping
        for entity in self.ha_discovery.entities:
            if entity.get('entity_id') == entity_id:
                return entity.get('instance', 1)

        # Not found
        return None

    # =========================================================================
    # MQTT Publishing (Acknowledgments & Errors)
    # =========================================================================

    def _publish_success(self, command: Dict[str, Any], latency_ms: float):
        """Publish success acknowledgment to MQTT"""
        if not self.mqtt_client:
            return

        status_topic = 'rv/command/status'
        payload = json.dumps({
            'entity_id': command.get('entity_id'),
            'command_type': command.get('command_type'),
            'action': command.get('action'),
            'value': command.get('value'),
            'status': 'success',
            'latency_ms': round(latency_ms, 2),
            'timestamp': datetime.now().isoformat()
        })

        self.mqtt_client.publish(status_topic, payload, retain=False)

    def _publish_error(self, command: Dict[str, Any], error_code: str, error_message: str):
        """Publish error to MQTT"""
        if not self.mqtt_client:
            return

        error_topic = 'rv/command/error'
        payload = json.dumps({
            'entity_id': command.get('entity_id'),
            'command_type': command.get('command_type'),
            'error_code': error_code,
            'error_message': error_message,
            'timestamp': datetime.now().isoformat()
        })

        self.mqtt_client.publish(error_topic, payload, retain=False)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _format_frame(self, can_id: int, data: List[int]) -> str:
        """Format CAN frame as hex string for logging"""
        data_hex = ''.join(f'{b:02X}' for b in data)
        return f"{can_id:08X}#{data_hex}"

    def get_stats(self) -> Dict[str, Any]:
        """Get handler statistics"""
        stats = self.stats.copy()

        if stats['total_commands'] > 0:
            stats['success_rate'] = round(
                (stats['successful_commands'] / stats['total_commands']) * 100,
                2
            )
        else:
            stats['success_rate'] = 0

        return stats

    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'total_commands': 0,
            'successful_commands': 0,
            'validation_failures': 0,
            'transmission_failures': 0,
            'encoding_failures': 0,
        }


# =============================================================================
# Testing
# =============================================================================

def test_command_handler():
    """Test command handler"""
    print("Testing CommandHandler...")
    print()

    # Create components (mocked for testing)
    encoder = RVCCommandEncoder()
    validator = CommandValidator(config={
        'security_enabled': True,
        'rate_limit_enabled': True,
        'global_commands_per_second': 10,
        'entity_commands_per_second': 2,
        'entity_cooldown_ms': 100,  # Reduced for testing
        'denylist': [],
        'allowlist': [],
        'allowed_commands': ['light', 'climate', 'switch']
    })

    # Note: Actual CAN TX would require hardware, so we skip that for this test
    print("Test 1: MQTT Message Parsing")

    handler = CommandHandler(
        encoder=encoder,
        validator=validator,
        transmitter=None,  # Would need real CAN bus
        audit_logger=AuditLogger(log_file='logs/test_handler.log', console_output=False),
        debug_level=1
    )

    # Test light commands
    test_cases = [
        ('rv/light/ceiling/set', 'ON', {
            'entity_id': 'ceiling',
            'command_type': 'light',
            'action': 'state',
            'value': 'ON'
        }),
        ('rv/light/ceiling/brightness/set', '75', {
            'entity_id': 'ceiling',
            'command_type': 'light',
            'action': 'brightness',
            'value': 75
        }),
        ('rv/climate/hvac_front/mode/set', 'cool', {
            'entity_id': 'hvac_front',
            'command_type': 'climate',
            'action': 'mode',
            'value': 'cool'
        }),
        ('rv/climate/hvac_front/temperature/set', '72', {
            'entity_id': 'hvac_front',
            'command_type': 'climate',
            'action': 'temperature',
            'value': 72.0
        }),
        ('rv/switch/water_pump/set', 'ON', {
            'entity_id': 'water_pump',
            'command_type': 'switch',
            'action': 'state',
            'value': 'ON'
        }),
    ]

    for topic, payload, expected in test_cases:
        result = handler._parse_mqtt_message(topic, payload)
        if result == expected:
            print(f"  ✓ {topic} → {payload}")
        else:
            print(f"  ✗ {topic} → {payload}")
            print(f"    Expected: {expected}")
            print(f"    Got: {result}")

    print()

    print("Test 2: Command Encoding")
    # Test encoding (without transmission)
    command = {
        'entity_id': 'test_light',
        'command_type': 'light',
        'action': 'brightness',
        'value': 75
    }

    frames = handler._encode_command(command)
    if frames and len(frames) == 3:  # Should have 3-frame sequence
        print(f"  ✓ Encoded to {len(frames)} frames")
        for i, (can_id, data, delay) in enumerate(frames):
            frame_str = handler._format_frame(can_id, data)
            print(f"    Frame {i+1}: {frame_str} (delay={delay}ms)")
    else:
        print(f"  ✗ Encoding failed or unexpected frame count")

    print()

    print("Test 3: Statistics")
    stats = handler.get_stats()
    print(f"  Total commands: {stats['total_commands']}")
    print(f"  Success rate: {stats['success_rate']}%")
    print()

    print("All tests completed!")

    # Cleanup
    import os
    if os.path.exists('logs/test_handler.log'):
        os.remove('logs/test_handler.log')


if __name__ == "__main__":
    test_command_handler()
