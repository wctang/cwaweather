import logging
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any
from collections.abc import Callable
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntityDescription, SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE
from .coordinator import CWAWeatherCoordinator, CWAWeatherData
from .const import (
    DOMAIN,
    ATTRIBUTION,
)

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True, kw_only=True)
class CWAWeatherSensorEntityDescription(SensorEntityDescription):
    native_value_fn: Callable[[CWAWeatherData], float | None]

SENSOR_TYPES: tuple[CWAWeatherSensorEntityDescription, ...] = (
    CWAWeatherSensorEntityDescription(
        key="temperature",
        # name="Temperature",
        native_value_fn=lambda data: data.native_temperature,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=CWAWeatherCoordinator._attr_native_temperature_unit
    ),
    CWAWeatherSensorEntityDescription(
        key="humidity",
        # name="Humidity",
        native_value_fn=lambda data: data.humidity,
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE
    ),
)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([CWAWeatherSensorEntity(coordinator, description) for description in SENSOR_TYPES], False)


class CWAWeatherSensorEntity(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: CWAWeatherCoordinator, description: CWAWeatherSensorEntityDescription):
        super().__init__(coordinator)
        self.entity_description = description
        # self._attr_name = description.name
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}-{description.key}"
        self._attr_native_value = self.entity_description.native_value_fn(self.coordinator.data)

    def _handle_coordinator_update(self) -> None:
        if (val := self.entity_description.native_value_fn(self.coordinator.data)) != self._attr_native_value:
            print(f"Updating sensor {self.coordinator.name} {self.entity_description.key} from {self._attr_native_value} to {val}")
            self._attr_native_value = val
            self.async_write_ha_state()
