"""CWA Weather Integration for Home Assistant."""
# import logging
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv
from .coordinator import CWAWeatherCoordinator
from .const import (
    DOMAIN,
)

# _LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.WEATHER, Platform.SENSOR, Platform.AIR_QUALITY]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    coordinator = CWAWeatherCoordinator(hass, config_entry)
    config_entry.runtime_data = coordinator

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    config_entry.async_on_unload(config_entry.add_update_listener(_async_update_entry))
    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)

async def _async_update_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    await hass.config_entries.async_reload(config_entry.entry_id)
