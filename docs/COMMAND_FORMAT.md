# MQTT Command Format Guide

Complete guide to sending commands from Home Assistant to RV devices via MQTT.

## Quick Start

```yaml
# Example: Turn on ceiling light
service: mqtt.publish
data:
  topic: "rv/light/ceiling_light/set"
  payload: "ON"

# Example: Set light brightness to 75%
service: mqtt.publish
data:
  topic: "rv/light/ceiling_light/brightness/set"
  payload: "75"

# Example: Set HVAC to heat mode
service: mqtt.publish
data:
  topic: "rv/climate/hvac_front/mode/set"
  payload: "heat"
```

## Topic Structure

All command topics follow this pattern:
```
rv/{device_type}/{entity_id}/{action}/set
```

- **rv**: Base topic prefix (matches `state_topic_prefix` in mapping file)
- **device_type**: Type of device (`light`, `climate`, `switch`)
- **entity_id**: Unique identifier for the device
- **action**: Command action (optional for simple commands)
- **set**: Command suffix

---

## Light Commands

### Light ON/OFF

**Topic:**
```
rv/light/{entity_id}/set
```

**Payloads:**
- `ON` - Turn light on (100% brightness)
- `OFF` - Turn light off (0% brightness)

**Examples:**
```yaml
# Turn on ceiling light
topic: "rv/light/ceiling_light/set"
payload: "ON"

# Turn off floor lamp
topic: "rv/light/floor_lamp/set"
payload: "OFF"
```

**RV-C Behavior:**
- ON command generates 3 CAN frames (set level + cleanup sequence)
- OFF command generates 1 CAN frame
- Commands execute with 150ms delays between frames

---

### Light Brightness

**Topic:**
```
rv/light/{entity_id}/brightness/set
```

**Payload:**
- Integer from 0-100 (percentage)

**Examples:**
```yaml
# Set ceiling light to 50%
topic: "rv/light/ceiling_light/brightness/set"
payload: "50"

# Dim to 25%
topic: "rv/light/bedroom_light/brightness/set"
payload: "25"
```

**Validation:**
- Minimum: 0
- Maximum: 100
- Type: Integer

**RV-C Behavior:**
- Generates 3 CAN frames (set level + cleanup sequence)
- Brightness is converted to RV-C scale (0-200)
- Formula: `rvc_brightness = percentage * 2`

---

## Climate Commands

### Climate Mode

**Topic:**
```
rv/climate/{entity_id}/mode/set
```

**Payloads:**
- `off` - Turn HVAC off
- `heat` - Heat mode
- `cool` - Cool mode
- `auto` - Auto mode (if supported)

**Examples:**
```yaml
# Set front HVAC to heat
topic: "rv/climate/hvac_front/mode/set"
payload: "heat"

# Turn off rear HVAC
topic: "rv/climate/hvac_rear/mode/set"
payload: "off"
```

**Validation:**
- Allowed values: `off`, `heat`, `cool`, `auto`
- Case insensitive

**RV-C Behavior:**
- Generates 1 CAN frame
- Command codes:
  - off: `0xC0`
  - cool: `0xC1`
  - heat: `0xC2`

---

### Climate Temperature

**Topic:**
```
rv/climate/{entity_id}/temperature/set
```

**Payload:**
- Integer or float from 50-100 (Fahrenheit)

**Examples:**
```yaml
# Set temperature to 72°F
topic: "rv/climate/hvac_front/temperature/set"
payload: "72"

# Set to 68.5°F
topic: "rv/climate/hvac_front/temperature/set"
payload: "68.5"
```

**Validation:**
- Minimum: 50°F
- Maximum: 100°F
- Type: Integer or Float

**RV-C Behavior:**
- Generates 1-2 CAN frames (thermostat + optional furnace sync)
- Temperature conversion: Fahrenheit → Kelvin → RV-C hex
- Formula: `((F - 32) * 5/9 + 273) / 0.03125 + 0.999`
- Supports half-degree increments

---

### Climate Fan Mode

**Topic:**
```
rv/climate/{entity_id}/fan_mode/set
```

**Payloads:**
- `auto` - Auto fan mode
- `low` - Low fan speed
- `high` - High fan speed

**Examples:**
```yaml
# Set fan to auto
topic: "rv/climate/hvac_front/fan_mode/set"
payload: "auto"

# Set fan to high
topic: "rv/climate/hvac_front/fan_mode/set"
payload: "high"
```

**Validation:**
- Allowed values: `auto`, `low`, `high`
- Case insensitive

**RV-C Behavior:**
- Generates 1 CAN frame
- Command codes:
  - auto: `0xCF`
  - low: `0xDF64`
  - high: `0xDFC8`
- Context-aware (different codes for fan-only vs heat/cool modes)

---

## Switch Commands

### Switch ON/OFF

**Topic:**
```
rv/switch/{entity_id}/set
```

**Payloads:**
- `ON` - Turn switch/pump on
- `OFF` - Turn switch/pump off

**Examples:**
```yaml
# Turn on water pump
topic: "rv/switch/water_pump/set"
payload: "ON"

# Turn off generator
topic: "rv/switch/generator/set"
payload: "OFF"
```

**Validation:**
- Allowed values: `ON`, `OFF`
- Case insensitive

**RV-C Behavior:**
- Generates 1 CAN frame
- Uses GENERIC_INDICATOR_COMMAND (DGN 0x1FFED)
- Default source address: 96

---

## Command Flow

When a command is published to MQTT, it flows through multiple validation and processing stages:

```
MQTT Topic + Payload
       ↓
[1] Parse MQTT Message
       ↓
[2] Schema Validation (required fields, structure)
       ↓
[3] Entity Validation (entity exists)
       ↓
[4] Value Range Validation (min/max, allowed values)
       ↓
[5] Security Check (allowlist/denylist)
       ↓
[6] Rate Limiting (global + per-entity)
       ↓
[7] Encode to RV-C CAN Frames
       ↓
[8] Transmit to CAN Bus
       ↓
[9] Audit Log + Acknowledgment
```

---

## Validation Rules

### Schema Validation
All commands must have:
- `entity_id` - Device identifier
- `command_type` - Device type (light, climate, switch)
- `value` - Command value

Climate commands also require:
- `action` - Command action (mode, temperature, fan_mode)

### Range Validation

| Command | Min | Max | Type | Allowed Values |
|---------|-----|-----|------|----------------|
| Light State | - | - | String | ON, OFF |
| Light Brightness | 0 | 100 | Integer | - |
| Climate Mode | - | - | String | off, heat, cool, auto |
| Climate Temperature | 50 | 100 | Int/Float | - |
| Climate Fan Mode | - | - | String | auto, low, high |
| Switch State | - | - | String | ON, OFF |

### Security Controls

Commands can be restricted via configuration (`rvc2mqtt.ini`):

```ini
[Security]
enabled = 1
allowlist =                              # If set, only these entities allowed
denylist = sensitive_light,critical_pump # These entities blocked
allowed_commands = light,climate,switch  # Only these command types allowed
```

### Rate Limiting

Protection against CAN bus flooding:

```ini
[RateLimiting]
enabled = 1
global_commands_per_second = 10         # Max 10 commands/sec across all devices
entity_commands_per_second = 2          # Max 2 commands/sec per device
entity_cooldown_ms = 500                # Min 500ms between commands to same device
```

---

## Error Handling

### Command Acknowledgments

Successful commands publish status to:
```
rv/command/status
```

Payload:
```json
{
  "entity_id": "ceiling_light",
  "command_type": "light",
  "action": "state",
  "value": "ON",
  "status": "success",
  "latency_ms": 45.2,
  "timestamp": "2025-11-15T10:30:45.123456"
}
```

### Error Messages

Failed commands publish errors to:
```
rv/command/error
```

Payload:
```json
{
  "entity_id": "ceiling_light",
  "command_type": "light",
  "error_code": "E014",
  "error_message": "Value 150 above maximum 100",
  "timestamp": "2025-11-15T10:30:45.123456"
}
```

### Error Codes

| Code | Description | Common Cause |
|------|-------------|--------------|
| E001 | Missing required field | Incomplete command |
| E002 | Invalid command type | Unsupported device type |
| E003 | Invalid action | Wrong action for device type |
| E004 | Missing action field | Climate command without action |
| E011 | Invalid value type | String instead of number |
| E012 | Invalid allowed value | Value not in enum list |
| E013 | Value below minimum | Brightness < 0, temp < 50 |
| E014 | Value above maximum | Brightness > 100, temp > 100 |
| E015 | Entity denied | Entity in denylist |
| E017 | Entity not allowed | Entity not in allowlist |
| E018 | Command type not allowed | Type not in allowed_commands |
| E019 | Rate limit exceeded | Too many commands too fast |
| E020 | Entity cooldown | Command sent too soon after previous |
| E100 | Encoding failed | Unable to create CAN frames |
| E101 | Transmission failed | CAN bus error |

---

## Best Practices

### 1. Use Home Assistant Entities
Instead of publishing directly, use HA entities created by MQTT Discovery:

```yaml
# Good: Use HA entity
service: light.turn_on
target:
  entity_id: light.rv_ceiling_light
data:
  brightness_pct: 75

# Also good: Direct MQTT (for advanced use)
service: mqtt.publish
data:
  topic: "rv/light/ceiling_light/brightness/set"
  payload: "75"
```

### 2. Respect Rate Limits
Avoid sending rapid-fire commands:

```yaml
# Bad: Too fast
- service: light.turn_on
  entity_id: light.rv_ceiling
- service: light.turn_on  # May fail due to cooldown
  entity_id: light.rv_ceiling

# Good: Add delay
- service: light.turn_on
  entity_id: light.rv_ceiling
- delay: 1  # Wait 1 second
- service: light.turn_on
  entity_id: light.rv_ceiling
```

### 3. Check Command Status
Monitor `rv/command/status` and `rv/command/error` topics for feedback:

```yaml
automation:
  - alias: "Monitor RV Command Failures"
    trigger:
      platform: mqtt
      topic: "rv/command/error"
    action:
      service: notify.mobile_app
      data:
        message: "RV Command Failed: {{ trigger.payload_json.error_message }}"
```

### 4. Use Appropriate Temperature Units
Always use Fahrenheit for temperature commands (RV-C standard):

```yaml
# Correct
topic: "rv/climate/hvac_front/temperature/set"
payload: "72"  # 72°F

# Incorrect - Celsius not supported
payload: "22"  # Don't use Celsius!
```

---

## Troubleshooting

### Command Not Working

1. **Check Entity ID**
   - Verify entity exists in HA
   - Check mapping file for correct `entity_id`

2. **Check Payload Format**
   - Use correct case (ON not on for lights/switches)
   - Use correct type (number for brightness, string for mode)

3. **Check Rate Limiting**
   - Wait at least 500ms between commands to same device
   - Don't exceed 10 commands/sec globally

4. **Check Logs**
   ```bash
   tail -f logs/command_audit.log
   ```

5. **Monitor Error Topic**
   ```bash
   mosquitto_sub -h localhost -t "rv/command/error"
   ```

### Common Issues

**"E014: Value above maximum"**
- Brightness > 100 or temperature > 100°F
- Solution: Use values within valid range

**"E020: Entity cooldown"**
- Commands sent too quickly
- Solution: Add delays between commands

**"E015: Entity denied"**
- Entity in denylist
- Solution: Remove from denylist or use different entity

**"E101: Transmission failed"**
- CAN bus not connected
- Solution: Check CAN connection, restart service

---

## Advanced Usage

### Scripted Light Scenes

```yaml
script:
  rv_evening_lights:
    sequence:
      - service: mqtt.publish
        data:
          topic: "rv/light/ceiling_light/brightness/set"
          payload: "50"
      - delay: 1
      - service: mqtt.publish
        data:
          topic: "rv/light/accent_lights/set"
          payload: "ON"
```

### Temperature Scheduling

```yaml
automation:
  - alias: "RV Night Temperature"
    trigger:
      platform: time
      at: "22:00:00"
    action:
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/temperature/set"
          payload: "68"
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/mode/set"
          payload: "heat"
```

### Multi-Zone Climate Control

```yaml
script:
  rv_cool_all_zones:
    sequence:
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/mode/set"
          payload: "cool"
      - delay: 1
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_rear/mode/set"
          payload: "cool"
      - delay: 1
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/temperature/set"
          payload: "72"
      - delay: 1
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_rear/temperature/set"
          payload: "72"
```

---

## Reference

### Full Command List

```
# Lights
rv/light/{entity_id}/set               → ON|OFF
rv/light/{entity_id}/brightness/set    → 0-100

# Climate
rv/climate/{entity_id}/mode/set        → off|heat|cool|auto
rv/climate/{entity_id}/temperature/set → 50-100 (°F)
rv/climate/{entity_id}/fan_mode/set    → auto|low|high

# Switches
rv/switch/{entity_id}/set              → ON|OFF
```

### Configuration Files

- **Command Config**: `rvc2mqtt.ini` - Section `[Commands]`
- **Security Config**: `rvc2mqtt.ini` - Section `[Security]`
- **Rate Limiting**: `rvc2mqtt.ini` - Section `[RateLimiting]`
- **Audit Logging**: `rvc2mqtt.ini` - Section `[Audit]`
- **Entity Mapping**: `mappings/tiffin_default.yaml`

### Related Documentation

- [RV-C Command Reference](RVC_COMMAND_REFERENCE.md) - Low-level CAN frame details
- [Phase 2 Architecture](PHASE2_ARCHITECTURE.md) - System design
- [Phase 2 Testing](PHASE2_TESTING.md) - Test results
