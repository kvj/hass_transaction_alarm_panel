from __future__ import annotations
from .constants import DOMAIN, PLATFORMS

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

import logging

_LOGGER = logging.getLogger(__name__)

#   // "mqtt": ["homeassistant/sensor/+/action_transaction/config"],

# async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
#     data = entry.as_dict()['data']
#     _LOGGER.debug(f"async_setup_entry: {data}")
#     for p in PLATFORMS:
#         hass.async_create_task(
#             hass.config_entries.async_forward_entry_setup(entry, p)
#         )
#     return True


# async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
#     for p in PLATFORMS:
#         await hass.config_entries.async_forward_entry_unload(entry, p)
#     # hass.data[DOMAIN]['devices'].pop(entry.entry_id)
#     return True


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data[DOMAIN] = dict()

    return True
