import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components import weather
from homeassistant.components import sensor
from homeassistant.const import PERCENTAGE
from .const import (
    DOMAIN,
    ATTRIBUTION,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([CWAWeatherSensorEntity(coordinator, config_entry, type) for type in ["temperature", "humidity"]], False)

class CWAWeatherSensorEntity(sensor.SensorEntity):
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator, config, type):
        self.coordinator = coordinator
        self.type = type
        self._attr_device_info = coordinator.device_info
        if self.type == "temperature":
            self._attr_name = "Temperature"
            self._attr_unique_id = f"{config.entry_id}-temperature"
        elif self.type == "humidity":
            self._attr_name = "Humidity"
            self._attr_unique_id = f"{config.entry_id}-humidity"

    @property
    def device_class(self):
        if self.type == "temperature":
            return sensor.SensorDeviceClass.TEMPERATURE
        elif self.type == "humidity":
            return sensor.SensorDeviceClass.HUMIDITY

    @property
    def native_value(self):
        if self.type == "temperature":
            return self.coordinator.data.get(weather.ATTR_FORECAST_NATIVE_TEMP)
        elif self.type == "humidity":
            return self.coordinator.data.get(weather.ATTR_FORECAST_HUMIDITY)

    @property
    def native_unit_of_measurement(self):
        if self.type == "temperature":
            return self.coordinator._attr_native_temperature_unit
        elif self.type == "humidity":
            return PERCENTAGE

    @property
    def state_class(self):
        return sensor.SensorStateClass.MEASUREMENT
