#!/usr/bin/env python3
"""
Command Audit Logger

Comprehensive logging system for all RV-C commands sent via MQTT.
Tracks command attempts, success/failure, latency, and provides
audit trail for security and debugging.

Phase 2: Bidirectional Communication
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from logging.handlers import RotatingFileHandler


class AuditLogger:
    """
    Audit logger for RV-C commands

    Logs all command attempts with:
    - Timestamp
    - Entity ID
    - Command type and action
    - Command value
    - Validation result
    - CAN frames sent (if successful)
    - Execution result (success/failure)
    - Error details (if failed)
    - Latency metrics
    - Source information
    """

    # Log levels
    LEVEL_DEBUG = logging.DEBUG      # Detailed debugging info
    LEVEL_INFO = logging.INFO        # Normal command logging
    LEVEL_WARNING = logging.WARNING  # Validation failures, rate limits
    LEVEL_ERROR = logging.ERROR      # Transmission failures, errors
    LEVEL_CRITICAL = logging.CRITICAL # System failures

    def __init__(self,
                 log_file: str = 'logs/command_audit.log',
                 log_level: int = LEVEL_INFO,
                 max_bytes: int = 10 * 1024 * 1024,  # 10 MB
                 backup_count: int = 5,
                 json_format: bool = True,
                 console_output: bool = False):
        """
        Initialize audit logger

        Args:
            log_file: Path to log file
            log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            max_bytes: Maximum log file size before rotation
            backup_count: Number of backup files to keep
            json_format: If True, log in JSON format; if False, human-readable
            console_output: If True, also output to console
        """
        self.log_file = log_file
        self.log_level = log_level
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.json_format = json_format
        self.console_output = console_output

        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Set up logger
        self.logger = logging.getLogger('rvc_command_audit')
        self.logger.setLevel(log_level)
        self.logger.propagate = False  # Don't propagate to root logger

        # Clear existing handlers
        self.logger.handlers = []

        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(log_level)

        # Console handler (optional)
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            self.logger.addHandler(console_handler)

        # Format
        if json_format:
            formatter = logging.Formatter('%(message)s')
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Statistics
        self.stats = {
            'total_commands': 0,
            'successful_commands': 0,
            'failed_commands': 0,
            'validation_failures': 0,
            'transmission_failures': 0,
            'total_latency_ms': 0,
        }

    # =========================================================================
    # Main Logging Methods
    # =========================================================================

    def log_command_attempt(self,
                           command: Dict[str, Any],
                           source: str = 'mqtt') -> int:
        """
        Log command attempt (before validation)

        Args:
            command: Command dictionary
            source: Source of command (mqtt, api, test, etc.)

        Returns:
            Command ID for tracking
        """
        self.stats['total_commands'] += 1
        cmd_id = self.stats['total_commands']

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event': 'command_attempt',
            'cmd_id': cmd_id,
            'source': source,
            'entity_id': command.get('entity_id'),
            'command_type': command.get('command_type'),
            'action': command.get('action'),
            'value': command.get('value'),
        }

        self._log(logging.DEBUG, log_entry)
        return cmd_id

    def log_validation_failure(self,
                               cmd_id: int,
                               command: Dict[str, Any],
                               error_code: str,
                               error_message: str,
                               field: Optional[str] = None):
        """
        Log validation failure

        Args:
            cmd_id: Command ID from log_command_attempt
            command: Command dictionary
            error_code: Error code (E001-E020)
            error_message: Error description
            field: Field that failed validation (if applicable)
        """
        self.stats['validation_failures'] += 1
        self.stats['failed_commands'] += 1

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event': 'validation_failure',
            'cmd_id': cmd_id,
            'entity_id': command.get('entity_id'),
            'command_type': command.get('command_type'),
            'error_code': error_code,
            'error_message': error_message,
            'field': field,
        }

        self._log(logging.WARNING, log_entry)

    def log_command_success(self,
                           cmd_id: int,
                           command: Dict[str, Any],
                           can_frames: List[str],
                           latency_ms: float):
        """
        Log successful command execution

        Args:
            cmd_id: Command ID from log_command_attempt
            command: Command dictionary
            can_frames: List of CAN frames sent (formatted as hex strings)
            latency_ms: Total execution time in milliseconds
        """
        self.stats['successful_commands'] += 1
        self.stats['total_latency_ms'] += latency_ms

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event': 'command_success',
            'cmd_id': cmd_id,
            'entity_id': command.get('entity_id'),
            'command_type': command.get('command_type'),
            'action': command.get('action'),
            'value': command.get('value'),
            'can_frames': can_frames,
            'frame_count': len(can_frames),
            'latency_ms': round(latency_ms, 2),
        }

        self._log(logging.INFO, log_entry)

    def log_transmission_failure(self,
                                 cmd_id: int,
                                 command: Dict[str, Any],
                                 error_message: str,
                                 can_frames_attempted: Optional[List[str]] = None):
        """
        Log CAN transmission failure

        Args:
            cmd_id: Command ID from log_command_attempt
            command: Command dictionary
            error_message: Error description
            can_frames_attempted: Frames that were attempted (if available)
        """
        self.stats['transmission_failures'] += 1
        self.stats['failed_commands'] += 1

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event': 'transmission_failure',
            'cmd_id': cmd_id,
            'entity_id': command.get('entity_id'),
            'command_type': command.get('command_type'),
            'error_message': error_message,
            'can_frames_attempted': can_frames_attempted,
        }

        self._log(logging.ERROR, log_entry)

    def log_system_event(self,
                        event_type: str,
                        message: str,
                        details: Optional[Dict[str, Any]] = None,
                        level: int = LEVEL_INFO):
        """
        Log system event (startup, shutdown, config change, etc.)

        Args:
            event_type: Type of event (startup, shutdown, config_change, etc.)
            message: Event description
            details: Additional event details
            level: Log level
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event': event_type,
            'message': message,
        }

        if details:
            log_entry['details'] = details

        self._log(level, log_entry)

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _log(self, level: int, entry: Dict[str, Any]):
        """
        Internal logging method

        Args:
            level: Log level
            entry: Log entry dictionary
        """
        if self.json_format:
            # JSON format - one entry per line
            log_message = json.dumps(entry)
        else:
            # Human-readable format
            log_message = self._format_human_readable(entry)

        self.logger.log(level, log_message)

    def _format_human_readable(self, entry: Dict[str, Any]) -> str:
        """
        Format log entry as human-readable string

        Args:
            entry: Log entry dictionary

        Returns:
            Formatted string
        """
        event = entry.get('event', 'unknown')
        entity_id = entry.get('entity_id', 'N/A')
        cmd_type = entry.get('command_type', 'N/A')

        if event == 'command_attempt':
            return f"[{entry.get('cmd_id')}] Attempt: {entity_id} ({cmd_type}) = {entry.get('value')}"

        elif event == 'validation_failure':
            return f"[{entry.get('cmd_id')}] Validation Failed: {entity_id} - {entry.get('error_code')}: {entry.get('error_message')}"

        elif event == 'command_success':
            frames = len(entry.get('can_frames', []))
            latency = entry.get('latency_ms', 0)
            return f"[{entry.get('cmd_id')}] Success: {entity_id} ({cmd_type}) - {frames} frames in {latency}ms"

        elif event == 'transmission_failure':
            return f"[{entry.get('cmd_id')}] TX Failed: {entity_id} - {entry.get('error_message')}"

        else:
            return f"{event}: {entry.get('message', json.dumps(entry))}"

    # =========================================================================
    # Statistics and Reporting
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """
        Get audit statistics

        Returns:
            Dictionary with statistics
        """
        stats = self.stats.copy()

        # Calculate derived stats
        if stats['successful_commands'] > 0:
            stats['avg_latency_ms'] = round(
                stats['total_latency_ms'] / stats['successful_commands'],
                2
            )
        else:
            stats['avg_latency_ms'] = 0

        if stats['total_commands'] > 0:
            stats['success_rate'] = round(
                (stats['successful_commands'] / stats['total_commands']) * 100,
                2
            )
        else:
            stats['success_rate'] = 0

        return stats

    def reset_stats(self):
        """Reset statistics counters"""
        self.stats = {
            'total_commands': 0,
            'successful_commands': 0,
            'failed_commands': 0,
            'validation_failures': 0,
            'transmission_failures': 0,
            'total_latency_ms': 0,
        }

    def print_stats(self):
        """Print statistics to console"""
        stats = self.get_stats()

        print("\n" + "=" * 60)
        print("Command Audit Statistics")
        print("=" * 60)
        print(f"Total Commands:        {stats['total_commands']}")
        print(f"Successful:            {stats['successful_commands']}")
        print(f"Failed:                {stats['failed_commands']}")
        print(f"  - Validation:        {stats['validation_failures']}")
        print(f"  - Transmission:      {stats['transmission_failures']}")
        print(f"Success Rate:          {stats['success_rate']}%")
        print(f"Average Latency:       {stats['avg_latency_ms']} ms")
        print("=" * 60 + "\n")

    # =========================================================================
    # Context Manager Support
    # =========================================================================

    def __enter__(self):
        """Context manager entry"""
        self.log_system_event('audit_start', 'Audit logging started')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.log_system_event('audit_stop', 'Audit logging stopped')
        self.print_stats()


# =============================================================================
# Testing
# =============================================================================

def test_audit_logger():
    """Test audit logger functionality"""
    print("Testing AuditLogger...")
    print()

    # Create logger (JSON format for production, human-readable for testing)
    logger = AuditLogger(
        log_file='logs/test_audit.log',
        log_level=AuditLogger.LEVEL_DEBUG,
        json_format=False,  # Human-readable for testing
        console_output=True
    )

    print("Test 1: System Event Logging")
    logger.log_system_event('startup', 'Test audit system started', {
        'version': '2.0.0',
        'mode': 'test'
    })
    print("  ✓ System event logged")
    print()

    print("Test 2: Successful Command Flow")
    # Simulate successful command
    command = {
        'entity_id': 'light_ceiling',
        'command_type': 'light',
        'action': 'brightness',
        'value': 75
    }

    cmd_id = logger.log_command_attempt(command, source='test')
    print(f"  Command ID: {cmd_id}")

    # Simulate successful execution
    can_frames = [
        '19FEDB63#01FF9600FF00FFFF',
        '19FEDB63#01FF00150000FFFF',
        '19FEDB63#01FF00040000FFFF'
    ]
    logger.log_command_success(cmd_id, command, can_frames, latency_ms=45.2)
    print("  ✓ Success logged")
    print()

    print("Test 3: Validation Failure")
    # Simulate validation failure
    command2 = {
        'entity_id': 'light_ceiling',
        'command_type': 'light',
        'action': 'brightness',
        'value': 150  # Invalid - too high
    }

    cmd_id2 = logger.log_command_attempt(command2, source='test')
    logger.log_validation_failure(
        cmd_id2,
        command2,
        error_code='E014',
        error_message='Value 150 above maximum 100',
        field='value'
    )
    print("  ✓ Validation failure logged")
    print()

    print("Test 4: Transmission Failure")
    # Simulate transmission failure
    command3 = {
        'entity_id': 'hvac_front',
        'command_type': 'climate',
        'action': 'temperature',
        'value': 72
    }

    cmd_id3 = logger.log_command_attempt(command3, source='test')
    logger.log_transmission_failure(
        cmd_id3,
        command3,
        error_message='CAN bus timeout',
        can_frames_attempted=['19FEF963#00FFFFF024F024FF']
    )
    print("  ✓ Transmission failure logged")
    print()

    print("Test 5: Multiple Commands (Performance Test)")
    for i in range(10):
        cmd = {
            'entity_id': f'light_{i}',
            'command_type': 'light',
            'value': 'ON'
        }
        cmd_id = logger.log_command_attempt(cmd, source='test')

        # Simulate success for even-numbered commands
        if i % 2 == 0:
            logger.log_command_success(
                cmd_id,
                cmd,
                ['19FEDB63#01FFC800FF00FFFF'],
                latency_ms=30.0 + i
            )
        else:
            logger.log_validation_failure(
                cmd_id,
                cmd,
                error_code='E015',
                error_message='Entity denied',
                field='entity_id'
            )

    print("  ✓ 10 commands logged")
    print()

    print("Test 6: Statistics")
    logger.print_stats()
    print("  ✓ Statistics displayed")
    print()

    print("Test 7: JSON Format Logging")
    logger_json = AuditLogger(
        log_file='logs/test_audit_json.log',
        json_format=True,
        console_output=False
    )

    cmd = {
        'entity_id': 'test_entity',
        'command_type': 'light',
        'value': 'ON'
    }
    cmd_id = logger_json.log_command_attempt(cmd)
    logger_json.log_command_success(
        cmd_id,
        cmd,
        ['19FEDB63#01FFC800FF00FFFF'],
        latency_ms=25.5
    )

    # Read and verify JSON
    with open('logs/test_audit_json.log', 'r') as f:
        lines = f.readlines()
        for line in lines:
            entry = json.loads(line)
            assert 'timestamp' in entry
            assert 'event' in entry

    print("  ✓ JSON format verified")
    print()

    print("All tests completed!")
    print()

    # Cleanup
    import os
    if os.path.exists('logs/test_audit.log'):
        os.remove('logs/test_audit.log')
    if os.path.exists('logs/test_audit_json.log'):
        os.remove('logs/test_audit_json.log')


if __name__ == "__main__":
    test_audit_logger()
