import logging
from dataclasses import dataclass
from typing import Any
from collections.abc import Callable
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntityDescription, SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, CONCENTRATION_PARTS_PER_MILLION
from .coordinator import CWAWeatherCoordinator, CWAWeatherData
from .const import (
    DOMAIN,
    ATTRIBUTION_CWA,
    ATTRIBUTION_MOENV,
)

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True, kw_only=True)
class CommonSensorEntityDescription(SensorEntityDescription):
    native_value_fn: Callable[[CWAWeatherData], float | None]

SENSOR_TYPES: tuple[CommonSensorEntityDescription, ...] = (
    CommonSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        native_value_fn=lambda data: data.native_temperature,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=CWAWeatherCoordinator.native_temperature_unit,
    ),
    CommonSensorEntityDescription(
        key="apparent_temperature",
        translation_key="apparent_temperature",
        native_value_fn=lambda data: data.native_apparent_temperature,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=CWAWeatherCoordinator.native_temperature_unit,
        entity_registry_enabled_default=False,
    ),
    CommonSensorEntityDescription(
        key="humidity",
        translation_key="humidity",
        native_value_fn=lambda data: data.humidity,
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
    ),
    CommonSensorEntityDescription(
        key="pressure",
        translation_key="pressure",
        native_value_fn=lambda data: data.native_pressure,
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        native_unit_of_measurement=CWAWeatherCoordinator.native_pressure_unit,
        entity_registry_enabled_default=False,
    ),
    CommonSensorEntityDescription(
        key="dew_point",
        translation_key="dew_point",
        native_value_fn=lambda data: data.native_dew_point,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=CWAWeatherCoordinator.native_temperature_unit,
        entity_registry_enabled_default=False,
    ),
    CommonSensorEntityDescription(
        key="uv_index",
        translation_key="uv_index",
        native_value_fn=lambda data: data.uv_index,
        native_unit_of_measurement=CWAWeatherCoordinator.uv_index_unit,
        entity_registry_enabled_default=False,
    ),
    CommonSensorEntityDescription(
        key="wind_speed",
        translation_key="wind_speed",
        native_value_fn=lambda data: data.native_wind_speed,
        native_unit_of_measurement=CWAWeatherCoordinator.native_wind_speed_unit,
        entity_registry_enabled_default=False,
    ),
)

class CWAWeatherSensorEntity(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION_CWA
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: CWAWeatherCoordinator, description: CommonSensorEntityDescription):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}-{description.key}"
        self._attr_native_value = self.entity_description.native_value_fn(self.coordinator.data)

    def _handle_coordinator_update(self) -> None:
        if (val := self.entity_description.native_value_fn(self.coordinator.data)) != self._attr_native_value:
            _LOGGER.debug(f"Updating sensor {self.coordinator.name} {self.entity_description.key} from {self._attr_native_value} to {val}")
            self._attr_native_value = val
            self.async_write_ha_state()


MOENV_SENSOR_TYPES: tuple[CommonSensorEntityDescription, ...] = (
    CommonSensorEntityDescription(
        key="aqi",
        translation_key="aqi",
        native_value_fn=lambda aqi: aqi.aqi,
        device_class=SensorDeviceClass.AQI,
        native_unit_of_measurement=None,
    ),
    CommonSensorEntityDescription(
        key="pm2_5",
        translation_key="pm2_5",
        native_value_fn=lambda aqi: aqi.pm2_5,
        device_class=SensorDeviceClass.PM25,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    ),
    CommonSensorEntityDescription(
        key="pm10",
        translation_key="pm10",
        native_value_fn=lambda aqi: aqi.pm10,
        device_class=SensorDeviceClass.PM10,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    ),
    CommonSensorEntityDescription(
        key="o3",
        translation_key="o3",
        native_value_fn=lambda aqi: aqi.o3,
        device_class=SensorDeviceClass.OZONE,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        entity_registry_enabled_default=False,
    ),
    CommonSensorEntityDescription(
        key="co",
        translation_key="co",
        native_value_fn=lambda aqi: aqi.co,
        device_class=SensorDeviceClass.CO,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        entity_registry_enabled_default=False,
    ),
    CommonSensorEntityDescription(
        key="no2",
        translation_key="no2",
        native_value_fn=lambda aqi: aqi.no2,
        device_class=SensorDeviceClass.NITROGEN_DIOXIDE,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        entity_registry_enabled_default=False,
    ),
    CommonSensorEntityDescription(
        key="no",
        translation_key="no",
        native_value_fn=lambda aqi: aqi.no,
        device_class=SensorDeviceClass.NITROGEN_MONOXIDE,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        entity_registry_enabled_default=False,
    ),
    CommonSensorEntityDescription(
        key="so2",
        translation_key="so2",
        native_value_fn=lambda aqi: aqi.so2,
        device_class=SensorDeviceClass.SULPHUR_DIOXIDE,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        entity_registry_enabled_default=False,
    ),
)


class MOENVSensorEntity(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION_MOENV
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: CWAWeatherCoordinator, description: CommonSensorEntityDescription):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_device_info = coordinator.device_info
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}-{description.key}"
        self._attr_native_value = self.entity_description.native_value_fn(self.coordinator.data.aqi_station)

    def _handle_coordinator_update(self) -> None:
        if (val := self.entity_description.native_value_fn(self.coordinator.data.aqi_station)) != self._attr_native_value:
            _LOGGER.debug(f"Updating sensor {self.coordinator.name} {self.entity_description.key} from {self._attr_native_value} to {val}")
            self._attr_native_value = val
            self.async_write_ha_state()


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = config_entry.runtime_data
    entities = [CWAWeatherSensorEntity(coordinator, description) for description in SENSOR_TYPES]
    entities.extend(MOENVSensorEntity(coordinator, description) for description in MOENV_SENSOR_TYPES)
    async_add_entities(entities, False)
