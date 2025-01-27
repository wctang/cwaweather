import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.typing import StateType
from homeassistant.components.air_quality import AirQualityEntity

from .const import (
    DOMAIN,
    ATTRIBUTION_MOENV,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = config_entry.runtime_data
    async_add_entities([MOENVAQIAirQualityEntity(coordinator)], False)

class MOENVAQIAirQualityEntity(CoordinatorEntity, AirQualityEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_attribution = ATTRIBUTION_MOENV

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = coordinator.config_entry.entry_id
        self._aqi_data = self.coordinator.data.aqi_station

    def _handle_coordinator_update(self) -> None:
        if self._aqi_data != self.coordinator.data.aqi_station:
            self._aqi_data = self.coordinator.data.aqi_station
            _LOGGER.debug(f"Updating {self.coordinator.name} aqi data")
            self.async_write_ha_state()

    @property
    def air_quality_index(self) -> StateType:
        return self._aqi_data.aqi

    @property
    def particulate_matter_2_5(self) -> StateType:
        return self._aqi_data.pm2_5

    @property
    def particulate_matter_10(self) -> StateType:
        return self._aqi_data.pm10

    @property
    def ozone(self) -> StateType:
        return self._aqi_data.o3

    @property
    def carbon_monoxide(self) -> StateType:
        return self._aqi_data.co

    @property
    def sulphur_dioxide(self) -> StateType:
        return self._aqi_data.so2

    @property
    def state(self) -> StateType:
        return self._aqi_data.status

    @property
    def unit_of_measurement(self) -> str:
        return None
