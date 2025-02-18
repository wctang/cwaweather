"""CWA Weather Platform for Home Assistant."""
# https://www.home-assistant.io/integrations/weather/
# https://www.cwa.gov.tw/V8/C/K/Weather_Icon.html

import logging
from homeassistant.core import HomeAssistant, callback
from homeassistant.components import weather
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .coordinator import CWAWeatherCoordinator
from .const import (
    DOMAIN,
    ATTRIBUTION_CWA,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = config_entry.runtime_data
    async_add_entities([CWAWeatherEntity(coordinator)], False)


class CWAWeatherEntity(weather.SingleCoordinatorWeatherEntity[CWAWeatherCoordinator]):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_attribution = ATTRIBUTION_CWA

    _attr_supported_features = (
        weather.WeatherEntityFeature.FORECAST_HOURLY |
        weather.WeatherEntityFeature.FORECAST_DAILY |
        weather.WeatherEntityFeature.FORECAST_TWICE_DAILY
    )

    def __init__(self, coordinator: CWAWeatherCoordinator):
        super().__init__(coordinator)
        self._unsubscribe_listener = None
        self._attr_native_temperature_unit = coordinator.native_temperature_unit
        self._attr_native_wind_speed_unit = coordinator.native_wind_speed_unit
        self._attr_unique_id = coordinator.config_entry.entry_id
        self._attr_device_info = coordinator.device_info

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
        return self.coordinator.data.condition

    @property
    def native_temperature(self) -> float | None:
        return self.coordinator.data.native_temperature

    @property
    def native_apparent_temperature(self) -> float | None:
        return self.coordinator.data.native_apparent_temperature

    @property
    def native_pressure(self) -> float | None:
        return self.coordinator.data.native_pressure

    @property
    def humidity(self) -> float | None:
        return self.coordinator.data.humidity

    @property
    def native_dew_point(self) -> float:
        return self.coordinator.data.native_dew_point

    @property
    def native_wind_speed(self) -> float:
        return self.coordinator.data.native_wind_speed

    @property
    def wind_bearing(self) -> float:
        return self.coordinator.data.wind_bearing

    # @property
    # def native_wind_gust_speed(self) -> float | None:
    #     return self.coordinator.data.get(weather.ATTR_FORECAST_NATIVE_WIND_GUST_SPEED)

    @property
    def uv_index(self) -> float:
        return self.coordinator.data.uv_index

    @property
    def extra_state_attributes(self):
        return self.coordinator.extra_attributes_weather
