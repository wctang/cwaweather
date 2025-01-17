"""CWA Weather Platform for Home Assistant."""
# https://www.home-assistant.io/integrations/weather/
# https://www.cwa.gov.tw/V8/C/K/Weather_Icon.html

import logging
import asyncio
import re
from random import randrange
from homeassistant.core import HomeAssistant, callback
from homeassistant.components import weather
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .coordinator import CWAWeatherCoordinator
from .const import (
    DOMAIN,
    ATTRIBUTION,
    MANUFACTURER,
    MODEL_NAME,
    HOME_URL,
    CONF_API_KEY,
    CONF_LOCATION,
    CONF_NAME,
    SELECT_ITEM_TRACK_REGEX,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    api_key = config_entry.data.get(CONF_API_KEY)
    name = config_entry.data.get(CONF_NAME)
    location = config_entry.data.get(CONF_LOCATION)

    if m := re.match(SELECT_ITEM_TRACK_REGEX, location):
        if not name:
            name = m[1]
        location = m[2]

    await asyncio.sleep(randrange(0, 3))
    _LOGGER.info("'%s' '%s' '%s'", api_key, name, location)

    coordinator = CWAWeatherCoordinator(hass, api_key, location)
    await coordinator.async_config_entry_first_refresh()

    # print("=============")
    # from homeassistant.helpers import entity_registry
    # er = entity_registry.async_get(hass)
    # eid = er.async_get_entity_id("weather", "cwaweather", config_entry.entry_id)
    # print(eid)

    async_add_entities([CWAWeatherEntity(coordinator, config_entry, name or location)], True)


class CWAWeatherEntity(weather.SingleCoordinatorWeatherEntity[CWAWeatherCoordinator]):
    _attr_attribution = ATTRIBUTION
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
        self._attr_unique_id = config_entry.entry_id
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            name=self.name,
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self.unique_id)},
            manufacturer=MANUFACTURER,
            model=MODEL_NAME,
            configuration_url=HOME_URL,
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
    def native_temperature(self) -> float | None:
        return self.coordinator.data.get(weather.ATTR_FORECAST_NATIVE_TEMP)

    @property
    def native_apparent_temperature(self) -> float | None:
        return self.coordinator.data.get(weather.ATTR_FORECAST_NATIVE_APPARENT_TEMP)

    @property
    def native_pressure(self) -> float | None:
        return self.coordinator.data.get(weather.ATTR_FORECAST_PRESSURE)

    @property
    def humidity(self) -> float | None:
        return self.coordinator.data.get(weather.ATTR_FORECAST_HUMIDITY)

    @property
    def native_dew_point(self) -> float:
        return self.coordinator.data.get(weather.ATTR_FORECAST_NATIVE_DEW_POINT)

    @property
    def native_wind_speed(self) -> float:
        return self.coordinator.data.get(weather.ATTR_FORECAST_NATIVE_WIND_SPEED)

    @property
    def wind_bearing(self) -> float:
        return self.coordinator.data.get(weather.ATTR_FORECAST_WIND_BEARING)

    @property
    def native_wind_gust_speed(self) -> float | None:
        return self.coordinator.data.get(weather.ATTR_FORECAST_NATIVE_WIND_GUST_SPEED)

    @property
    def uv_index(self) -> float:
        return self.coordinator.data.get(weather.ATTR_FORECAST_UV_INDEX)

    @property
    def state_attributes(self):
        attr = super().state_attributes
        attr.update(self.coordinator.extra_attributes)
        return attr

