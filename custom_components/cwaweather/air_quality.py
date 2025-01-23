from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.components import air_quality

from .const import (
    DOMAIN,
    ATTRIBUTION,
)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([MOENVAQIAirQualityEntity(coordinator)], False)

class MOENVAQIAirQualityEntity(air_quality.AirQualityEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_attribution = ATTRIBUTION
    _attr_should_poll = False

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.entry_id}-aqi"

    @property
    def state(self) -> StateType:
        return self.air_quality_index

    @property
    def air_quality_index(self) -> StateType:
        return self.coordinator.data.aqi_station.aqi

    @property
    def particulate_matter_2_5(self) -> StateType:
        return self.coordinator.data.aqi_station.pm2_5

    @property
    def particulate_matter_10(self) -> StateType:
        return self.coordinator.data.aqi_station.pm10

    @property
    def ozone(self) -> StateType:
        return self.coordinator.data.aqi_station.o3

    @property
    def carbon_monoxide(self) -> StateType:
        return self.coordinator.data.aqi_station.co

    @property
    def sulphur_dioxide(self) -> StateType:
        return self.coordinator.data.aqi_station.so2
