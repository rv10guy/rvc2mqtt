# RVC to MQTT Bridge

A Python-based bridge that connects RV-C (RV Controller Area Network) CAN bus systems to MQTT, enabling integration with home automation platforms like Home Assistant.

## Overview

This tool reads messages from an RV's CAN bus network, decodes them using the RV-C specification, and publishes the data to an MQTT broker. It's particularly useful for monitoring and controlling RV systems through home automation platforms.

## Features

### Monitoring (Phase 1 - ✅ Complete)
- **Real-time CAN Bus Monitoring**: Connects to CAN bus via TCP/IP using SLCAN protocol
- **RV-C Protocol Decoding**: Interprets RV-C messages using a YAML specification file
- **MQTT Publishing**: Sends decoded data to MQTT topics for easy integration
- **Home Assistant MQTT Discovery**: Zero-configuration auto-discovery of all devices and sensors in Home Assistant
- **Intelligent Device Grouping**: Entities organized into logical devices (HVAC zones, power systems, tanks, etc.)
- **Multi-Entity Type Support**: Sensors, binary sensors, climate controls, lights, and more
- **Custom Device Mappings**: Configurable entity mappings via YAML files for different RV models
- **Auto-Reconnection**: Automatically reconnects to CAN bus if connection is lost
- **Timestamping**: Publishes timestamps of last received messages
- **Configurable Output**: Flexible debug levels and output modes
- **Unit Conversions**: Automatic conversion of temperatures (C to F), voltages, currents, etc.

### Bidirectional Control (Phase 2 - ✅ Complete)
- **MQTT → CAN Control**: Send commands from Home Assistant to control RV devices
- **Light Control**: Turn lights on/off, adjust brightness (0-100%)
- **Climate Control**: Set HVAC mode (heat/cool/off), temperature (50-100°F), fan speed (auto/low/high)
- **Switch Control**: Control pumps, generators, and other switches
- **Multi-Layer Validation**: Schema, entity, range, security, and rate limit validation
- **Security Controls**: Allowlist/denylist for entities and commands
- **Rate Limiting**: Prevent CAN bus flooding with configurable limits
- **Command Audit Logging**: Complete audit trail of all commands with timestamps and latency
- **Error Handling**: Comprehensive error codes and MQTT status/error topics
- **Command Acknowledgments**: Real-time feedback on command success/failure

## Supported Systems

The bridge can decode and publish data for:
- DC power sources (house & chassis batteries)
- Tank levels (fresh water, gray water, black water, propane)
- HVAC systems (thermostats, temperature sensors)
- Lighting controls (DC dimmers)
- Generator status
- And any other RV-C compatible devices

## Requirements

- Python 3.8 or higher
- Network-accessible CAN bus interface (SLCAN over TCP/IP)
- MQTT broker (e.g., Mosquitto)
- RV-C specification file (included as `rvc-spec.yml`)

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/rvc2mqtt.git
   cd rvc2mqtt
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the application**:
   Edit `rvc2mqtt.ini` with your settings (see Configuration section below)

## Configuration

Edit `rvc2mqtt.ini` to configure the bridge:

```ini
[General]
debug = 0                       # Debug level: 0=none, 1=errors, 2=errors+warnings, 3=all
parameterized_strings = 0       # Send parameterized strings to MQTT (0 or 1)
screenout = 0                   # Console output: 0=none, 1=dump parsed messages
specfile = rvc-spec.yml         # RV-C specification file path

[MQTT]
mqttBroker = 192.168.1.100      # MQTT broker IP address
mqttOut = 2                     # Send to MQTT: 0=off, 1=publish, 2=retain
mqttUser = username             # MQTT username
mqttPass = password             # MQTT password
mqttOutputTopic = RVC2          # Base MQTT topic for publishing

[CAN]
CANport = 192.168.1.200:3333    # CAN bus interface IP:port

[HomeAssistant]
discovery_enabled = 1                        # Enable HA MQTT Discovery (0=disabled, 1=enabled)
discovery_prefix = homeassistant             # HA discovery prefix (usually 'homeassistant')
mapping_file = mappings/tiffin_default.yaml  # Entity mapping configuration file
legacy_topics = 1                            # Keep publishing old RVC2/* topics (0=no, 1=yes)

[Commands]
enabled = 1                     # Enable bidirectional commands (0=disabled, 1=enabled)
source_address = 99             # CAN source address for commands (default: 99)
retry_count = 3                 # Number of retries for failed CAN transmissions
retry_delay_ms = 100            # Delay between retries in milliseconds

[RateLimiting]
enabled = 1                             # Enable rate limiting (0=disabled, 1=enabled)
global_commands_per_second = 10         # Max commands per second (global)
entity_commands_per_second = 2          # Max commands per second per entity
entity_cooldown_ms = 500                # Minimum delay between commands to same entity (ms)

[Security]
enabled = 1                             # Enable security controls (0=disabled, 1=enabled)
allowlist =                             # Comma-separated list of allowed entity_ids (empty = all allowed)
denylist =                              # Comma-separated list of denied entity_ids (empty = none denied)
allowed_commands = light,climate,switch # Allowed command types (comma-separated)

[Audit]
enabled = 1                             # Enable audit logging (0=disabled, 1=enabled)
log_file = logs/command_audit.log       # Audit log file path
log_level = INFO                        # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
json_format = 1                         # Use JSON format (1) or human-readable (0)
max_bytes = 10485760                    # Max log file size before rotation (10 MB)
backup_count = 5                        # Number of backup files to keep
```

### Configuration Options

- **debug**: Set to higher values (1-3) for troubleshooting
- **parameterized_strings**: When enabled, converts field names to lowercase with underscores
- **mqttOut**:
  - `0` = Disabled
  - `1` = Publish (non-retained)
  - `2` = Publish with retain flag (recommended for state data)
- **CANport**: IP address and port of your CAN bus interface device

## Usage

Run the bridge:
```bash
python3 rvc2mqtt.py
```

The script will:
1. Connect to the MQTT broker
2. Load the RV-C specification file
3. Connect to the CAN bus interface
4. Begin receiving and decoding CAN messages
5. Publish decoded data to MQTT topics

### MQTT Topic Structure

#### Legacy RV-C Topics (for debugging and raw data access)

Messages are published to topics in the format:
```
{mqttOutputTopic}/{MESSAGE_NAME}/{instance}
```

For example:
- `RVC2/DC_SOURCE_STATUS_1/1` - House battery voltage (raw)
- `RVC2/TANK_STATUS/0` - Fresh water tank level (raw)
- `RVC2/THERMOSTAT_AMBIENT_STATUS/0` - Front HVAC temperature (raw)

#### Home Assistant Discovery Topics

When Home Assistant MQTT Discovery is enabled, entities are published to friendly topics:

**State Topics:**
- `rv/sensor/{entity_id}/state` - Sensor values (temperature, voltage, tank levels, etc.)
- `rv/binary_sensor/{entity_id}/state` - Binary sensors (ON/OFF states)
- `rv/climate/{entity_id}/mode` - Climate control mode
- `rv/climate/{entity_id}/setpoint` - Climate control setpoint temperature
- `rv/climate/{entity_id}/fan` - Climate fan mode
- `rv/light/{entity_id}/state` - Light state (ON/OFF)
- `rv/light/{entity_id}/brightness` - Light brightness (if supported)

**Discovery Topics:**
- `homeassistant/{entity_type}/{entity_id}/config` - Auto-discovery configuration messages

**Examples:**
- `rv/sensor/battery_house/state` - House battery voltage
- `rv/sensor/tank_fresh_0/state` - Fresh water tank percentage
- `rv/climate/hvac_front/mode` - Front HVAC operating mode
- `rv/light/light_ceiling/state` - Ceiling light state

**Command Topics (Phase 2 - Bidirectional Control):**

Send commands to RV devices by publishing to:
- `rv/light/{entity_id}/set` - Turn light ON/OFF
- `rv/light/{entity_id}/brightness/set` - Set light brightness (0-100)
- `rv/climate/{entity_id}/mode/set` - Set HVAC mode (off, heat, cool, auto)
- `rv/climate/{entity_id}/temperature/set` - Set temperature setpoint (50-100°F)
- `rv/climate/{entity_id}/fan_mode/set` - Set fan mode (auto, low, high)
- `rv/switch/{entity_id}/set` - Turn switch ON/OFF

**Command Feedback Topics:**
- `rv/command/status` - Success acknowledgments with latency
- `rv/command/error` - Error messages with error codes

**Quick Example:**
```yaml
# Turn on ceiling light
service: mqtt.publish
data:
  topic: "rv/light/ceiling_light/set"
  payload: "ON"

# Set HVAC to 72°F
service: mqtt.publish
data:
  topic: "rv/climate/hvac_front/temperature/set"
  payload: "72"
```

See [Command Format Guide](docs/COMMAND_FORMAT.md) for complete documentation.

## Project Structure

```
rvc2mqtt/
├── rvc2mqtt.py                      # Main application script
├── rvc2mqtt.ini                     # Configuration file
├── ha_discovery.py                  # Home Assistant MQTT Discovery module
├── rvc-spec.yml                     # RV-C protocol specification
├── mqttlog.py                       # MQTT logging utility
├── requirements.txt                 # Python dependencies
├── mappings/                        # Entity mapping configurations
│   ├── tiffin_default.yaml          # Default Tiffin motorhome mapping
│   └── custom_template.yaml         # Template for custom mappings
├── docs/                            # Documentation
│   ├── TOPIC_SCHEMA_DESIGN.md       # MQTT topic schema design
│   ├── HA_DISCOVERY_RESEARCH.md     # Home Assistant discovery research
│   ├── COMMAND_FORMAT.md            # Command format guide (Phase 2)
│   ├── HA_AUTOMATION_EXAMPLES.md    # Automation examples (Phase 2)
│   ├── RVC_COMMAND_REFERENCE.md     # RV-C command reference (Phase 2)
│   ├── PHASE2_ARCHITECTURE.md       # Phase 2 architecture design
│   └── PHASE2_TESTING.md            # Phase 2 testing results
├── tests/                           # Test suite (Phase 2)
│   ├── test_phase2_core.py          # Core functionality tests
│   ├── test_rvc_commands.py         # Command encoder tests
│   ├── test_command_validator.py    # Validator tests
│   └── test_integration.py          # Integration tests
├── rvc_commands.py                  # RV-C command encoder (Phase 2)
├── command_validator.py             # Command validation (Phase 2)
├── command_handler.py               # MQTT→CAN orchestration (Phase 2)
├── can_tx.py                        # CAN bus transmitter (Phase 2)
├── audit_logger.py                  # Command audit logging (Phase 2)
├── run_tests.py                     # Test runner (Phase 2)
├── ROADMAP.md                       # Project roadmap
├── README.md                        # This file
└── .gitignore                       # Git ignore rules
```

## Utilities

### mqttlog.py

A utility script for logging and monitoring MQTT messages. Useful for debugging and verifying data flow.

## Troubleshooting

### Connection Issues

If you see "No route to host" or connection errors:
1. Verify the CAN bus device is powered on and reachable
2. Check network connectivity: `ping <CAN_device_IP>`
3. Test port accessibility: `nc -zv <CAN_device_IP> 3333`
4. Verify the IP address and port in `rvc2mqtt.ini`

### No Messages Received

1. Enable debug output: Set `debug = 3` in `rvc2mqtt.ini`
2. Verify CAN bus has active traffic
3. Check that `rvc-spec.yml` contains definitions for your device's messages

### MQTT Issues

1. Verify MQTT broker is running
2. Check MQTT credentials in `rvc2mqtt.ini`
3. Test MQTT connection manually using `mosquitto_pub`/`mosquitto_sub`

## Home Assistant Integration

### Automatic Discovery

With Home Assistant MQTT Discovery enabled (default), all RV devices and sensors will automatically appear in Home Assistant with **zero configuration required**. Simply:

1. Ensure your MQTT broker is configured in Home Assistant
2. Start `rvc2mqtt.py`
3. Wait a few seconds for discovery messages to be published
4. Check Home Assistant - all entities will appear under the "MQTT" integration

### Supported Entity Types

- **Sensors**: Battery voltage, tank levels, temperatures, generator status
- **Binary Sensors**: Door/window states, system statuses
- **Climate**: HVAC thermostats with mode, setpoint, and fan control
- **Lights**: Interior and exterior lighting with state tracking

### Device Organization

Entities are automatically grouped into logical devices:
- **HVAC Front Zone** - Front climate control and temperature
- **HVAC Rear Zone** - Rear climate control and temperature
- **RV Power Systems** - Battery voltages and power sources
- **RV Systems** - Generator and other system statuses
- **RV Tank Monitoring** - Fresh, gray, black water and propane levels
- **RV Ventilation** - Vent fan controls
- **RV Lighting** - All interior and exterior lights

### Custom Mappings

To create a custom mapping for your RV:

1. Copy `mappings/custom_template.yaml`
2. Edit the file to match your RV's specific configuration
3. Update `rvc2mqtt.ini` to point to your custom mapping file
4. Restart `rvc2mqtt.py`

See `docs/TOPIC_SCHEMA_DESIGN.md` for detailed mapping documentation.

## Phase 2 Bidirectional Control

### Supported Commands

**Lights:**
- Turn on/off
- Set brightness (0-100%)
- Multi-frame sequences for smooth dimming

**Climate (HVAC):**
- Set mode (off, heat, cool, auto)
- Set temperature (50-100°F)
- Set fan speed (auto, low, high)
- Automatic furnace zone sync

**Switches:**
- Control water pumps
- Control generator
- Control other RV switches

### Safety Features

- **Multi-layer validation** prevents invalid commands from reaching CAN bus
- **Rate limiting** prevents CAN bus flooding (configurable limits)
- **Security controls** with allowlist/denylist for entities and commands
- **Audit logging** tracks all commands with timestamps and outcomes
- **Error handling** provides detailed error codes and messages
- **Command retries** for failed CAN transmissions

### Documentation

- [Command Format Guide](docs/COMMAND_FORMAT.md) - Complete MQTT command reference
- [Automation Examples](docs/HA_AUTOMATION_EXAMPLES.md) - Real-world HA automations
- [RV-C Command Reference](docs/RVC_COMMAND_REFERENCE.md) - Low-level CAN frame details
- [Phase 2 Architecture](docs/PHASE2_ARCHITECTURE.md) - System design
- [Phase 2 Testing](docs/PHASE2_TESTING.md) - Test results (20/20 passing)

### Testing

Phase 2 includes comprehensive test coverage:

```bash
# Run all tests
python3 run_tests.py

# Run core tests only
python3 tests/test_phase2_core.py
```

**Test Results:** ✅ 20/20 tests passing
- RV-C command encoding
- Multi-layer validation
- End-to-end MQTT→CAN flow
- Error handling
- Rate limiting
- Security controls

## Future Enhancements

- [x] Enable two-way MQTT to CAN bus communication (✅ Phase 2 Complete)
- [x] Add Home Assistant MQTT discovery (✅ Phase 1 Complete)
- [ ] Docker container support
- [ ] Web-based configuration interface
- [ ] Support for additional RV manufacturers (custom mapping templates available)
- [ ] Additional device types (awnings, leveling jacks, etc.)

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

[Specify your license here - e.g., MIT, GPL, Apache 2.0]

## Acknowledgments

- RV-C specification from RVIA (RV Industry Association)
- Built with [python-can](https://python-can.readthedocs.io/)
- MQTT client by [Eclipse Paho](https://www.eclipse.org/paho/)

## Support

For issues, questions, or feature requests, please open an issue on GitHub.
