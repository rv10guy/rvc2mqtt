# Home Assistant MQTT Discovery - Research Summary

**Date:** 2025-11-15
**Purpose:** Research for Phase 1 implementation of HA MQTT Discovery in rvc2mqtt
**Sources:** Home Assistant official documentation

---

## Executive Summary

MQTT Discovery allows devices to automatically register themselves in Home Assistant without any manual YAML configuration. When properly implemented, sensors will appear in HA as soon as the bridge starts - no user configuration needed.

**Key Benefits:**
- ✅ Zero-config experience for users
- ✅ Automatic device grouping and organization
- ✅ Proper icons, units, and device classes
- ✅ Clean entity registry management
- ✅ Availability tracking built-in

---

## 1. How MQTT Discovery Works

### Overview
1. Device publishes a **discovery message** to a special topic
2. Home Assistant reads this message and creates the entity
3. Device publishes **state updates** to a separate state topic
4. Home Assistant updates the entity in real-time

### Discovery Message Flow
```
[rvc2mqtt] --discovery--> [MQTT Broker] --subscribe--> [Home Assistant]
           --state------> [MQTT Broker] --subscribe--> [Home Assistant]
```

### Important Notes
- Discovery messages should be **retained** or published on HA birth messages
- Each entity needs a **unique_id** for registry management
- Discovery payloads are JSON dictionaries
- State topics are separate from discovery topics

---

## 2. Discovery Topic Structure

### Format
```
<discovery_prefix>/<component>/[<node_id>/]<object_id>/config
```

### Components
- **discovery_prefix**: Default is `homeassistant` (customizable)
- **component**: Entity type (`sensor`, `binary_sensor`, `switch`, `light`, `climate`)
- **node_id**: Optional grouping identifier (recommended for organization)
- **object_id**: Unique identifier for this specific entity
- **config**: Literal string indicating this is a configuration message

### Topic Naming Rules
- Only alphanumerics, underscores, and hyphens allowed
- Use lowercase for consistency
- Make object_id descriptive and unique

### Examples for RV-C Bridge

**Tank Sensor:**
```
homeassistant/sensor/rvc2_tank_fresh/config
```

**Battery Voltage:**
```
homeassistant/sensor/rvc2_battery_house/config
```

**Light Control:**
```
homeassistant/light/rvc2_ceiling_light/config
```

**HVAC Climate:**
```
homeassistant/climate/rvc2_hvac_front/config
```

**With node_id for organization:**
```
homeassistant/sensor/rvc2/tank_fresh/config
homeassistant/sensor/rvc2/battery_house/config
homeassistant/sensor/rvc2/battery_chassis/config
```
*(Using `rvc2` as node_id groups all entities)*

---

## 3. Discovery Payload Structure

### Minimal Example
```json
{
  "name": "Fresh Water Tank",
  "state_topic": "rvc2/sensor/tank_fresh/state",
  "unique_id": "rvc2_tank_fresh_0"
}
```

### Complete Example with Device Info
```json
{
  "name": "Fresh Water Tank",
  "state_topic": "rvc2/sensor/tank_fresh/state",
  "unit_of_measurement": "%",
  "device_class": "volume",
  "state_class": "measurement",
  "icon": "mdi:water",
  "unique_id": "rvc2_tank_fresh_0",
  "availability_topic": "rvc2/status",
  "payload_available": "online",
  "payload_not_available": "offline",
  "device": {
    "identifiers": ["rvc2_tiffin_001"],
    "name": "RV Systems",
    "model": "Tiffin Motorhome",
    "manufacturer": "RVC-MQTT Bridge",
    "sw_version": "2.0.0",
    "configuration_url": "http://rvc2mqtt.local"
  }
}
```

### Required Fields (Minimum)
- `state_topic` or equivalent data topic
- `unique_id` (highly recommended for entity registry)

### Recommended Fields
- `name` - Human-readable entity name
- `device` - Groups entities under common device
- `availability_topic` - Shows online/offline status
- `unit_of_measurement` - For numeric sensors
- `device_class` - Enables proper UI rendering

---

## 4. Device Information

### Purpose
Groups multiple entities under a single device in HA's device registry. Users see all related entities on one device page.

### Device Configuration
```json
"device": {
  "identifiers": ["rvc2_tiffin_001"],
  "name": "RV Systems",
  "model": "Tiffin Motorhome",
  "manufacturer": "RVC-MQTT Bridge",
  "sw_version": "2.0.0",
  "configuration_url": "http://rvc2mqtt.local",
  "suggested_area": "RV"
}
```

### Device Fields

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `identifiers` | Yes* | List of unique IDs | `["rvc2_001"]` |
| `connections` | Yes* | Alternative to identifiers | `[["mac", "02:5b:26:a8:dc:12"]]` |
| `name` | Recommended | Device display name | `"RV Power Systems"` |
| `manufacturer` | Optional | Maker name | `"RVC-MQTT Bridge"` |
| `model` | Optional | Model identifier | `"Tiffin Motorhome"` |
| `sw_version` | Optional | Software version | `"2.0.0"` |
| `configuration_url` | Optional | Link to config page | `"http://..."` |
| `suggested_area` | Optional | Default area placement | `"RV"` |

*Either `identifiers` or `connections` required

### Multiple Device Strategy for RV-C

Create logical device groupings:

**Device 1: Power Systems**
```json
{
  "identifiers": ["rvc2_power"],
  "name": "RV Power Systems",
  "model": "DC/AC Power Monitoring"
}
```
Entities: house battery, chassis battery, solar, shore power

**Device 2: Tank Levels**
```json
{
  "identifiers": ["rvc2_tanks"],
  "name": "RV Tank Monitoring",
  "model": "Fresh/Gray/Black Water"
}
```
Entities: fresh water, gray water, black water, propane

**Device 3: HVAC Front**
```json
{
  "identifiers": ["rvc2_hvac_front"],
  "name": "HVAC Front Zone",
  "model": "Thermostat Control"
}
```
Entities: temperature, climate control

**Device 4: HVAC Rear**
```json
{
  "identifiers": ["rvc2_hvac_rear"],
  "name": "HVAC Rear Zone",
  "model": "Thermostat Control"
}
```

**Device 5: Lighting**
```json
{
  "identifiers": ["rvc2_lighting"],
  "name": "RV Lighting",
  "model": "DC Dimmer Control"
}
```
Entities: all light entities

---

## 5. Availability Configuration

### Purpose
Shows entity as "unavailable" when the bridge goes offline. Critical for user awareness.

### Basic Availability
```json
{
  "availability_topic": "rvc2/status",
  "payload_available": "online",
  "payload_not_available": "offline"
}
```

### Implementation
```python
# On MQTT connect, set last will
mqttc.will_set("rvc2/status", "offline", retain=True, qos=1)

# On startup, publish online status
mqttc.publish("rvc2/status", "online", retain=True, qos=1)
```

### Advanced: Multiple Availability Topics
```json
{
  "availability": [
    {
      "topic": "rvc2/status",
      "payload_available": "online",
      "payload_not_available": "offline"
    },
    {
      "topic": "rvc2/canbus/status",
      "payload_available": "connected",
      "payload_not_available": "disconnected"
    }
  ],
  "availability_mode": "all"
}
```

**Modes:**
- `all`: Entity available only when ALL topics report available
- `any`: Entity available when ANY topic reports available
- `latest`: Last received payload determines status

---

## 6. State Topics vs Discovery Topics

### Discovery Topics (Config)
- **Purpose**: Define entity configuration
- **Pattern**: `homeassistant/<component>/<object_id>/config`
- **Payload**: JSON configuration object
- **Frequency**: Published once at startup (or when config changes)
- **Retained**: Usually YES (persists across restarts)

### State Topics (Data)
- **Purpose**: Publish ongoing state updates
- **Pattern**: Custom (defined in discovery config)
- **Payload**: Simple value or JSON object
- **Frequency**: Whenever state changes
- **Retained**: Optional (depends on use case)

### Example Flow

**Step 1: Publish Discovery** (once at startup)
```
Topic: homeassistant/sensor/rvc2_tank_fresh/config
Payload: {
  "name": "Fresh Water Tank",
  "state_topic": "rvc2/sensor/tank_fresh/state",
  "unit_of_measurement": "%"
}
Retained: true
```

**Step 2: Publish State Updates** (ongoing)
```
Topic: rvc2/sensor/tank_fresh/state
Payload: 75
Retained: true (so HA gets latest value on restart)
```

**Step 3: State Changes**
```
Topic: rvc2/sensor/tank_fresh/state
Payload: 73
```
(HA automatically updates the sensor)

---

## 7. Sensor Configuration Details

### Device Classes for RV-C Sensors

| RV-C Data | HA Device Class | Unit | Icon |
|-----------|----------------|------|------|
| Tank levels | `volume` or none | `%` | `mdi:water` |
| Battery voltage | `voltage` | `V` | `mdi:battery` |
| Battery current | `current` | `A` | `mdi:current-dc` |
| Temperature | `temperature` | `°F` or `°C` | `mdi:thermometer` |
| Frequency | `frequency` | `Hz` | `mdi:sine-wave` |
| Generator status | none | none | `mdi:engine` |
| Pump status | none (binary) | none | `mdi:pump` |

### State Classes

| State Class | Use Case | Example |
|-------------|----------|---------|
| `measurement` | Instant readings | Temperature, voltage, tank level |
| `total` | Cumulative values | Energy consumption |
| `total_increasing` | Ever-increasing | Water usage meter |

### Sensor Example with JSON State
```json
{
  "name": "House Battery",
  "state_topic": "rvc2/sensor/battery_house/state",
  "unit_of_measurement": "V",
  "device_class": "voltage",
  "state_class": "measurement",
  "value_template": "{{ value_json.voltage }}",
  "json_attributes_topic": "rvc2/sensor/battery_house/state",
  "json_attributes_template": "{{ {'current': value_json.current, 'soc': value_json.soc} | tojson }}",
  "unique_id": "rvc2_battery_house"
}
```

State payload:
```json
{
  "voltage": 12.8,
  "current": 5.2,
  "soc": 85
}
```

HA shows:
- **State**: 12.8 V
- **Attributes**: current=5.2, soc=85

---

## 8. Climate Entity Configuration

### Required for Climate
- At minimum: `mode_command_topic`
- Practical: temperature, mode, and fan topics

### Complete RV HVAC Example
```json
{
  "name": "Front HVAC",
  "unique_id": "rvc2_hvac_front",
  "modes": ["off", "cool", "heat", "auto"],
  "fan_modes": ["auto", "low", "high"],
  "mode_state_topic": "rvc2/climate/hvac_front/mode",
  "mode_command_topic": "rvc2/climate/hvac_front/mode/set",
  "temperature_state_topic": "rvc2/climate/hvac_front/temperature",
  "temperature_command_topic": "rvc2/climate/hvac_front/temperature/set",
  "current_temperature_topic": "rvc2/climate/hvac_front/current_temp",
  "fan_mode_state_topic": "rvc2/climate/hvac_front/fan",
  "fan_mode_command_topic": "rvc2/climate/hvac_front/fan/set",
  "temp_step": 1,
  "min_temp": 60,
  "max_temp": 85,
  "temperature_unit": "F",
  "precision": 1.0,
  "device": {
    "identifiers": ["rvc2_hvac_front"],
    "name": "HVAC Front Zone"
  }
}
```

### Command Topics (for Phase 2)
When HA user changes setting:
```
Topic: rvc2/climate/hvac_front/temperature/set
Payload: 72
```

Bridge receives this, converts to RV-C CAN command, sends to bus.

---

## 9. Light Entity Configuration

### Basic Light (On/Off Only)
```json
{
  "name": "Ceiling Light",
  "unique_id": "rvc2_light_ceiling",
  "state_topic": "rvc2/light/ceiling/state",
  "command_topic": "rvc2/light/ceiling/set",
  "payload_on": "ON",
  "payload_off": "OFF",
  "device": {
    "identifiers": ["rvc2_lighting"],
    "name": "RV Lighting"
  }
}
```

### Dimmable Light
```json
{
  "name": "Dinette Light",
  "unique_id": "rvc2_light_dinette",
  "state_topic": "rvc2/light/dinette/state",
  "command_topic": "rvc2/light/dinette/set",
  "brightness_state_topic": "rvc2/light/dinette/brightness",
  "brightness_command_topic": "rvc2/light/dinette/brightness/set",
  "brightness_scale": 100,
  "payload_on": "ON",
  "payload_off": "OFF"
}
```

---

## 10. Binary Sensor Configuration

### For On/Off Status (Generator, Pumps, etc.)
```json
{
  "name": "Water Pump",
  "unique_id": "rvc2_pump_water",
  "state_topic": "rvc2/binary_sensor/pump_water/state",
  "device_class": "running",
  "payload_on": "ON",
  "payload_off": "OFF",
  "icon": "mdi:pump",
  "device": {
    "identifiers": ["rvc2_systems"],
    "name": "RV Systems"
  }
}
```

### Device Classes for Binary Sensors
- `running`: Pumps, generator, motors
- `opening`: Vents, doors, windows
- `problem`: Fault conditions
- `power`: Power status

---

## 11. Switch Configuration

### For Controllable On/Off Devices
```json
{
  "name": "Water Heater",
  "unique_id": "rvc2_switch_water_heater",
  "state_topic": "rvc2/switch/water_heater/state",
  "command_topic": "rvc2/switch/water_heater/set",
  "payload_on": "ON",
  "payload_off": "OFF",
  "icon": "mdi:water-boiler",
  "device": {
    "identifiers": ["rvc2_systems"],
    "name": "RV Systems"
  }
}
```

---

## 12. Best Practices

### ✅ DO
1. **Use unique_id for every entity** - Enables registry management
2. **Group entities with device info** - Better organization
3. **Publish discovery on startup** - Ensures entities exist
4. **Retain discovery messages** - Survives MQTT broker restarts
5. **Include availability tracking** - Shows online/offline status
6. **Use descriptive names** - Users see these in UI
7. **Set appropriate device classes** - Proper icons and units
8. **Publish state changes only** - Don't spam unchanged values

### ❌ DON'T
1. **Don't republish discovery constantly** - Once at startup is enough
2. **Don't use special characters in object_id** - Only alphanumeric + underscore
3. **Don't forget to set retain on availability** - Must persist
4. **Don't use same unique_id for different entities** - Causes conflicts
5. **Don't publish all data to state topic** - Use attributes for metadata

### Memory Optimization with Base Topic
For devices with many entities, use `~` to reduce payload size:
```json
{
  "~": "rvc2/sensor/tank_fresh",
  "name": "Fresh Water Tank",
  "stat_t": "~/state",
  "avty_t": "~/availability"
}
```
This expands to full topics but saves memory.

---

## 13. Testing MQTT Discovery

### Tools Needed
1. **MQTT Explorer** - Visual MQTT client to inspect topics
2. **Home Assistant Developer Tools** - MQTT tab for testing
3. **mosquitto_pub/sub** - Command-line MQTT tools

### Testing Workflow

**Step 1: Publish Discovery Message**
```bash
mosquitto_pub -h localhost -t "homeassistant/sensor/test_sensor/config" \
  -m '{"name":"Test Sensor","state_topic":"test/state","unique_id":"test123"}' \
  -r
```

**Step 2: Check HA**
Go to Configuration → Devices → MQTT
Entity should appear immediately.

**Step 3: Publish State**
```bash
mosquitto_pub -h localhost -t "test/state" -m "42"
```

**Step 4: Verify Update**
Entity in HA should show value "42"

**Step 5: Test Availability**
```bash
mosquitto_pub -h localhost -t "test/availability" -m "offline" -r
```
Entity should show as "unavailable"

---

## 14. Example Implementation Plan for rvc2mqtt

### Phase 1.1: Basic Sensor Discovery
1. Start with tank sensors (simple, visible results)
2. Publish discovery on startup
3. Map state to discovery-compliant topics
4. Test with HA

### Phase 1.2: Add Battery/Voltage Sensors
1. Add DC_SOURCE_STATUS sensors
2. Include device grouping
3. Add availability tracking

### Phase 1.3: Add Climate Entities
1. Implement THERMOSTAT_STATUS as climate entities
2. Read-only for now (Phase 2 will add commands)
3. Test mode, temperature, fan display

### Phase 1.4: Add Lights
1. Map DC_DIMMER_STATUS to light entities
2. Read-only for now
3. Support brightness if available

### Phase 1.5: Add Switches/Binary Sensors
1. Generator status → binary_sensor
2. Pumps → binary_sensor or switch
3. Other on/off devices

---

## 15. RV-C to HA Entity Mapping (Draft)

### Tanks (Sensors)
```
RV-C: TANK_STATUS instance 0 → HA: sensor.fresh_water_tank
RV-C: TANK_STATUS instance 1 → HA: sensor.black_water_tank
RV-C: TANK_STATUS instance 2 → HA: sensor.gray_water_tank
RV-C: TANK_STATUS instance 3 → HA: sensor.propane_tank
```

### Power (Sensors)
```
RV-C: DC_SOURCE_STATUS instance 1 → HA: sensor.house_battery_voltage
RV-C: DC_SOURCE_STATUS instance 2 → HA: sensor.chassis_battery_voltage
```

### HVAC (Climate)
```
RV-C: THERMOSTAT_STATUS instance 0 → HA: climate.hvac_front
RV-C: THERMOSTAT_STATUS instance 2 → HA: climate.hvac_rear
RV-C: THERMOSTAT_AMBIENT_STATUS instance 0 → HA: sensor.front_temperature
```

### Lights (Light Entities)
```
RV-C: DC_DIMMER_STATUS instance 1 → HA: light.ceiling
RV-C: DC_DIMMER_STATUS instance 2 → HA: light.entry
... (map all instances)
```

---

## 16. Implementation Checklist

- [ ] Create discovery message generator function
- [ ] Design topic schema (discovery prefix, state topics)
- [ ] Implement device grouping strategy
- [ ] Add availability birth/will messages
- [ ] Publish discovery on startup
- [ ] Map RV-C messages to state topics
- [ ] Test with MQTT Explorer
- [ ] Test with Home Assistant
- [ ] Add configuration options (enable/disable discovery)
- [ ] Document for users

---

## Conclusion

MQTT Discovery is straightforward but requires attention to detail:
1. Publish proper discovery JSON to `homeassistant/<component>/<id>/config`
2. Include unique_id and device info
3. Publish state updates to separate state topics
4. Add availability tracking
5. Test thoroughly

The result: entities auto-appear in HA with zero user configuration!

**Next Step:** Design our specific topic schema for rvc2mqtt
