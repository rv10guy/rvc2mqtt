#!/usr/bin/env python3
"""
Command Validation Module

Multi-layer validation for RV-C commands including schema validation,
value range checking, entity verification, security controls, and rate limiting.

Phase 2: Bidirectional Communication
"""

import time
from collections import deque
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class ValidationError:
    """Validation error details"""
    code: str
    message: str
    field: Optional[str] = None


class CommandValidator:
    """
    Multi-layer command validator

    Validation layers:
    1. Schema validation (structure, required fields)
    2. Entity validation (exists, controllable)
    3. Value range validation (bounds checking)
    4. Security validation (allowlist/denylist)
    5. Rate limiting (prevent flooding)
    """

    # Validation rules for each command type
    VALIDATION_RULES = {
        'light': {
            'required_fields': ['entity_id', 'command_type'],
            'actions': {
                'state': {
                    'value_field': 'value',
                    'value_type': str,
                    'allowed_values': ['ON', 'OFF'],
                },
                'brightness': {
                    'value_field': 'value',
                    'value_type': int,
                    'min_value': 0,
                    'max_value': 100,
                }
            }
        },
        'climate': {
            'required_fields': ['entity_id', 'command_type', 'action'],
            'actions': {
                'mode': {
                    'value_field': 'value',
                    'value_type': str,
                    'allowed_values': ['off', 'cool', 'heat', 'auto'],
                },
                'temperature': {
                    'value_field': 'value',
                    'value_type': (int, float),
                    'min_value': 50,
                    'max_value': 100,
                },
                'fan_mode': {
                    'value_field': 'value',
                    'value_type': str,
                    'allowed_values': ['auto', 'low', 'high'],
                }
            }
        },
        'switch': {
            'required_fields': ['entity_id', 'command_type'],
            'actions': {
                'state': {
                    'value_field': 'value',
                    'value_type': str,
                    'allowed_values': ['ON', 'OFF'],
                }
            }
        }
    }

    def __init__(self,
                 ha_discovery=None,
                 config: Optional[Dict] = None):
        """
        Initialize command validator

        Args:
            ha_discovery: HADiscovery instance for entity lookup
            config: Configuration dictionary with security and rate limit settings
        """
        self.ha_discovery = ha_discovery
        self.config = config or {}

        # Security settings
        self.security_enabled = self.config.get('security_enabled', True)
        self.allowlist = set(self.config.get('allowlist', []))
        self.denylist = set(self.config.get('denylist', []))
        self.allowed_command_types = set(self.config.get('allowed_commands', ['light', 'climate', 'switch']))

        # Rate limiting settings
        self.rate_limit_enabled = self.config.get('rate_limit_enabled', True)
        self.global_limit = self.config.get('global_commands_per_second', 10)
        self.entity_limit = self.config.get('entity_commands_per_second', 2)
        self.entity_cooldown_ms = self.config.get('entity_cooldown_ms', 500)

        # Rate limiting state
        self.global_timestamps = deque(maxlen=100)
        self.entity_timestamps: Dict[str, deque] = {}

    # =========================================================================
    # Main Validation Entry Point
    # =========================================================================

    def validate(self, command: Dict[str, Any]) -> Tuple[bool, Optional[ValidationError]]:
        """
        Validate command through all layers

        Args:
            command: Command dictionary to validate

        Returns:
            (is_valid, error) - error is None if valid

        Command structure:
            {
                'entity_id': str,
                'command_type': 'light' | 'climate' | 'switch',
                'action': str (optional, for climate),
                'value': any (the command value)
            }
        """
        # Layer 1: Schema validation
        valid, error = self._validate_schema(command)
        if not valid:
            return False, error

        # Layer 2: Entity validation
        valid, error = self._validate_entity(command)
        if not valid:
            return False, error

        # Layer 3: Value range validation
        valid, error = self._validate_value_range(command)
        if not valid:
            return False, error

        # Layer 4: Security check
        valid, error = self._validate_security(command)
        if not valid:
            return False, error

        # Layer 5: Rate limiting
        valid, error = self._check_rate_limit(command)
        if not valid:
            return False, error

        return True, None

    # =========================================================================
    # Layer 1: Schema Validation
    # =========================================================================

    def _validate_schema(self, command: Dict[str, Any]) -> Tuple[bool, Optional[ValidationError]]:
        """
        Validate command structure and required fields

        Checks:
        - Command is a dictionary
        - Required fields present
        - Command type is valid
        - Action is valid for command type
        """
        # Check command is dict
        if not isinstance(command, dict):
            return False, ValidationError(
                code='E001',
                message='Command must be a dictionary'
            )

        # Check command_type exists and is valid
        command_type = command.get('command_type')
        if not command_type:
            return False, ValidationError(
                code='E002',
                message='Missing required field: command_type',
                field='command_type'
            )

        if command_type not in self.VALIDATION_RULES:
            return False, ValidationError(
                code='E003',
                message=f'Invalid command_type: {command_type}',
                field='command_type'
            )

        # Get validation rules for this command type
        rules = self.VALIDATION_RULES[command_type]

        # Check required fields
        for field in rules['required_fields']:
            if field not in command:
                return False, ValidationError(
                    code='E004',
                    message=f'Missing required field: {field}',
                    field=field
                )

        # Check action is valid (for command types that have actions)
        if 'action' in rules['required_fields']:
            action = command.get('action')
            if action not in rules['actions']:
                return False, ValidationError(
                    code='E005',
                    message=f'Invalid action: {action}',
                    field='action'
                )

        return True, None

    # =========================================================================
    # Layer 2: Entity Validation
    # =========================================================================

    def _validate_entity(self, command: Dict[str, Any]) -> Tuple[bool, Optional[ValidationError]]:
        """
        Validate entity exists and is controllable

        Checks:
        - Entity exists in HA discovery mapping
        - Entity is of correct type for command
        """
        entity_id = command.get('entity_id')

        if not entity_id:
            return False, ValidationError(
                code='E006',
                message='Missing entity_id',
                field='entity_id'
            )

        # If HA discovery is not available, skip entity validation
        # (allows testing without full HA setup)
        if not self.ha_discovery:
            return True, None

        # Check if entity exists
        entity = self._get_entity(entity_id)
        if not entity:
            return False, ValidationError(
                code='E007',
                message=f'Entity not found: {entity_id}',
                field='entity_id'
            )

        # Verify entity type matches command type
        command_type = command.get('command_type')
        entity_type = entity.get('entity_type')

        if entity_type != command_type:
            return False, ValidationError(
                code='E008',
                message=f'Entity type mismatch: entity is {entity_type}, command is {command_type}',
                field='entity_id'
            )

        return True, None

    def _get_entity(self, entity_id: str) -> Optional[Dict]:
        """Get entity configuration from HA discovery"""
        if not self.ha_discovery or not hasattr(self.ha_discovery, 'entities'):
            return None

        for entity in self.ha_discovery.entities:
            if entity.get('entity_id') == entity_id:
                return entity

        return None

    # =========================================================================
    # Layer 3: Value Range Validation
    # =========================================================================

    def _validate_value_range(self, command: Dict[str, Any]) -> Tuple[bool, Optional[ValidationError]]:
        """
        Validate command value is within acceptable range

        Checks:
        - Value type is correct
        - Value is within min/max bounds (for numeric values)
        - Value is in allowed values list (for enum values)
        """
        command_type = command.get('command_type')
        rules = self.VALIDATION_RULES[command_type]

        # Determine which action rules to use
        if 'action' in command:
            # Climate commands have explicit actions
            action = command.get('action')
            if action not in rules['actions']:
                return False, ValidationError(
                    code='E009',
                    message=f'Invalid action: {action}',
                    field='action'
                )
            action_rules = rules['actions'][action]
        else:
            # Light/switch commands infer action from presence of fields
            if 'brightness' in command or command.get('action') == 'brightness':
                action_rules = rules['actions']['brightness']
            else:
                action_rules = rules['actions']['state']

        # Get value to validate
        value_field = action_rules.get('value_field', 'value')
        value = command.get(value_field)

        if value is None:
            return False, ValidationError(
                code='E010',
                message=f'Missing value field: {value_field}',
                field=value_field
            )

        # Check value type
        expected_type = action_rules.get('value_type')
        if expected_type:
            if not isinstance(value, expected_type):
                return False, ValidationError(
                    code='E011',
                    message=f'Invalid value type: expected {expected_type.__name__}, got {type(value).__name__}',
                    field=value_field
                )

        # Check allowed values (for enums)
        if 'allowed_values' in action_rules:
            allowed = action_rules['allowed_values']
            # Case-insensitive comparison for strings
            if isinstance(value, str):
                value_lower = value.lower()
                allowed_lower = [v.lower() if isinstance(v, str) else v for v in allowed]
                if value_lower not in allowed_lower:
                    return False, ValidationError(
                        code='E012',
                        message=f'Invalid value: {value}. Allowed: {allowed}',
                        field=value_field
                    )
            else:
                if value not in allowed:
                    return False, ValidationError(
                        code='E012',
                        message=f'Invalid value: {value}. Allowed: {allowed}',
                        field=value_field
                    )

        # Check numeric range
        if 'min_value' in action_rules:
            min_val = action_rules['min_value']
            if value < min_val:
                return False, ValidationError(
                    code='E013',
                    message=f'Value {value} below minimum {min_val}',
                    field=value_field
                )

        if 'max_value' in action_rules:
            max_val = action_rules['max_value']
            if value > max_val:
                return False, ValidationError(
                    code='E014',
                    message=f'Value {value} above maximum {max_val}',
                    field=value_field
                )

        return True, None

    # =========================================================================
    # Layer 4: Security Validation
    # =========================================================================

    def _validate_security(self, command: Dict[str, Any]) -> Tuple[bool, Optional[ValidationError]]:
        """
        Validate command is authorized

        Checks:
        - Entity not in denylist
        - Entity in allowlist (if allowlist is configured)
        - Command type is allowed
        """
        if not self.security_enabled:
            return True, None

        entity_id = command.get('entity_id')
        command_type = command.get('command_type')

        # Check denylist
        if entity_id in self.denylist:
            return False, ValidationError(
                code='E015',
                message=f'Entity {entity_id} is denied',
                field='entity_id'
            )

        # Check allowlist (if configured)
        if self.allowlist and entity_id not in self.allowlist:
            return False, ValidationError(
                code='E016',
                message=f'Entity {entity_id} is not in allowlist',
                field='entity_id'
            )

        # Check command type allowed
        if command_type not in self.allowed_command_types:
            return False, ValidationError(
                code='E017',
                message=f'Command type {command_type} is not allowed',
                field='command_type'
            )

        return True, None

    # =========================================================================
    # Layer 5: Rate Limiting
    # =========================================================================

    def _check_rate_limit(self, command: Dict[str, Any]) -> Tuple[bool, Optional[ValidationError]]:
        """
        Check if command exceeds rate limits

        Checks:
        - Global rate limit (commands per second across all entities)
        - Per-entity rate limit (commands per second for this entity)
        - Per-entity cooldown (minimum time between commands)
        """
        if not self.rate_limit_enabled:
            return True, None

        now = time.time()
        entity_id = command.get('entity_id')

        # Check global rate
        recent_global = [t for t in self.global_timestamps if now - t < 1.0]
        if len(recent_global) >= self.global_limit:
            return False, ValidationError(
                code='E018',
                message=f'Global rate limit exceeded ({self.global_limit} commands/sec)',
                field=None
            )

        # Initialize entity timestamp queue if needed
        if entity_id not in self.entity_timestamps:
            self.entity_timestamps[entity_id] = deque(maxlen=10)

        # Check entity rate
        recent_entity = [t for t in self.entity_timestamps[entity_id] if now - t < 1.0]
        if len(recent_entity) >= self.entity_limit:
            return False, ValidationError(
                code='E019',
                message=f'Entity rate limit exceeded ({self.entity_limit} commands/sec)',
                field='entity_id'
            )

        # Check entity cooldown
        if self.entity_timestamps[entity_id]:
            last_command = self.entity_timestamps[entity_id][-1]
            time_since_last_ms = (now - last_command) * 1000

            if time_since_last_ms < self.entity_cooldown_ms:
                remaining_ms = self.entity_cooldown_ms - time_since_last_ms
                return False, ValidationError(
                    code='E020',
                    message=f'Entity cooldown active ({remaining_ms:.0f}ms remaining)',
                    field='entity_id'
                )

        # Record timestamps
        self.global_timestamps.append(now)
        self.entity_timestamps[entity_id].append(now)

        return True, None

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return {
            'global_queue_size': len(self.global_timestamps),
            'entity_queues': len(self.entity_timestamps),
            'security_enabled': self.security_enabled,
            'rate_limit_enabled': self.rate_limit_enabled,
            'allowlist_size': len(self.allowlist),
            'denylist_size': len(self.denylist),
        }


# =============================================================================
# Testing
# =============================================================================

def test_validator():
    """Test command validator"""
    print("Testing CommandValidator...")
    print()

    # Create validator with test config
    config = {
        'security_enabled': True,
        'allowlist': [],  # Empty = all allowed
        'denylist': ['generator'],
        'allowed_commands': ['light', 'climate', 'switch'],
        'rate_limit_enabled': True,
        'global_commands_per_second': 10,
        'entity_commands_per_second': 2,
        'entity_cooldown_ms': 500
    }

    validator = CommandValidator(config=config)

    # Test 1: Valid light command
    print("Test 1: Valid Light On Command")
    command = {
        'entity_id': 'light_ceiling',
        'command_type': 'light',
        'value': 'ON'
    }
    valid, error = validator.validate(command)
    if valid:
        print("  ✓ PASS - Command validated")
    else:
        print(f"  ✗ FAIL - {error.code}: {error.message}")
    print()

    # Test 2: Valid brightness command (different entity to avoid cooldown)
    print("Test 2: Valid Brightness Command")
    time.sleep(0.6)  # Wait for cooldown
    command = {
        'entity_id': 'light_entry',  # Different entity
        'command_type': 'light',
        'action': 'brightness',
        'value': 75
    }
    valid, error = validator.validate(command)
    if valid:
        print("  ✓ PASS - Command validated")
    else:
        print(f"  ✗ FAIL - {error.code}: {error.message}")
    print()

    # Test 3: Invalid brightness (out of range)
    print("Test 3: Invalid Brightness (150 > 100)")
    command = {
        'entity_id': 'light_ceiling',
        'command_type': 'light',
        'action': 'brightness',
        'value': 150
    }
    valid, error = validator.validate(command)
    if not valid and error.code == 'E014':
        print(f"  ✓ PASS - Correctly rejected: {error.message}")
    else:
        print(f"  ✗ FAIL - Should have been rejected")
    print()

    # Test 4: Missing required field
    print("Test 4: Missing Required Field")
    command = {
        'command_type': 'light'
        # Missing entity_id
    }
    valid, error = validator.validate(command)
    if not valid and error.code == 'E004':
        print(f"  ✓ PASS - Correctly rejected: {error.message}")
    else:
        print(f"  ✗ FAIL - Should have been rejected")
    print()

    # Test 5: Climate temperature command
    print("Test 5: Valid Climate Temperature")
    command = {
        'entity_id': 'hvac_front',
        'command_type': 'climate',
        'action': 'temperature',
        'value': 72
    }
    valid, error = validator.validate(command)
    if valid:
        print("  ✓ PASS - Command validated")
    else:
        print(f"  ✗ FAIL - {error.code}: {error.message}")
    print()

    # Test 6: Denied entity
    print("Test 6: Denied Entity")
    command = {
        'entity_id': 'generator',
        'command_type': 'switch',
        'value': 'ON'
    }
    valid, error = validator.validate(command)
    if not valid and error.code == 'E015':
        print(f"  ✓ PASS - Correctly denied: {error.message}")
    else:
        print(f"  ✗ FAIL - Should have been denied")
    print()

    # Test 7: Rate limiting
    print("Test 7: Rate Limiting")
    command = {
        'entity_id': 'light_test',
        'command_type': 'light',
        'value': 'ON'
    }

    # First command should pass
    valid1, error1 = validator.validate(command)

    # Wait for cooldown (500ms)
    time.sleep(0.6)

    # Second command should pass (within rate limit of 2/sec and after cooldown)
    valid2, error2 = validator.validate(command)

    # Third command immediately should fail (exceeds 2 commands/sec for this entity)
    valid3, error3 = validator.validate(command)

    if valid1 and valid2 and not valid3 and ('rate limit' in error3.message.lower() or 'cooldown' in error3.message.lower()):
        print(f"  ✓ PASS - Rate limiting working: {error3.message}")
    else:
        print(f"  ✗ FAIL - Rate limiting not working correctly")
        print(f"    valid1={valid1}, valid2={valid2}, valid3={valid3}")
        if error3:
            print(f"    error3: {error3.message}")
    print()

    # Show stats
    print("Validator Statistics:")
    stats = validator.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()

    print("All tests completed!")


if __name__ == "__main__":
    test_validator()
