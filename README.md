## hass_transaction_alarm_panel
Alarm Control Panel component for Zigbee Keypads using `action_transaction` field. Works together with zigbee2mqtt

### Supported devices:

Devices using `action_transaction` state field: [See all devices on zigbee2mqtt.io](https://www.zigbee2mqtt.io/information/supported_devices.html#e=action_transaction)

### Installation
Usig HACS, add custom repository (integration) and install the component

### Configuration

As the code is based on the [`manual`](https://www.home-assistant.io/integrations/manual/) alarm control panel platform, the behaviour and the configuration is very similar to the original one:

Add to your `configuration.yaml`:

```yaml
alarm_control_panel:
  - platform: transaction_alarm_panel # Required
    name: Home Alarm # Required
    code: "1234" # Common arm/disarm code 
    code_arm_required: false # Set to true, if needed
    arming_time: 10 # See the original configuration
    delay_time: 20
    mqtt_state_topic: "zigbee2mqtt/Alarm Keypad" # Required: MQTT topic of your Zigbee2mqtt keypad
    disarm_codes: # Optional: new feature - additional disarm codes
      secret: "4321"
    arm_codes: # Same as above, for arming
      easy: "0000"
```

### Additional codes:

When the feature above is being used, the name of the code is exposed as an additional state attribute `last_code_id`
