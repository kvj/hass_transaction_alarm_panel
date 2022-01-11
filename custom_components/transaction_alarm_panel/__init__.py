from __future__ import annotations
from .constants import DOMAIN, PLATFORMS

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data[DOMAIN] = dict()

    return True
