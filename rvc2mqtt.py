#!/usr/bin/env python3

import argparse, array, can, json, os, queue, re, signal, threading, time, sys, serial, time, configparser
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
import ruamel.yaml as yaml
from datetime import datetime
from ha_discovery import HADiscovery

config = configparser.ConfigParser(inline_comment_prefixes=';')
config.read('rvc2mqtt.ini')
debug_level = config.getint('General', 'debug')
parameterized_strings = config.getboolean('General', 'parameterized_strings')
screenOut = config.getint('General', 'screenout')
specfile = config.get('General', 'specfile')
mqttBroker = config.get('MQTT', 'mqttBroker')
mqttUser = config.get('MQTT', 'mqttUser')
mqttPass = config.get('MQTT', 'mqttPass')
mqttOut = config.getint('MQTT', 'mqttOut')
mqttOutputTopic = config.get('MQTT', 'mqttOutputTopic')
canbus = config.get('CAN', 'CANport')

# Home Assistant Discovery settings
ha_discovery_enabled = config.getboolean('HomeAssistant', 'discovery_enabled', fallback=False)
ha_discovery_prefix = config.get('HomeAssistant', 'discovery_prefix', fallback='homeassistant')
ha_mapping_file = config.get('HomeAssistant', 'mapping_file', fallback='mappings/tiffin_default.yaml')
ha_legacy_topics = config.getboolean('HomeAssistant', 'legacy_topics', fallback=True)

last_msg_time = None
ha_discovery = None  # Will be initialized if discovery is enabled

def signal_handler(signal, frame):
    global t
    print('')
    print('You pressed Ctrl+C!  Exiting...')
    print('')
    t.kill_received = True
    exit(0)

def on_mqtt_connect(client, userdata, flags, reason_code, properties):
    if debug_level:
        print("MQTT Connected with code "+str(reason_code))
#   client.subscribe("rvc/#")

def on_mqtt_subscribe(client, userdata, mid, reason_code_list, properties):
    if debug_level:
        print("MQTT Sub: "+str(mid))

def on_mqtt_message(client, userdata, msg):
    global last_msg_time
    try:
        topic = msg.topic[13:]
        payload = json.loads(msg.payload)
        frames = payload.get("frame", [])
        num_frames = len(frames)
            
        if debug_level:
            print(f"Send CAN ID: {topic}")

        for frame in frames:
            if debug_level:
                print(f"Data: {frame}")

            # Put the received JSON frame into the queue
            json_data = json.dumps(frame)
            q.put(json_data)

    except Exception as e:
        print(f"Error in processing message: {e}")

def on_mqtt_publish(client, userdata, mid, reason_code, properties):
    if debug_level:
        print("MQTT Published: " + str(mid))

# can_tx(canid, canmsg)
#    canid = numeric CAN ID, not string
#    canmsg = Array of numeric values to transmit
#           - Alternately, a string of two position hex values can be accepted
#
# Examples:
#   can_tx( 0x19FEDB99, [0x02, 0xFF, 0xC8, 0x03, 0xFF, 0x00, 0xFF, 0xFF] )
#   can_tx( 0x19FEDB99, '02FFC803FF00FFFF' )
#
#def can_tx(canid,canmsg):
#    if isinstance(canmsg, str):
#        tmp = canmsg
#        canmsg = [int(tmp[x:x+2],16) for x in range( 0, len(tmp), 2 )]
#    msg = can.Message(arbitration_id=canid, data=canmsg, extended_id=True)
#    try:
#        bus.send(msg)
#        if debug_level>0:
#            print("Message sent on {}".format(bus.channel_info))
#    except can.CanError:
#        print("CAN Send Failed")

class TCP_CANWatcher(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.kill_received = False
        self.queue = queue

    def run(self):
        connected = False
        while not self.kill_received:
            if not connected:
                try:
                    bus = can.interface.Bus(interface='slcan',
                                            channel='socket://' + canbus,
                                            rtscts=True,
                                            bitrate=250000)
                    connected = True
                    print("Connected to the CANbus.")
                except serial.serialutil.SerialException as err:
                    print("Failed to connect to the CANbus. Retrying in 1 minute.")
                    time.sleep(60)
                    continue

            msg = bus.recv(timeout=30)  # Set a timeout of 30 seconds for receiving messages
            if msg is None:
                print("No messages received for 30 seconds. Reconnecting...")
                connected = False
                bus.shutdown()
                continue

            frame = {
                "id": msg.arbitration_id,
                "dlc": msg.dlc,
                "data": list(msg.data)
            }
            self.queue.put(json.dumps(frame))

        if connected:
            bus.shutdown()

def mqtt_safe_publish(client, topic, payload, retain):
    global last_msg_time
    # Publish the main MQTT message
    client.publish(topic, payload, retain=retain)

    # Get the current timestamp
    current_time = time.time()

    # Convert the current time to a human-readable format
    human_readable_time = datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')

    # Publish the time since the last message to an MQTT topic
    client.publish("OpenRoad/time_of_last", human_readable_time, retain=retain)

def publish_ha_state(mqttc, dgn, instance, decoded_data, retain):
    """
    Publish state messages for Home Assistant entities

    Args:
        mqttc: MQTT client
        dgn: RV-C message name (DGN)
        instance: Instance number or None
        decoded_data: Decoded RV-C message dictionary
        retain: Whether to retain the message
    """
    if not ha_discovery:
        return

    # Find matching entities in the mapping
    entities = ha_discovery.get_entity_by_rvc_message(dgn, instance)

    for entity in entities:
        try:
            # Extract value based on entity configuration
            value = ha_discovery.extract_value(entity, decoded_data)

            if value is None:
                continue

            entity_type = entity['entity_type']

            if entity_type == 'sensor' or entity_type == 'binary_sensor':
                # Simple sensors: publish single value
                state_topic = ha_discovery.get_state_topic(entity)

                # Convert binary sensor values to ON/OFF
                if entity_type == 'binary_sensor':
                    on_value = entity.get('on_value', '01')
                    if str(value) == on_value or value == True or value == 1:
                        value = "ON"
                    else:
                        value = "OFF"

                mqttc.publish(state_topic, str(value), retain=retain)

            elif entity_type == 'light':
                # Lights: publish state and brightness
                state_topic = ha_discovery.get_state_topic(entity)

                # Convert load status to ON/OFF
                if str(value) == '01' or value == True or value == 1:
                    mqttc.publish(state_topic, "ON", retain=retain)
                else:
                    mqttc.publish(state_topic, "OFF", retain=retain)

                # TODO: Brightness support (Phase 1 is read-only)

            elif entity_type == 'switch':
                # Switches: publish ON/OFF state
                state_topic = ha_discovery.get_state_topic(entity)

                if str(value) == '01' or value == True or value == 1:
                    mqttc.publish(state_topic, "ON", retain=retain)
                else:
                    mqttc.publish(state_topic, "OFF", retain=retain)

            elif entity_type == 'climate':
                # Climate: publish multiple topics
                topics = ha_discovery.get_climate_topics(entity)

                # Mode
                mode_value = decoded_data.get(entity.get('mode_field', 'operating mode definition'))
                if mode_value:
                    mqttc.publish(topics['mode'], str(mode_value).lower(), retain=retain)

                # Setpoint temperature
                setpoint_value = decoded_data.get(entity.get('setpoint_field', 'setpoint temp cool F'))
                if setpoint_value and setpoint_value != 'n/a':
                    mqttc.publish(topics['setpoint'], str(int(round(setpoint_value))), retain=retain)

                # Fan mode
                fan_value = decoded_data.get(entity.get('fan_mode_field', 'fan mode definition'))
                if fan_value:
                    mqttc.publish(topics['fan'], str(fan_value).lower(), retain=retain)

                # Current temperature comes from THERMOSTAT_AMBIENT_STATUS, not this message

        except Exception as e:
            if debug_level > 0:
                print(f"Error publishing HA state for {entity.get('entity_id')}: {e}")

def rvc_decode(mydgn, mydata):
    result = { 'dgn':mydgn, 'data':mydata, 'name':"UNKNOWN-"+mydgn }
    if mydgn not in spec:
        return result

    decoder = spec[mydgn]
    result['name'] = decoder['name']
    params = []
    try:
        params.extend(spec[decoder['alias']]['parameters'])
    except:
        pass

    try:
        params.extend(decoder['parameters'])
    except:
        pass

    param_count = 0
    for param in params:
        if parameterized_strings:
            param['name'] = parameterize_string(param['name'])

        try:
            mybytes = get_bytes(mydata,param['byte'])
            myvalue = int(mybytes,16) # Get the decimal value of the hex bytes
        except:
            # If you get here, it's because the params had more bytes than the data packet.
            # Thus, skip the rest of the processing
            continue

        try:
            myvalue = get_bits(myvalue,param['bit'])
            if param['type'][:4] == 'uint':
                myvalue = int(myvalue,2)
        except:
            pass

        try:
            myvalue = convert_unit(myvalue,param['unit'],param['type'])
        except:
            pass

        result[param['name']] = myvalue

        try:
            if param['unit'].lower() == 'deg c':
                if parameterized_strings:
                    result[param['name'] + '_f'] = tempC2F(myvalue)
                else:
                    result[param['name'] + ' F'] = tempC2F(myvalue)
        except:
            pass

        try:
            mydef = 'undefined'
            mydef = param['values'][int(myvalue)]
            # int(myvalue) is a hack because the spec yaml interprets binary bits
            # as integers instead of binary strings.
            if parameterized_strings:
                result[param['name'] + "_definition"] = mydef
            else:
                result[param['name'] + " definition"] = mydef
        except:
            pass

        param_count += 1

    if param_count == 0:
        result['DECODER PENDING'] = 1

    return result

def get_bytes(mybytes,byterange):
    try:
        bset=byterange.split('-')
        sub_bytes = "".join(mybytes[i:i+2] for i in range(int(bset[1])*2, (int(bset[0])-1)*2, -2))
    except:
        sub_bytes = mybytes[ byterange * 2 : ( byterange + 1 ) * 2 ]

    return sub_bytes

def get_bits(mydata,bitrange):
    mybits="{0:08b}".format(mydata)
    try:
        bset=bitrange.split('-')
        sub_bits = mybits[ 7 - int(bset[1]) : 8 - int(bset[0]) ]
    except:
        sub_bits = mybits[ 7 - bitrange : 8 - bitrange ]

    return sub_bits

# Convert a string to something easier to use as a JSON parameter by
# converting spaces and slashes to underscores, and removing parentheses.
# e.g.: "Manufacturer Code (LSB) in/out" => "manufacturer_code_lsb_in_out"
def parameterize_string(string):
    return string.translate(string.maketrans(' /', '__', '()')).lower()

def tempC2F(degc):
    return round( ( degc * 9 / 5 ) + 32, 1 )

def convert_unit(myvalue,myunit,mytype):
    new_value = myvalue
    mu = myunit.lower()
    if mu == 'pct':
        if myvalue != 255:
            new_value = myvalue / 2

    elif mu == 'deg c':
        new_value = 'n/a'
        if mytype == 'uint8' and myvalue != ( 1 << 8 ) - 1:
            new_value = myvalue - 40
        elif mytype == 'uint16' and myvalue != ( 1 << 16 ) - 1:
            new_value = round( ( myvalue * 0.03125 ) - 273, 2 )

    elif mu == 'v':
        new_value = 'n/a'
        if mytype == 'uint8' and myvalue != ( 1 << 8 ) - 1:
            new_value = myvalue
        elif mytype == 'uint16' and myvalue != ( 1 << 16 ) - 1:
            new_value = round( myvalue * 0.05, 2 )

    elif mu == 'a':
        new_value = 'n/a'
        if mytype == 'uint8':
            new_value = myvalue
        elif mytype == 'uint16' and myvalue != ( 1 << 16 ) - 1:
            new_value = round( ( myvalue * 0.05 ) - 1600 , 2)
        elif mytype == 'uint32' and myvalue != ( 1 << 32 ) - 1:
            new_value = round( ( myvalue * 0.001 ) - 2000000 , 3)

    elif mu == 'hz':
        if mytype == 'uint16' and myvalue != ( 1 << 16 ) - 1:
            new_value = round( myvalue / 128 , 2)

    elif mu == 'sec':
        if mytype == 'uint8' and myvalue > 240 and myvalue < 251:
            new_value = ( ( myvalue - 240 ) + 4 ) * 60
        elif mytype == 'uint16':
            new_value = myvalue * 2

    elif mu == 'bitmap':
        new_value = "{0:08b}".format(myvalue)

    return new_value

def process_Tiffin(topic, payload, previous_values):
    def process_dc_dimmer_status_3(topic,payload):
        lookup_table = {
            mqttOutputTopic + "/DC_DIMMER_STATUS_3/1": "OpenRoad/light/ceiling/state",
            mqttOutputTopic + "/DC_DIMMER_STATUS_3/2": "OpenRoad/light/entry/state",
            mqttOutputTopic + "/DC_DIMMER_STATUS_3/3": "OpenRoad/light/task/state",
            mqttOutputTopic + "/DC_DIMMER_STATUS_3/4": "OpenRoad/light/hall/state",
            mqttOutputTopic + "/DC_DIMMER_STATUS_3/5": "OpenRoad/light/bedroom/state",
            mqttOutputTopic + "/DC_DIMMER_STATUS_3/6": "OpenRoad/light/bathroom/state",
            mqttOutputTopic + "/DC_DIMMER_STATUS_3/8": "OpenRoad/light/floor/state",
            mqttOutputTopic + "/DC_DIMMER_STATUS_3/9": "OpenRoad/light/dinette/state",
            mqttOutputTopic + "/DC_DIMMER_STATUS_3/10": "OpenRoad/light/sconce/state",
            mqttOutputTopic + "/DC_DIMMER_STATUS_3/11": "OpenRoad/light/tvaccent/state",
            mqttOutputTopic + "/DC_DIMMER_STATUS_3/12": "OpenRoad/light/awning/state",
            mqttOutputTopic + "/DC_DIMMER_STATUS_3/93": "OpenRoad/switch/waterpump/state",
            mqttOutputTopic + "/DC_DIMMER_STATUS_3/94": "OpenRoad/light/porch/state",
            mqttOutputTopic + "/DC_DIMMER_STATUS_3/95": "OpenRoad/switch/elecwaterheat/state",
            mqttOutputTopic + "/DC_DIMMER_STATUS_3/96": "OpenRoad/switch/gaswaterheat/state",
            mqttOutputTopic + "/DC_DIMMER_STATUS_3/23": "OpenRoad/vent/galley/state/fan",
            mqttOutputTopic + "/DC_DIMMER_STATUS_3/19": "OpenRoad/vent/bath/state/fan",
        }

        newtopic = lookup_table.get(topic, "UNCHANGED")

        load_status = payload_dict.get('load status')
        if load_status == '01':
            newpayload = "ON"
        elif load_status == '00':
            newpayload = "OFF"

        if topic == mqttOutputTopic + "/DC_DIMMER_STATUS_3/21":
            newtopic = "OpenRoad/vent/galley/state/lid"
            if payload['load status'] == '01':
                newpayload = "OPEN"
        elif topic == mqttOutputTopic + "/DC_DIMMER_STATUS_3/22":
            newtopic = "OpenRoad/vent/galley/state/lid"
            if payload['load status'] == '01':
                newpayload = "CLOSED"
        elif topic == mqttOutputTopic + "/DC_DIMMER_STATUS_3/17":
            newtopic = "OpenRoad/vent/bath/state/lid"
            if payload['load status'] == '01':
                newpayload = "OPEN"
        elif topic == mqttOutputTopic + "/DC_DIMMER_STATUS_3/18":
            newtopic = "OpenRoad/vent/bath/state/lid"
            if payload['load status'] == '01':
                newpayload = "CLOSED"

        return [(newtopic, newpayload)]    

    def process_dc_source_satus_1(topic, payload):
        lookup_table = {
            mqttOutputTopic + "/DC_SOURCE_STATUS_1/1": "OpenRoad/battery/house",
            mqttOutputTopic + "/DC_SOURCE_STATUS_1/2": "OpenRoad/battery/chassis",
        }
        newtopic = lookup_table.get(topic, "UNCHANGED")

        newpayload = payload.get('dc voltage')

        return [(newtopic, newpayload)]

    def process_thermistor(topic, payload):
        lookup_table = {
            mqttOutputTopic + "/THERMOSTAT_AMBIENT_STATUS/0": "OpenRoad/HVAC/front/state/temperature",
            mqttOutputTopic + "/THERMOSTAT_AMBIENT_STATUS/1": "IGNORE",
            mqttOutputTopic + "/THERMOSTAT_AMBIENT_STATUS/2": "OpenRoad/HVAC/rear/state/temperature",
        }
        newtopic = lookup_table.get(topic, topic)

        newpayload = round(payload['ambient temp F'], 1)

        return [(newtopic, newpayload)]
    
    def process_generatorStatus(topic, payload):
        newtopic = "OpenRoad/Generator/Status"

        newpayload = payload['status definition'].upper()

        return [(newtopic, newpayload)]

    def process_thermostat(topic, payload):
        newtopic = "IGNORE"
        newpayload = "IGNORE"
        ## Process Operating Mode
        if topic == mqttOutputTopic + "/THERMOSTAT_STATUS_1/0":
            if payload['operating mode definition'] == "heat":
                newpayload = "ON"
                newtopic = "OpenRoad/HVAC/front/state/auxheat"
            else:
                newtopic = "OpenRoad/HVAC/front/state/mode"
                newpayload = payload['operating mode definition'].upper()
        elif topic == mqttOutputTopic + "/THERMOSTAT_STATUS_1/3":
            if payload['operating mode definition'] == "heat":
                newtopic = "OpenRoad/HVAC/front/state/mode"
                newpayload = "HEAT"
        elif topic == mqttOutputTopic + "/THERMOSTAT_STATUS_1/2":
                newtopic = "OpenRoad/HVAC/rear/state/mode"
                newpayload = payload['operating mode definition'].upper()
        elif topic == mqttOutputTopic + "/THERMOSTAT_STATUS_1/4":
            if payload['operating mode definition'] == "heat":
                newtopic = "OpenRoad/HVAC/rear/state/mode"
                newpayload = "HEAT"
        else:
            newtopic = "IGNORE"
            newpayload = "IGNORE"
        messages.append((newtopic, newpayload))

        ## Process Fan Mode
        lookup_table = {
            mqttOutputTopic + "/THERMOSTAT_STATUS_1/0": "OpenRoad/HVAC/front/state/fan",
            mqttOutputTopic + "/THERMOSTAT_STATUS_1/2": "OpenRoad/HVAC/rear/state/fan",
        }
        newtopic = lookup_table.get(topic, "IGNORE")
        if payload['fan mode definition'] == "auto":
            newpayload = "AUTO"
        elif payload['fan mode definition'] == "on" and payload['fan speed'] == "low":
            newpayload = "LOW"
        elif payload['fan mode definition'] == "on" and payload['fan speed'] == "high":
            newpayload = "HIGH"
        messages.append((newtopic, newpayload))

       ## Fix Condition for Aux Heat - If system is off, Aux Heat is off
        if topic == mqttOutputTopic + "/RVC/THERMOSTAT_STATUS_1/0" and payload['operating mode definition'] == "off":
            newtopic = "OpenRoad/HVAC/front/state/auxheat"
            newpayload = "OFF"
            messages.append((newtopic, newpayload))

        ## Process Setpoint
        lookup_table = {
            mqttOutputTopic + "/THERMOSTAT_STATUS_1/0": "OpenRoad/HVAC/front/state/setpoint",
            mqttOutputTopic + "/THERMOSTAT_STATUS_1/2": "OpenRoad/HVAC/rear/state/setpoint",
        }
        newtopic = lookup_table.get(topic, "IGNORE")
        newpayload = int(round(payload['setpoint temp cool F'],0))
        messages.append((newtopic, newpayload))

        return messages

    def process_tankStatus(topic, payload):
        lookup_table = {
            mqttOutputTopic + "/TANK_STATUS/0": "OpenRoad/Tank/Fresh",
            mqttOutputTopic + "/TANK_STATUS/1": "OpenRoad/Tank/Black",
            mqttOutputTopic + "/TANK_STATUS/2": "OpenRoad/Tank/Grey",
            mqttOutputTopic + "/TANK_STATUS/3": "OpenRoad/Tank/Propane",
        }
        newtopic = lookup_table.get(topic, topic)

        newpayload = int(round(payload['relative level'] / payload['resolution'] * 100, 0))

        return [(newtopic, newpayload)]
    
    messages = []
    payload_dict = json.loads(payload)
    new_topic, new_payload = None, None
    if "DC_DIMMER_STATUS_3" in topic:
        messages.extend(process_dc_dimmer_status_3(topic, payload_dict))
    elif "DC_SOURCE_STATUS_1" in topic:
        messages.extend(process_dc_source_satus_1(topic, payload_dict))
    elif "THERMOSTAT_AMBIENT_STATUS" in topic:
        messages.extend(process_thermistor(topic, payload_dict))
    elif "TANK_STATUS" in topic:
        messages.extend(process_tankStatus(topic, payload_dict)) 
    elif "GENERATOR_STATUS_1" in topic:
        messages.extend(process_generatorStatus(topic, payload_dict))
    elif "THERMOSTAT_STATUS_1" in topic:
        messages.extend(process_thermostat(topic, payload_dict))
     
    for new_topic, new_payload in messages:
        if new_topic != "UNCHANGED":
            if new_topic != "IGNORE":
                if previous_values.get(new_topic) != new_payload:
                    previous_values[new_topic] = new_payload
                else:
                    new_topic = "IGNORE"
            yield new_topic, new_payload

signal.signal(signal.SIGINT, signal_handler)

def main():
    retain=False
    previous_values = {}


    if(mqttOut==2):
        retain=True

    def get_json_line():
        global last_msg_time

        if q.empty():
            return
        json_data = q.get()
        frame = json.loads(json_data)

        arbitration_id = frame['id']
        dlc = frame['dlc']
        data = frame['data']
        
        if debug_level > 0:
            print("{0:f} {1:X} ({2:X}) ".format(arbitration_id, dlc), end='', flush=True)

        try:
            canID = "{0:b}".format(arbitration_id)
            prio = int(canID[0:3], 2)
            dgn = "{0:05X}".format(int(canID[4:21], 2))
            srcAD = "{0:02X}".format(int(canID[24:], 2))
        except Exception as e:
            if debug_level > 0:
                print(f"Failed to parse {frame}: {e}")
        else:
            if debug_level > 0:
                print("DGN: {0:s}, Prio: {1:d}, srcAD: {2:s}, Data: {3:s}".format(
                    dgn, prio, srcAD, ", ".join("{0:02X}".format(x) for x in data)))

            myresult = rvc_decode(dgn, "".join("{0:02X}".format(x) for x in data))

            if screenOut > 0:
                print(json.dumps(myresult))

            if mqttOut:
                topic = mqttOutputTopic + "/" + myresult['name']
                try:
                    topic += "/" + str(myresult['instance'])
                    instance = myresult['instance']
                except:
                    instance = None

                if debug_level:
                    print("Publishing to MQTT topic:", topic)  # Debug print

                # Publish to Home Assistant discovery topics
                if ha_discovery_enabled and ha_discovery:
                    publish_ha_state(mqttc, myresult['name'], instance, myresult, retain)

                # Publish to legacy topics (if enabled)
                if ha_legacy_topics:
                    for newtopic, payload in process_Tiffin(topic, json.dumps(myresult),previous_values):
                        if newtopic == "UNCHANGED":
                            mqtt_safe_publish(mqttc, topic, json.dumps(myresult),retain)
                        elif newtopic != "IGNORE":
                            mqtt_safe_publish(mqttc, newtopic, payload, retain)

    def mainLoop():
        # Use the global mqttc client instead of creating a new one
        mqttc.loop_start()
        try:
            while True:
                get_json_line()
                time.sleep(0.001)
        except KeyboardInterrupt:
            print("Interrupted by user, stopping.")
        finally:
            mqttc.loop_stop()
    mainLoop()

if __name__ == "__main__":


    if mqttOut:
        mqttc = mqtt.Client(CallbackAPIVersion.VERSION2) #create new instance
        mqttc.username_pw_set(mqttUser, mqttPass)
        mqttc.on_connect = on_mqtt_connect
        mqttc.on_subscribe = on_mqtt_subscribe
        mqttc.on_message = on_mqtt_message
        mqttc.on_publish = on_mqtt_publish

        # Set up Home Assistant Discovery if enabled
        if ha_discovery_enabled:
            try:
                print("Loading HA MQTT Discovery mapping from {}...".format(ha_mapping_file))
                ha_discovery = HADiscovery(ha_mapping_file, ha_discovery_prefix)
                print("Loaded {} entities for HA Discovery".format(len(ha_discovery.entities)))

                # Set availability will message (published when we disconnect)
                availability_topic = "{}/status".format(ha_discovery.state_topic_prefix)
                mqttc.will_set(availability_topic, "offline", retain=True, qos=1)
            except Exception as e:
                print("Error loading HA Discovery mapping: {}".format(e))
                ha_discovery = None

        try:
            print("Connecting to MQTT: {0:s}".format(mqttBroker))
            mqttc.connect(mqttBroker, port=1883) #connect to broker

            # Publish HA Discovery messages and availability status
            if ha_discovery:
                print("Publishing HA MQTT Discovery messages...")
                ha_discovery.publish_discovery_messages(mqttc, debug_level)

                # Publish online status
                availability_topic = "{}/status".format(ha_discovery.state_topic_prefix)
                mqttc.publish(availability_topic, "online", retain=True, qos=1)
                print("HA MQTT Discovery complete - entities should appear in Home Assistant")

        except:
            print("MQTT Broker Connection Failed")

    print("Loading RVC Spec file {}.".format(specfile))
    with open(specfile,'r') as specfile:
        try:
            yaml_loader = yaml.YAML()
            spec = yaml_loader.load(specfile)
        except yaml.YAMLError as err:
            print(err)
            exit(1)

    print("Processing start...")

    q = queue.Queue()
    t = TCP_CANWatcher(q)	# Start CAN receive thread
    t.start()

    main()
