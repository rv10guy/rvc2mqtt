#!/usr/bin/env python3
"""
Integration Tests for Phase 2 Bidirectional Communication

Tests the complete command flow from MQTT message parsing through
encoding and validation.
"""

import unittest
import sys
import os
import time
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from command_handler import CommandHandler
from rvc_commands import RVCCommandEncoder
from command_validator import CommandValidator
from audit_logger import AuditLogger


class MockCANTransmitter:
    """Mock CAN transmitter for testing"""

    def __init__(self):
        self.frames_sent = []
        self.send_success = True
        self.send_error = None

    def send_frames(self, frames):
        """Mock send_frames method"""
        if self.send_success:
            self.frames_sent.extend(frames)
            return True, None
        else:
            return False, self.send_error or "CAN transmission failed"


class MockHADiscovery:
    """Mock HA Discovery for testing"""

    def __init__(self):
        self.entities = [
            {'entity_id': 'ceiling_light', 'instance': 1, 'entity_type': 'light'},
            {'entity_id': 'floor_lamp', 'instance': 2, 'entity_type': 'light'},
            {'entity_id': 'hvac_front', 'instance': 1, 'entity_type': 'climate'},
            {'entity_id': 'water_pump', 'instance': 3, 'entity_type': 'switch'},
        ]


class TestMQTTMessageParsing(unittest.TestCase):
    """Test MQTT message parsing"""

    def setUp(self):
        """Set up test handler"""
        encoder = RVCCommandEncoder()
        validator = CommandValidator(config={'security_enabled': False, 'rate_limit_enabled': False})
        transmitter = MockCANTransmitter()
        audit_logger = AuditLogger(log_file='/tmp/test_audit.log', console_output=False)

        self.handler = CommandHandler(
            encoder=encoder,
            validator=validator,
            transmitter=transmitter,
            audit_logger=audit_logger,
            ha_discovery=None,
            mqtt_client=None,
            debug_level=0
        )

    def test_parse_light_on_off(self):
        """Test parsing light ON/OFF command"""
        command = self.handler._parse_mqtt_message('rv/light/ceiling_light/set', 'ON')

        self.assertIsNotNone(command)
        self.assertEqual(command['entity_id'], 'ceiling_light')
        self.assertEqual(command['command_type'], 'light')
        self.assertEqual(command['action'], 'state')
        self.assertEqual(command['value'], 'ON')

    def test_parse_light_brightness(self):
        """Test parsing light brightness command"""
        command = self.handler._parse_mqtt_message('rv/light/ceiling_light/brightness/set', '75')

        self.assertIsNotNone(command)
        self.assertEqual(command['entity_id'], 'ceiling_light')
        self.assertEqual(command['command_type'], 'light')
        self.assertEqual(command['action'], 'brightness')
        self.assertEqual(command['value'], 75)

    def test_parse_climate_mode(self):
        """Test parsing climate mode command"""
        command = self.handler._parse_mqtt_message('rv/climate/hvac_front/mode/set', 'heat')

        self.assertIsNotNone(command)
        self.assertEqual(command['entity_id'], 'hvac_front')
        self.assertEqual(command['command_type'], 'climate')
        self.assertEqual(command['action'], 'mode')
        self.assertEqual(command['value'], 'heat')

    def test_parse_climate_temperature(self):
        """Test parsing climate temperature command"""
        command = self.handler._parse_mqtt_message('rv/climate/hvac_front/temperature/set', '72')

        self.assertIsNotNone(command)
        self.assertEqual(command['entity_id'], 'hvac_front')
        self.assertEqual(command['command_type'], 'climate')
        self.assertEqual(command['action'], 'temperature')
        self.assertEqual(command['value'], 72.0)

    def test_parse_climate_fan_mode(self):
        """Test parsing climate fan mode command"""
        command = self.handler._parse_mqtt_message('rv/climate/hvac_front/fan_mode/set', 'auto')

        self.assertIsNotNone(command)
        self.assertEqual(command['entity_id'], 'hvac_front')
        self.assertEqual(command['command_type'], 'climate')
        self.assertEqual(command['action'], 'fan_mode')
        self.assertEqual(command['value'], 'auto')

    def test_parse_switch_on_off(self):
        """Test parsing switch ON/OFF command"""
        command = self.handler._parse_mqtt_message('rv/switch/water_pump/set', 'ON')

        self.assertIsNotNone(command)
        self.assertEqual(command['entity_id'], 'water_pump')
        self.assertEqual(command['command_type'], 'switch')
        self.assertEqual(command['action'], 'state')
        self.assertEqual(command['value'], 'ON')

    def test_parse_invalid_topic(self):
        """Test parsing invalid topic format"""
        command = self.handler._parse_mqtt_message('invalid/topic/format', 'ON')
        self.assertIsNone(command)

    def test_parse_invalid_payload(self):
        """Test parsing invalid payload"""
        # Non-numeric brightness
        command = self.handler._parse_mqtt_message('rv/light/ceiling_light/brightness/set', 'invalid')
        self.assertIsNone(command)


class TestCommandEncoding(unittest.TestCase):
    """Test command encoding"""

    def setUp(self):
        """Set up test handler"""
        encoder = RVCCommandEncoder()
        validator = CommandValidator(config={'security_enabled': False, 'rate_limit_enabled': False})
        transmitter = MockCANTransmitter()
        audit_logger = AuditLogger(log_file='/tmp/test_audit.log', console_output=False)

        self.handler = CommandHandler(
            encoder=encoder,
            validator=validator,
            transmitter=transmitter,
            audit_logger=audit_logger,
            ha_discovery=MockHADiscovery(),
            mqtt_client=None,
            debug_level=0
        )

    def test_encode_light_on(self):
        """Test encoding light ON command"""
        command = {
            'entity_id': 'ceiling_light',
            'command_type': 'light',
            'action': 'state',
            'value': 'ON'
        }

        frames = self.handler._encode_command(command)

        self.assertIsNotNone(frames)
        self.assertEqual(len(frames), 1)

        can_id, data, delay = frames[0]
        self.assertEqual(data[0], 1)      # Instance 1
        self.assertEqual(data[2], 0xC8)   # Brightness 100%

    def test_encode_light_brightness(self):
        """Test encoding light brightness command"""
        command = {
            'entity_id': 'ceiling_light',
            'command_type': 'light',
            'action': 'brightness',
            'value': 75
        }

        frames = self.handler._encode_command(command)

        self.assertIsNotNone(frames)
        self.assertEqual(len(frames), 3)  # 3-frame sequence

        # Check first frame
        can_id, data, delay = frames[0]
        self.assertEqual(data[0], 1)      # Instance 1
        self.assertEqual(data[2], 150)    # Brightness 75% -> 150

    def test_encode_climate_mode(self):
        """Test encoding climate mode command"""
        command = {
            'entity_id': 'hvac_front',
            'command_type': 'climate',
            'action': 'mode',
            'value': 'heat'
        }

        frames = self.handler._encode_command(command)

        self.assertIsNotNone(frames)
        self.assertEqual(len(frames), 1)

        can_id, data, delay = frames[0]
        self.assertEqual(data[0], 1)      # Instance 1
        self.assertEqual(data[4], 0xF0)   # Heat mode

    def test_encode_climate_temperature(self):
        """Test encoding climate temperature command"""
        command = {
            'entity_id': 'hvac_front',
            'command_type': 'climate',
            'action': 'temperature',
            'value': 72.0
        }

        frames = self.handler._encode_command(command)

        self.assertIsNotNone(frames)
        self.assertGreater(len(frames), 0)

        # Verify temperature is encoded in bytes 3-4
        can_id, data, delay = frames[0]
        temp_value = data[3] | (data[4] << 8)
        self.assertGreater(temp_value, 0)
        self.assertNotEqual(temp_value, 0xFFFF)

    def test_encode_switch_on(self):
        """Test encoding switch ON command"""
        command = {
            'entity_id': 'water_pump',
            'command_type': 'switch',
            'action': 'state',
            'value': 'ON'
        }

        frames = self.handler._encode_command(command)

        self.assertIsNotNone(frames)
        self.assertEqual(len(frames), 1)

        can_id, data, delay = frames[0]
        self.assertEqual(data[0], 3)      # Instance 3
        self.assertEqual(data[2], 0xC8)   # On (200)


class TestEndToEndCommandFlow(unittest.TestCase):
    """Test complete end-to-end command processing"""

    def setUp(self):
        """Set up test handler with all components"""
        self.encoder = RVCCommandEncoder()
        self.validator = CommandValidator(config={
            'security_enabled': True,
            'rate_limit_enabled': True,
            'global_commands_per_second': 10,
            'entity_commands_per_second': 2,
            'entity_cooldown_ms': 100,
            'denylist': [],
            'allowlist': [],
            'allowed_commands': ['light', 'climate', 'switch']
        })
        self.transmitter = MockCANTransmitter()
        self.audit_logger = AuditLogger(log_file='/tmp/test_audit.log', console_output=False)
        self.ha_discovery = MockHADiscovery()

        self.handler = CommandHandler(
            encoder=self.encoder,
            validator=self.validator,
            transmitter=self.transmitter,
            audit_logger=self.audit_logger,
            ha_discovery=self.ha_discovery,
            mqtt_client=None,
            debug_level=0
        )

    def test_successful_light_command(self):
        """Test successful light command processing"""
        # Process light ON command
        success = self.handler.process_mqtt_command('rv/light/ceiling_light/set', 'ON')

        self.assertTrue(success)
        self.assertEqual(len(self.transmitter.frames_sent), 1)

        # Verify stats
        stats = self.handler.get_stats()
        self.assertEqual(stats['total_commands'], 1)
        self.assertEqual(stats['successful_commands'], 1)

    def test_successful_brightness_command(self):
        """Test successful brightness command processing"""
        success = self.handler.process_mqtt_command('rv/light/ceiling_light/brightness/set', '75')

        self.assertTrue(success)
        self.assertEqual(len(self.transmitter.frames_sent), 3)  # 3-frame sequence

    def test_successful_climate_command(self):
        """Test successful climate command processing"""
        success = self.handler.process_mqtt_command('rv/climate/hvac_front/mode/set', 'heat')

        self.assertTrue(success)
        self.assertEqual(len(self.transmitter.frames_sent), 1)

    def test_validation_failure(self):
        """Test command fails validation"""
        # Invalid brightness value
        success = self.handler.process_mqtt_command('rv/light/ceiling_light/brightness/set', '150')

        self.assertFalse(success)
        self.assertEqual(len(self.transmitter.frames_sent), 0)

        # Verify stats
        stats = self.handler.get_stats()
        self.assertEqual(stats['validation_failures'], 1)

    def test_transmission_failure(self):
        """Test command fails transmission"""
        # Set transmitter to fail
        self.transmitter.send_success = False
        self.transmitter.send_error = "CAN bus timeout"

        success = self.handler.process_mqtt_command('rv/light/ceiling_light/set', 'ON')

        self.assertFalse(success)

        # Verify stats
        stats = self.handler.get_stats()
        self.assertEqual(stats['transmission_failures'], 1)

    def test_invalid_topic(self):
        """Test invalid MQTT topic"""
        success = self.handler.process_mqtt_command('invalid/topic', 'ON')

        self.assertFalse(success)
        self.assertEqual(len(self.transmitter.frames_sent), 0)

    def test_rate_limiting(self):
        """Test rate limiting enforcement"""
        # Reset transmitter
        self.transmitter.frames_sent = []

        # Send multiple commands rapidly
        topic = 'rv/light/ceiling_light/set'

        # First command should succeed
        success1 = self.handler.process_mqtt_command(topic, 'ON')
        self.assertTrue(success1)

        # Wait for cooldown
        time.sleep(0.15)

        # Second command should succeed
        success2 = self.handler.process_mqtt_command(topic, 'OFF')
        self.assertTrue(success2)

        # Third command (immediate) should fail cooldown
        success3 = self.handler.process_mqtt_command(topic, 'ON')
        self.assertFalse(success3)

        # Verify stats
        stats = self.handler.get_stats()
        self.assertEqual(stats['successful_commands'], 2)
        self.assertEqual(stats['validation_failures'], 1)


class TestStatistics(unittest.TestCase):
    """Test statistics tracking"""

    def setUp(self):
        """Set up test handler"""
        encoder = RVCCommandEncoder()
        validator = CommandValidator(config={'security_enabled': False, 'rate_limit_enabled': False})
        transmitter = MockCANTransmitter()
        audit_logger = AuditLogger(log_file='/tmp/test_audit.log', console_output=False)

        self.handler = CommandHandler(
            encoder=encoder,
            validator=validator,
            transmitter=transmitter,
            audit_logger=audit_logger,
            ha_discovery=MockHADiscovery(),
            mqtt_client=None,
            debug_level=0
        )

    def test_success_rate_calculation(self):
        """Test success rate is calculated correctly"""
        # Process some commands
        self.handler.process_mqtt_command('rv/light/ceiling_light/set', 'ON')
        self.handler.process_mqtt_command('rv/light/ceiling_light/set', 'OFF')
        self.handler.process_mqtt_command('rv/light/ceiling_light/brightness/set', '150')  # Invalid

        stats = self.handler.get_stats()

        self.assertEqual(stats['total_commands'], 3)
        self.assertEqual(stats['successful_commands'], 2)
        self.assertEqual(stats['validation_failures'], 1)
        self.assertAlmostEqual(stats['success_rate'], 66.67, places=1)

    def test_stats_reset(self):
        """Test statistics can be reset"""
        # Process some commands
        self.handler.process_mqtt_command('rv/light/ceiling_light/set', 'ON')
        self.handler.process_mqtt_command('rv/light/ceiling_light/set', 'OFF')

        # Reset
        self.handler.reset_stats()

        stats = self.handler.get_stats()
        self.assertEqual(stats['total_commands'], 0)
        self.assertEqual(stats['successful_commands'], 0)


def run_tests():
    """Run all integration tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestMQTTMessageParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestCommandEncoding))
    suite.addTests(loader.loadTestsFromTestCase(TestEndToEndCommandFlow))
    suite.addTests(loader.loadTestsFromTestCase(TestStatistics))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit(run_tests())
