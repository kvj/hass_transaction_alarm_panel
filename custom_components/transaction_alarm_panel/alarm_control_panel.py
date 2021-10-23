
from .constants import DOMAIN
import copy
import json
import logging
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.alarm_control_panel.const import (
    SUPPORT_ALARM_ARM_AWAY,
    SUPPORT_ALARM_ARM_HOME,
    SUPPORT_ALARM_ARM_NIGHT,
    SUPPORT_ALARM_TRIGGER,
)
import homeassistant.components.manual.alarm_control_panel as manual

from homeassistant.components import mqtt
from homeassistant.const import (
    CONF_CODE,
    CONF_DISARM_AFTER_TRIGGER,
    CONF_NAME,
    CONF_PLATFORM,
    CONF_DELAY_TIME,
    CONF_ARMING_TIME,
    CONF_TRIGGER_TIME,

    STATE_ALARM_DISARMED,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_TRIGGERED,
    STATE_ALARM_ARMING,
    STATE_ALARM_PENDING
)

CONF_ARM_CODES = "arm_codes"
CONF_DISARM_CODES = "disarm_codes"


_LOGGER = logging.getLogger(__name__)

CONF_MQTT_TOPIC = "mqtt_state_topic"

STATE_MAPPING = {
    STATE_ALARM_DISARMED: "disarm",
    STATE_ALARM_ARMED_AWAY: "arm_all_zones",
    STATE_ALARM_ARMED_HOME: "arm_day_zones",
    STATE_ALARM_ARMED_NIGHT: "arm_night_zones",
    STATE_ALARM_ARMING: "entry_delay",
    STATE_ALARM_PENDING: "exit_delay",
    STATE_ALARM_TRIGGERED: "arm_all_zones",
}


def _state_validator(config):
    """Validate the state."""
    config = copy.deepcopy(config)
    for state in manual.SUPPORTED_PRETRIGGER_STATES:
        config[state] = {}
    return manual._state_validator(config)


PLATFORM_SCHEMA = vol.Schema(
    vol.All(
        {
            vol.Required(CONF_PLATFORM): "transaction_alarm_panel",
            vol.Required(CONF_NAME): cv.string,
            vol.Required(CONF_MQTT_TOPIC): cv.string,
            vol.Exclusive(CONF_CODE, "code validation"): cv.string,
            vol.Exclusive(manual.CONF_CODE_TEMPLATE, "code validation"): cv.template,
            vol.Optional(manual.CONF_CODE_ARM_REQUIRED, default=True): cv.boolean,
            vol.Optional(CONF_DELAY_TIME, default=manual.DEFAULT_DELAY_TIME): vol.All(
                cv.time_period, cv.positive_timedelta
            ),
            vol.Optional(CONF_ARMING_TIME, default=manual.DEFAULT_ARMING_TIME): vol.All(
                cv.time_period, cv.positive_timedelta
            ),
            vol.Optional(CONF_TRIGGER_TIME, default=manual.DEFAULT_TRIGGER_TIME): vol.All(
                cv.time_period, cv.positive_timedelta
            ),
            vol.Optional(
                CONF_DISARM_AFTER_TRIGGER, default=manual.DEFAULT_DISARM_AFTER_TRIGGER
            ): cv.boolean,
            vol.Optional(CONF_ARM_CODES, default={}): dict,
            vol.Optional(CONF_DISARM_CODES, default={}): dict,
            vol.Optional(STATE_ALARM_ARMED_AWAY, default={}): manual._state_schema(
                STATE_ALARM_ARMED_AWAY
            ),
            vol.Optional(STATE_ALARM_ARMED_HOME, default={}): manual._state_schema(
                STATE_ALARM_ARMED_HOME
            ),
            vol.Optional(STATE_ALARM_ARMED_NIGHT, default={}): manual._state_schema(
                STATE_ALARM_ARMED_NIGHT
            ),
            vol.Optional(STATE_ALARM_DISARMED, default={}): manual._state_schema(
                STATE_ALARM_DISARMED
            ),
            vol.Optional(STATE_ALARM_TRIGGERED, default={}): manual._state_schema(
                STATE_ALARM_TRIGGERED
            ),
        },
        _state_validator,
    )
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    add_entities([AlarmPanel(hass, config)])


class AlarmPanel(manual.ManualAlarm):

    def __init__(
        self,
        hass,
        config,

    ) -> None:
        super().__init__(
            hass,
            config[CONF_NAME],
            config.get(CONF_CODE),
            config.get(manual.CONF_CODE_TEMPLATE),
            config.get(manual.CONF_CODE_ARM_REQUIRED),
            config.get(CONF_DISARM_AFTER_TRIGGER,
                       manual.DEFAULT_DISARM_AFTER_TRIGGER),
            config,
        )
        self._arm_codes = config.get(CONF_ARM_CODES)
        self._disarm_codes = config.get(CONF_DISARM_CODES)
        self._last_code_id = None
        self.mqtt_topic = config[CONF_MQTT_TOPIC]

    @property
    def extra_state_attributes(self):
        values = copy.copy(super().extra_state_attributes)
        values["last_code_id"] = self._last_code_id
        return values

    def _validate_code(self, code, state):
        self._last_code_id = None
        codes = self._disarm_codes if state == STATE_ALARM_DISARMED else self._arm_codes
        for key, value in codes.items():
            if value == code:
                _LOGGER.debug(f"Found code in dictionary: {key}")
                self._last_code_id = key
                return True
        return super()._validate_code(code, state)

    async def _process_state(self, state, code, transaction):
        _LOGGER.debug(f"_process_state: {state}, {code}, {transaction}")
        await self._send_state(transaction, state_override=state)
        mapping = {
            "disarm": ({STATE_ALARM_DISARMED}, self.async_alarm_disarm),
            "arm_day_zones": ({STATE_ALARM_ARMING, STATE_ALARM_ARMED_HOME}, self.async_alarm_arm_home),
            "arm_night_zones": ({STATE_ALARM_ARMING, STATE_ALARM_ARMED_NIGHT}, self.async_alarm_arm_night),
            "arm_all_zones": ({STATE_ALARM_ARMING, STATE_ALARM_ARMED_AWAY}, self.async_alarm_arm_away)
        }
        expected_states, fn = mapping.get(state, (None, None))
        if not expected_states:
            _LOGGER.warning(f"Invalid incoming state: {state}")
            return
        await fn(code)
        if self.state not in expected_states:
            _LOGGER.warning(
                f"Unexpected state: {self.state} - {expected_states}")
            await self._send_state(
                state_override="invalid_code"
            )

    def _make_state_subscribe(self):
        async def callback(message):
            payload = json.loads(message.payload)
            _LOGGER.debug(f"State: {payload}")
            transaction = payload.get("action_transaction")
            if not transaction:
                return
            await self._process_state(
                payload.get("action"),
                payload.get("action_code"),
                transaction
            )
        return callback

    async def _send_alarm_state(self):
        await self._send_state()

    async def _send_state(self, transaction=None, state_override=None):
        topic = "%s/set" % (self.mqtt_topic)
        state = STATE_MAPPING.get(self.state)
        if state_override:
            state = state_override
        if not state:
            _LOGGER.warning(
                f"Ignoring state: {self._active_state} - {self.state}")
            return
        payload = dict(arm_mode=dict(mode=state))
        if transaction:
            payload["arm_mode"]["transaction"] = transaction
        _LOGGER.debug(
            f"Sending state: {payload} - {self.state}, {self._active_state}")
        mqtt.async_publish(self.hass, topic, json.dumps(payload))

    async def _subscribe(self, hass):
        await mqtt.async_subscribe(hass, self.mqtt_topic, self._make_state_subscribe())

    @property
    def supported_features(self):
        return SUPPORT_ALARM_ARM_AWAY | SUPPORT_ALARM_ARM_HOME | SUPPORT_ALARM_ARM_NIGHT | SUPPORT_ALARM_TRIGGER

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        await self._subscribe(self.hass)
        _LOGGER.debug(
            f"async_added_to_hass: {self._state}, {self.state}, {self._active_state}")

    def _async_write_ha_state(self):
        super()._async_write_ha_state()
        _LOGGER.debug(
            f"_async_write_ha_state: {self.state} - {self._active_state}")
        self.hass.add_job(self._send_alarm_state())
