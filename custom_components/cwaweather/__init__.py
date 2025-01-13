"""CWA Weather Integration for Home Assistant."""

from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.config_entries import ConfigEntry
# from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    # await _async_migrate_unique_ids(hass, entry)

    await hass.config_entries.async_forward_entry_setups(config_entry, [Platform.WEATHER])

    config_entry.async_on_unload(config_entry.add_update_listener(_async_update_entry))
    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(config_entry, [Platform.WEATHER])

async def _async_update_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    await hass.config_entries.async_reload(config_entry.entry_id)
