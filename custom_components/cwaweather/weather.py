"""CWA Weather Platform for Home Assistant."""
# https://www.home-assistant.io/integrations/weather/
# https://www.cwa.gov.tw/V8/C/K/Weather_Icon.html

import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry
from homeassistant.components import weather
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .coordinator import CWAWeatherCoordinator
from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_LOCATION,
    CONF_NAME,
)

# _LOGGER = logging.getLogger(__name__)

def _calculate_unique_id(config_entry: ConfigEntry) -> str:
    return f"{config_entry.entry_id}"

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    api_key = config_entry.data.get(CONF_API_KEY)
    location = config_entry.data.get(CONF_LOCATION)
    name = config_entry.data.get(CONF_NAME) or location

    print(api_key, location, name)

    coordinator = CWAWeatherCoordinator(hass, api_key, location)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities([CWAWeatherEntity(coordinator, config_entry, name)], True)


class CWAWeatherEntity(weather.SingleCoordinatorWeatherEntity[CWAWeatherCoordinator]):
    _attr_attribution = (
        "CWA Weather intergeration"
        "wctang"
    )
    # _attr_has_entity_name = True
    _attr_supported_features = (
        weather.WeatherEntityFeature.FORECAST_HOURLY |
        weather.WeatherEntityFeature.FORECAST_DAILY |
        weather.WeatherEntityFeature.FORECAST_TWICE_DAILY
    )

    def __init__(self, coordinator, config_entry: ConfigEntry, name: str):
        super().__init__(coordinator)
        self._unsubscribe_listener = None
        self._attr_native_temperature_unit = coordinator._attr_native_temperature_unit
        self._attr_native_wind_speed_unit = coordinator._attr_native_wind_speed_unit
        self._attr_unique_id = _calculate_unique_id(config_entry)
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            name="CWA Weather",
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, config_entry.entry_id)},
            manufacturer="wctang",
            model="CWA Weather",
            configuration_url="https://github.com/wctang/cwaweather",
        )

    async def async_added_to_hass(self):
        self._unsubscribe_listener = self.coordinator.async_add_listener(self._handle_coordinator_update)

    async def async_will_remove_from_hass(self):
        if self._unsubscribe_listener:
            self._unsubscribe_listener()

    @callback
    def _async_forecast_hourly(self) -> list[weather.Forecast] | None:
        return self.coordinator.get_forcasts("hourly")

    @callback
    def _async_forecast_twice_daily(self) -> list[weather.Forecast] | None:
        return self.coordinator.get_forcasts("twice_daily")

    @callback
    def _async_forecast_daily(self) -> list[weather.Forecast] | None:
        return self.coordinator.get_forcasts("daily")

    @property
    def condition(self) -> str | None:
        self._attr_state = self.coordinator.data[weather.ATTR_FORECAST_CONDITION]
        return self._attr_state

    @property
    def icon(self) -> str | None:
        return self.coordinator.data["icon"]

    @property
    def native_temperature(self) -> float | None:
        return self.coordinator.data[weather.ATTR_FORECAST_NATIVE_TEMP]

    @property
    def native_apparent_temperature(self) -> float | None:
        return self.coordinator.data[weather.ATTR_FORECAST_NATIVE_APPARENT_TEMP]

    @property
    def humidity(self) -> float | None:
        return self.coordinator.data[weather.ATTR_FORECAST_HUMIDITY]

    @property
    def native_dew_point(self) -> float:
        return self.coordinator.data[weather.ATTR_FORECAST_NATIVE_DEW_POINT]

    @property
    def native_wind_speed(self) -> float:
        return self.coordinator.data[weather.ATTR_FORECAST_NATIVE_WIND_SPEED]

    @property
    def native_wind_speed(self) -> float:
        return None if weather.ATTR_FORECAST_NATIVE_WIND_SPEED not in self.coordinator.data else self.coordinator.data[weather.ATTR_FORECAST_NATIVE_WIND_SPEED]

    @property
    def wind_bearing(self) -> float:
        return None if weather.ATTR_FORECAST_WIND_BEARING not in self.coordinator.data else self.coordinator.data[weather.ATTR_FORECAST_WIND_BEARING]

    @property
    def uv_index(self) -> float:
        return None if weather.ATTR_FORECAST_UV_INDEX not in self.coordinator.data else self.coordinator.data[weather.ATTR_FORECAST_UV_INDEX]
