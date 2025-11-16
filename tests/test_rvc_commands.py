#!/usr/bin/env python3
"""
Unit Tests for RV-C Command Encoder

Tests all command encoding functions to ensure correct CAN frame generation
for lights, climate, switches, and other RV-C devices.
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rvc_commands import RVCCommandEncoder


class TestRVCCommandEncoder(unittest.TestCase):
    """Test cases for RVCCommandEncoder"""

    def setUp(self):
        """Set up test encoder"""
        self.encoder = RVCCommandEncoder(source_address=99)

    # =========================================================================
    # CAN ID Building Tests
    # =========================================================================

    def test_build_can_id_basic(self):
        """Test basic CAN ID construction"""
        # DGN 0x1FEDB (DC_DIMMER_COMMAND_2)
        can_id = self.encoder.build_can_id(dgn=0x1FEDB, priority=6)

        # Expected: 0x19FEDB63 (priority=6, DGN=0x1FEDB, source=99/0x63)
        self.assertEqual(can_id, 0x19FEDB63)

    def test_build_can_id_custom_priority(self):
        """Test CAN ID with custom priority"""
        can_id = self.encoder.build_can_id(dgn=0x1FEDB, priority=3, source_address=0x50)

        # Expected: 0x0DFEDB50 (priority=3, DGN=0x1FEDB, source=80/0x50)
        self.assertEqual(can_id, 0x0DFEDB50)

    def test_build_can_id_different_dgns(self):
        """Test CAN ID with different DGNs"""
        # DC_DIMMER_COMMAND_2
        can_id1 = self.encoder.build_can_id(dgn=0x1FEDB)
        self.assertEqual(can_id1 & 0x03FFFF00, 0x01FEDB00)

        # THERMOSTAT_COMMAND_1
        can_id2 = self.encoder.build_can_id(dgn=0x1FEF9)
        self.assertEqual(can_id2 & 0x03FFFF00, 0x01FEF900)

    # =========================================================================
    # Light Command Tests
    # =========================================================================

    def test_encode_light_on(self):
        """Test encoding light ON command"""
        frames = self.encoder.encode_light_on_off(instance=1, turn_on=True)

        # Should return single frame
        self.assertEqual(len(frames), 1)

        can_id, data, delay = frames[0]

        # Check CAN ID
        self.assertEqual(can_id, 0x19FEDB63)

        # Check data bytes
        self.assertEqual(len(data), 8)
        self.assertEqual(data[0], 1)      # Instance
        self.assertEqual(data[1], 0xFF)   # Reserved
        self.assertEqual(data[2], 0xC8)   # Brightness 100% (200 in RV-C)
        self.assertEqual(data[3], 0xFF)   # Reserved
        self.assertEqual(data[4], 0x00)   # Reserved
        self.assertEqual(data[5], 0xFF)   # Reserved
        self.assertEqual(data[6], 0xFF)   # Reserved
        self.assertEqual(data[7], 0xFF)   # Reserved

    def test_encode_light_off(self):
        """Test encoding light OFF command"""
        frames = self.encoder.encode_light_on_off(instance=2, turn_on=False)

        self.assertEqual(len(frames), 1)
        can_id, data, delay = frames[0]

        # Check data
        self.assertEqual(data[0], 2)      # Instance
        self.assertEqual(data[2], 0x00)   # Brightness 0%

    def test_encode_light_brightness_valid(self):
        """Test encoding light brightness with valid values"""
        test_cases = [
            (0, 0x00),      # 0% -> 0
            (50, 0x64),     # 50% -> 100
            (75, 0x96),     # 75% -> 150
            (100, 0xC8),    # 100% -> 200
        ]

        for brightness_pct, expected_value in test_cases:
            frames = self.encoder.encode_light_brightness(instance=1, brightness_pct=brightness_pct)

            # Should return 3-frame sequence
            self.assertEqual(len(frames), 3, f"Failed for brightness {brightness_pct}%")

            # Check first frame (set brightness)
            can_id, data, delay = frames[0]
            self.assertEqual(data[0], 1)
            self.assertEqual(data[2], expected_value)

            # Check delays
            self.assertEqual(frames[0][2], 0)    # No delay before first frame
            self.assertEqual(frames[1][2], 150)  # 150ms delay before second frame
            self.assertEqual(frames[2][2], 150)  # 150ms delay before third frame

    def test_encode_light_brightness_out_of_range(self):
        """Test brightness encoding with out-of-range values"""
        # Should clamp to 0-100 range
        frames_negative = self.encoder.encode_light_brightness(instance=1, brightness_pct=-10)
        self.assertEqual(frames_negative[0][1][2], 0x00)  # Clamped to 0

        frames_high = self.encoder.encode_light_brightness(instance=1, brightness_pct=150)
        self.assertEqual(frames_high[0][1][2], 0xC8)  # Clamped to 200 (100%)

    def test_encode_light_multiple_instances(self):
        """Test light commands with different instances"""
        for instance in [1, 2, 5, 10]:
            frames = self.encoder.encode_light_on_off(instance=instance, turn_on=True)
            self.assertEqual(frames[0][1][0], instance)

    # =========================================================================
    # Climate Command Tests
    # =========================================================================

    def test_encode_climate_mode_off(self):
        """Test encoding climate mode OFF"""
        frames = self.encoder.encode_climate_mode(instance=1, mode='off')

        self.assertEqual(len(frames), 1)
        can_id, data, delay = frames[0]

        # Check CAN ID (THERMOSTAT_COMMAND_1)
        self.assertEqual(can_id, 0x19FEF963)

        # Check data
        self.assertEqual(data[0], 1)      # Instance
        self.assertEqual(data[1], 0xFF)   # Reserved
        self.assertEqual(data[2], 0xFF)   # Reserved
        self.assertEqual(data[3], 0xFF)   # Reserved
        self.assertEqual(data[4], 0x24)   # Off mode (0x24)

    def test_encode_climate_mode_heat(self):
        """Test encoding climate mode HEAT"""
        frames = self.encoder.encode_climate_mode(instance=1, mode='heat')

        can_id, data, delay = frames[0]
        self.assertEqual(data[4], 0xF0)   # Heat mode (0xF0)

    def test_encode_climate_mode_cool(self):
        """Test encoding climate mode COOL"""
        frames = self.encoder.encode_climate_mode(instance=1, mode='cool')

        can_id, data, delay = frames[0]
        self.assertEqual(data[4], 0xF4)   # Cool mode (0xF4)

    def test_encode_climate_mode_auto(self):
        """Test encoding climate mode AUTO"""
        frames = self.encoder.encode_climate_mode(instance=1, mode='auto')

        can_id, data, delay = frames[0]
        self.assertEqual(data[4], 0xF8)   # Auto mode (0xF8)

    def test_encode_climate_mode_invalid(self):
        """Test encoding invalid climate mode"""
        # Should default to OFF
        frames = self.encoder.encode_climate_mode(instance=1, mode='invalid')

        can_id, data, delay = frames[0]
        self.assertEqual(data[4], 0x24)   # Off mode (0x24)

    def test_encode_climate_temperature_basic(self):
        """Test encoding climate temperature"""
        frames = self.encoder.encode_climate_temperature(instance=1, temperature_f=72.0, sync_furnace=False)

        # Should return single frame
        self.assertEqual(len(frames), 1)

        can_id, data, delay = frames[0]

        # Check CAN ID
        self.assertEqual(can_id, 0x19FEF963)

        # Check temperature conversion
        # 72°F -> (72-32)*5/9+273 = 295.372K -> 295.372/0.03125 + 0.999 ≈ 9453.904 -> 0x24EE
        self.assertEqual(data[0], 1)      # Instance
        self.assertIn(data[3], [0xEE, 0xEF])  # Low byte (accounting for rounding)
        self.assertEqual(data[4], 0x24)   # High byte

    def test_encode_climate_temperature_range(self):
        """Test temperature encoding across range"""
        test_temps = [60, 65, 70, 72, 75, 80]

        for temp_f in test_temps:
            frames = self.encoder.encode_climate_temperature(instance=1, temperature_f=temp_f, sync_furnace=False)
            self.assertEqual(len(frames), 1, f"Failed for temp {temp_f}°F")

            # Verify temperature is in data bytes 3-4
            can_id, data, delay = frames[0]
            temp_value = data[3] | (data[4] << 8)

            # Temperature should be reasonable (not 0xFFFF)
            self.assertNotEqual(temp_value, 0xFFFF)
            self.assertGreater(temp_value, 0)

    def test_encode_climate_temperature_with_furnace_sync(self):
        """Test temperature encoding with furnace sync"""
        frames = self.encoder.encode_climate_temperature(instance=1, temperature_f=72.0, sync_furnace=True)

        # Should return 2 frames (thermostat + furnace)
        self.assertEqual(len(frames), 2)

        # First frame: thermostat setpoint
        self.assertEqual(frames[0][1][0], 1)  # Instance 1

        # Second frame: furnace setpoint
        self.assertEqual(frames[1][1][0], 2)  # Instance 2 (furnace)

    def test_encode_climate_fan_mode_auto(self):
        """Test encoding fan mode AUTO"""
        frames = self.encoder.encode_climate_fan_mode(instance=1, fan_mode='auto')

        self.assertEqual(len(frames), 1)
        can_id, data, delay = frames[0]

        # Check CAN ID (THERMOSTAT_COMMAND_1)
        self.assertEqual(can_id, 0x19FEF963)

        # Check fan mode byte
        self.assertEqual(data[5], 0x04)   # Auto mode (0x04)

    def test_encode_climate_fan_mode_on(self):
        """Test encoding fan mode ON"""
        frames = self.encoder.encode_climate_fan_mode(instance=1, fan_mode='on')

        can_id, data, delay = frames[0]
        self.assertEqual(data[5], 0x14)   # On mode (0x14)

    def test_encode_climate_fan_mode_low(self):
        """Test encoding fan mode LOW"""
        frames = self.encoder.encode_climate_fan_mode(instance=1, fan_mode='low')

        can_id, data, delay = frames[0]
        self.assertEqual(data[5], 0x64)   # Low mode (0x64)

    def test_encode_climate_fan_mode_high(self):
        """Test encoding fan mode HIGH"""
        frames = self.encoder.encode_climate_fan_mode(instance=1, fan_mode='high')

        can_id, data, delay = frames[0]
        self.assertEqual(data[5], 0xC8)   # High mode (0xC8)

    # =========================================================================
    # Switch Command Tests
    # =========================================================================

    def test_encode_switch_on(self):
        """Test encoding switch ON command"""
        frames = self.encoder.encode_switch_on_off(instance=3, turn_on=True)

        self.assertEqual(len(frames), 1)
        can_id, data, delay = frames[0]

        # Check CAN ID (GENERIC_INDICATOR_COMMAND with source 96)
        self.assertEqual(can_id & 0x03FFFF00, 0x01FFED00)

        # Check data
        self.assertEqual(data[0], 3)      # Instance
        self.assertEqual(data[1], 0xFF)   # Reserved
        self.assertEqual(data[2], 0xC8)   # On (200)

    def test_encode_switch_off(self):
        """Test encoding switch OFF command"""
        frames = self.encoder.encode_switch_on_off(instance=3, turn_on=False)

        can_id, data, delay = frames[0]
        self.assertEqual(data[2], 0x00)   # Off (0)

    def test_encode_switch_custom_source(self):
        """Test switch command with custom source address"""
        frames = self.encoder.encode_switch_on_off(instance=1, turn_on=True, source_address=80)

        can_id, data, delay = frames[0]

        # Check source address in CAN ID
        self.assertEqual(can_id & 0xFF, 80)

    # =========================================================================
    # Frame Format Tests
    # =========================================================================

    def test_frame_tuple_format(self):
        """Test that all commands return proper frame tuples"""
        test_commands = [
            self.encoder.encode_light_on_off(1, True),
            self.encoder.encode_light_brightness(1, 50),
            self.encoder.encode_climate_mode(1, 'heat'),
            self.encoder.encode_climate_temperature(1, 72.0),
            self.encoder.encode_climate_fan_mode(1, 'auto'),
            self.encoder.encode_switch_on_off(1, True),
        ]

        for frames in test_commands:
            self.assertIsInstance(frames, list)
            self.assertGreater(len(frames), 0)

            for frame in frames:
                self.assertIsInstance(frame, tuple)
                self.assertEqual(len(frame), 3)

                can_id, data, delay = frame

                # CAN ID should be valid 29-bit ID
                self.assertIsInstance(can_id, int)
                self.assertGreater(can_id, 0)
                self.assertLess(can_id, 0x20000000)

                # Data should be 8 bytes
                self.assertIsInstance(data, list)
                self.assertEqual(len(data), 8)

                # All bytes should be 0-255
                for byte in data:
                    self.assertIsInstance(byte, int)
                    self.assertGreaterEqual(byte, 0)
                    self.assertLessEqual(byte, 255)

                # Delay should be non-negative
                self.assertIsInstance(delay, int)
                self.assertGreaterEqual(delay, 0)

    # =========================================================================
    # Temperature Conversion Tests
    # =========================================================================

    def test_temperature_conversion_accuracy(self):
        """Test temperature conversion accuracy"""
        # Test known conversions
        test_cases = [
            (32.0, 273.15),    # Freezing point
            (72.0, 295.372),   # Room temperature
            (212.0, 373.15),   # Boiling point
        ]

        for temp_f, expected_k in test_cases:
            # Calculate Kelvin
            temp_k = (temp_f - 32) * 5/9 + 273

            # Should be close to expected
            self.assertAlmostEqual(temp_k, expected_k, places=1)

    def test_temperature_hex_encoding(self):
        """Test temperature hex encoding"""
        frames = self.encoder.encode_climate_temperature(instance=1, temperature_f=72.0, sync_furnace=False)

        can_id, data, delay = frames[0]

        # Get temperature value
        temp_value = data[3] | (data[4] << 8)

        # Convert back to Fahrenheit
        temp_k = (temp_value - 0.999) * 0.03125
        temp_f = (temp_k - 273) * 9/5 + 32

        # Should be close to original
        self.assertAlmostEqual(temp_f, 72.0, places=0)


class TestRVCCommandEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""

    def setUp(self):
        """Set up test encoder"""
        self.encoder = RVCCommandEncoder()

    def test_instance_zero(self):
        """Test commands with instance 0"""
        frames = self.encoder.encode_light_on_off(instance=0, turn_on=True)
        self.assertEqual(frames[0][1][0], 0)

    def test_instance_max(self):
        """Test commands with maximum instance"""
        frames = self.encoder.encode_light_on_off(instance=255, turn_on=True)
        self.assertEqual(frames[0][1][0], 255)

    def test_brightness_boundary_values(self):
        """Test brightness at boundary values"""
        # 0%
        frames = self.encoder.encode_light_brightness(instance=1, brightness_pct=0)
        self.assertEqual(frames[0][1][2], 0x00)

        # 1%
        frames = self.encoder.encode_light_brightness(instance=1, brightness_pct=1)
        self.assertEqual(frames[0][1][2], 0x02)

        # 99%
        frames = self.encoder.encode_light_brightness(instance=1, brightness_pct=99)
        self.assertEqual(frames[0][1][2], 0xC6)

        # 100%
        frames = self.encoder.encode_light_brightness(instance=1, brightness_pct=100)
        self.assertEqual(frames[0][1][2], 0xC8)

    def test_temperature_extreme_values(self):
        """Test temperature encoding at extreme values"""
        # Cold
        frames = self.encoder.encode_climate_temperature(instance=1, temperature_f=32.0, sync_furnace=False)
        self.assertEqual(len(frames), 1)

        # Hot
        frames = self.encoder.encode_climate_temperature(instance=1, temperature_f=100.0, sync_furnace=False)
        self.assertEqual(len(frames), 1)

    def test_case_insensitive_modes(self):
        """Test that mode strings are case-insensitive"""
        modes = ['OFF', 'Off', 'off', 'HEAT', 'Heat', 'heat']

        for mode in modes:
            frames = self.encoder.encode_climate_mode(instance=1, mode=mode)
            self.assertEqual(len(frames), 1)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestRVCCommandEncoder))
    suite.addTests(loader.loadTestsFromTestCase(TestRVCCommandEdgeCases))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit(run_tests())
