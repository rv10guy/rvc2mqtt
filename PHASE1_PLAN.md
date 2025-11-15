# Phase 1: Home Assistant MQTT Discovery - Detailed Plan

**Branch:** `feature/ha-mqtt-discovery`
**Goal:** Enable zero-configuration sensor creation in Home Assistant
**Timeline:** 2-3 weeks development + 1 week testing
**Status:** Planning

---

## Overview

Currently, users must manually configure MQTT sensors in Home Assistant's `configuration.yaml`. With MQTT Discovery, devices will auto-populate in HA with proper icons, units, and device grouping.

### Before Phase 1
```yaml
# User has to manually add in configuration.yaml:
mqtt:
  sensor:
    - name: "Fresh Water Tank"
      state_topic: "RVC2/TANK_STATUS/0"
      unit_of_measurement: "%"
      value_template: "{{ value_json.relative_level }}"
```

### After Phase 1
```
# Sensors auto-appear in HA - ZERO configuration needed!
# Just start rvc2mqtt.py and entities appear
```

---

## Detailed Task Breakdown

### Task 1: Research HA MQTT Discovery Protocol ✓ (Will do first)

**Objectives:**
- Understand HA MQTT Discovery message format
- Learn about device vs entity relationships
- Study device class mappings
- Review best practices from other integrations

**Key Documentation:**
- https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
- https://www.home-assistant.io/integrations/sensor.mqtt/
- https://www.home-assistant.io/integrations/binary_sensor.mqtt/
- https://www.home-assistant.io/integrations/climate.mqtt/
- https://www.home-assistant.io/integrations/light.mqtt/

**Research Questions:**
- What device classes exist for sensors?
- How to properly structure device info?
- How to handle availability?
- How to manage entity updates vs discovery?
- What's the recommended topic structure?

**Deliverable:** Research summary document with examples

---

### Task 2: Design MQTT Topic Schema

**Current Structure:**
```
RVC2/TANK_STATUS/0 → {"relative_level": 75, "resolution": 4, ...}
RVC2/DC_SOURCE_STATUS_1/1 → {"dc voltage": 12.8, ...}
RVC2/THERMOSTAT_AMBIENT_STATUS/0 → {"ambient temp F": 72.5, ...}
```

**Proposed Discovery Structure:**
```
Discovery Topics (config messages):
homeassistant/sensor/rvc2_tank_fresh/config
homeassistant/sensor/rvc2_battery_house/config
homeassistant/climate/rvc2_hvac_front/config
homeassistant/light/rvc2_light_ceiling/config
homeassistant/switch/rvc2_pump_water/config
homeassistant/binary_sensor/rvc2_generator_status/config

State Topics (data messages):
rvc2/sensor/tank_fresh/state → "75"
rvc2/sensor/battery_house/state → "12.8"
rvc2/climate/hvac_front/state → JSON with temp, mode, etc.
rvc2/light/ceiling/state → "ON"

Availability Topic (for all entities):
rvc2/status → "online" or "offline"
```

**Design Decisions:**
- [ ] Decide on topic prefix (rvc2 vs openroad vs custom)
- [ ] Determine unique_id format (instance-based)
- [ ] Choose state format (simple value vs JSON)
- [ ] Plan for multi-RV scenarios (unique device IDs)

**Deliverable:** Topic schema documentation

---

### Task 3: Map RV-C Message Types to HA Device Classes

**Sensor Device Classes to Map:**
| RV-C Message | HA Device Class | Unit | Icon |
|--------------|-----------------|------|------|
| TANK_STATUS | volume | % | mdi:water |
| DC_SOURCE_STATUS | voltage | V | mdi:battery |
| THERMOSTAT_AMBIENT_STATUS | temperature | °F | mdi:thermometer |
| AC_SOURCE_STATUS | voltage | V | mdi:power-plug |
| GENERATOR_STATUS | - | - | mdi:engine |

**Entity Types to Support:**

**1. Sensors (read-only values):**
- Tank levels → sensor (volume)
- Battery voltage → sensor (voltage)
- Temperature → sensor (temperature)
- Current → sensor (current)
- Frequency → sensor (frequency)

**2. Binary Sensors (on/off states):**
- Generator running → binary_sensor (running)
- Pump status → binary_sensor (running)
- Door/window sensors → binary_sensor (opening)

**3. Lights:**
- DC_DIMMER_STATUS → light (with brightness if supported)

**4. Switches:**
- Water pump → switch
- Water heater → switch
- Generic loads → switch

**5. Climate:**
- THERMOSTAT_STATUS → climate (HVAC control)
- Setpoint, mode, fan control

**Deliverable:** Complete mapping table with device classes

---

### Task 4: Implement Discovery Message Generator

**Requirements:**
- Function to generate discovery payloads for each entity type
- Include device information for grouping
- Support for attributes (additional data)
- Proper unique_id generation
- Icon selection logic

**Code Structure:**
```python
def generate_discovery_config(entity_type, entity_name, config):
    """
    Generate HA MQTT Discovery config message

    Args:
        entity_type: 'sensor', 'binary_sensor', 'light', 'switch', 'climate'
        entity_name: Unique name for entity
        config: Dict with state_topic, unit, device_class, etc.

    Returns:
        tuple: (discovery_topic, discovery_payload)
    """
    pass

def publish_discovery_messages(mqttc):
    """
    Publish all discovery messages on startup
    """
    pass
```

**Discovery Message Example:**
```python
{
    "name": "Fresh Water Tank",
    "unique_id": "rvc2_tank_fresh_0",
    "state_topic": "rvc2/sensor/tank_fresh/state",
    "unit_of_measurement": "%",
    "device_class": "volume",
    "icon": "mdi:water",
    "availability_topic": "rvc2/status",
    "device": {
        "identifiers": ["rvc2_tiffin_001"],
        "name": "RV Systems",
        "model": "Tiffin Motorhome",
        "manufacturer": "RVC-MQTT Bridge",
        "sw_version": "2.0.0"
    }
}
```

**Deliverable:** Working discovery message generator

---

### Task 5: Implement Proper State Topic Publishing

**Current Behavior:**
```python
# Publishes to: RVC2/TANK_STATUS/0
mqtt_safe_publish(mqttc, topic, json.dumps(myresult), retain)
```

**New Behavior:**
```python
# Publishes to BOTH:
# 1. Discovery-compliant state topic: rvc2/sensor/tank_fresh/state
# 2. Legacy topic (for backwards compatibility): RVC2/TANK_STATUS/0

# State should be simple value OR JSON depending on entity type
# Sensors: Simple value "75"
# Climate: JSON {"temperature": 72, "mode": "cool", "fan_mode": "auto"}
```

**Implementation Tasks:**
- [ ] Refactor `process_Tiffin()` to return discovery-compliant topics
- [ ] Create state message formatter for each entity type
- [ ] Maintain backwards compatibility with legacy topics
- [ ] Handle state changes (only publish when changed)
- [ ] Add configuration option to disable legacy topics

**Deliverable:** State publishing that works with HA discovery

---

### Task 6: Add Device Grouping and Metadata

**Device Structure:**
All entities should be grouped under logical devices in HA:

**Device 1: Power Systems**
- House Battery Voltage
- House Battery Current
- Chassis Battery Voltage
- Solar Power

**Device 2: Tank Levels**
- Fresh Water Tank
- Gray Water Tank
- Black Water Tank
- Propane Tank

**Device 3: HVAC Front Zone**
- Temperature
- Setpoint
- Mode
- Fan Mode

**Device 4: HVAC Rear Zone**
- Temperature
- Setpoint
- Mode
- Fan Mode

**Device 5: Lighting**
- Individual light entities

**Implementation:**
```python
DEVICE_DEFINITIONS = {
    "power": {
        "identifiers": ["rvc2_power_001"],
        "name": "RV Power Systems",
        "model": "DC/AC Power",
        "manufacturer": "RVC-MQTT Bridge"
    },
    "tanks": {
        "identifiers": ["rvc2_tanks_001"],
        "name": "RV Tank Levels",
        "model": "Tank Monitoring",
        "manufacturer": "RVC-MQTT Bridge"
    },
    # ... more devices
}
```

**Deliverable:** Logical device grouping in HA

---

### Task 7: Implement Availability Tracking

**Birth/Will Messages:**
```python
# On startup, publish:
rvc2/status → "online" (retained)

# Configure MQTT will message (auto-published on disconnect):
mqttc.will_set("rvc2/status", "offline", retain=True)
```

**All entities reference availability:**
```json
{
    "availability_topic": "rvc2/status",
    "payload_available": "online",
    "payload_not_available": "offline"
}
```

**Benefits:**
- HA shows entities as "unavailable" when bridge is offline
- Users can see system status at a glance
- Automations can react to bridge going offline

**Deliverable:** Working availability tracking

---

### Task 8: Add Configuration Options

**New Config File Section:**
```ini
[HomeAssistant]
discovery_enabled = 1           ; Enable HA MQTT Discovery (0=disabled, 1=enabled)
discovery_prefix = homeassistant ; HA discovery prefix
device_name = RV Systems        ; Device name in HA
device_model = Tiffin Motorhome ; Device model
device_id = rvc2_001            ; Unique device identifier (for multi-RV)
legacy_topics = 1               ; Keep publishing old RVC2/* topics (0=no, 1=yes)
state_topic_prefix = rvc2       ; Prefix for state topics
```

**Customization Support:**
```ini
[EntityCustomization]
; Override default entity names and settings
tank_fresh_name = Fresh Water Tank
tank_fresh_icon = mdi:water-pump
battery_house_name = House Battery Bank
```

**Deliverable:** Flexible configuration system

---

### Task 9: Testing with Home Assistant

**Test Environment Setup:**
- [ ] Install Home Assistant (or use existing instance)
- [ ] Configure MQTT integration
- [ ] Point to same MQTT broker as rvc2mqtt

**Test Cases:**

**Test 1: Fresh Install**
1. Start rvc2mqtt with discovery enabled
2. Check HA → Configuration → Devices
3. Verify "RV Systems" device(s) appear
4. Verify all entities are created
5. Check entity states update in real-time

**Test 2: Entity Updates**
1. Trigger CAN bus changes
2. Verify HA entities update within 1 second
3. Check history graphs populate correctly

**Test 3: Restart Scenarios**
1. Restart rvc2mqtt → entities should remain
2. Restart HA → entities should remain
3. Restart MQTT broker → entities should recover

**Test 4: Availability**
1. Stop rvc2mqtt
2. Verify entities show as "unavailable" in HA
3. Start rvc2mqtt
4. Verify entities show as "available"

**Test 5: Device Organization**
1. Check device page shows grouped entities
2. Verify icons and units are correct
3. Check entity registry has proper unique IDs

**Test 6: Backwards Compatibility**
1. Verify old RVC2/* topics still work
2. Check existing automations aren't broken

**Deliverable:** Passing test suite

---

### Task 10: Create Example HA Dashboard

**Dashboard Configuration:**
Create example Lovelace YAML for common use cases:

**Dashboard 1: RV Overview**
- Tank levels (visual gauges)
- Battery status
- Temperature sensors
- Quick controls (lights, pumps)

**Dashboard 2: Climate Control**
- Front HVAC card
- Rear HVAC card
- Temperature history graphs

**Dashboard 3: Lighting**
- All light controls
- Scenes (movie mode, bedtime, etc.)

**Dashboard 4: Diagnostics**
- Voltage graphs
- Current draw
- System availability status

**Deliverable:** Example dashboard YAML files

---

### Task 11: Update Documentation

**Documentation Updates Needed:**

**README.md:**
- [ ] Add "Home Assistant Integration" section
- [ ] Include quick start guide for HA users
- [ ] Add screenshots of HA device page
- [ ] Document configuration options

**New File: HOMEASSISTANT.md:**
- [ ] Detailed HA setup instructions
- [ ] Discovery protocol explanation
- [ ] Topic structure documentation
- [ ] Troubleshooting guide
- [ ] Example automations
- [ ] Dashboard examples

**Update: rvc2mqtt.ini.example:**
- [ ] Add [HomeAssistant] section
- [ ] Add [EntityCustomization] section

**Deliverable:** Complete documentation

---

### Task 12: Phase 1 Completion

**Final Checklist:**
- [ ] All discovery messages publish correctly
- [ ] Entities auto-create in HA
- [ ] State updates work in real-time
- [ ] Availability tracking functional
- [ ] Device grouping logical
- [ ] Configuration options work
- [ ] Backwards compatibility maintained
- [ ] Tests pass
- [ ] Documentation complete
- [ ] Example dashboards created

**Deliverable:** Merge-ready code with documentation

---

## Success Criteria

### Must Have (Blocking)
✓ Sensors auto-create in HA without manual config
✓ State updates work in real-time
✓ Entities show correct icons and units
✓ Availability tracking works
✓ Backwards compatible with existing deployments

### Should Have (Important)
✓ Device grouping is logical
✓ Configuration is flexible
✓ Documentation is complete
✓ Examples are provided

### Nice to Have (Future)
- Entity customization UI
- Discovery message debugging tool
- HA addon for easy installation
- Auto-detection of device model

---

## Testing Matrix

| Feature | Test Method | Status |
|---------|-------------|--------|
| Discovery messages publish | MQTT inspector | ⏳ |
| Entities appear in HA | Manual HA check | ⏳ |
| State updates | Live monitoring | ⏳ |
| Availability | Disconnect test | ⏳ |
| Device grouping | HA device page | ⏳ |
| Icon/unit correctness | Visual inspection | ⏳ |
| Backwards compatibility | Legacy topic check | ⏳ |
| Configuration options | Config file test | ⏳ |
| Multi-restart stability | Restart all components | ⏳ |
| Performance | 100+ message stress test | ⏳ |

---

## Code Organization

### New Files to Create:
```
rvc2mqtt/
├── ha_discovery.py          # Discovery message generation
├── device_mappings.py       # RV-C to HA mappings
├── examples/
│   ├── ha_dashboard_overview.yaml
│   ├── ha_dashboard_climate.yaml
│   └── ha_automations.yaml
├── docs/
│   └── HOMEASSISTANT.md     # HA-specific docs
└── tests/
    └── test_ha_discovery.py # Unit tests
```

### Modified Files:
```
rvc2mqtt.py                  # Add discovery logic
rvc2mqtt.ini.example         # Add HA config section
README.md                    # Add HA integration docs
```

---

## Migration Guide (for existing users)

**Upgrading from v1.x to v2.0 (Phase 1):**

1. **Backup your configuration:**
   ```bash
   cp rvc2mqtt.ini rvc2mqtt.ini.backup
   ```

2. **Update configuration file:**
   ```bash
   # Add new [HomeAssistant] section from rvc2mqtt.ini.example
   ```

3. **Test with discovery disabled first:**
   ```ini
   [HomeAssistant]
   discovery_enabled = 0
   ```

4. **Enable discovery when ready:**
   ```ini
   discovery_enabled = 1
   ```

5. **Remove old manual MQTT sensors** (optional):
   - Old sensors in configuration.yaml can be removed
   - Or keep both during transition period

---

## Known Limitations

1. **Single RV Support** - Multi-RV scenarios need unique device_id configuration
2. **Tiffin-Specific** - Custom mappings are Tiffin-focused (will expand in Phase 5)
3. **No Auto-Detection** - Can't auto-detect RV model (manual config needed)
4. **Limited Entity Types** - Only sensors/switches/climate for now (no covers, fans, etc.)

---

## Next Steps After Phase 1

Once Phase 1 is complete and tested:
1. Merge `feature/ha-mqtt-discovery` → `master`
2. Tag release as `v2.0.0`
3. Gather user feedback
4. Begin Phase 2 planning (bidirectional control)

---

## Questions & Decisions Needed

- [ ] What should the default device_id be? (MAC address? Random UUID?)
- [ ] Should legacy topics be enabled by default? (yes for backwards compat)
- [ ] Discovery prefix: always "homeassistant" or configurable?
- [ ] State format: simple values or always JSON?
- [ ] Should we support multiple MQTT brokers?
- [ ] Entity naming: use RVC message names or friendly names?

---

## Resources

### Home Assistant Documentation
- MQTT Discovery: https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
- Device Registry: https://developers.home-assistant.io/docs/device_registry_index
- Entity Categories: https://developers.home-assistant.io/docs/core/entity#generic-properties

### Example Integrations
- ESPHome MQTT Discovery
- Tasmota MQTT Discovery
- Zigbee2MQTT

### Tools
- MQTT Explorer (for debugging topics)
- HA Developer Tools → MQTT (for testing)
- VS Code with YAML extension

---

**Status:** Ready to begin implementation
**First Task:** Research HA MQTT Discovery protocol
