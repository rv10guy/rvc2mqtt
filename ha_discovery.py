#!/usr/bin/env python3
"""
Home Assistant MQTT Discovery Module

This module handles generating and publishing MQTT Discovery messages
for Home Assistant integration.

Documentation: https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
"""

import json
import yaml
import os

class HADiscovery:
    """Manages Home Assistant MQTT Discovery configuration and publishing"""

    def __init__(self, mapping_file, discovery_prefix="homeassistant"):
        """
        Initialize HA Discovery manager

        Args:
            mapping_file: Path to YAML mapping configuration file
            discovery_prefix: MQTT discovery prefix (default: homeassistant)
        """
        self.mapping_file = mapping_file
        self.discovery_prefix = discovery_prefix
        self.mapping = None
        self.entities = []
        self.devices = {}
        self.settings = {}

        self.load_mapping()

    def load_mapping(self):
        """Load mapping configuration from YAML file"""
        if not os.path.exists(self.mapping_file):
            raise FileNotFoundError(f"Mapping file not found: {self.mapping_file}")

        with open(self.mapping_file, 'r') as f:
            self.mapping = yaml.safe_load(f)

        # Extract settings
        self.settings = self.mapping.get('settings', {})
        self.state_topic_prefix = self.settings.get('state_topic_prefix', 'rv')
        self.device_id_prefix = self.settings.get('device_id_prefix', 'rv')
        self.sw_version = self.settings.get('sw_version', '2.0.0')

        # Build device definitions
        for device_id, device_config in self.mapping.get('devices', {}).items():
            self.devices[device_id] = self._build_device_info(device_config)

        # Store entities for lookup
        self.entities = self.mapping.get('entities', [])

    def _build_device_info(self, device_config):
        """
        Build Home Assistant device information dictionary

        Args:
            device_config: Device configuration from mapping file

        Returns:
            dict: Device info for HA discovery message
        """
        device_info = {
            "identifiers": [f"{self.device_id_prefix}_{device_config['identifier']}"],
            "name": device_config['name'],
            "model": device_config['model'],
            "manufacturer": device_config['manufacturer'],
            "sw_version": self.sw_version
        }

        if 'suggested_area' in device_config:
            device_info['suggested_area'] = device_config['suggested_area']

        if 'configuration_url' in device_config:
            device_info['configuration_url'] = device_config['configuration_url']

        return device_info

    def generate_discovery_messages(self):
        """
        Generate all discovery messages for configured entities

        Returns:
            list: List of (topic, payload) tuples ready to publish
        """
        messages = []

        for entity in self.entities:
            topic, payload = self._generate_entity_discovery(entity)
            if topic and payload:
                messages.append((topic, payload))

        return messages

    def _generate_entity_discovery(self, entity):
        """
        Generate discovery message for a single entity

        Args:
            entity: Entity configuration from mapping file

        Returns:
            tuple: (topic, payload) or (None, None) if error
        """
        entity_type = entity['entity_type']
        entity_id = entity['entity_id']

        # Build unique_id
        unique_id = f"{self.device_id_prefix}_{entity_id}"

        # Build discovery topic
        topic = f"{self.discovery_prefix}/{entity_type}/{unique_id}/config"

        # Generate payload based on entity type
        if entity_type == 'sensor':
            payload = self._generate_sensor_discovery(entity, unique_id)
        elif entity_type == 'binary_sensor':
            payload = self._generate_binary_sensor_discovery(entity, unique_id)
        elif entity_type == 'light':
            payload = self._generate_light_discovery(entity, unique_id)
        elif entity_type == 'switch':
            payload = self._generate_switch_discovery(entity, unique_id)
        elif entity_type == 'climate':
            payload = self._generate_climate_discovery(entity, unique_id)
        elif entity_type == 'fan':
            payload = self._generate_fan_discovery(entity, unique_id)
        elif entity_type == 'cover':
            payload = self._generate_cover_discovery(entity, unique_id)
        else:
            print(f"Warning: Unknown entity type '{entity_type}' for {entity_id}")
            return None, None

        # Convert payload to JSON
        payload_json = json.dumps(payload)

        return topic, payload_json

    def _generate_sensor_discovery(self, entity, unique_id):
        """Generate discovery payload for sensor entity"""
        state_topic = f"{self.state_topic_prefix}/sensor/{entity['entity_id']}/state"

        payload = {
            "name": entity['name'],
            "unique_id": unique_id,
            "state_topic": state_topic,
            "availability_topic": f"{self.state_topic_prefix}/status",
            "payload_available": "online",
            "payload_not_available": "offline"
        }

        # Add optional fields
        if entity.get('unit_of_measurement'):
            payload['unit_of_measurement'] = entity['unit_of_measurement']

        if entity.get('device_class'):
            payload['device_class'] = entity['device_class']

        if entity.get('state_class'):
            payload['state_class'] = entity['state_class']

        if entity.get('icon'):
            payload['icon'] = entity['icon']

        # Add display precision (configurable or auto-set for voltage)
        if entity.get('suggested_display_precision') is not None:
            payload['suggested_display_precision'] = entity['suggested_display_precision']
        elif entity.get('device_class') == 'voltage':
            # Default to 1 decimal place for voltage sensors
            payload['suggested_display_precision'] = 1

        # Add device info
        if entity.get('device') and entity['device'] in self.devices:
            payload['device'] = self.devices[entity['device']]

        return payload

    def _generate_binary_sensor_discovery(self, entity, unique_id):
        """Generate discovery payload for binary_sensor entity"""
        state_topic = f"{self.state_topic_prefix}/binary_sensor/{entity['entity_id']}/state"

        payload = {
            "name": entity['name'],
            "unique_id": unique_id,
            "state_topic": state_topic,
            "payload_on": "ON",
            "payload_off": "OFF",
            "availability_topic": f"{self.state_topic_prefix}/status",
            "payload_available": "online",
            "payload_not_available": "offline"
        }

        # Add optional fields
        if entity.get('device_class'):
            payload['device_class'] = entity['device_class']

        if entity.get('icon'):
            payload['icon'] = entity['icon']

        # Add device info
        if entity.get('device') and entity['device'] in self.devices:
            payload['device'] = self.devices[entity['device']]

        return payload

    def _generate_light_discovery(self, entity, unique_id):
        """Generate discovery payload for light entity"""
        state_topic = f"{self.state_topic_prefix}/light/{entity['entity_id']}/state"
        command_topic = f"{self.state_topic_prefix}/light/{entity['entity_id']}/set"

        payload = {
            "name": entity['name'],
            "unique_id": unique_id,
            "state_topic": state_topic,
            "command_topic": command_topic,
            "payload_on": "ON",
            "payload_off": "OFF",
            "availability_topic": f"{self.state_topic_prefix}/status",
            "payload_available": "online",
            "payload_not_available": "offline"
        }

        # Add brightness support if specified
        if entity.get('supports_brightness', False):
            brightness_topic = f"{self.state_topic_prefix}/light/{entity['entity_id']}/brightness"
            brightness_command_topic = f"{self.state_topic_prefix}/light/{entity['entity_id']}/brightness/set"
            payload['brightness_state_topic'] = brightness_topic
            payload['brightness_command_topic'] = brightness_command_topic
            payload['brightness_scale'] = 100

        # Add optional fields
        if entity.get('icon'):
            payload['icon'] = entity['icon']

        # Add device info
        if entity.get('device') and entity['device'] in self.devices:
            payload['device'] = self.devices[entity['device']]

        return payload

    def _generate_switch_discovery(self, entity, unique_id):
        """Generate discovery payload for switch entity"""
        state_topic = f"{self.state_topic_prefix}/switch/{entity['entity_id']}/state"
        command_topic = f"{self.state_topic_prefix}/switch/{entity['entity_id']}/set"

        payload = {
            "name": entity['name'],
            "unique_id": unique_id,
            "state_topic": state_topic,
            "command_topic": command_topic,
            "payload_on": "ON",
            "payload_off": "OFF",
            "availability_topic": f"{self.state_topic_prefix}/status",
            "payload_available": "online",
            "payload_not_available": "offline"
        }

        # Add optional fields
        if entity.get('icon'):
            payload['icon'] = entity['icon']

        if entity.get('device_class'):
            payload['device_class'] = entity['device_class']

        # Add device info
        if entity.get('device') and entity['device'] in self.devices:
            payload['device'] = self.devices[entity['device']]

        return payload

    def _generate_climate_discovery(self, entity, unique_id):
        """Generate discovery payload for climate entity"""
        base_topic = f"{self.state_topic_prefix}/climate/{entity['entity_id']}"

        payload = {
            "name": entity['name'],
            "unique_id": unique_id,
            "mode_state_topic": f"{base_topic}/mode",
            "mode_command_topic": f"{base_topic}/mode/set",
            "temperature_state_topic": f"{base_topic}/setpoint",
            "temperature_command_topic": f"{base_topic}/temperature/set",
            "current_temperature_topic": f"{base_topic}/temperature",
            "fan_mode_state_topic": f"{base_topic}/fan",
            "fan_mode_command_topic": f"{base_topic}/fan_mode/set",
            "availability_topic": f"{self.state_topic_prefix}/status",
            "payload_available": "online",
            "payload_not_available": "offline"
        }

        # Add climate-specific configuration
        if entity.get('modes'):
            payload['modes'] = entity['modes']

        if entity.get('fan_modes'):
            payload['fan_modes'] = entity['fan_modes']

        if entity.get('temp_step'):
            payload['temp_step'] = entity['temp_step']

        if entity.get('min_temp'):
            payload['min_temp'] = entity['min_temp']

        if entity.get('max_temp'):
            payload['max_temp'] = entity['max_temp']

        if entity.get('temperature_unit'):
            payload['temperature_unit'] = entity['temperature_unit']

        if entity.get('precision'):
            payload['precision'] = entity['precision']

        # Add device info
        if entity.get('device') and entity['device'] in self.devices:
            payload['device'] = self.devices[entity['device']]

        return payload

    def _generate_fan_discovery(self, entity, unique_id):
        """Generate discovery payload for fan entity"""
        state_topic = f"{self.state_topic_prefix}/fan/{entity['entity_id']}/state"
        command_topic = f"{self.state_topic_prefix}/fan/{entity['entity_id']}/set"

        payload = {
            "name": entity['name'],
            "unique_id": unique_id,
            "state_topic": state_topic,
            "command_topic": command_topic,
            "payload_on": "ON",
            "payload_off": "OFF",
            "availability_topic": f"{self.state_topic_prefix}/status",
            "payload_available": "online",
            "payload_not_available": "offline"
        }

        # Add speed support for ceiling fans
        if entity.get('supports_speed'):
            # Use preset modes for discrete speeds (LOW/HIGH)
            payload['preset_mode_state_topic'] = state_topic
            payload['preset_mode_command_topic'] = command_topic
            payload['preset_modes'] = ["LOW", "HIGH"]

        # Add optional fields
        if entity.get('icon'):
            payload['icon'] = entity['icon']

        # Add device info
        if entity.get('device') and entity['device'] in self.devices:
            payload['device'] = self.devices[entity['device']]

        return payload

    def _generate_cover_discovery(self, entity, unique_id):
        """Generate discovery payload for cover entity"""
        state_topic = f"{self.state_topic_prefix}/cover/{entity['entity_id']}/state"
        command_topic = f"{self.state_topic_prefix}/cover/{entity['entity_id']}/position/set"

        payload = {
            "name": entity['name'],
            "unique_id": unique_id,
            "state_topic": state_topic,
            "command_topic": command_topic,
            "payload_open": "open",
            "payload_close": "close",
            "availability_topic": f"{self.state_topic_prefix}/status",
            "payload_available": "online",
            "payload_not_available": "offline"
        }

        # Add optional fields
        if entity.get('device_class'):
            payload['device_class'] = entity['device_class']

        if entity.get('icon'):
            payload['icon'] = entity['icon']

        # Add device info
        if entity.get('device') and entity['device'] in self.devices:
            payload['device'] = self.devices[entity['device']]

        return payload

    def get_entity_by_rvc_message(self, rvc_message, instance):
        """
        Find entity configuration by RV-C message and instance

        Args:
            rvc_message: RV-C message name (e.g., "TANK_STATUS")
            instance: Instance number or None

        Returns:
            list: List of matching entity configurations
        """
        matches = []
        for entity in self.entities:
            if entity['rvc_message'] == rvc_message:
                # Match if instance is None (no instance) or matches
                if entity.get('instance') is None or entity.get('instance') == instance:
                    matches.append(entity)
        return matches

    def get_state_topic(self, entity):
        """
        Get state topic for an entity

        Args:
            entity: Entity configuration

        Returns:
            str: State topic path
        """
        entity_type = entity['entity_type']
        entity_id = entity['entity_id']
        return f"{self.state_topic_prefix}/{entity_type}/{entity_id}/state"

    def get_brightness_topic(self, entity):
        """
        Get brightness topic for a light entity

        Args:
            entity: Light entity configuration

        Returns:
            str: Brightness topic path or None
        """
        if entity['entity_type'] == 'light' and entity.get('supports_brightness'):
            entity_id = entity['entity_id']
            return f"{self.state_topic_prefix}/light/{entity_id}/brightness"
        return None

    def get_climate_topics(self, entity):
        """
        Get all climate topics for a climate entity

        Args:
            entity: Climate entity configuration

        Returns:
            dict: Dictionary of topic names and paths
        """
        if entity['entity_type'] != 'climate':
            return {}

        entity_id = entity['entity_id']
        base_topic = f"{self.state_topic_prefix}/climate/{entity_id}"

        return {
            'mode': f"{base_topic}/mode",
            'setpoint': f"{base_topic}/setpoint",
            'temperature': f"{base_topic}/temperature",
            'fan': f"{base_topic}/fan"
        }

    def extract_value(self, entity, decoded_data):
        """
        Extract value from decoded RV-C data based on entity configuration

        Args:
            entity: Entity configuration
            decoded_data: Decoded RV-C message dictionary

        Returns:
            Value extracted based on value_template or value_field
        """
        # If there's a value_template, evaluate it
        if 'value_template' in entity:
            try:
                # Create safe evaluation context
                # Helper function to get field with both underscore and space variants
                def get_field(data, field):
                    """Try to get field with underscores, then with spaces"""
                    if field in data:
                        return data[field]
                    # Try replacing underscores with spaces
                    field_with_spaces = field.replace('_', ' ')
                    if field_with_spaces in data:
                        return data[field_with_spaces]
                    # Try without changes
                    return data.get(field)

                # Make decoded_data accessible to template
                value = decoded_data
                # Add helper to access fields flexibly
                import types
                value_dict = types.SimpleNamespace()
                for key in decoded_data.keys():
                    # Make fields accessible with underscores
                    safe_key = key.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
                    setattr(value_dict, safe_key, decoded_data[key])

                # Evaluate template with flexible field access
                # Replace value['field'] with get_field(value, 'field')
                template = entity['value_template']
                # Simple approach: make value support both formats
                class FlexDict(dict):
                    def __getitem__(self, key):
                        if key in self:
                            return dict.__getitem__(self, key)
                        # Try with spaces
                        key_with_spaces = key.replace('_', ' ')
                        if key_with_spaces in self:
                            return dict.__getitem__(self, key_with_spaces)
                        raise KeyError(key)

                value = FlexDict(decoded_data)
                result = eval(template)
                return result
            except Exception as e:
                if str(e) not in ["'relative_level'", "'relative level'"]:  # Don't spam for known issue
                    print(f"Error evaluating value_template for {entity['entity_id']}: {e}")
                return None

        # Otherwise use value_field or state_field
        field_name = entity.get('value_field') or entity.get('state_field')
        if field_name:
            # Try both underscore and space variants
            if field_name in decoded_data:
                return decoded_data[field_name]
            field_with_spaces = field_name.replace('_', ' ')
            return decoded_data.get(field_with_spaces)

        return None

    def publish_discovery_messages(self, mqttc, debug_level=0):
        """
        Publish all discovery messages to MQTT

        Args:
            mqttc: MQTT client instance
            debug_level: Debug output level
        """
        messages = self.generate_discovery_messages()

        if debug_level > 0:
            print(f"Publishing {len(messages)} HA MQTT Discovery messages...")

        for topic, payload in messages:
            mqttc.publish(topic, payload, retain=True, qos=1)
            if debug_level > 1:
                print(f"  Published: {topic}")

        if debug_level > 0:
            print(f"HA MQTT Discovery complete. {len(messages)} entities configured.")


def test_discovery():
    """Test function to validate discovery message generation"""
    print("Testing HA Discovery Module...")

    # Load mapping
    discovery = HADiscovery("mappings/tiffin_default.yaml")

    print(f"Loaded {len(discovery.entities)} entities from mapping file")
    print(f"Devices: {list(discovery.devices.keys())}")

    # Generate discovery messages
    messages = discovery.generate_discovery_messages()
    print(f"\nGenerated {len(messages)} discovery messages")

    # Show first few examples
    print("\nExample Discovery Messages:")
    for i, (topic, payload) in enumerate(messages[:3]):
        print(f"\n--- Message {i+1} ---")
        print(f"Topic: {topic}")
        print(f"Payload: {json.dumps(json.loads(payload), indent=2)}")

    # Test entity lookup
    print("\n--- Testing Entity Lookup ---")
    tank_entities = discovery.get_entity_by_rvc_message("TANK_STATUS", 0)
    print(f"Found {len(tank_entities)} entities for TANK_STATUS instance 0")
    if tank_entities:
        print(f"Entity: {tank_entities[0]['name']} ({tank_entities[0]['entity_id']})")
        print(f"State Topic: {discovery.get_state_topic(tank_entities[0])}")


if __name__ == "__main__":
    test_discovery()
