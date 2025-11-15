# MQTT Topic Schema Design - Phase 1

**Date:** 2025-11-15
**Status:** Design Phase
**Branch:** feature/ha-mqtt-discovery

---

## Design Principles

1. **Generic naming** - Use "rv" not model-specific names
2. **Config-driven** - Mappings defined in external config, not code
3. **Multi-manufacturer ready** - Support different RV models via config profiles
4. **Backwards compatible** - Maintain legacy topics during transition
5. **HA-friendly** - Follow HA MQTT Discovery conventions

---

## Topic Prefix Decision

**Selected:** `rv` (lowercase, generic, short)

**Rationale:**
- ✅ Generic across all RV manufacturers
- ✅ Short and memorable
- ✅ Future-proof (not tied to specific model)
- ❌ NOT "openroad" (too specific to Tiffin model)
- ❌ NOT "rvc2" (refers to protocol version, confusing)

**Configurable:** Yes, via `state_topic_prefix` in config

---

## Topic Structure

### Discovery Topics (HA Auto-Config)
```
homeassistant/<component>/<unique_id>/config
```

**Examples:**
```
homeassistant/sensor/rv_tank_fresh_0/config
homeassistant/sensor/rv_battery_house/config
homeassistant/climate/rv_hvac_front/config
homeassistant/light/rv_light_ceiling/config
homeassistant/switch/rv_pump_water/config
```

### State Topics (Data Publishing)
```
<prefix>/<component>/<entity_name>/state
```

**Examples:**
```
rv/sensor/tank_fresh_0/state → "75"
rv/sensor/battery_house/state → "12.8"
rv/climate/hvac_front/state → JSON
rv/light/ceiling/state → "ON"
```

### Availability Topic (Global for All Entities)
```
<prefix>/status → "online" or "offline"
```

**Example:**
```
rv/status → "online"
```

### Legacy Topics (Backwards Compatibility)
```
RVC2/<RVC_MESSAGE_NAME>/<instance> → JSON (existing format)
```

**Configurable:** Can be disabled via `legacy_topics = 0`

---

## Configuration-Driven Mapping System

### Problem Statement
Current code has hardcoded Tiffin-specific mappings in `process_Tiffin()`:
```python
mqttOutputTopic + "/DC_DIMMER_STATUS_3/1": "OpenRoad/light/ceiling/state"
```

**Issues:**
- Hardcoded for one RV model
- Not maintainable for multiple manufacturers
- Difficult for users to customize

### Solution: Mapping Configuration File

Create external YAML mapping files that define:
1. RV-C message → HA entity translation
2. Device groupings
3. Entity customization (names, icons, device classes)

---

## Mapping Configuration Format

### File: `mappings/tiffin_default.yaml`

```yaml
# RV Model Mapping Configuration
# This file maps RV-C CAN bus messages to Home Assistant entities

metadata:
  name: "Tiffin Motorhome Default Mapping"
  manufacturer: "Tiffin"
  model: "Generic"
  version: "1.0"
  description: "Default mapping for Tiffin motorhomes with standard RV-C"

# Device groupings - multiple entities can belong to same device
devices:
  power:
    name: "RV Power Systems"
    model: "DC/AC Power Monitoring"
    manufacturer: "RV-C"

  tanks:
    name: "RV Tank Monitoring"
    model: "Waste & Fresh Water"
    manufacturer: "RV-C"

  hvac_front:
    name: "HVAC Front Zone"
    model: "Climate Control"
    manufacturer: "RV-C"

  hvac_rear:
    name: "HVAC Rear Zone"
    model: "Climate Control"
    manufacturer: "RV-C"

  lighting:
    name: "RV Lighting"
    model: "DC Dimmer Control"
    manufacturer: "RV-C"

  systems:
    name: "RV Systems"
    model: "Generator, Pumps, etc."
    manufacturer: "RV-C"

# Entity mappings - maps RV-C messages to HA entities
entities:
  # Tank Sensors
  - rvc_message: "TANK_STATUS"
    instance: 0
    entity_type: "sensor"
    entity_id: "tank_fresh_0"
    name: "Fresh Water Tank"
    device: "tanks"
    device_class: "volume"
    unit_of_measurement: "%"
    icon: "mdi:water"
    state_class: "measurement"
    value_field: "relative_level"  # Which field from decoded RVC message
    calculation: "lambda x: int(round(x['relative_level'] / x['resolution'] * 100))"

  - rvc_message: "TANK_STATUS"
    instance: 1
    entity_type: "sensor"
    entity_id: "tank_black_1"
    name: "Black Water Tank"
    device: "tanks"
    device_class: "volume"
    unit_of_measurement: "%"
    icon: "mdi:water"
    state_class: "measurement"
    value_field: "relative_level"
    calculation: "lambda x: int(round(x['relative_level'] / x['resolution'] * 100))"

  - rvc_message: "TANK_STATUS"
    instance: 2
    entity_type: "sensor"
    entity_id: "tank_gray_2"
    name: "Gray Water Tank"
    device: "tanks"
    device_class: "volume"
    unit_of_measurement: "%"
    icon: "mdi:water"
    state_class: "measurement"
    value_field: "relative_level"
    calculation: "lambda x: int(round(x['relative_level'] / x['resolution'] * 100))"

  - rvc_message: "TANK_STATUS"
    instance: 3
    entity_type: "sensor"
    entity_id: "tank_propane_3"
    name: "Propane Tank"
    device: "tanks"
    device_class: "gas"
    unit_of_measurement: "%"
    icon: "mdi:propane-tank"
    state_class: "measurement"
    value_field: "relative_level"
    calculation: "lambda x: int(round(x['relative_level'] / x['resolution'] * 100))"

  # Battery Voltage Sensors
  - rvc_message: "DC_SOURCE_STATUS_1"
    instance: 1
    entity_type: "sensor"
    entity_id: "battery_house"
    name: "House Battery Voltage"
    device: "power"
    device_class: "voltage"
    unit_of_measurement: "V"
    icon: "mdi:battery"
    state_class: "measurement"
    value_field: "dc voltage"

  - rvc_message: "DC_SOURCE_STATUS_1"
    instance: 2
    entity_type: "sensor"
    entity_id: "battery_chassis"
    name: "Chassis Battery Voltage"
    device: "power"
    device_class: "voltage"
    unit_of_measurement: "V"
    icon: "mdi:car-battery"
    state_class: "measurement"
    value_field: "dc voltage"

  # Temperature Sensors
  - rvc_message: "THERMOSTAT_AMBIENT_STATUS"
    instance: 0
    entity_type: "sensor"
    entity_id: "temperature_front"
    name: "Front Zone Temperature"
    device: "hvac_front"
    device_class: "temperature"
    unit_of_measurement: "°F"
    icon: "mdi:thermometer"
    state_class: "measurement"
    value_field: "ambient temp F"

  - rvc_message: "THERMOSTAT_AMBIENT_STATUS"
    instance: 2
    entity_type: "sensor"
    entity_id: "temperature_rear"
    name: "Rear Zone Temperature"
    device: "hvac_rear"
    device_class: "temperature"
    unit_of_measurement: "°F"
    icon: "mdi:thermometer"
    state_class: "measurement"
    value_field: "ambient temp F"

  # Climate Entities (HVAC)
  - rvc_message: "THERMOSTAT_STATUS_1"
    instance: 0
    entity_type: "climate"
    entity_id: "hvac_front"
    name: "Front HVAC"
    device: "hvac_front"
    modes: ["off", "cool", "heat", "auto"]
    fan_modes: ["auto", "low", "high"]
    temp_step: 1
    min_temp: 60
    max_temp: 85
    temperature_unit: "F"
    precision: 1.0
    # Phase 2 will add command topics

  - rvc_message: "THERMOSTAT_STATUS_1"
    instance: 2
    entity_type: "climate"
    entity_id: "hvac_rear"
    name: "Rear HVAC"
    device: "hvac_rear"
    modes: ["off", "cool", "heat", "auto"]
    fan_modes: ["auto", "low", "high"]
    temp_step: 1
    min_temp: 60
    max_temp: 85
    temperature_unit: "F"
    precision: 1.0

  # Lights
  - rvc_message: "DC_DIMMER_STATUS_3"
    instance: 1
    entity_type: "light"
    entity_id: "light_ceiling"
    name: "Ceiling Light"
    device: "lighting"
    icon: "mdi:ceiling-light"
    supports_brightness: true
    value_field: "load status"

  - rvc_message: "DC_DIMMER_STATUS_3"
    instance: 2
    entity_type: "light"
    entity_id: "light_entry"
    name: "Entry Light"
    device: "lighting"
    icon: "mdi:lightbulb"
    supports_brightness: true
    value_field: "load status"

  - rvc_message: "DC_DIMMER_STATUS_3"
    instance: 5
    entity_type: "light"
    entity_id: "light_bedroom"
    name: "Bedroom Light"
    device: "lighting"
    icon: "mdi:bed"
    supports_brightness: true
    value_field: "load status"

  - rvc_message: "DC_DIMMER_STATUS_3"
    instance: 8
    entity_type: "light"
    entity_id: "light_floor"
    name: "Floor Light"
    device: "lighting"
    icon: "mdi:floor-lamp"
    supports_brightness: true
    value_field: "load status"

  - rvc_message: "DC_DIMMER_STATUS_3"
    instance: 12
    entity_type: "light"
    entity_id: "light_awning"
    name: "Awning Light"
    device: "lighting"
    icon: "mdi:coach-lamp"
    supports_brightness: true
    value_field: "load status"

  # Switches
  - rvc_message: "DC_DIMMER_STATUS_3"
    instance: 93
    entity_type: "switch"
    entity_id: "pump_water"
    name: "Water Pump"
    device: "systems"
    icon: "mdi:pump"
    device_class: "switch"
    value_field: "load status"

  - rvc_message: "DC_DIMMER_STATUS_3"
    instance: 95
    entity_type: "switch"
    entity_id: "heater_electric"
    name: "Electric Water Heater"
    device: "systems"
    icon: "mdi:water-boiler"
    device_class: "switch"
    value_field: "load status"

  - rvc_message: "DC_DIMMER_STATUS_3"
    instance: 96
    entity_type: "switch"
    entity_id: "heater_gas"
    name: "Gas Water Heater"
    device: "systems"
    icon: "mdi:fire"
    device_class: "switch"
    value_field: "load status"

  # Binary Sensors
  - rvc_message: "GENERATOR_STATUS_1"
    instance: null  # No instance
    entity_type: "binary_sensor"
    entity_id: "generator_running"
    name: "Generator"
    device: "systems"
    device_class: "running"
    icon: "mdi:engine"
    value_field: "status definition"
    on_value: "RUNNING"  # What value means "on"
    off_value: "STOPPED"

# Special handling rules (replaces hardcoded process_Tiffin logic)
special_rules:
  # Vent lid position handling
  - rvc_message: "DC_DIMMER_STATUS_3"
    instances: [21, 22]  # Galley vent open/close
    rule_type: "combined_binary_sensor"
    entity_type: "binary_sensor"
    entity_id: "vent_galley_lid"
    name: "Galley Vent Lid"
    device: "systems"
    device_class: "opening"
    logic: "instance_21_on=OPEN, instance_22_on=CLOSED"

  - rvc_message: "DC_DIMMER_STATUS_3"
    instances: [17, 18]  # Bath vent open/close
    rule_type: "combined_binary_sensor"
    entity_type: "binary_sensor"
    entity_id: "vent_bath_lid"
    name: "Bath Vent Lid"
    device: "systems"
    device_class: "opening"
    logic: "instance_17_on=OPEN, instance_18_on=CLOSED"
```

---

## Configuration File Location

### Directory Structure
```
rvc2mqtt/
├── mappings/
│   ├── tiffin_default.yaml       # Your current RV
│   ├── newmar_default.yaml       # Future: Newmar RVs
│   ├── winnebago_default.yaml    # Future: Winnebago RVs
│   └── custom_example.yaml       # User customization template
├── rvc2mqtt.py
└── rvc2mqtt.ini
```

### Configuration Selection (rvc2mqtt.ini)
```ini
[General]
mapping_file = mappings/tiffin_default.yaml  ; Which mapping to use
```

---

## Topic Examples with New Schema

### Example 1: Fresh Water Tank

**Discovery Topic:**
```
homeassistant/sensor/rv_tank_fresh_0/config
```

**Discovery Payload:**
```json
{
  "name": "Fresh Water Tank",
  "unique_id": "rv_tank_fresh_0",
  "state_topic": "rv/sensor/tank_fresh_0/state",
  "unit_of_measurement": "%",
  "device_class": "volume",
  "state_class": "measurement",
  "icon": "mdi:water",
  "availability_topic": "rv/status",
  "device": {
    "identifiers": ["rv_tanks"],
    "name": "RV Tank Monitoring",
    "model": "Waste & Fresh Water",
    "manufacturer": "RV-C"
  }
}
```

**State Topic:**
```
rv/sensor/tank_fresh_0/state → "75"
```

**Legacy Topic (optional, for backwards compatibility):**
```
RVC2/TANK_STATUS/0 → {"relative_level": 3, "resolution": 4, ...}
```

---

### Example 2: House Battery

**Discovery Topic:**
```
homeassistant/sensor/rv_battery_house/config
```

**Discovery Payload:**
```json
{
  "name": "House Battery Voltage",
  "unique_id": "rv_battery_house",
  "state_topic": "rv/sensor/battery_house/state",
  "unit_of_measurement": "V",
  "device_class": "voltage",
  "state_class": "measurement",
  "icon": "mdi:battery",
  "availability_topic": "rv/status",
  "device": {
    "identifiers": ["rv_power"],
    "name": "RV Power Systems",
    "model": "DC/AC Power Monitoring",
    "manufacturer": "RV-C"
  }
}
```

**State Topic:**
```
rv/sensor/battery_house/state → "12.8"
```

---

### Example 3: Front HVAC (Climate)

**Discovery Topic:**
```
homeassistant/climate/rv_hvac_front/config
```

**Discovery Payload:**
```json
{
  "name": "Front HVAC",
  "unique_id": "rv_hvac_front",
  "modes": ["off", "cool", "heat", "auto"],
  "fan_modes": ["auto", "low", "high"],
  "mode_state_topic": "rv/climate/hvac_front/mode",
  "temperature_state_topic": "rv/climate/hvac_front/setpoint",
  "current_temperature_topic": "rv/climate/hvac_front/temperature",
  "fan_mode_state_topic": "rv/climate/hvac_front/fan",
  "temp_step": 1,
  "min_temp": 60,
  "max_temp": 85,
  "temperature_unit": "F",
  "precision": 1.0,
  "availability_topic": "rv/status",
  "device": {
    "identifiers": ["rv_hvac_front"],
    "name": "HVAC Front Zone",
    "model": "Climate Control",
    "manufacturer": "RV-C"
  }
}
```

**State Topics:**
```
rv/climate/hvac_front/mode → "cool"
rv/climate/hvac_front/setpoint → "72"
rv/climate/hvac_front/temperature → "74"
rv/climate/hvac_front/fan → "auto"
```

---

### Example 4: Ceiling Light

**Discovery Topic:**
```
homeassistant/light/rv_light_ceiling/config
```

**Discovery Payload:**
```json
{
  "name": "Ceiling Light",
  "unique_id": "rv_light_ceiling",
  "state_topic": "rv/light/ceiling/state",
  "brightness_state_topic": "rv/light/ceiling/brightness",
  "brightness_scale": 100,
  "availability_topic": "rv/status",
  "icon": "mdi:ceiling-light",
  "device": {
    "identifiers": ["rv_lighting"],
    "name": "RV Lighting",
    "model": "DC Dimmer Control",
    "manufacturer": "RV-C"
  }
}
```

**State Topics:**
```
rv/light/ceiling/state → "ON"
rv/light/ceiling/brightness → "75"
```

---

## Complete Topic Inventory

### Discovery Topics (Published once at startup)
```
homeassistant/sensor/rv_tank_fresh_0/config
homeassistant/sensor/rv_tank_black_1/config
homeassistant/sensor/rv_tank_gray_2/config
homeassistant/sensor/rv_tank_propane_3/config
homeassistant/sensor/rv_battery_house/config
homeassistant/sensor/rv_battery_chassis/config
homeassistant/sensor/rv_temperature_front/config
homeassistant/sensor/rv_temperature_rear/config
homeassistant/climate/rv_hvac_front/config
homeassistant/climate/rv_hvac_rear/config
homeassistant/light/rv_light_ceiling/config
homeassistant/light/rv_light_entry/config
homeassistant/light/rv_light_bedroom/config
... (all mapped entities)
```

### State Topics (Published on change)
```
rv/status → "online" | "offline"
rv/sensor/tank_fresh_0/state → "75"
rv/sensor/tank_black_1/state → "23"
rv/sensor/battery_house/state → "12.8"
rv/climate/hvac_front/mode → "cool"
rv/climate/hvac_front/temperature → "74"
rv/light/ceiling/state → "ON"
rv/light/ceiling/brightness → "75"
... (all entity states)
```

### Legacy Topics (Optional, for backwards compatibility)
```
RVC2/TANK_STATUS/0 → JSON
RVC2/DC_SOURCE_STATUS_1/1 → JSON
RVC2/THERMOSTAT_STATUS_1/0 → JSON
... (all existing topics)
```

---

## Implementation Notes

### Loading Mapping Configuration
```python
import yaml

def load_mapping_config(mapping_file):
    """Load entity mapping configuration from YAML file"""
    with open(mapping_file, 'r') as f:
        return yaml.safe_load(f)

# At startup
mapping = load_mapping_config(config.get('General', 'mapping_file'))
devices = mapping['devices']
entities = mapping['entities']
```

### Processing RV-C Messages
```python
def process_rvc_message(dgn, instance, decoded_data, mapping):
    """
    Process RV-C message and return entities to update

    Returns list of (entity_config, state_value) tuples
    """
    matching_entities = []

    for entity in mapping['entities']:
        if entity['rvc_message'] == dgn:
            if entity.get('instance') is None or entity['instance'] == instance:
                # Extract value based on value_field
                value = decoded_data.get(entity['value_field'])

                # Apply calculation if specified
                if 'calculation' in entity:
                    value = eval(entity['calculation'])(decoded_data)

                matching_entities.append((entity, value))

    return matching_entities
```

### Publishing to HA
```python
def publish_entity_state(mqttc, entity, value, topic_prefix):
    """Publish entity state to HA-compatible topic"""

    entity_type = entity['entity_type']
    entity_id = entity['entity_id']

    # Build state topic
    state_topic = f"{topic_prefix}/{entity_type}/{entity_id}/state"

    # Publish state
    mqttc.publish(state_topic, str(value), retain=True)
```

---

## Migration Strategy

### For Existing Users

**Phase 1: Dual Publishing**
- Publish to BOTH new discovery topics AND legacy topics
- Users see entities auto-appear in HA
- Old integrations continue working

**Phase 2: Migration Period**
- Encourage users to remove manual MQTT config
- Provide migration guide
- Keep legacy topics for 6-12 months

**Phase 3: Legacy Deprecation**
- Add config option: `legacy_topics = 0`
- Default to disabled in future version
- Eventually remove legacy code

---

## Multi-Manufacturer Support (Future)

### Creating New Mapping Files

**For Newmar RVs:**
```bash
cp mappings/tiffin_default.yaml mappings/newmar_default.yaml
# Edit to match Newmar's specific RV-C implementation
```

**For User Customization:**
```bash
cp mappings/tiffin_default.yaml mappings/my_custom_rv.yaml
# User edits to match their specific setup
```

**Select in config:**
```ini
[General]
mapping_file = mappings/my_custom_rv.yaml
```

---

## Summary

**Topic Prefix:** `rv` (configurable)
**Discovery Format:** Standard HA MQTT Discovery
**State Format:** Simple values for sensors, JSON for complex entities
**Configuration:** YAML mapping files (manufacturer-specific)
**Backwards Compatibility:** Legacy RVC2/* topics (optional)
**Device Grouping:** 5 logical devices (power, tanks, hvac_front, hvac_rear, lighting, systems)

**Next Steps:**
1. Create mapping YAML file for Tiffin
2. Implement YAML loader
3. Implement discovery message generator
4. Test with HA

---

**Decision Log:**
- ✅ Topic prefix: `rv` (not openroad, not rvc2)
- ✅ Config format: YAML (more flexible than INI for complex mappings)
- ✅ Mapping files in `mappings/` directory
- ✅ Support legacy topics during transition
- ✅ Device grouping: 6 logical devices
