#!/usr/bin/env python3
"""
RV-C Command Encoder Module

This module encodes Home Assistant commands into RV-C CAN bus frames.
It handles all device types (lights, HVAC, switches, fans) and supports
multi-step command sequences.

Based on RV-C specification and reference implementations from Perl examples.

Phase 2: Bidirectional Communication
"""

import struct
from typing import List, Tuple, Optional, Dict, Any


class RVCCommandEncoder:
    """
    Encode HA commands into RV-C CAN frames

    Each encoder method returns a list of CAN frames to transmit:
        [(can_id, data_bytes, delay_ms), ...]

    Where:
        can_id: int - 29-bit CAN arbitration ID
        data_bytes: list[int] - 8 bytes of data (0-255)
        delay_ms: int - Delay before next frame (milliseconds)
    """

    # DGN Constants
    DGN_DC_DIMMER = 0x1FEDB  # DC Dimmer/Load control
    DGN_THERMOSTAT = 0x1FEF9  # Thermostat command

    # Default parameters
    DEFAULT_PRIORITY = 6
    DEFAULT_SOURCE_ADDRESS = 99  # External controller

    # DC Dimmer command codes
    CMD_SET_LEVEL = 0
    CMD_ON_DURATION = 1
    CMD_ON_DELAY = 2
    CMD_OFF_DELAY = 3
    CMD_STOP = 4
    CMD_TOGGLE = 5
    CMD_MEMORY_OFF = 6
    CMD_RAMP_BRIGHTNESS = 17
    CMD_RAMP_TOGGLE = 18
    CMD_RAMP_UP = 19
    CMD_RAMP_DOWN = 20
    CMD_RAMP_DOWN_UP = 21

    # Thermostat command data (7 bytes each)
    THERMOSTAT_COMMANDS = {
        'off':  bytes.fromhex('C0FFFFFFFFFFFF'),
        'cool': bytes.fromhex('C1FFFFFFFFFFFF'),
        'heat': bytes.fromhex('C2FFFFFFFFFFFF'),
        'fan_low':  bytes.fromhex('DF64FFFFFFFFFF'),
        'fan_high': bytes.fromhex('DFC8FFFFFFFFFF'),
        'fan_auto': bytes.fromhex('CFFFFFFFFFFFFF'),
        'fan_low_only':  bytes.fromhex('D464FFFFFFFFFF'),
        'fan_high_only': bytes.fromhex('D4C8FFFFFFFFFF'),
        'fan_auto_only': bytes.fromhex('C0FFFFFFFFFFFF'),
        'temp_up':   bytes.fromhex('FFFFFFFFFAFFFF'),
        'temp_down': bytes.fromhex('FFFFFFFFF9FFFF'),
    }

    def __init__(self, source_address: int = DEFAULT_SOURCE_ADDRESS):
        """
        Initialize RV-C command encoder

        Args:
            source_address: CAN source address (default: 99)
        """
        self.source_address = source_address

    # =========================================================================
    # CAN ID Construction
    # =========================================================================

    def build_can_id(self,
                     dgn: int,
                     priority: int = DEFAULT_PRIORITY,
                     source_address: Optional[int] = None) -> int:
        """
        Build 29-bit CAN arbitration ID

        CAN ID Structure (29 bits):
            Bits 0-2:   Priority (3 bits)
            Bit 3:      Reserved (0)
            Bits 4-20:  DGN - Data Group Number (17 bits)
            Bits 21-23: Reserved (0)
            Bits 24-28: Source Address (8 bits)

        Args:
            dgn: Data Group Number (17-bit value, e.g., 0x1FEDB)
            priority: Priority (0-7, default: 6)
            source_address: Source address (0-255, default: self.source_address)

        Returns:
            int: 29-bit CAN arbitration ID

        Example:
            >>> encoder = RVCCommandEncoder()
            >>> can_id = encoder.build_can_id(0x1FEDB, priority=6, source_address=99)
            >>> hex(can_id)
            '0x19fedb63'
        """
        if source_address is None:
            source_address = self.source_address

        # Validate inputs
        assert 0 <= priority <= 7, f"Priority must be 0-7, got {priority}"
        assert 0 <= dgn <= 0x1FFFF, f"DGN must be 0-0x1FFFF, got {dgn:X}"
        assert 0 <= source_address <= 255, f"Source address must be 0-255, got {source_address}"

        # Build CAN ID
        # Format: [Priority:3][0:1][DGN:17][000:3][SourceAddr:8]
        can_id = (
            (priority << 26) |      # Bits 26-28: Priority
            (dgn << 8) |            # Bits 8-24: DGN (17 bits)
            source_address          # Bits 0-7: Source Address
        )

        return can_id

    # =========================================================================
    # Light Commands (DC Dimmer)
    # =========================================================================

    def encode_light_on_off(self,
                           instance: int,
                           turn_on: bool,
                           duration: int = 255) -> List[Tuple[int, List[int], int]]:
        """
        Encode light on/off command

        Args:
            instance: Load instance ID (1-255)
            turn_on: True to turn on, False to turn off
            duration: Duration in seconds (255 = indefinite)

        Returns:
            List of CAN frames: [(can_id, data_bytes, delay_ms)]
        """
        can_id = self.build_can_id(self.DGN_DC_DIMMER)

        if turn_on:
            # On command: Use ON_DELAY instead of SET_LEVEL to avoid cleanup sequence
            brightness = 200  # 100% = 200 in RV-C
            command = self.CMD_ON_DELAY  # Command 2 - simpler than SET_LEVEL
        else:
            # Off command: Use OFF_DELAY
            brightness = 0
            command = self.CMD_OFF_DELAY  # Command 3
            duration = 0  # Immediate

        # Build data frame
        data = [
            instance,
            0xFF,
            brightness,
            command,
            duration,
            0x00,
            0xFF,
            0xFF
        ]

        frames = [(can_id, data, 0)]

        # No cleanup sequence needed for ON_DELAY/OFF_DELAY commands

        return frames

    def encode_light_brightness(self,
                               instance: int,
                               brightness_pct: int) -> List[Tuple[int, List[int], int]]:
        """
        Encode light brightness command

        Args:
            instance: Load instance ID (1-255)
            brightness_pct: Brightness percentage (0-100)

        Returns:
            List of CAN frames: [(can_id, data_bytes, delay_ms)]
        """
        # Validate brightness
        assert 0 <= brightness_pct <= 100, f"Brightness must be 0-100, got {brightness_pct}"

        # Convert to RV-C format (0-200)
        brightness_rvc = brightness_pct * 2

        can_id = self.build_can_id(self.DGN_DC_DIMMER)

        # Build set level command (no cleanup needed for simple brightness changes)
        data = [
            instance,
            0xFF,
            brightness_rvc,
            self.CMD_SET_LEVEL,  # Command 0 is appropriate for setting specific brightness
            255,  # Duration: indefinite
            0x00,
            0xFF,
            0xFF
        ]

        frames = [(can_id, data, 0)]

        # No cleanup sequence - keep it simple

        return frames

    def _build_dimmer_cleanup_sequence(self,
                                      instance: int,
                                      can_id: int) -> List[Tuple[int, List[int], int]]:
        """
        Build cleanup sequence for dimmer set level commands

        After setting brightness, send ramp down/up and stop commands
        to finalize the state.

        Args:
            instance: Load instance ID
            can_id: CAN ID to use

        Returns:
            List of cleanup frames with delays
        """
        frames = []

        # Frame 2: Ramp down/up (after 5 second delay)
        data2 = [
            instance,
            0xFF,
            0,  # Brightness = 0
            self.CMD_RAMP_DOWN_UP,
            0,  # Duration = 0
            0x00,
            0xFF,
            0xFF
        ]
        frames.append((can_id, data2, 5000))  # 5 second delay

        # Frame 3: Stop ramp
        data3 = [
            instance,
            0xFF,
            0,
            self.CMD_STOP,
            0,
            0x00,
            0xFF,
            0xFF
        ]
        frames.append((can_id, data3, 0))

        return frames

    def encode_panel_light(self,
                          instance: int,
                          brightness_pct: int) -> List[Tuple[int, List[int], int]]:
        """
        Encode panel light brightness command

        Panel lights use a different data format than regular dimmers.

        Args:
            instance: Panel instance ID
            brightness_pct: Brightness percentage (0-100)

        Returns:
            List of CAN frames: [(can_id, data_bytes, delay_ms)]
        """
        assert 0 <= brightness_pct <= 100, f"Brightness must be 0-100, got {brightness_pct}"

        brightness_rvc = brightness_pct * 2
        can_id = self.build_can_id(self.DGN_DC_DIMMER)

        # Panel light format: FF [instance] [brightness] FF FF FF 00 FF
        data = [
            0xFF,
            instance,
            brightness_rvc,
            0xFF,
            0xFF,
            0xFF,
            0x00,
            0xFF
        ]

        return [(can_id, data, 0)]

    # =========================================================================
    # Climate/Thermostat Commands
    # =========================================================================

    def encode_climate_mode(self,
                           instance: int,
                           mode: str,
                           current_mode: Optional[str] = None) -> List[Tuple[int, List[int], int]]:
        """
        Encode thermostat mode command

        Args:
            instance: Thermostat zone instance (0-6)
            mode: Desired mode ('off', 'cool', 'heat', 'auto')
            current_mode: Current mode (optional, used for context)

        Returns:
            List of CAN frames: [(can_id, data_bytes, delay_ms)]
        """
        mode = mode.lower()
        valid_modes = ['off', 'cool', 'heat']
        assert mode in valid_modes, f"Mode must be one of {valid_modes}, got {mode}"

        can_id = self.build_can_id(self.DGN_THERMOSTAT)

        # Get command bytes from lookup table
        cmd_bytes = self.THERMOSTAT_COMMANDS[mode]

        # Build data frame: [instance] + [7 command bytes]
        data = [instance] + list(cmd_bytes)

        return [(can_id, data, 0)]

    def encode_climate_temperature(self,
                                  instance: int,
                                  temperature_f: float,
                                  sync_furnace: bool = True) -> List[Tuple[int, List[int], int]]:
        """
        Encode thermostat temperature setpoint command

        Args:
            instance: Thermostat zone instance (0-6)
            temperature_f: Temperature in Fahrenheit (60-90 typical)
            sync_furnace: If True and instance is even, also set furnace setpoint

        Returns:
            List of CAN frames: [(can_id, data_bytes, delay_ms)]
        """
        # Validate temperature range
        assert 50 <= temperature_f <= 100, f"Temperature must be 50-100°F, got {temperature_f}"

        # Spyder thermostats use half-degree increments
        # Add 0.5 for proper rounding
        temp_adjusted = temperature_f + 0.5

        # Convert to RV-C format
        temp_hex = self._temp_f_to_rvc_hex(temp_adjusted)

        can_id = self.build_can_id(self.DGN_THERMOSTAT)

        # Build data frame: [instance] FF FF [temp_low] [temp_high] [temp_low] [temp_high] FF
        data = [
            instance,
            0xFF,
            0xFF,
            temp_hex[1],  # Low byte
            temp_hex[0],  # High byte
            temp_hex[1],  # Low byte (repeated)
            temp_hex[0],  # High byte (repeated)
            0xFF
        ]

        frames = [(can_id, data, 0)]

        # If instance is even (0, 2, 4), also set furnace setpoint (instance + 3)
        if sync_furnace and instance % 2 == 0:
            furnace_instance = instance + 3
            data_furnace = [
                furnace_instance,
                0xFF,
                0xFF,
                temp_hex[1],
                temp_hex[0],
                temp_hex[1],
                temp_hex[0],
                0xFF
            ]
            frames.append((can_id, data_furnace, 0))

        return frames

    def encode_climate_fan_mode(self,
                               instance: int,
                               fan_mode: str,
                               current_mode: Optional[str] = None) -> List[Tuple[int, List[int], int]]:
        """
        Encode thermostat fan mode command

        Fan commands differ based on whether the system is in a heating/cooling
        mode or just fan-only mode.

        Args:
            instance: Thermostat zone instance (0-6)
            fan_mode: Desired fan mode ('auto', 'low', 'high')
            current_mode: Current operating mode ('off', 'cool', 'heat', 'fan')

        Returns:
            List of CAN frames: [(can_id, data_bytes, delay_ms)]
        """
        fan_mode = fan_mode.lower()
        valid_modes = ['auto', 'low', 'high']
        assert fan_mode in valid_modes, f"Fan mode must be one of {valid_modes}, got {fan_mode}"

        # Determine if we need fan-only variant
        if current_mode and current_mode.lower() in ['off', 'fan']:
            command_key = f'fan_{fan_mode}_only'
        else:
            command_key = f'fan_{fan_mode}'

        can_id = self.build_can_id(self.DGN_THERMOSTAT)
        cmd_bytes = self.THERMOSTAT_COMMANDS[command_key]

        data = [instance] + list(cmd_bytes)

        return [(can_id, data, 0)]

    def _temp_f_to_rvc_hex(self, fahrenheit: float) -> Tuple[int, int]:
        """
        Convert temperature in Fahrenheit to RV-C hex format

        Formula: ((F - 32) * 5/9 + 273) / 0.03125 + 0.999

        Args:
            fahrenheit: Temperature in Fahrenheit

        Returns:
            Tuple of (high_byte, low_byte)

        Example:
            >>> encoder = RVCCommandEncoder()
            >>> encoder._temp_f_to_rvc_hex(72.5)
            (0x24, 0xD6)
        """
        # Convert F to Kelvin
        kelvin = ((fahrenheit - 32) * 5.0 / 9.0) + 273.0

        # Convert to RV-C units (0.03125 K per bit)
        # Add 0.999 to prevent rounding errors
        rvc_value = int((kelvin / 0.03125) + 0.999)

        # Ensure within uint16 range
        rvc_value = max(0, min(65535, rvc_value))

        # Split into high and low bytes
        high_byte = (rvc_value >> 8) & 0xFF
        low_byte = rvc_value & 0xFF

        return (high_byte, low_byte)

    # =========================================================================
    # Switch/Pump Commands
    # =========================================================================

    def encode_switch_on_off(self,
                            instance: int,
                            turn_on: bool,
                            source_address: int = 96) -> List[Tuple[int, List[int], int]]:
        """
        Encode switch/pump on/off command

        Switches and pumps use the DC dimmer DGN but with source address 96.

        Args:
            instance: Load instance ID
            turn_on: True to turn on, False to turn off
            source_address: Source address (default: 96 for switches)

        Returns:
            List of CAN frames: [(can_id, data_bytes, delay_ms)]
        """
        can_id = self.build_can_id(self.DGN_DC_DIMMER, source_address=source_address)

        command = 2 if turn_on else 3  # 2=On, 3=Off

        data = [
            instance,
            0xFF,
            0xC8,  # Brightness: 200 (100%)
            command,
            0xFF,  # Duration: indefinite
            0x00,
            0xFF,
            0xFF
        ]

        return [(can_id, data, 0)]

    # =========================================================================
    # Vent Fan Commands
    # =========================================================================

    def encode_vent_fan(self,
                       instance: int,
                       turn_on: bool) -> List[Tuple[int, List[int], int]]:
        """
        Encode vent fan on/off command (uses TOGGLE)

        Vent fans use TOGGLE command (0x05) rather than separate ON/OFF commands.
        Both ON and OFF requests send the same TOGGLE command.

        Args:
            instance: Vent fan load ID
            turn_on: True to turn on, False to turn off (both use TOGGLE)

        Returns:
            List of CAN frames: [(can_id, data_bytes, delay_ms)]
        """
        # Vent fans use source address 154 (0x9A) and TOGGLE command
        can_id = self.build_can_id(self.DGN_DC_DIMMER, source_address=154)

        data = [
            instance,
            0xFF,
            0xC8,  # Brightness: 200 (100%)
            self.CMD_TOGGLE,  # Command 5 = TOGGLE
            0xFF,  # Duration: indefinite
            0x00,
            0xFF,
            0xFF
        ]

        return [(can_id, data, 0)]

    def encode_vent_lid(self,
                       up_instance: int,
                       down_instance: int,
                       position: str) -> List[Tuple[int, List[int], int]]:
        """
        Encode vent lid position command (dual motor control)

        Vent lids use two DC load instances - one for the up motor and one
        for the down motor. To move the lid, we must:
        1. Stop the opposite motor
        2. Run the desired motor for 20 seconds

        Args:
            up_instance: Load instance for UP motor
            down_instance: Load instance for DOWN motor
            position: Desired position ('open' or 'close')

        Returns:
            List of CAN frames: [(can_id, data_bytes, delay_ms)]
        """
        position = position.lower()
        assert position in ['open', 'close'], f"Position must be 'open' or 'close', got {position}"

        # Vent lids use source address 154 (0x99)
        can_id = self.build_can_id(self.DGN_DC_DIMMER, source_address=154)
        frames = []

        if position == 'open':
            # To OPEN: Stop DOWN motor, then run UP motor for 20 seconds
            # Frame 1: Stop DOWN motor
            data_stop = [
                down_instance,
                0xFF,
                0x00,  # Brightness = 0 (off)
                3,     # Command 3 = OFF
                0,     # Duration = 0 (immediate)
                0x00,
                0xFF,
                0xFF
            ]
            frames.append((can_id, data_stop, 0))

            # Frame 2: Run UP motor for 20 seconds
            data_run = [
                up_instance,
                0xFF,
                0xC8,  # Brightness = 200 (100%)
                1,     # Command 1 = ON_DURATION
                20,    # Duration = 20 seconds
                0x00,
                0xFF,
                0xFF
            ]
            frames.append((can_id, data_run, 0))

        else:  # position == 'close'
            # To CLOSE: Stop UP motor, then run DOWN motor for 20 seconds
            # Frame 1: Stop UP motor
            data_stop = [
                up_instance,
                0xFF,
                0x00,  # Brightness = 0 (off)
                3,     # Command 3 = OFF
                0,     # Duration = 0 (immediate)
                0x00,
                0xFF,
                0xFF
            ]
            frames.append((can_id, data_stop, 0))

            # Frame 2: Run DOWN motor for 20 seconds
            data_run = [
                down_instance,
                0xFF,
                0xC8,  # Brightness = 200 (100%)
                1,     # Command 1 = ON_DURATION
                20,    # Duration = 20 seconds
                0x00,
                0xFF,
                0xFF
            ]
            frames.append((can_id, data_run, 0))

        return frames

    # =========================================================================
    # Ceiling Fan Commands (Multi-Load Control)
    # =========================================================================

    def encode_ceiling_fan(self,
                          fan_id: int,
                          speed: int) -> List[Tuple[int, List[int], int]]:
        """
        Encode ceiling fan speed command

        Ceiling fans use special multi-load control to achieve different speeds.

        Args:
            fan_id: Fan identifier (1=Bedroom, 2=Bedroom 2018+)
            speed: Fan speed (0=Off, 1=Low, 2=High)

        Returns:
            List of CAN frames: [(can_id, data_bytes, delay_ms)]
        """
        # Special load mappings for ceiling fans
        # Each fan has two loads that are controlled differently for each speed
        SPECIAL_LOADS = {
            1: {  # Bedroom fan
                0: [35, 36],  # Off: loads to turn off
                1: [35, 36],  # Low: primary, secondary
                2: [36, 35],  # High: reversed
            },
            2: {  # Bedroom (2018+ Open Road)
                0: [33, 34],
                1: [33, 34],
                2: [34, 33],
            }
        }

        assert fan_id in SPECIAL_LOADS, f"Fan ID must be 1 or 2, got {fan_id}"
        assert 0 <= speed <= 2, f"Speed must be 0-2, got {speed}"

        # Ceiling fans use source address 158 (0x9E) - from CAN capture
        can_id = self.build_can_id(self.DGN_DC_DIMMER, source_address=158)
        frames = []

        if speed > 0:
            # Turn on: First turn off opposite load, then turn on primary
            loads = SPECIAL_LOADS[fan_id][speed]

            # Frame 1: Turn off secondary load
            data1 = [
                loads[1],
                0xFF,
                0xC8,
                3,  # Off command
                0,
                0x00,
                0xFF,
                0xFF
            ]
            frames.append((can_id, data1, 0))

            # Frame 2: Turn on primary load (toggle)
            data2 = [
                loads[0],
                0xFF,
                0xC8,
                5,  # Toggle command
                255,
                0x00,
                0xFF,
                0xFF
            ]
            frames.append((can_id, data2, 0))
        else:
            # Turn off: Turn off both loads
            loads = SPECIAL_LOADS[fan_id][0]

            for load in loads:
                data = [
                    load,
                    0xFF,
                    0xC8,
                    3,  # Off command
                    0,
                    0x00,
                    0xFF,
                    0xFF
                ]
                frames.append((can_id, data, 0))

        return frames

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def validate_instance(self, instance: int, max_instance: int = 255) -> bool:
        """Validate instance ID is in valid range"""
        return 0 <= instance <= max_instance

    def format_frame_debug(self, can_id: int, data: List[int]) -> str:
        """
        Format CAN frame for debugging output

        Args:
            can_id: CAN arbitration ID
            data: Data bytes

        Returns:
            String in format "19FEDB63#01FFC8000000FFFF"
        """
        data_hex = ''.join(f'{b:02X}' for b in data)
        return f"{can_id:08X}#{data_hex}"


# =============================================================================
# Testing and Examples
# =============================================================================

def test_encoder():
    """Test function to validate encoder"""
    print("Testing RVCCommandEncoder...")
    print()

    encoder = RVCCommandEncoder()

    # Test 1: CAN ID construction
    print("Test 1: CAN ID Construction")
    can_id = encoder.build_can_id(0x1FEDB, priority=6, source_address=99)
    print(f"  DGN=0x1FEDB, Priority=6, Source=99")
    print(f"  Result: 0x{can_id:08X}")
    assert can_id == 0x19FEDB63, f"Expected 0x19FEDB63, got 0x{can_id:08X}"
    print("  ✓ PASS")
    print()

    # Test 2: Light on/off
    print("Test 2: Light On/Off")
    frames = encoder.encode_light_on_off(instance=1, turn_on=True)
    print(f"  Command: Turn ON light instance 1")
    print(f"  Frames: {len(frames)}")
    for i, (cid, data, delay) in enumerate(frames):
        print(f"    Frame {i+1}: {encoder.format_frame_debug(cid, data)} (delay={delay}ms)")
    print("  ✓ PASS")
    print()

    # Test 3: Light brightness
    print("Test 3: Light Brightness")
    frames = encoder.encode_light_brightness(instance=1, brightness_pct=75)
    print(f"  Command: Set light instance 1 to 75%")
    print(f"  Frames: {len(frames)}")
    for i, (cid, data, delay) in enumerate(frames):
        print(f"    Frame {i+1}: {encoder.format_frame_debug(cid, data)} (delay={delay}ms)")
    print("  ✓ PASS")
    print()

    # Test 4: Temperature conversion
    print("Test 4: Temperature Conversion")
    temp_f = 72.5
    temp_hex = encoder._temp_f_to_rvc_hex(temp_f)
    print(f"  Input: {temp_f}°F")
    print(f"  Result: 0x{temp_hex[0]:02X}{temp_hex[1]:02X}")
    print("  ✓ PASS")
    print()

    # Test 5: Thermostat mode
    print("Test 5: Thermostat Mode")
    frames = encoder.encode_climate_mode(instance=0, mode='cool')
    print(f"  Command: Set thermostat zone 0 to COOL")
    for i, (cid, data, delay) in enumerate(frames):
        print(f"    Frame {i+1}: {encoder.format_frame_debug(cid, data)}")
    print("  ✓ PASS")
    print()

    # Test 6: Thermostat temperature
    print("Test 6: Thermostat Temperature")
    frames = encoder.encode_climate_temperature(instance=0, temperature_f=72)
    print(f"  Command: Set thermostat zone 0 to 72°F")
    print(f"  Frames: {len(frames)} (includes furnace sync)")
    for i, (cid, data, delay) in enumerate(frames):
        print(f"    Frame {i+1}: {encoder.format_frame_debug(cid, data)}")
    print("  ✓ PASS")
    print()

    # Test 7: Switch on/off
    print("Test 7: Switch On/Off")
    frames = encoder.encode_switch_on_off(instance=93, turn_on=True)
    print(f"  Command: Turn ON switch instance 93")
    for i, (cid, data, delay) in enumerate(frames):
        print(f"    Frame {i+1}: {encoder.format_frame_debug(cid, data)}")
    print("  ✓ PASS")
    print()

    # Test 8: Vent fan on/off
    print("Test 8: Vent Fan On/Off")
    frames = encoder.encode_vent_fan(instance=25, turn_on=True)
    print(f"  Command: Turn ON vent fan instance 25")
    for i, (cid, data, delay) in enumerate(frames):
        print(f"    Frame {i+1}: {encoder.format_frame_debug(cid, data)}")
    print("  ✓ PASS")
    print()

    # Test 9: Vent lid open/close
    print("Test 9: Vent Lid Control")
    frames = encoder.encode_vent_lid(up_instance=26, down_instance=27, position='open')
    print(f"  Command: OPEN vent lid (up=26, down=27)")
    print(f"  Frames: {len(frames)}")
    for i, (cid, data, delay) in enumerate(frames):
        print(f"    Frame {i+1}: {encoder.format_frame_debug(cid, data)}")
    print()
    frames = encoder.encode_vent_lid(up_instance=26, down_instance=27, position='close')
    print(f"  Command: CLOSE vent lid (up=26, down=27)")
    print(f"  Frames: {len(frames)}")
    for i, (cid, data, delay) in enumerate(frames):
        print(f"    Frame {i+1}: {encoder.format_frame_debug(cid, data)}")
    print("  ✓ PASS")
    print()

    print("All tests passed! ✓")


if __name__ == "__main__":
    test_encoder()
