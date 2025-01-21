"""CWA Weather Integration for Home Assistant."""
import logging
import asyncio
import re
from random import randrange
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from .coordinator import CWAWeatherCoordinator
from .const import (
    DOMAIN,
    ATTRIBUTION,
    MANUFACTURER,
    MODEL_NAME,
    HOME_URL,
    CONF_API_KEY,
    CONF_LOCATION,
    # CONF_NAME,
    SELECT_ITEM_TRACK_REGEX,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    print(f"async_setup {config}")
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    # await _async_migrate_unique_ids(hass, entry)

    api_key = config_entry.data.get(CONF_API_KEY)
    location = config_entry.data.get(CONF_LOCATION)

    print(f"async_setup_entry {location}")

    name = location
    if m := re.match(SELECT_ITEM_TRACK_REGEX, name):
        name = m[1]
        location = m[2]

    coordinator = CWAWeatherCoordinator(hass, api_key, location)
    coordinator.device_info = DeviceInfo(
        name=name,
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, config_entry.entry_id)},
        manufacturer=MANUFACTURER,
        model=MODEL_NAME,
        configuration_url=HOME_URL,
    )
    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    await asyncio.sleep(randrange(0, 2))
    _LOGGER.info("'%s' '%s' '%s'", api_key, name, location)
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(config_entry, [Platform.WEATHER, Platform.SENSOR])

    config_entry.async_on_unload(config_entry.add_update_listener(_async_update_entry))
    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(config_entry, [Platform.WEATHER, Platform.SENSOR])

async def _async_update_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    await hass.config_entries.async_reload(config_entry.entry_id)
