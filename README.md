# RVC to MQTT Bridge

A Python-based bridge that connects RV-C (RV Controller Area Network) CAN bus systems to MQTT, enabling integration with home automation platforms like Home Assistant.

## Overview

This tool reads messages from an RV's CAN bus network, decodes them using the RV-C specification, and publishes the data to an MQTT broker. It's particularly useful for monitoring and controlling RV systems through home automation platforms.

## Features

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
│   └── HA_DISCOVERY_RESEARCH.md     # Home Assistant discovery research
├── PHASE1_PLAN.md                   # Phase 1 development plan (COMPLETED)
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

## Known Limitations

- Currently **one-way only**: CAN bus → MQTT (no MQTT → CAN bus control)
- Phase 2 will add bidirectional control (lights, climate, etc.)

## Future Enhancements

- [ ] Enable two-way MQTT to CAN bus communication (Phase 2)
- [x] Add Home Assistant MQTT discovery (✅ Phase 1 Complete)
- [ ] Docker container support
- [ ] Web-based configuration interface
- [ ] Support for additional RV manufacturers (custom mapping templates available)

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
