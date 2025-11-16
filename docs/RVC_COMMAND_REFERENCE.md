# RV-C Command Message Reference

**Phase 2: Bidirectional Communication**
**Document Version:** 1.0
**Date:** November 2025

This document provides a comprehensive reference for RV-C command messages that will be implemented in Phase 2. The information is extracted from working Perl examples and will guide the Python implementation.

---

## Table of Contents
- [Overview](#overview)
- [CAN Frame Structure](#can-frame-structure)
- [Command Types](#command-types)
  - [DC Dimmer Commands (Lights)](#dc-dimmer-commands-lights)
  - [Thermostat Commands (HVAC)](#thermostat-commands-hvac)
  - [Vent Fan Commands](#vent-fan-commands)
  - [Panel Light Commands](#panel-light-commands)
  - [Generator Commands](#generator-commands)
- [Implementation Notes](#implementation-notes)

---

## Overview

RV-C (RV Controller Area Network) uses standard CAN bus messaging with a specific protocol for RV systems. Commands are sent as CAN frames with:
- 29-bit extended CAN ID (containing priority, DGN, and source address)
- 8-byte data payload
- Specific byte layouts for each command type

### Common Parameters
- **Source Address:** `99` (0x63) - Used for external controllers
- **Priority:** `6` - Standard priority for control commands
- **Extended ID:** Always `True` (29-bit addressing)

---

## CAN Frame Structure

### CAN ID Composition (29 bits)
```
Bits 0-2:   Priority (3 bits)
Bit 3:      Reserved (always 0)
Bits 4-20:  Data Group Number - DGN (17 bits)
Bits 21-23: Reserved (always 0)
Bits 24-28: Source Address (8 bits)
```

### Building CAN ID
```python
# Binary composition
binCanId = sprintf("%b0%b%b%b", hex(prio), hex(dgnhi), hex(dgnlo), hex(srcAD))
hexCanId = sprintf("%08X", oct("0b" + binCanId))

# Example: Priority=6, DGN=0x1FEDB, SourceAddr=99
# Result: 0x19FEDB63
```

---

## Command Types

### DC Dimmer Commands (Lights)

**DGN:** `0x1FEDB` (DGN_HI=0x1FE, DGN_LO=0xDB)
**Source:** `examples/dc_dimmer.pl`, `examples/panel_lights.pl`
**CAN ID:** `0x19FEDB63` (Priority=6, Source=99)

#### Data Frame Format (8 bytes)
```
Byte 0: Instance ID (load number)
Byte 1: 0xFF (reserved)
Byte 2: Brightness (0-200, where 100% = 200)
Byte 3: Command code
Byte 4: Duration (0-255 seconds, or special values)
Byte 5: 0x00 (reserved)
Byte 6: 0xFF (reserved)
Byte 7: 0xFF (reserved)
```

#### Command Codes
| Code | Name | Description | Notes |
|------|------|-------------|-------|
| 0 | Set Level (delay) | Set brightness with optional delay | Requires cleanup sequence |
| 1 | On (Duration) | Turn on for duration | |
| 2 | On (Delay) | Turn on after delay | |
| 3 | Off (Delay) | Turn off after delay | |
| 5 | Toggle | Toggle current state | |
| 6 | Memory Off | Turn off and save state | |
| 17 | Ramp Brightness | Gradually change brightness | Requires cleanup sequence |
| 18 | Ramp Toggle | Toggle with ramping | |
| 19 | Ramp Up | Increase brightness gradually | |
| 20 | Ramp Down | Decrease brightness gradually | |
| 21 | Ramp Down/Up | Bidirectional ramp | |

#### Brightness Conversion
```python
# HA uses 0-100%, RV-C uses 0-200
rvc_brightness = ha_brightness * 2
```

#### Special Command Sequences

**Set Level (Command 0) Cleanup:**
```python
# Step 1: Set brightness
send_frame([instance, 0xFF, brightness, 0, duration, 0x00, 0xFF, 0xFF])

# Step 2: After 5 seconds (if command==17) or immediately
send_frame([instance, 0xFF, 0, 21, 0, 0x00, 0xFF, 0xFF])

# Step 3: Stop ramp
send_frame([instance, 0xFF, 0, 4, 0, 0x00, 0xFF, 0xFF])
```

#### Example Instances (Tiffin-specific)
| Instance | Location |
|----------|----------|
| 1 | Ceiling Light |
| 2 | Entry Light |
| 3 | Task Light |
| 4 | Hall Light |
| 5 | Bedroom Light |
| 6 | Bathroom Light |
| 8 | Floor Light |
| 9 | Dinette Light |
| 10 | Sconce Light |
| 11 | TV Accent Light |
| 12 | Awning Light |
| 94 | Porch Light |

#### Panel Light Control
Panel lights use a simpler command format:
```
Byte 0: 0xFF
Byte 1: Instance ID
Byte 2: Brightness (0-200)
Byte 3: 0xFF
Byte 4: 0xFF
Byte 5: 0xFF
Byte 6: 0x00
Byte 7: 0xFF

# Data format
sprintf("FF%02X%02XFFFFFF00FF", instance, brightness)
```

---

### Thermostat Commands (HVAC)

**DGN:** `0x1FEF9` (DGN_HI=0x1FE, DGN_LO=0xF9)
**Source:** `examples/thermostats.pl`
**CAN ID:** `0x19FEF963` (Priority=6, Source=99)

#### Data Frame Format (8 bytes)
```
Byte 0: Instance ID (zone number)
Bytes 1-7: Command-specific data (7 bytes)
```

#### Command Map
```python
thermostat_commands = {
    'off':  'C0FFFFFFFFFFFF',
    'cool': 'C1FFFFFFFFFFFF',
    'heat': 'C2FFFFFFFFFFFF',
    'low':  'DF64FFFFFFFFFF',
    'high': 'DFC8FFFFFFFFFF',
    'auto': 'CFFFFFFFFFFFFF',
    'low_fanonly':  'D464FFFFFFFFFF',
    'high_fanonly': 'D4C8FFFFFFFFFF',
    'auto_fanonly': 'C0FFFFFFFFFFFF',
    'up':   'FFFFFFFFFAFFFF',
    'down': 'FFFFFFFFF9FFFF',
}
```

#### Fan Mode Handling
Fan commands differ based on current operating mode:
- If current mode is 'off' or 'fan': Use `*_fanonly` variants
- If current mode is 'cool' or 'heat': Use regular fan commands

#### Temperature Setpoint
```python
# Set temperature command format
# Bytes: [instance, 0xFF, 0xFF, temp_low, temp_high, temp_low, temp_high, 0xFF]

# Temperature conversion formula
def tempF2hex(fahrenheit):
    # Add 0.999 to prevent rounding errors
    # Spyder thermostats use half-degree increments (75.5, 76.5, etc.)
    kelvin = ((fahrenheit - 32) * 5 / 9) + 273
    rvc_value = int((kelvin / 0.03125) + 0.999)

    # Convert to hex and swap bytes (little-endian)
    hex_str = format(rvc_value, '04X')
    return hex_str[2:4] + hex_str[0:2]  # Swap byte order

# Example: 72°F
# Input: 72 + 0.5 = 72.5°F (Spyder adjustment)
# Output: "24D6" (swapped bytes)

# Data frame
sprintf("%02XFFFF%s%sFF", instance, temp_hex, temp_hex)
```

#### Zone Instances (Tiffin-specific)
| Instance | Zone | Type |
|----------|------|------|
| 0 | Front | AC/Heat |
| 1 | Mid | AC |
| 2 | Rear | AC/Heat |
| 3 | Front Furnace | Furnace only |
| 4 | Rear Furnace | Furnace only |

**Note:** Highline coaches use instances 2-6, Lowline use 0-4

#### Furnace Setpoint Sync
When setting temperature for zones with furnaces (even-numbered instances), also set the furnace setpoint:
```python
# If instance is even (0, 2, 4), also set instance+3
if instance % 2 == 0:
    send_frame([instance + 3, 0xFF, 0xFF, temp_hex, temp_hex, 0xFF])
```

---

### Vent Fan Commands

**DGN:** `0x1FEDB` (same as DC Dimmer)
**Source:** `examples/vent_fan_new.pl`
**CAN ID:** `0x19FEDB60` (Priority=6, Source=96)

**Note:** Uses source address 96 instead of 99

#### Data Frame Format
```
Byte 0: Load ID (vent fan instance)
Byte 1: 0xFF
Byte 2: 0xC8 (200 - brightness always at 100%)
Byte 3: Command (2=On, 3=Off)
Byte 4: 0xFF (duration)
Byte 5: 0x00
Byte 6: 0xFF
Byte 7: 0xFF

# Format
sprintf("%02XFFC8%02X%02X00FFFF", load_id, command, 255)
```

#### Vent Fan Commands
| Command | Function |
|---------|----------|
| 2 | On |
| 3 | Off |

---

### Ceiling Fan Commands

**DGN:** `0x1FEDB` (same as DC Dimmer)
**Source:** `examples/ceiling_fan.pl`
**CAN ID:** `0x19FEDB60` (Priority=6, Source=96)

Ceiling fans use a special multi-load control:

#### Special Load Mapping
```python
specials = {
    1: {  # Bedroom fan
        0: [35, 36],  # Off: both loads off
        1: [35, 36],  # Low: both on at same level
        2: [36, 35],  # High: reversed priority
    },
    2: {  # Bedroom (2018+ Open Road)
        0: [33, 34],
        1: [33, 34],
        2: [34, 33],
    }
}
```

#### Command Sequence
```python
# For speed > 0 (Low or High)
# Step 1: Turn off opposite load
send_frame([specials[instance][speed][1], 0xFF, 0xC8, 3, 0, 0x00, 0xFF, 0xFF])

# Step 2: Turn on primary load
send_frame([specials[instance][speed][0], 0xFF, 0xC8, 5, 255, 0x00, 0xFF, 0xFF])

# For speed = 0 (Off)
# Turn off both loads
send_frame([specials[instance][0][0], 0xFF, 0xC8, 3, 0, 0x00, 0xFF, 0xFF])
send_frame([specials[instance][0][1], 0xFF, 0xC8, 3, 0, 0x00, 0xFF, 0xFF])
```

---

### Generator Commands

**DGN:** `0x1FEDB` (same as DC Dimmer)
**Source:** `examples/generator.pl`
**CAN ID:** `0x19FEDB63` (Priority=6, Source=99)

**WARNING:** Generator control requires state monitoring for safety!

#### Load IDs by Model Year
| Year | Stop ID | Start ID |
|------|---------|----------|
| 2014 | 18 | 14 |
| 2015 | 104 | 103 |
| 2016+ | 104 | 103 |
| 2018+ | 84 | 83 |

#### Start Sequence
```python
# Step 1: Prime fuel pump (5 seconds)
send_frame([stop_id, 0xFF, 0xC8, 1, 0xFF, 0x00, 0xFF, 0xFF])
sleep(5)

# Step 2: Release prime
send_frame([stop_id, 0xFF, 0xC8, 4, 0xFF, 0x00, 0xFF, 0xFF])
sleep(1)

# Step 3: Start (monitor for 30 seconds)
send_frame([start_id, 0xFF, 0xC8, 1, 0xFF, 0x00, 0xFF, 0xFF])

# Monitor MQTT topic "CP/GENERATOR_STATUS" for state change to "running"
# Timeout after 30 seconds

# Step 4: Release start
send_frame([start_id, 0xFF, 0xC8, 4, 0xFF, 0x00, 0xFF, 0xFF])
```

#### Stop Sequence
```python
# Step 1: Turn off start load
send_frame([start_id, 0xFF, 0xC8, 4, 0xFF, 0x00, 0xFF, 0xFF])

# Step 2: Activate stop
send_frame([stop_id, 0xFF, 0xC8, 1, 0xFF, 0x00, 0xFF, 0xFF])

# Monitor MQTT topic for state change to "stopped" (30 second timeout)

# Step 3: Release stop
send_frame([stop_id, 0xFF, 0xC8, 4, 0xFF, 0x00, 0xFF, 0xFF])
```

#### State Validation
- Always check MQTT state before starting/stopping
- Verify state is fresh (timestamp < 3 seconds old)
- Abort if state is stale or already in desired state
- Wait for state confirmation with timeout

---

## Implementation Notes

### General Guidelines

1. **CAN ID Construction**
   - Use binary string manipulation to build 29-bit CAN ID
   - Convert to 32-bit hex string with proper padding
   - Always use extended_id=True

2. **Data Validation**
   - Validate all input ranges before encoding
   - Brightness: 0-100 (convert to 0-200 for RV-C)
   - Temperature: Valid HVAC range (typically 60-90°F)
   - Instance IDs: Match configured devices
   - Command codes: Only allow documented commands

3. **Multi-Step Commands**
   - DC Dimmer Set Level (0) requires 3-step sequence
   - Generator start/stop requires state monitoring
   - Ceiling fans require specific load sequencing
   - Add appropriate delays between steps

4. **Error Handling**
   - Log all command attempts
   - Validate state before executing (generator)
   - Return acknowledgment to MQTT
   - Implement timeout for state-dependent commands

5. **Rate Limiting**
   - Prevent CAN bus flooding
   - Queue commands if needed
   - Per-device cooldown periods
   - Global command rate limit

6. **Security**
   - Validate command source (MQTT authentication)
   - Allowlist of controllable instances
   - Audit all commands
   - Reject out-of-range values

### Python Implementation Plan

```python
# Module structure
rvc_commands.py
├── build_can_id(priority, dgn_hi, dgn_lo, src_addr)
├── encode_dimmer_command(instance, brightness, command, duration)
├── encode_thermostat_command(instance, command, value=None)
├── encode_vent_command(instance, command)
├── encode_generator_command(year, command, state_monitor)
└── validate_command(command_type, parameters)
```

### Testing Strategy

1. **Unit Tests**
   - Test CAN ID construction
   - Validate data encoding
   - Test all command variants
   - Verify temperature conversion

2. **Integration Tests**
   - Test MQTT → CAN flow
   - Verify HA integration
   - Test multi-step sequences
   - State monitoring validation

3. **Safety Tests**
   - Invalid command rejection
   - Rate limiting verification
   - Audit log completeness
   - Error recovery

---

## References

- RV-C Specification: RVIA Standard
- Perl Examples: `examples/*.pl`
- Tiffin Spyder System Documentation
- Home Assistant MQTT Discovery: https://www.home-assistant.io/integrations/mqtt/

---

**Document Status:** ✅ Complete - Ready for implementation
**Next Step:** Design Phase 2 architecture based on this reference
