# Home Assistant Automation Examples

Real-world automation examples for controlling your RV via MQTT.

## Table of Contents
- [Lighting Automations](#lighting-automations)
- [Climate Control](#climate-control)
- [Energy Management](#energy-management)
- [Security & Safety](#security--safety)
- [Convenience Automations](#convenience-automations)
- [Advanced Scenes](#advanced-scenes)

---

## Lighting Automations

### Auto Evening Lights

Automatically dim lights at sunset for comfortable evening ambiance.

```yaml
automation:
  - alias: "RV Evening Lights"
    description: "Dim lights to 40% at sunset"
    trigger:
      - platform: sun
        event: sunset
        offset: "-00:30:00"  # 30 min before sunset
    action:
      - service: mqtt.publish
        data:
          topic: "rv/light/ceiling_light/brightness/set"
          payload: "40"
      - delay: 1
      - service: mqtt.publish
        data:
          topic: "rv/light/kitchen_light/brightness/set"
          payload: "30"
```

### Motion-Activated Lights

Turn on lights when motion detected, turn off after delay.

```yaml
automation:
  - alias: "RV Bathroom Light Motion"
    description: "Turn on bathroom light with motion"
    trigger:
      - platform: state
        entity_id: binary_sensor.bathroom_motion
        to: "on"
    action:
      - service: mqtt.publish
        data:
          topic: "rv/light/bathroom_light/set"
          payload: "ON"
      - wait_for_trigger:
          - platform: state
            entity_id: binary_sensor.bathroom_motion
            to: "off"
            for: "00:02:00"  # 2 minutes no motion
      - service: mqtt.publish
        data:
          topic: "rv/light/bathroom_light/set"
          payload: "OFF"
```

### Bedtime Lights

Gradual dimming sequence for bedtime.

```yaml
script:
  rv_bedtime_lights:
    alias: "Bedtime Light Sequence"
    sequence:
      # Dim to 50%
      - service: mqtt.publish
        data:
          topic: "rv/light/bedroom_light/brightness/set"
          payload: "50"
      - delay: 300  # Wait 5 minutes

      # Dim to 20%
      - service: mqtt.publish
        data:
          topic: "rv/light/bedroom_light/brightness/set"
          payload: "20"
      - delay: 300  # Wait 5 minutes

      # Turn off
      - service: mqtt.publish
        data:
          topic: "rv/light/bedroom_light/set"
          payload: "OFF"

# Trigger with button or voice command
automation:
  - alias: "RV Bedtime Button"
    trigger:
      - platform: state
        entity_id: input_boolean.bedtime_mode
        to: "on"
    action:
      - service: script.rv_bedtime_lights
```

### Low Battery Emergency Lights

Turn off non-essential lights when battery low.

```yaml
automation:
  - alias: "RV Low Battery Light Shutoff"
    description: "Turn off non-essential lights at 30% battery"
    trigger:
      - platform: numeric_state
        entity_id: sensor.rv_battery_level
        below: 30
    action:
      - service: mqtt.publish
        data:
          topic: "rv/light/accent_lights/set"
          payload: "OFF"
      - delay: 1
      - service: mqtt.publish
        data:
          topic: "rv/light/outdoor_lights/set"
          payload: "OFF"
      - service: notify.mobile_app
        data:
          message: "RV battery low - non-essential lights turned off"
```

---

## Climate Control

### Smart Thermostat Schedule

Adjust temperature based on time of day and occupancy.

```yaml
automation:
  # Morning warmup
  - alias: "RV Morning Warmup"
    trigger:
      - platform: time
        at: "06:30:00"
    condition:
      - condition: numeric_state
        entity_id: sensor.rv_interior_temp
        below: 65
    action:
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/mode/set"
          payload: "heat"
      - delay: 1
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/temperature/set"
          payload: "70"

  # Daytime comfort
  - alias: "RV Daytime Climate"
    trigger:
      - platform: time
        at: "09:00:00"
    action:
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/temperature/set"
          payload: "72"

  # Night cooldown
  - alias: "RV Night Cooldown"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/temperature/set"
          payload: "68"
      - delay: 1
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/fan_mode/set"
          payload: "low"
```

### Weather-Based Climate

Automatically switch between heat/cool based on weather.

```yaml
automation:
  - alias: "RV Auto Heat/Cool"
    description: "Switch HVAC mode based on outside temperature"
    trigger:
      - platform: numeric_state
        entity_id: sensor.outside_temperature
        above: 75
        for: "00:15:00"
      - platform: numeric_state
        entity_id: sensor.outside_temperature
        below: 60
        for: "00:15:00"
    action:
      - choose:
          # Hot weather - switch to cool
          - conditions:
              - condition: numeric_state
                entity_id: sensor.outside_temperature
                above: 75
            sequence:
              - service: mqtt.publish
                data:
                  topic: "rv/climate/hvac_front/mode/set"
                  payload: "cool"
              - delay: 1
              - service: mqtt.publish
                data:
                  topic: "rv/climate/hvac_front/temperature/set"
                  payload: "72"

          # Cold weather - switch to heat
          - conditions:
              - condition: numeric_state
                entity_id: sensor.outside_temperature
                below: 60
            sequence:
              - service: mqtt.publish
                data:
                  topic: "rv/climate/hvac_front/mode/set"
                  payload: "heat"
              - delay: 1
              - service: mqtt.publish
                data:
                  topic: "rv/climate/hvac_front/temperature/set"
                  payload: "70"
```

### Departure Preparation

Pre-heat or pre-cool RV before departure.

```yaml
script:
  rv_departure_prep:
    alias: "RV Departure Climate Prep"
    sequence:
      # Turn on climate
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/mode/set"
          payload: >
            {% if states('sensor.outside_temperature')|float > 75 %}
              cool
            {% else %}
              heat
            {% endif %}
      - delay: 1

      # Set comfortable temperature
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/temperature/set"
          payload: "72"
      - delay: 1

      # Set fan to high for quick temp change
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/fan_mode/set"
          payload: "high"

      # Notify when ready
      - delay: 900  # 15 minutes
      - service: notify.mobile_app
        data:
          message: "RV climate ready for departure"

      # Return fan to auto
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/fan_mode/set"
          payload: "auto"

# Trigger 30 minutes before planned departure
automation:
  - alias: "RV Prep Before Calendar Event"
    trigger:
      - platform: calendar
        entity_id: calendar.rv_trips
        event: start
        offset: "-00:30:00"
    action:
      - service: script.rv_departure_prep
```

---

## Energy Management

### Shore Power Connected

Adjust power usage based on shore power availability.

```yaml
automation:
  - alias: "RV Shore Power Connected"
    description: "Enable high-power devices when on shore power"
    trigger:
      - platform: state
        entity_id: binary_sensor.shore_power
        to: "on"
    action:
      # Enable water heater
      - service: mqtt.publish
        data:
          topic: "rv/switch/water_heater/set"
          payload: "ON"
      - delay: 1

      # Set climate to normal operation
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/mode/set"
          payload: "auto"

      - service: notify.mobile_app
        data:
          message: "Shore power connected - full power mode enabled"

  - alias: "RV Shore Power Disconnected"
    description: "Reduce power usage when on battery"
    trigger:
      - platform: state
        entity_id: binary_sensor.shore_power
        to: "off"
    action:
      # Disable water heater
      - service: mqtt.publish
        data:
          topic: "rv/switch/water_heater/set"
          payload: "OFF"
      - delay: 1

      # Set HVAC to efficient mode
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/fan_mode/set"
          payload: "low"

      - service: notify.mobile_app
        data:
          message: "Running on battery - conservation mode enabled"
```

### Generator Auto-Start

Start generator when battery low and not on shore power.

```yaml
automation:
  - alias: "RV Auto-Start Generator"
    description: "Start generator at 40% battery if not on shore power"
    trigger:
      - platform: numeric_state
        entity_id: sensor.rv_battery_level
        below: 40
    condition:
      - condition: state
        entity_id: binary_sensor.shore_power
        state: "off"
      - condition: state
        entity_id: binary_sensor.generator_running
        state: "off"
    action:
      - service: mqtt.publish
        data:
          topic: "rv/switch/generator/set"
          payload: "ON"
      - service: notify.mobile_app
        data:
          message: "Battery low ({{ states('sensor.rv_battery_level') }}%) - starting generator"

  - alias: "RV Auto-Stop Generator"
    description: "Stop generator at 90% battery"
    trigger:
      - platform: numeric_state
        entity_id: sensor.rv_battery_level
        above: 90
    condition:
      - condition: state
        entity_id: binary_sensor.generator_running
        state: "on"
      - condition: state
        entity_id: binary_sensor.shore_power
        state: "off"
    action:
      - service: mqtt.publish
        data:
          topic: "rv/switch/generator/set"
          payload: "OFF"
      - service: notify.mobile_app
        data:
          message: "Battery charged ({{ states('sensor.rv_battery_level') }}%) - stopping generator"
```

---

## Security & Safety

### Propane Leak Detection

Turn off appliances and alert if propane detected.

```yaml
automation:
  - alias: "RV Propane Leak Alert"
    description: "Emergency shutdown on propane detection"
    trigger:
      - platform: state
        entity_id: binary_sensor.propane_detector
        to: "on"
    action:
      # Turn off all gas appliances
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/mode/set"
          payload: "off"
      - service: mqtt.publish
        data:
          topic: "rv/switch/water_heater/set"
          payload: "OFF"
      - service: mqtt.publish
        data:
          topic: "rv/switch/stove/set"
          payload: "OFF"

      # Turn on ventilation
      - service: mqtt.publish
        data:
          topic: "rv/switch/vent_fan/set"
          payload: "ON"

      # Alert immediately
      - service: notify.mobile_app
        data:
          message: "PROPANE LEAK DETECTED - Gas appliances shut off"
          title: "RV EMERGENCY"
          data:
            priority: high
            ttl: 0
            sound: alarm.mp3
```

### Away Mode

Enhanced security when RV is unoccupied.

```yaml
script:
  rv_away_mode:
    alias: "RV Away Mode"
    sequence:
      # Turn off all lights
      - service: mqtt.publish
        data:
          topic: "rv/light/ceiling_light/set"
          payload: "OFF"
      - delay: 1
      - service: mqtt.publish
        data:
          topic: "rv/light/bedroom_light/set"
          payload: "OFF"
      - delay: 1

      # Set HVAC to away temperature
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/temperature/set"
          payload: "60"  # Prevent freezing
      - delay: 1

      # Turn off water pump
      - service: mqtt.publish
        data:
          topic: "rv/switch/water_pump/set"
          payload: "OFF"

      # Enable motion alerts
      - service: input_boolean.turn_on
        target:
          entity_id: input_boolean.rv_motion_alerts

automation:
  - alias: "RV Motion Alert When Away"
    trigger:
      - platform: state
        entity_id: binary_sensor.rv_motion
        to: "on"
    condition:
      - condition: state
        entity_id: input_boolean.rv_away_mode
        state: "on"
    action:
      # Turn on lights
      - service: mqtt.publish
        data:
          topic: "rv/light/outdoor_lights/set"
          payload: "ON"

      # Alert owner
      - service: notify.mobile_app
        data:
          message: "Motion detected in RV while in away mode!"
          data:
            actions:
              - action: "view_camera"
                title: "View Camera"
```

---

## Convenience Automations

### Morning Routine

Automated morning sequence.

```yaml
automation:
  - alias: "RV Morning Routine"
    trigger:
      - platform: time
        at: "07:00:00"
    condition:
      - condition: state
        entity_id: binary_sensor.rv_occupied
        state: "on"
    action:
      # Warm up climate
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/mode/set"
          payload: "heat"
      - delay: 1
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/temperature/set"
          payload: "70"
      - delay: 1

      # Turn on water heater
      - service: mqtt.publish
        data:
          topic: "rv/switch/water_heater/set"
          payload: "ON"
      - delay: 1

      # Gradual light brightening
      - service: mqtt.publish
        data:
          topic: "rv/light/bedroom_light/brightness/set"
          payload: "20"
      - delay: 300  # 5 minutes
      - service: mqtt.publish
        data:
          topic: "rv/light/bedroom_light/brightness/set"
          payload: "50"
      - delay: 300  # 5 minutes
      - service: mqtt.publish
        data:
          topic: "rv/light/bedroom_light/brightness/set"
          payload: "100"
```

### Automatic Tank Monitoring

Monitor and alert on tank levels.

```yaml
automation:
  - alias: "RV Fresh Water Low"
    trigger:
      - platform: numeric_state
        entity_id: sensor.rv_fresh_water_level
        below: 25
    action:
      - service: notify.mobile_app
        data:
          message: "Fresh water tank at {{ states('sensor.rv_fresh_water_level') }}% - refill soon"

  - alias: "RV Black Tank Full"
    trigger:
      - platform: numeric_state
        entity_id: sensor.rv_black_tank_level
        above: 75
    action:
      - service: notify.mobile_app
        data:
          message: "Black tank at {{ states('sensor.rv_black_tank_level') }}% - dump soon"
          data:
            priority: high
```

### Slide-Out Climate Control

Adjust HVAC when slides extended.

```yaml
automation:
  - alias: "RV Slides Extended - Boost Climate"
    description: "Increase fan speed when slides extended (more volume)"
    trigger:
      - platform: state
        entity_id: binary_sensor.rv_slide_out
        to: "on"
    action:
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/fan_mode/set"
          payload: "high"
      - delay: 300  # Run high for 5 minutes
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/fan_mode/set"
          payload: "auto"

  - alias: "RV Slides Retracted - Normal Climate"
    trigger:
      - platform: state
        entity_id: binary_sensor.rv_slide_out
        to: "off"
    action:
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/fan_mode/set"
          payload: "auto"
```

---

## Advanced Scenes

### Movie Night Scene

```yaml
script:
  rv_movie_night:
    alias: "Movie Night Scene"
    sequence:
      # Dim main lights
      - service: mqtt.publish
        data:
          topic: "rv/light/ceiling_light/brightness/set"
          payload: "10"
      - delay: 1

      # Turn on accent lights
      - service: mqtt.publish
        data:
          topic: "rv/light/accent_lights/set"
          payload: "ON"
      - delay: 1
      - service: mqtt.publish
        data:
          topic: "rv/light/accent_lights/brightness/set"
          payload: "30"
      - delay: 1

      # Set comfortable climate
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/temperature/set"
          payload: "70"
      - delay: 1
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/fan_mode/set"
          payload: "low"  # Quiet for movie
```

### Dinner Party Scene

```yaml
script:
  rv_dinner_party:
    alias: "Dinner Party Scene"
    sequence:
      # Bright dining area
      - service: mqtt.publish
        data:
          topic: "rv/light/dining_light/brightness/set"
          payload: "100"
      - delay: 1

      # Dim bedroom lights
      - service: mqtt.publish
        data:
          topic: "rv/light/bedroom_light/brightness/set"
          payload: "20"
      - delay: 1

      # Comfortable temperature
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/temperature/set"
          payload: "72"
      - delay: 1

      # Good air circulation
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/fan_mode/set"
          payload: "auto"
```

### Stormy Weather Mode

```yaml
automation:
  - alias: "RV Storm Mode"
    description: "Prepare for severe weather"
    trigger:
      - platform: state
        entity_id: weather.home
        attribute: condition
        to: "lightning-rainy"
    action:
      # Bring in slides (if automated)
      - service: cover.close_cover
        target:
          entity_id: cover.rv_slide_out

      # Turn on interior lights
      - service: mqtt.publish
        data:
          topic: "rv/light/ceiling_light/set"
          payload: "ON"
      - delay: 1

      # Turn off outdoor lights
      - service: mqtt.publish
        data:
          topic: "rv/light/outdoor_lights/set"
          payload: "OFF"
      - delay: 1

      # Set HVAC to recirculate
      - service: mqtt.publish
        data:
          topic: "rv/climate/hvac_front/fan_mode/set"
          payload: "auto"

      # Alert
      - service: notify.mobile_app
        data:
          message: "Storm detected - RV prepped for weather"
```

---

## Tips & Best Practices

### 1. Add Delays Between Commands
Always add 1-second delays between MQTT commands:
```yaml
- service: mqtt.publish
  data: { topic: "rv/light/ceiling_light/set", payload: "ON" }
- delay: 1  # IMPORTANT!
- service: mqtt.publish
  data: { topic: "rv/light/floor_lamp/set", payload: "ON" }
```

### 2. Use Conditions to Prevent Conflicts
Check current state before sending commands:
```yaml
condition:
  - condition: state
    entity_id: binary_sensor.shore_power
    state: "on"  # Only run if on shore power
```

### 3. Handle Command Failures
Monitor error topic and retry:
```yaml
automation:
  - alias: "RV Command Retry"
    trigger:
      - platform: mqtt
        topic: "rv/command/error"
    action:
      - delay: 2
      - service: mqtt.publish
        data:
          topic: "{{ trigger.payload_json.command_topic }}"
          payload: "{{ trigger.payload_json.command_value }}"
```

### 4. Group Related Commands
Use scripts for multi-step sequences:
```yaml
script:
  rv_shutdown_sequence:
    sequence:
      - [Turn off lights]
      - delay: 1
      - [Turn off climate]
      - delay: 1
      - [Turn off pumps]
```

### 5. Test Automations Safely
Use input_booleans for testing:
```yaml
condition:
  - condition: state
    entity_id: input_boolean.rv_automation_enabled
    state: "on"
```

---

## More Examples

For additional automation ideas, see:
- [Command Format Guide](COMMAND_FORMAT.md) - MQTT command reference
- [Phase 2 Architecture](PHASE2_ARCHITECTURE.md) - System capabilities
- Home Assistant Community Forums - RV automation category
