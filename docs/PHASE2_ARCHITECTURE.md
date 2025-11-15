# Phase 2 Architecture Design
## Bidirectional Communication System

**Version:** 1.0
**Date:** November 2025
**Status:** Design Document

---

## Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Component Design](#component-design)
- [Data Flow](#data-flow)
- [Security Model](#security-model)
- [Error Handling](#error-handling)
- [Configuration](#configuration)
- [Testing Strategy](#testing-strategy)

---

## Overview

Phase 2 adds bidirectional communication to rvc2mqtt, enabling Home Assistant to send commands to RV systems via MQTT, which are then transmitted to the CAN bus. This architecture document defines the system design, component interactions, and implementation approach.

### Goals
- ✅ Enable HA to control RV systems (lights, HVAC, switches)
- ✅ Validate all commands before CAN transmission
- ✅ Prevent CAN bus flooding with rate limiting
- ✅ Maintain security with authorization and audit logging
- ✅ Provide command acknowledgment and error feedback
- ✅ Support multi-step command sequences safely

### Success Criteria
- Commands execute within 100ms
- Zero invalid commands reach CAN bus
- Full audit trail of all commands
- Graceful degradation on errors

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Home Assistant                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Light   │  │  Climate │  │  Switch  │  │ Button   │       │
│  │  Entity  │  │  Entity  │  │  Entity  │  │  Entity  │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │             │               │             │             │
│       └─────────────┴───────────────┴─────────────┘             │
│                          │                                       │
└──────────────────────────┼───────────────────────────────────────┘
                           │ MQTT Commands
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       MQTT Broker                                │
│                    (mosquitto, etc.)                             │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      rvc2mqtt.py                                 │
│ ┌───────────────────────────────────────────────────────────┐   │
│ │  Phase 1: CAN → MQTT (Existing)                           │   │
│ │  ┌────────┐  ┌────────┐  ┌──────────┐  ┌──────────┐     │   │
│ │  │ CAN RX │─▶│ Decode │─▶│ HA State │─▶│ Publish  │     │   │
│ │  └────────┘  └────────┘  └──────────┘  └──────────┘     │   │
│ └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│ ┌───────────────────────────────────────────────────────────┐   │
│ │  Phase 2: MQTT → CAN (New)                                │   │
│ │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │   │
│ │  │ MQTT Sub │─▶│ Parse    │─▶│ Validate │─▶│ Encode   │ │   │
│ │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │   │
│ │       │             │              │             │        │   │
│ │       ▼             ▼              ▼             ▼        │   │
│ │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │   │
│ │  │  Audit   │  │ Security │  │   Rate   │  │   CAN    │ │   │
│ │  │   Log    │  │  Check   │  │  Limit   │  │    TX    │ │   │
│ │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │   │
│ └───────────────────────────────────────────────────────────┘   │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CAN Bus (RV-C)                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Lights  │  │   HVAC   │  │ Switches │  │   Fans   │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. Command Receiver (`rvc2mqtt.py`)

**Responsibilities:**
- Subscribe to HA command topics
- Route commands to appropriate handlers
- Manage MQTT connection lifecycle

**MQTT Topic Structure:**
```
# Command Topics (subscribe)
rv/light/{entity_id}/set                    # Light on/off
rv/light/{entity_id}/brightness/set         # Light brightness
rv/climate/{entity_id}/mode/set             # Climate mode
rv/climate/{entity_id}/temperature/set      # Temperature setpoint
rv/climate/{entity_id}/fan_mode/set         # Fan mode
rv/switch/{entity_id}/set                   # Switch on/off

# Status Topics (publish)
rv/command/status                           # Command execution status
rv/command/error                            # Error messages
```

**Implementation:**
```python
def on_mqtt_connect(client, userdata, flags, reason_code, properties):
    # Subscribe to all command topics
    client.subscribe("rv/light/+/set")
    client.subscribe("rv/light/+/brightness/set")
    client.subscribe("rv/climate/+/mode/set")
    client.subscribe("rv/climate/+/temperature/set")
    client.subscribe("rv/climate/+/fan_mode/set")
    client.subscribe("rv/switch/+/set")

def on_mqtt_message(client, userdata, msg):
    try:
        # Parse topic and extract entity_id
        entity_id, command_type = parse_command_topic(msg.topic)

        # Parse payload
        payload = msg.payload.decode('utf-8')

        # Route to command handler
        command_handler.process_command(entity_id, command_type, payload)

    except Exception as e:
        log_error(f"Command processing failed: {e}")
        publish_error(msg.topic, str(e))
```

---

### 2. Command Parser (`command_parser.py`)

**Responsibilities:**
- Parse MQTT command payloads
- Extract entity_id from topics
- Normalize command format
- Initial validation

**Module Structure:**
```python
class CommandParser:
    """Parse and normalize MQTT commands"""

    def parse_light_command(self, entity_id, payload):
        """
        Parse light command (ON/OFF or brightness)

        Returns:
            {
                'entity_id': str,
                'command_type': 'light',
                'action': 'state' or 'brightness',
                'value': str or int
            }
        """

    def parse_climate_command(self, entity_id, command_type, payload):
        """
        Parse climate command (mode, temp, fan)

        Returns:
            {
                'entity_id': str,
                'command_type': 'climate',
                'action': 'mode' or 'temperature' or 'fan_mode',
                'value': str or int
            }
        """

    def parse_switch_command(self, entity_id, payload):
        """Parse switch command (ON/OFF)"""
```

---

### 3. Command Validator (`command_validator.py`)

**Responsibilities:**
- Validate command structure
- Check value ranges
- Verify entity exists and is controllable
- Apply security policies
- Rate limiting

**Validation Layers:**

```python
class CommandValidator:
    def __init__(self, config, ha_discovery):
        self.config = config
        self.ha_discovery = ha_discovery
        self.rate_limiter = RateLimiter(config)
        self.security = SecurityManager(config)

    def validate(self, command):
        """
        Multi-layer validation

        Returns: (is_valid, error_message)
        """
        # Layer 1: Schema validation
        if not self._validate_schema(command):
            return False, "Invalid command structure"

        # Layer 2: Entity validation
        if not self._validate_entity(command['entity_id']):
            return False, "Entity not found or not controllable"

        # Layer 3: Value range validation
        if not self._validate_value_range(command):
            return False, "Value out of range"

        # Layer 4: Security check
        if not self.security.is_allowed(command):
            return False, "Command not authorized"

        # Layer 5: Rate limiting
        if not self.rate_limiter.allow(command):
            return False, "Rate limit exceeded"

        return True, None
```

**Value Range Validation:**
```python
VALIDATION_RULES = {
    'light': {
        'brightness': {'min': 0, 'max': 100, 'type': int},
        'state': {'values': ['ON', 'OFF'], 'type': str},
    },
    'climate': {
        'temperature': {'min': 60, 'max': 90, 'type': int},
        'mode': {'values': ['off', 'cool', 'heat', 'auto'], 'type': str},
        'fan_mode': {'values': ['auto', 'low', 'high'], 'type': str},
    },
    'switch': {
        'state': {'values': ['ON', 'OFF'], 'type': str},
    }
}
```

---

### 4. Rate Limiter (`rate_limiter.py`)

**Responsibilities:**
- Prevent CAN bus flooding
- Per-entity rate limiting
- Global rate limiting
- Command queuing

**Design:**
```python
class RateLimiter:
    def __init__(self, config):
        self.global_limit = config['global_commands_per_second']  # e.g., 10
        self.entity_limit = config['entity_commands_per_second']  # e.g., 2
        self.entity_cooldown = config['entity_cooldown_ms']       # e.g., 500

        self.global_timestamps = deque(maxlen=100)
        self.entity_timestamps = {}  # entity_id -> deque of timestamps

    def allow(self, command):
        """Check if command is allowed based on rate limits"""
        now = time.time()
        entity_id = command['entity_id']

        # Check global rate
        recent_global = [t for t in self.global_timestamps if now - t < 1.0]
        if len(recent_global) >= self.global_limit:
            return False

        # Check entity rate
        if entity_id not in self.entity_timestamps:
            self.entity_timestamps[entity_id] = deque(maxlen=10)

        recent_entity = [t for t in self.entity_timestamps[entity_id]
                        if now - t < 1.0]
        if len(recent_entity) >= self.entity_limit:
            return False

        # Check entity cooldown
        if self.entity_timestamps[entity_id]:
            last_command = self.entity_timestamps[entity_id][-1]
            if (now - last_command) * 1000 < self.entity_cooldown:
                return False

        # Record timestamp
        self.global_timestamps.append(now)
        self.entity_timestamps[entity_id].append(now)

        return True
```

---

### 5. RV-C Command Encoder (`rvc_commands.py`)

**Responsibilities:**
- Build CAN IDs
- Encode command data frames
- Handle multi-step sequences
- Device-specific encoding

**Module Structure:**
```python
class RVCCommandEncoder:
    """Encode commands into RV-C CAN frames"""

    def __init__(self, config):
        self.config = config
        self.source_address = 99  # Default controller address

    def build_can_id(self, priority, dgn_hi, dgn_lo, src_addr=None):
        """
        Build 29-bit CAN ID

        Returns: int (CAN arbitration ID)
        """

    def encode_light_command(self, instance, state=None, brightness=None):
        """
        Encode DC dimmer light command

        Returns: list of (can_id, data_bytes, delay_ms) tuples
        """

    def encode_climate_mode(self, instance, mode, current_mode=None):
        """
        Encode thermostat mode command

        Returns: list of (can_id, data_bytes, delay_ms) tuples
        """

    def encode_climate_temperature(self, instance, temperature_f):
        """
        Encode thermostat setpoint command

        Returns: list of (can_id, data_bytes, delay_ms) tuples
        """

    def encode_climate_fan(self, instance, fan_mode, current_mode=None):
        """
        Encode thermostat fan command

        Returns: list of (can_id, data_bytes, delay_ms) tuples
        """

    def encode_switch_command(self, instance, state):
        """
        Encode switch on/off command

        Returns: list of (can_id, data_bytes, delay_ms) tuples
        """
```

---

### 6. CAN Transmitter (`can_tx.py`)

**Responsibilities:**
- Send CAN frames to bus
- Handle multi-frame sequences
- Retry logic
- Error reporting

**Implementation:**
```python
class CANTransmitter:
    def __init__(self, bus):
        self.bus = bus
        self.retry_count = 3
        self.retry_delay_ms = 100

    def send_command(self, frames):
        """
        Send one or more CAN frames

        Args:
            frames: list of (can_id, data_bytes, delay_ms) tuples

        Returns: (success, error_message)
        """
        try:
            for can_id, data, delay_ms in frames:
                # Create CAN message
                msg = can.Message(
                    arbitration_id=can_id,
                    data=data,
                    is_extended_id=True
                )

                # Send with retry
                success = self._send_with_retry(msg)
                if not success:
                    return False, f"Failed to send frame {can_id:08X}"

                # Delay between frames if needed
                if delay_ms > 0:
                    time.sleep(delay_ms / 1000.0)

            return True, None

        except Exception as e:
            return False, str(e)

    def _send_with_retry(self, msg):
        """Send CAN message with retry logic"""
        for attempt in range(self.retry_count):
            try:
                self.bus.send(msg)
                return True
            except can.CanError as e:
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay_ms / 1000.0)
                else:
                    raise
        return False
```

---

### 7. Audit Logger (`audit_logger.py`)

**Responsibilities:**
- Log all command attempts
- Track success/failure
- Provide audit trail
- Support debugging

**Log Format:**
```python
class AuditLogger:
    def __init__(self, log_file):
        self.log_file = log_file
        self.logger = self._setup_logger()

    def log_command(self, command, result):
        """
        Log command execution

        Format:
        {
            'timestamp': '2025-11-15 14:23:45.123',
            'entity_id': 'light_ceiling',
            'command_type': 'light',
            'action': 'brightness',
            'value': 75,
            'can_frames': ['19FEDB63#01FFC8000000FFFF'],
            'result': 'success' or 'failed',
            'error': 'error message if failed',
            'latency_ms': 45
        }
        """
```

---

### 8. Security Manager (`security_manager.py`)

**Responsibilities:**
- Allowlist/denylist enforcement
- Entity access control
- Command authorization

**Configuration:**
```python
class SecurityManager:
    def __init__(self, config):
        self.enabled = config.get('security_enabled', True)
        self.allowlist = config.get('allowlist', [])  # entity_ids
        self.denylist = config.get('denylist', [])    # entity_ids
        self.allowed_commands = config.get('allowed_commands', [])

    def is_allowed(self, command):
        """Check if command is authorized"""
        if not self.enabled:
            return True

        entity_id = command['entity_id']

        # Check denylist first
        if entity_id in self.denylist:
            return False

        # Check allowlist (if configured)
        if self.allowlist and entity_id not in self.allowlist:
            return False

        # Check command type
        command_type = command['command_type']
        if self.allowed_commands and command_type not in self.allowed_commands:
            return False

        return True
```

---

## Data Flow

### Command Execution Flow

```
1. Home Assistant sends MQTT command
   Topic: rv/light/ceiling/brightness/set
   Payload: 75

2. rvc2mqtt receives message (on_mqtt_message)
   ↓
3. CommandParser extracts and normalizes
   {
     'entity_id': 'light_ceiling',
     'command_type': 'light',
     'action': 'brightness',
     'value': 75
   }
   ↓
4. CommandValidator validates
   - Schema ✓
   - Entity exists ✓
   - Value in range (0-100) ✓
   - Security check ✓
   - Rate limit ✓
   ↓
5. AuditLogger logs attempt
   ↓
6. RVCCommandEncoder encodes
   - Maps entity_id to instance (from mapping file)
   - Converts brightness 75 → 150 (RV-C format)
   - Builds CAN frames:
     [
       (0x19FEDB63, [0x01, 0xFF, 0x96, 0x00, 0xFF, 0x00, 0xFF, 0xFF], 0),
       (0x19FEDB63, [0x01, 0xFF, 0x00, 0x15, 0x00, 0x00, 0xFF, 0xFF], 5000),
       (0x19FEDB63, [0x01, 0xFF, 0x00, 0x04, 0x00, 0x00, 0xFF, 0xFF], 0)
     ]
   ↓
7. CANTransmitter sends frames
   - Frame 1: Set brightness to 150
   - Wait 5 seconds
   - Frame 2: Ramp down/up command
   - Frame 3: Stop ramp
   ↓
8. AuditLogger logs result
   ↓
9. Publish acknowledgment to MQTT
   Topic: rv/command/status
   Payload: {"entity_id": "light_ceiling", "status": "success"}
```

---

## Security Model

### Defense in Depth

**Layer 1: MQTT Authentication**
- Require username/password for MQTT
- Use TLS for MQTT connection (optional)

**Layer 2: Entity Allowlist**
```ini
[Security]
enabled = 1
allowlist = light_ceiling,light_entry,hvac_front,hvac_rear
denylist = generator
```

**Layer 3: Command Type Restrictions**
```ini
[Security]
allowed_commands = light,climate,switch
# Prevents generator commands even if entity is allowlisted
```

**Layer 4: Value Validation**
- Hard-coded ranges in validator
- Cannot be overridden by config

**Layer 5: Rate Limiting**
- Prevent abuse/flooding
- Per-entity and global limits

**Layer 6: Audit Logging**
- All commands logged
- Immutable audit trail
- Forensic analysis

---

## Error Handling

### Error Types and Responses

```python
ERROR_RESPONSES = {
    'invalid_schema': {
        'code': 'E001',
        'message': 'Invalid command structure',
        'action': 'reject',
        'notify': True
    },
    'entity_not_found': {
        'code': 'E002',
        'message': 'Entity does not exist',
        'action': 'reject',
        'notify': True
    },
    'value_out_of_range': {
        'code': 'E003',
        'message': 'Value out of acceptable range',
        'action': 'reject',
        'notify': True
    },
    'rate_limit_exceeded': {
        'code': 'E004',
        'message': 'Too many commands, please slow down',
        'action': 'queue',  # Optional: queue instead of reject
        'notify': True
    },
    'security_denied': {
        'code': 'E005',
        'message': 'Command not authorized',
        'action': 'reject',
        'notify': True
    },
    'can_tx_failed': {
        'code': 'E006',
        'message': 'Failed to transmit to CAN bus',
        'action': 'retry',
        'notify': True
    }
}
```

### Error Notification
```python
def publish_error(entity_id, error_code, error_message):
    """Publish error to MQTT for HA notification"""
    payload = {
        'entity_id': entity_id,
        'error_code': error_code,
        'message': error_message,
        'timestamp': datetime.now().isoformat()
    }
    mqttc.publish('rv/command/error', json.dumps(payload), retain=False)
```

---

## Configuration

### New Configuration Options (`rvc2mqtt.ini`)

```ini
[Commands]
enabled = 1                     # Enable bidirectional commands (0=disabled, 1=enabled)
source_address = 99             # CAN source address for commands
retry_count = 3                 # Number of retries for failed CAN transmissions
retry_delay_ms = 100            # Delay between retries in milliseconds

[RateLimiting]
enabled = 1                     # Enable rate limiting
global_commands_per_second = 10 # Max commands per second (global)
entity_commands_per_second = 2  # Max commands per second per entity
entity_cooldown_ms = 500        # Minimum delay between commands to same entity

[Security]
enabled = 1                     # Enable security controls
allowlist =                     # Comma-separated list of allowed entity_ids (empty = all)
denylist =                      # Comma-separated list of denied entity_ids
allowed_commands = light,climate,switch  # Allowed command types

[Audit]
enabled = 1                     # Enable audit logging
log_file = logs/command_audit.log
log_level = INFO                # DEBUG, INFO, WARNING, ERROR
```

---

## Testing Strategy

### Unit Tests

**Test Coverage:**
- CAN ID construction
- Data encoding for each device type
- Temperature conversion
- Multi-frame sequences
- Validation logic
- Rate limiter behavior
- Security checks

### Integration Tests

**Test Scenarios:**
1. **Light Control**
   - Turn on/off
   - Set brightness
   - Multi-step sequence execution

2. **Climate Control**
   - Change mode (off/cool/heat)
   - Set temperature
   - Change fan mode
   - Fan mode context handling

3. **Switch Control**
   - Turn on/off
   - Pump control

4. **Error Handling**
   - Invalid commands rejected
   - Rate limiting enforced
   - Security denials
   - CAN transmission failures

### Performance Tests

**Metrics:**
- Command latency (target: <100ms)
- Rate limiter accuracy
- Memory usage under load
- CAN bus utilization

---

## Implementation Phases

### Phase 2.1: Foundation (Week 1)
- ✅ Command reference documentation
- ✅ Architecture design
- ⏳ RV-C command encoder module
- ⏳ CAN ID builder
- ⏳ Modernize can_tx() function

### Phase 2.2: Validation & Security (Week 2)
- ⏳ Command validator
- ⏳ Rate limiter
- ⏳ Security manager
- ⏳ Audit logger

### Phase 2.3: Integration (Week 3)
- ⏳ MQTT command subscription
- ⏳ Command parser
- ⏳ Update HA discovery
- ⏳ Error handling

### Phase 2.4: Testing (Week 4)
- ⏳ Unit tests
- ⏳ Integration tests
- ⏳ End-to-end testing
- ⏳ Performance validation

### Phase 2.5: Documentation (Week 5)
- ⏳ User documentation
- ⏳ API documentation
- ⏳ HA automation examples
- ⏳ README updates

---

## Success Metrics

- ✅ Commands execute within 100ms (target: 50-80ms)
- ✅ Zero invalid commands reach CAN bus (100% validation)
- ✅ Full audit trail (100% command logging)
- ✅ Rate limiting prevents flooding (<10 commands/sec globally)
- ✅ Multi-step sequences work reliably (lights, generator)
- ✅ Error handling graceful (no crashes on invalid input)

---

**Document Status:** ✅ Complete - Ready for implementation
**Next Step:** Begin building rvc_commands.py encoder module
