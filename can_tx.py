#!/usr/bin/env python3
"""
CAN Bus Transmitter Module

This module handles sending CAN frames to the RV-C bus.
It supports single frames, multi-frame sequences, retry logic,
and error handling.

Phase 2: Bidirectional Communication
"""

import can
import time
import serial
from typing import List, Tuple, Optional
from datetime import datetime


class CANTransmitter:
    """
    Transmit CAN frames to RV-C bus

    Manages CAN bus connection, frame transmission, multi-frame sequences,
    retry logic, and error reporting.
    """

    def __init__(self,
                 can_interface: str = None,
                 can_port: str = None,
                 bus: can.interface.Bus = None,
                 retry_count: int = 3,
                 retry_delay_ms: int = 100,
                 debug_level: int = 0):
        """
        Initialize CAN transmitter

        Args:
            can_interface: CAN interface type (e.g., 'slcan') - ignored if bus provided
            can_port: CAN port (e.g., 'socket://192.168.50.103:3333') - ignored if bus provided
            bus: Existing CAN bus object to use (if provided, no new connection created)
            retry_count: Number of retries for failed transmissions
            retry_delay_ms: Delay between retries in milliseconds
            debug_level: Debug output level (0=none, 1=errors, 2=all)
        """
        self.can_interface = can_interface
        self.can_port = can_port
        self.retry_count = retry_count
        self.retry_delay_ms = retry_delay_ms
        self.debug_level = debug_level

        # Use provided bus object or create our own later
        self.bus = bus
        self.connected = (bus is not None)
        self.owns_bus = (bus is None)  # Track if we created the bus

        self.stats = {
            'frames_sent': 0,
            'frames_failed': 0,
            'retries': 0,
            'last_error': None,
            'last_tx_time': None
        }

    def connect(self) -> Tuple[bool, Optional[str]]:
        """
        Connect to CAN bus

        Returns:
            (success, error_message)
        """
        # If we already have a bus object, we're connected
        if self.bus is not None:
            self.connected = True
            if self.debug_level > 0:
                print(f"CAN TX: Using shared CAN bus")
            return True, None

        # Create our own connection
        try:
            self.bus = can.interface.Bus(
                interface=self.can_interface,
                channel=self.can_port,
                bitrate=250000
            )
            self.connected = True

            if self.debug_level > 0:
                print(f"CAN TX: Connected to {self.can_port}")

            return True, None

        except serial.serialutil.SerialException as e:
            error_msg = f"Failed to connect to CAN bus: {e}"
            self.connected = False
            self.stats['last_error'] = error_msg

            if self.debug_level > 0:
                print(f"CAN TX: {error_msg}")

            return False, error_msg

        except Exception as e:
            error_msg = f"Unexpected error connecting to CAN bus: {e}"
            self.connected = False
            self.stats['last_error'] = error_msg

            if self.debug_level > 0:
                print(f"CAN TX: {error_msg}")

            return False, error_msg

    def disconnect(self):
        """Disconnect from CAN bus (only if we own it)"""
        if self.bus and self.connected and self.owns_bus:
            try:
                self.bus.shutdown()
                self.connected = False

                if self.debug_level > 0:
                    print("CAN TX: Disconnected")
            except Exception as e:
                if self.debug_level > 0:
                    print(f"CAN TX: Error during disconnect: {e}")

    def is_connected(self) -> bool:
        """Check if connected to CAN bus"""
        return self.connected and self.bus is not None

    def send_frame(self,
                   can_id: int,
                   data: List[int]) -> Tuple[bool, Optional[str]]:
        """
        Send a single CAN frame

        Args:
            can_id: CAN arbitration ID (29-bit)
            data: List of 8 data bytes (0-255)

        Returns:
            (success, error_message)
        """
        # Validate inputs
        if not self.is_connected():
            return False, "Not connected to CAN bus"

        if not isinstance(data, (list, bytes)):
            return False, f"Data must be list or bytes, got {type(data)}"

        if len(data) != 8:
            return False, f"Data must be 8 bytes, got {len(data)}"

        for i, byte in enumerate(data):
            if not isinstance(byte, int) or not (0 <= byte <= 255):
                return False, f"Data byte {i} must be 0-255, got {byte}"

        # Create CAN message
        try:
            msg = can.Message(
                arbitration_id=can_id,
                data=data,
                is_extended_id=True
            )
        except Exception as e:
            return False, f"Failed to create CAN message: {e}"

        # Send with retry logic
        success = self._send_with_retry(msg)

        if success:
            self.stats['frames_sent'] += 1
            self.stats['last_tx_time'] = datetime.now()

            if self.debug_level > 1:
                data_hex = ''.join(f'{b:02X}' for b in data)
                print(f"CAN TX: {can_id:08X}#{data_hex}")

            return True, None
        else:
            self.stats['frames_failed'] += 1
            error_msg = f"Failed to send CAN frame after {self.retry_count} attempts"
            self.stats['last_error'] = error_msg
            return False, error_msg

    def _send_with_retry(self, msg: can.Message) -> bool:
        """
        Send CAN message with retry logic

        Args:
            msg: CAN message to send

        Returns:
            True if successful, False otherwise
        """
        for attempt in range(self.retry_count):
            try:
                self.bus.send(msg)
                return True

            except can.CanError as e:
                self.stats['retries'] += 1

                if self.debug_level > 1:
                    print(f"CAN TX: Send failed (attempt {attempt + 1}/{self.retry_count}): {e}")

                # If not last attempt, wait and retry
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay_ms / 1000.0)
                else:
                    # Last attempt failed
                    if self.debug_level > 0:
                        print(f"CAN TX: All retry attempts exhausted")
                    return False

            except Exception as e:
                if self.debug_level > 0:
                    print(f"CAN TX: Unexpected error: {e}")
                return False

        return False

    def send_frames(self,
                    frames: List[Tuple[int, List[int], int]]) -> Tuple[bool, Optional[str]]:
        """
        Send multiple CAN frames with delays

        This method handles multi-frame command sequences as returned
        by the RVCCommandEncoder.

        Args:
            frames: List of (can_id, data_bytes, delay_ms) tuples

        Returns:
            (success, error_message)

        Example:
            frames = [
                (0x19FEDB63, [0x01, 0xFF, 0xC8, 0x00, 0xFF, 0x00, 0xFF, 0xFF], 0),
                (0x19FEDB63, [0x01, 0xFF, 0x00, 0x15, 0x00, 0x00, 0xFF, 0xFF], 5000),
                (0x19FEDB63, [0x01, 0xFF, 0x00, 0x04, 0x00, 0x00, 0xFF, 0xFF], 0)
            ]
            success, error = transmitter.send_frames(frames)
        """
        if not frames:
            return False, "No frames to send"

        start_time = time.time()

        for i, (can_id, data, delay_ms) in enumerate(frames):
            # Send frame
            success, error = self.send_frame(can_id, data)

            if not success:
                return False, f"Frame {i+1}/{len(frames)} failed: {error}"

            # Apply delay before next frame (if not last frame)
            if delay_ms > 0 and i < len(frames) - 1:
                if self.debug_level > 1:
                    print(f"CAN TX: Waiting {delay_ms}ms before next frame...")
                time.sleep(delay_ms / 1000.0)

        total_time_ms = (time.time() - start_time) * 1000

        if self.debug_level > 1:
            print(f"CAN TX: Sent {len(frames)} frames in {total_time_ms:.1f}ms")

        return True, None

    def send_command_string(self,
                           can_id: int,
                           data_hex: str) -> Tuple[bool, Optional[str]]:
        """
        Send CAN frame with hex string data

        Compatibility method for legacy code that uses hex strings.

        Args:
            can_id: CAN arbitration ID
            data_hex: Hex string (e.g., '02FFC803FF00FFFF')

        Returns:
            (success, error_message)

        Example:
            success, error = transmitter.send_command_string(
                0x19FEDB63, '02FFC803FF00FFFF'
            )
        """
        # Convert hex string to byte array
        try:
            if len(data_hex) != 16:
                return False, f"Data hex string must be 16 characters, got {len(data_hex)}"

            data = [int(data_hex[i:i+2], 16) for i in range(0, 16, 2)]
        except ValueError as e:
            return False, f"Invalid hex string: {e}"

        return self.send_frame(can_id, data)

    def get_stats(self) -> dict:
        """
        Get transmission statistics

        Returns:
            Dictionary with stats
        """
        return self.stats.copy()

    def reset_stats(self):
        """Reset transmission statistics"""
        self.stats = {
            'frames_sent': 0,
            'frames_failed': 0,
            'retries': 0,
            'last_error': None,
            'last_tx_time': self.stats.get('last_tx_time')  # Preserve last TX time
        }

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# =============================================================================
# Testing
# =============================================================================

def test_transmitter():
    """Test CAN transmitter (requires actual CAN hardware)"""
    print("Testing CANTransmitter...")
    print("Note: This test requires actual CAN hardware to pass")
    print()

    # Create transmitter (use actual port from config)
    tx = CANTransmitter(
        can_interface='slcan',
        can_port='socket://192.168.50.103:3333',
        debug_level=2
    )

    # Test connection
    print("Test 1: Connection")
    success, error = tx.connect()
    if success:
        print("  ✓ Connected to CAN bus")
    else:
        print(f"  ✗ Connection failed: {error}")
        print("  (This is expected if CAN hardware is not available)")
        return
    print()

    # Test single frame
    print("Test 2: Single Frame")
    can_id = 0x19FEDB63
    data = [0x01, 0xFF, 0xC8, 0x00, 0xFF, 0x00, 0xFF, 0xFF]
    success, error = tx.send_frame(can_id, data)
    if success:
        print("  ✓ Frame sent successfully")
    else:
        print(f"  ✗ Frame send failed: {error}")
    print()

    # Test multi-frame sequence
    print("Test 3: Multi-Frame Sequence")
    frames = [
        (0x19FEDB63, [0x01, 0xFF, 0xC8, 0x00, 0xFF, 0x00, 0xFF, 0xFF], 0),
        (0x19FEDB63, [0x01, 0xFF, 0x00, 0x15, 0x00, 0x00, 0xFF, 0xFF], 1000),
        (0x19FEDB63, [0x01, 0xFF, 0x00, 0x04, 0x00, 0x00, 0xFF, 0xFF], 0)
    ]
    success, error = tx.send_frames(frames)
    if success:
        print("  ✓ All frames sent successfully")
    else:
        print(f"  ✗ Frame sequence failed: {error}")
    print()

    # Test hex string method
    print("Test 4: Hex String Method")
    success, error = tx.send_command_string(0x19FEDB63, '02FFC803FF00FFFF')
    if success:
        print("  ✓ Hex string frame sent")
    else:
        print(f"  ✗ Hex string send failed: {error}")
    print()

    # Show stats
    print("Test 5: Statistics")
    stats = tx.get_stats()
    print(f"  Frames sent: {stats['frames_sent']}")
    print(f"  Frames failed: {stats['frames_failed']}")
    print(f"  Retries: {stats['retries']}")
    print(f"  Last TX: {stats['last_tx_time']}")
    print()

    # Disconnect
    tx.disconnect()
    print("Disconnected from CAN bus")
    print()
    print("All tests completed!")


if __name__ == "__main__":
    test_transmitter()
