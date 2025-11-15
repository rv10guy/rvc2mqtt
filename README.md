# RVC to MQTT Bridge

A Python-based bridge that connects RV-C (RV Controller Area Network) CAN bus systems to MQTT, enabling integration with home automation platforms like Home Assistant.

## Overview

This tool reads messages from an RV's CAN bus network, decodes them using the RV-C specification, and publishes the data to an MQTT broker. It's particularly useful for monitoring and controlling RV systems through home automation platforms.

## Features

- **Real-time CAN Bus Monitoring**: Connects to CAN bus via TCP/IP using SLCAN protocol
- **RV-C Protocol Decoding**: Interprets RV-C messages using a YAML specification file
- **MQTT Publishing**: Sends decoded data to MQTT topics for easy integration
- **Custom Device Mappings**: Includes specialized processing for Tiffin motorhomes (lights, HVAC, tanks, generators, etc.)
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

Messages are published to topics in the format:
```
{mqttOutputTopic}/{MESSAGE_NAME}/{instance}
```

For example:
- `RVC2/DC_SOURCE_STATUS_1/1` - House battery voltage
- `RVC2/TANK_STATUS/0` - Fresh water tank level
- `RVC2/THERMOSTAT_AMBIENT_STATUS/0` - Front HVAC temperature

### Custom Tiffin Mappings

The script includes custom processing for Tiffin motorhomes that maps RV-C messages to more user-friendly topics:

- `OpenRoad/light/ceiling/state` - Ceiling light status
- `OpenRoad/battery/house` - House battery voltage
- `OpenRoad/Tank/Fresh` - Fresh water tank percentage
- `OpenRoad/HVAC/front/state/temperature` - Front zone temperature
- And many more...

## Project Structure

```
rvc2mqtt/
├── rvc2mqtt.py           # Main application script
├── rvc2mqtt.ini          # Configuration file
├── rvc-spec.yml          # RV-C protocol specification
├── mqttlog.py            # MQTT logging utility
├── requirements.txt      # Python dependencies
├── README.md             # This file
└── .gitignore            # Git ignore rules
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

## Known Limitations

- Currently **one-way only**: CAN bus → MQTT (no MQTT → CAN bus control)
- Code includes framework for two-way communication (currently disabled)

## Future Enhancements

- [ ] Enable two-way MQTT to CAN bus communication
- [ ] Add Home Assistant MQTT discovery
- [ ] Docker container support
- [ ] Web-based configuration interface
- [ ] Support for additional RV manufacturers

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
