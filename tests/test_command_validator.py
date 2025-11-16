#!/usr/bin/env python3
"""
Unit Tests for Command Validator

Tests all validation layers: schema, entity, range, security, and rate limiting.
"""

import unittest
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from command_validator import CommandValidator, ValidationError


class TestSchemaValidation(unittest.TestCase):
    """Test schema validation (Layer 1)"""

    def setUp(self):
        """Set up test validator"""
        self.validator = CommandValidator(config={
            'security_enabled': False,
            'rate_limit_enabled': False,
        })

    def test_valid_light_command(self):
        """Test valid light command passes schema validation"""
        command = {
            'entity_id': 'ceiling_light',
            'command_type': 'light',
            'action': 'state',
            'value': 'ON'
        }

        valid, error = self.validator.validate(command)
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_missing_entity_id(self):
        """Test command missing entity_id fails"""
        command = {
            'command_type': 'light',
            'action': 'state',
            'value': 'ON'
        }

        valid, error = self.validator.validate(command)
        self.assertFalse(valid)
        self.assertEqual(error.code, 'E001')
        self.assertEqual(error.field, 'entity_id')

    def test_missing_command_type(self):
        """Test command missing command_type fails"""
        command = {
            'entity_id': 'ceiling_light',
            'action': 'state',
            'value': 'ON'
        }

        valid, error = self.validator.validate(command)
        self.assertFalse(valid)
        self.assertEqual(error.code, 'E001')
        self.assertEqual(error.field, 'command_type')

    def test_missing_value(self):
        """Test command missing value fails"""
        command = {
            'entity_id': 'ceiling_light',
            'command_type': 'light',
            'action': 'state'
        }

        valid, error = self.validator.validate(command)
        self.assertFalse(valid)
        self.assertEqual(error.code, 'E001')
        self.assertEqual(error.field, 'value')

    def test_invalid_command_type(self):
        """Test invalid command type fails"""
        command = {
            'entity_id': 'test',
            'command_type': 'invalid_type',
            'value': 'ON'
        }

        valid, error = self.validator.validate(command)
        self.assertFalse(valid)
        self.assertEqual(error.code, 'E002')

    def test_invalid_action(self):
        """Test invalid action for command type fails"""
        command = {
            'entity_id': 'test',
            'command_type': 'light',
            'action': 'invalid_action',
            'value': 'ON'
        }

        valid, error = self.validator.validate(command)
        self.assertFalse(valid)
        self.assertEqual(error.code, 'E003')


class TestValueRangeValidation(unittest.TestCase):
    """Test value range validation (Layer 3)"""

    def setUp(self):
        """Set up test validator"""
        self.validator = CommandValidator(config={
            'security_enabled': False,
            'rate_limit_enabled': False,
        })

    # Light value tests
    def test_light_state_valid_on(self):
        """Test valid light state ON"""
        command = {
            'entity_id': 'test',
            'command_type': 'light',
            'action': 'state',
            'value': 'ON'
        }

        valid, error = self.validator.validate(command)
        self.assertTrue(valid)

    def test_light_state_valid_off(self):
        """Test valid light state OFF"""
        command = {
            'entity_id': 'test',
            'command_type': 'light',
            'action': 'state',
            'value': 'OFF'
        }

        valid, error = self.validator.validate(command)
        self.assertTrue(valid)

    def test_light_state_case_insensitive(self):
        """Test light state is case-insensitive"""
        for value in ['on', 'ON', 'On', 'off', 'OFF', 'Off']:
            command = {
                'entity_id': 'test',
                'command_type': 'light',
                'action': 'state',
                'value': value
            }

            valid, error = self.validator.validate(command)
            self.assertTrue(valid, f"Failed for value: {value}")

    def test_light_state_invalid(self):
        """Test invalid light state fails"""
        command = {
            'entity_id': 'test',
            'command_type': 'light',
            'action': 'state',
            'value': 'INVALID'
        }

        valid, error = self.validator.validate(command)
        self.assertFalse(valid)
        self.assertEqual(error.code, 'E015')

    def test_light_brightness_valid_range(self):
        """Test valid brightness values"""
        for brightness in [0, 1, 50, 99, 100]:
            command = {
                'entity_id': 'test',
                'command_type': 'light',
                'action': 'brightness',
                'value': brightness
            }

            valid, error = self.validator.validate(command)
            self.assertTrue(valid, f"Failed for brightness: {brightness}")

    def test_light_brightness_below_minimum(self):
        """Test brightness below minimum fails"""
        command = {
            'entity_id': 'test',
            'command_type': 'light',
            'action': 'brightness',
            'value': -1
        }

        valid, error = self.validator.validate(command)
        self.assertFalse(valid)
        self.assertEqual(error.code, 'E013')

    def test_light_brightness_above_maximum(self):
        """Test brightness above maximum fails"""
        command = {
            'entity_id': 'test',
            'command_type': 'light',
            'action': 'brightness',
            'value': 101
        }

        valid, error = self.validator.validate(command)
        self.assertFalse(valid)
        self.assertEqual(error.code, 'E014')

    def test_light_brightness_wrong_type(self):
        """Test brightness with wrong type fails"""
        command = {
            'entity_id': 'test',
            'command_type': 'light',
            'action': 'brightness',
            'value': 'fifty'
        }

        valid, error = self.validator.validate(command)
        self.assertFalse(valid)
        self.assertEqual(error.code, 'E012')

    # Climate value tests
    def test_climate_mode_valid_values(self):
        """Test valid climate modes"""
        for mode in ['off', 'heat', 'cool', 'auto']:
            command = {
                'entity_id': 'test',
                'command_type': 'climate',
                'action': 'mode',
                'value': mode
            }

            valid, error = self.validator.validate(command)
            self.assertTrue(valid, f"Failed for mode: {mode}")

    def test_climate_mode_case_insensitive(self):
        """Test climate mode is case-insensitive"""
        for mode in ['OFF', 'Off', 'HEAT', 'Heat', 'COOL', 'Cool', 'AUTO', 'Auto']:
            command = {
                'entity_id': 'test',
                'command_type': 'climate',
                'action': 'mode',
                'value': mode
            }

            valid, error = self.validator.validate(command)
            self.assertTrue(valid, f"Failed for mode: {mode}")

    def test_climate_mode_invalid(self):
        """Test invalid climate mode fails"""
        command = {
            'entity_id': 'test',
            'command_type': 'climate',
            'action': 'mode',
            'value': 'invalid_mode'
        }

        valid, error = self.validator.validate(command)
        self.assertFalse(valid)
        self.assertEqual(error.code, 'E015')

    def test_climate_temperature_valid_range(self):
        """Test valid temperature values"""
        for temp in [60, 65, 70, 72, 75, 80, 85, 90]:
            command = {
                'entity_id': 'test',
                'command_type': 'climate',
                'action': 'temperature',
                'value': temp
            }

            valid, error = self.validator.validate(command)
            self.assertTrue(valid, f"Failed for temp: {temp}")

    def test_climate_temperature_below_minimum(self):
        """Test temperature below minimum fails"""
        command = {
            'entity_id': 'test',
            'command_type': 'climate',
            'action': 'temperature',
            'value': 59
        }

        valid, error = self.validator.validate(command)
        self.assertFalse(valid)
        self.assertEqual(error.code, 'E013')

    def test_climate_temperature_above_maximum(self):
        """Test temperature above maximum fails"""
        command = {
            'entity_id': 'test',
            'command_type': 'climate',
            'action': 'temperature',
            'value': 91
        }

        valid, error = self.validator.validate(command)
        self.assertFalse(valid)
        self.assertEqual(error.code, 'E014')

    def test_climate_fan_mode_valid(self):
        """Test valid fan modes"""
        for fan_mode in ['auto', 'on', 'low', 'high']:
            command = {
                'entity_id': 'test',
                'command_type': 'climate',
                'action': 'fan_mode',
                'value': fan_mode
            }

            valid, error = self.validator.validate(command)
            self.assertTrue(valid, f"Failed for fan_mode: {fan_mode}")

    def test_climate_fan_mode_invalid(self):
        """Test invalid fan mode fails"""
        command = {
            'entity_id': 'test',
            'command_type': 'climate',
            'action': 'fan_mode',
            'value': 'invalid'
        }

        valid, error = self.validator.validate(command)
        self.assertFalse(valid)
        self.assertEqual(error.code, 'E015')

    # Switch value tests
    def test_switch_state_valid(self):
        """Test valid switch states"""
        for state in ['ON', 'OFF', 'on', 'off']:
            command = {
                'entity_id': 'test',
                'command_type': 'switch',
                'action': 'state',
                'value': state
            }

            valid, error = self.validator.validate(command)
            self.assertTrue(valid, f"Failed for state: {state}")

    def test_switch_state_invalid(self):
        """Test invalid switch state fails"""
        command = {
            'entity_id': 'test',
            'command_type': 'switch',
            'action': 'state',
            'value': 'toggle'
        }

        valid, error = self.validator.validate(command)
        self.assertFalse(valid)
        self.assertEqual(error.code, 'E015')


class TestSecurityControls(unittest.TestCase):
    """Test security controls (Layer 4)"""

    def test_denylist_blocks_entity(self):
        """Test denylist blocks denied entities"""
        validator = CommandValidator(config={
            'security_enabled': True,
            'denylist': ['blocked_light', 'blocked_switch'],
            'rate_limit_enabled': False,
        })

        command = {
            'entity_id': 'blocked_light',
            'command_type': 'light',
            'action': 'state',
            'value': 'ON'
        }

        valid, error = validator.validate(command)
        self.assertFalse(valid)
        self.assertEqual(error.code, 'E016')

    def test_denylist_allows_other_entities(self):
        """Test denylist allows non-denied entities"""
        validator = CommandValidator(config={
            'security_enabled': True,
            'denylist': ['blocked_light'],
            'rate_limit_enabled': False,
        })

        command = {
            'entity_id': 'allowed_light',
            'command_type': 'light',
            'action': 'state',
            'value': 'ON'
        }

        valid, error = validator.validate(command)
        self.assertTrue(valid)

    def test_allowlist_allows_listed_entity(self):
        """Test allowlist allows listed entities"""
        validator = CommandValidator(config={
            'security_enabled': True,
            'allowlist': ['allowed_light', 'allowed_switch'],
            'rate_limit_enabled': False,
        })

        command = {
            'entity_id': 'allowed_light',
            'command_type': 'light',
            'action': 'state',
            'value': 'ON'
        }

        valid, error = validator.validate(command)
        self.assertTrue(valid)

    def test_allowlist_blocks_unlisted_entity(self):
        """Test allowlist blocks unlisted entities"""
        validator = CommandValidator(config={
            'security_enabled': True,
            'allowlist': ['allowed_light'],
            'rate_limit_enabled': False,
        })

        command = {
            'entity_id': 'other_light',
            'command_type': 'light',
            'action': 'state',
            'value': 'ON'
        }

        valid, error = validator.validate(command)
        self.assertFalse(valid)
        self.assertEqual(error.code, 'E017')

    def test_allowed_commands_permits_listed_type(self):
        """Test allowed_commands permits listed command types"""
        validator = CommandValidator(config={
            'security_enabled': True,
            'allowed_commands': ['light', 'switch'],
            'rate_limit_enabled': False,
        })

        command = {
            'entity_id': 'test',
            'command_type': 'light',
            'action': 'state',
            'value': 'ON'
        }

        valid, error = validator.validate(command)
        self.assertTrue(valid)

    def test_allowed_commands_blocks_unlisted_type(self):
        """Test allowed_commands blocks unlisted command types"""
        validator = CommandValidator(config={
            'security_enabled': True,
            'allowed_commands': ['light'],
            'rate_limit_enabled': False,
        })

        command = {
            'entity_id': 'test',
            'command_type': 'climate',
            'action': 'mode',
            'value': 'heat'
        }

        valid, error = validator.validate(command)
        self.assertFalse(valid)
        self.assertEqual(error.code, 'E018')

    def test_security_disabled(self):
        """Test security checks disabled when security_enabled=False"""
        validator = CommandValidator(config={
            'security_enabled': False,
            'denylist': ['blocked_light'],
            'allowlist': ['allowed_light'],
            'allowed_commands': ['light'],
            'rate_limit_enabled': False,
        })

        # Should allow blocked entity when security disabled
        command = {
            'entity_id': 'blocked_light',
            'command_type': 'climate',  # Not in allowed_commands
            'action': 'mode',
            'value': 'heat'
        }

        valid, error = validator.validate(command)
        self.assertTrue(valid)


class TestRateLimiting(unittest.TestCase):
    """Test rate limiting (Layer 5)"""

    def test_global_rate_limit(self):
        """Test global rate limiting enforces commands per second"""
        validator = CommandValidator(config={
            'security_enabled': False,
            'rate_limit_enabled': True,
            'global_commands_per_second': 2,  # Allow 2 commands per second
        })

        command = {
            'entity_id': 'test',
            'command_type': 'light',
            'action': 'state',
            'value': 'ON'
        }

        # First 2 commands should succeed
        valid1, _ = validator.validate(command)
        self.assertTrue(valid1)

        valid2, _ = validator.validate(command)
        self.assertTrue(valid2)

        # Third command should fail (exceeded rate limit)
        valid3, error3 = validator.validate(command)
        self.assertFalse(valid3)
        self.assertEqual(error3.code, 'E019')

        # Wait and try again - should succeed
        time.sleep(1.1)
        valid4, _ = validator.validate(command)
        self.assertTrue(valid4)

    def test_entity_rate_limit(self):
        """Test per-entity rate limiting"""
        validator = CommandValidator(config={
            'security_enabled': False,
            'rate_limit_enabled': True,
            'global_commands_per_second': 100,  # High global limit
            'entity_commands_per_second': 1,     # 1 command per entity per second
        })

        command1 = {
            'entity_id': 'light1',
            'command_type': 'light',
            'action': 'state',
            'value': 'ON'
        }

        command2 = {
            'entity_id': 'light2',
            'command_type': 'light',
            'action': 'state',
            'value': 'ON'
        }

        # First command to light1 should succeed
        valid1, _ = validator.validate(command1)
        self.assertTrue(valid1)

        # Second command to light1 should fail (entity rate limit)
        valid2, error2 = validator.validate(command1)
        self.assertFalse(valid2)
        self.assertEqual(error2.code, 'E019')

        # Command to different entity should succeed
        valid3, _ = validator.validate(command2)
        self.assertTrue(valid3)

    def test_entity_cooldown(self):
        """Test per-entity cooldown period"""
        validator = CommandValidator(config={
            'security_enabled': False,
            'rate_limit_enabled': True,
            'global_commands_per_second': 100,
            'entity_commands_per_second': 10,
            'entity_cooldown_ms': 500,  # 500ms cooldown
        })

        command = {
            'entity_id': 'test_light',
            'command_type': 'light',
            'action': 'state',
            'value': 'ON'
        }

        # First command should succeed
        valid1, _ = validator.validate(command)
        self.assertTrue(valid1)

        # Immediate second command should fail (cooldown)
        valid2, error2 = validator.validate(command)
        self.assertFalse(valid2)
        self.assertEqual(error2.code, 'E020')

        # Wait for cooldown and try again
        time.sleep(0.6)
        valid3, _ = validator.validate(command)
        self.assertTrue(valid3)

    def test_rate_limiting_disabled(self):
        """Test rate limiting disabled when rate_limit_enabled=False"""
        validator = CommandValidator(config={
            'security_enabled': False,
            'rate_limit_enabled': False,
            'global_commands_per_second': 1,
            'entity_commands_per_second': 1,
            'entity_cooldown_ms': 1000,
        })

        command = {
            'entity_id': 'test',
            'command_type': 'light',
            'action': 'state',
            'value': 'ON'
        }

        # Should allow rapid commands when disabled
        for _ in range(10):
            valid, error = validator.validate(command)
            self.assertTrue(valid)


class TestValidationStatistics(unittest.TestCase):
    """Test validation statistics tracking"""

    def test_stats_tracking(self):
        """Test validation statistics are tracked correctly"""
        validator = CommandValidator(config={
            'security_enabled': False,
            'rate_limit_enabled': False,
        })

        # Valid command
        valid_command = {
            'entity_id': 'test',
            'command_type': 'light',
            'action': 'state',
            'value': 'ON'
        }

        # Invalid command
        invalid_command = {
            'entity_id': 'test',
            'command_type': 'light',
            'action': 'state',
            'value': 'INVALID'
        }

        # Process some commands
        validator.validate(valid_command)
        validator.validate(valid_command)
        validator.validate(invalid_command)

        stats = validator.get_stats()

        self.assertEqual(stats['total_validations'], 3)
        self.assertEqual(stats['successful_validations'], 2)
        self.assertEqual(stats['failed_validations'], 1)
        self.assertGreater(stats['success_rate'], 60)

    def test_stats_reset(self):
        """Test statistics can be reset"""
        validator = CommandValidator(config={
            'security_enabled': False,
            'rate_limit_enabled': False,
        })

        command = {
            'entity_id': 'test',
            'command_type': 'light',
            'action': 'state',
            'value': 'ON'
        }

        # Process some commands
        validator.validate(command)
        validator.validate(command)

        # Reset
        validator.reset_stats()

        stats = validator.get_stats()
        self.assertEqual(stats['total_validations'], 0)
        self.assertEqual(stats['successful_validations'], 0)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestSchemaValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestValueRangeValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestSecurityControls))
    suite.addTests(loader.loadTestsFromTestCase(TestRateLimiting))
    suite.addTests(loader.loadTestsFromTestCase(TestValidationStatistics))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit(run_tests())
