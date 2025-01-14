from datetime import timedelta, datetime
import logging
from random import randrange
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.components import weather
from .cwa import CWA
from .datagovtw import DataGovTw
from .const import CONF_TRACK_HOME

_LOGGER = logging.getLogger(__name__)

CWA_WEATHER_SYMBOL_TO_HASS = [
    (weather.ATTR_CONDITION_SUNNY, ('01', '02')),
    (weather.ATTR_CONDITION_PARTLYCLOUDY, ('03', '04')),
    (weather.ATTR_CONDITION_CLOUDY, ('05', '06', '07')),
    (weather.ATTR_CONDITION_WINDY, ()),
    (weather.ATTR_CONDITION_RAINY, ('08', '09', '10', '11', '12', '13', '14', '19', '20', '29', '30', '31', '32', '38', '39')),
    (weather.ATTR_CONDITION_LIGHTNING, ()),
    (weather.ATTR_CONDITION_LIGHTNING_RAINY, ('15', '16', '17', '18', '21', '22', '33', '34', '35', '36', '41')),
    (weather.ATTR_CONDITION_POURING, ()),
    (weather.ATTR_CONDITION_FOG, ('24', '25', '26', '27', '28')),
    (weather.ATTR_CONDITION_SNOWY_RAINY, ('23', '37')),
    (weather.ATTR_CONDITION_SNOWY, ('42')),
    (weather.ATTR_CONDITION_HAIL, ()),
    (weather.ATTR_CONDITION_EXCEPTIONAL, ()),
    (weather.ATTR_CONDITION_WINDY_VARIANT, ()),
]

CWA_WIND_DIRECTION_TO_HASS = {
    '偏北風': 'N',
    '西北風': 'NW',
    '偏西風': 'W',
    '西南風': 'SW',
    '偏南風': 'S',
    '東南風': 'SE',
    '偏東風': 'E',
    '東北風': 'NE',
}

def convet_weather_to_ha_condition(fc):
    wc = fc[CWA.ATTR_WeatherCode]
    for id, cos in CWA_WEATHER_SYMBOL_TO_HASS:
        if wc in cos:
            if id == weather.ATTR_CONDITION_SUNNY or id == weather.ATTR_CONDITION_PARTLYCLOUDY:
                hour = fc[CWA.ATTR_DataTime if CWA.ATTR_DataTime in fc else CWA.ATTR_StartTime].hour
                if hour >= 18 or hour <= 5:
                    return weather.ATTR_CONDITION_CLEAR_NIGHT
            return id

    _LOGGER.debug(f"{fc[CWA.ATTR_WeatherCode]} = {fc[CWA.ATTR_Weather]}")
    return fc[CWA.ATTR_Weather]

def convet_cwa_to_ha_forcast(fc) -> weather.Forecast:
    forcast: weather.Forecast = {
        weather.ATTR_FORECAST_TIME: fc[CWA.ATTR_DataTime if CWA.ATTR_DataTime in fc else CWA.ATTR_StartTime],
        weather.ATTR_FORECAST_CONDITION: convet_weather_to_ha_condition(fc),
    }

    if CWA.ATTR_DewPoint in fc:
        forcast[weather.ATTR_FORECAST_NATIVE_DEW_POINT] = int(fc[CWA.ATTR_DewPoint])
    if CWA.ATTR_RelativeHumidity in fc:
        forcast[weather.ATTR_FORECAST_HUMIDITY] = int(fc[CWA.ATTR_RelativeHumidity])
    if CWA.ATTR_ProbabilityOfPrecipitation in fc:
        forcast[weather.ATTR_FORECAST_PRECIPITATION_PROBABILITY] = 0 if fc[CWA.ATTR_ProbabilityOfPrecipitation] == '-' else int(fc[CWA.ATTR_ProbabilityOfPrecipitation])
    if CWA.ATTR_MinTemperature in fc and CWA.ATTR_MaxTemperature in fc:
        forcast[weather.ATTR_FORECAST_NATIVE_TEMP] = int(fc[CWA.ATTR_MaxTemperature])
        forcast[weather.ATTR_FORECAST_NATIVE_TEMP_LOW] = int(fc[CWA.ATTR_MinTemperature])
    else:
        forcast[weather.ATTR_FORECAST_NATIVE_TEMP] = int(fc[CWA.ATTR_Temperature])
    if CWA.ATTR_ApparentTemperature in fc:
        forcast[weather.ATTR_FORECAST_NATIVE_APPARENT_TEMP] =  int(fc[CWA.ATTR_ApparentTemperature])
    if CWA.ATTR_EndTime in fc:
        forcast[weather.ATTR_FORECAST_IS_DAYTIME] = fc[CWA.ATTR_EndTime].hour == 18
    if CWA.ATTR_DewPoint in fc:
        forcast[weather.ATTR_FORECAST_NATIVE_DEW_POINT] = int(fc[CWA.ATTR_DewPoint])
    if CWA.ATTR_WindDirection in fc and fc[CWA.ATTR_WindDirection] in CWA_WIND_DIRECTION_TO_HASS:
        forcast[weather.ATTR_FORECAST_WIND_BEARING] = CWA_WIND_DIRECTION_TO_HASS[fc[CWA.ATTR_WindDirection]]
    if CWA.ATTR_WindSpeed in fc:
        forcast[weather.ATTR_FORECAST_NATIVE_WIND_SPEED] = int(fc[CWA.ATTR_WindSpeed])
    if CWA.ATTR_UVIndex in fc:
        forcast[weather.ATTR_FORECAST_UV_INDEX] = int(fc[CWA.ATTR_UVIndex])
    return forcast


class CWAWeatherCoordinator(DataUpdateCoordinator):
    _attr_native_temperature_unit = weather.UnitOfTemperature.CELSIUS
    _attr_native_wind_speed_unit = weather.UnitOfSpeed.METERS_PER_SECOND

    def __init__(self, hass: HomeAssistant, api_key: str, location: str):
        self._api_key = api_key
        self._location = location
        self._latitude = None
        self._longitude = None
        super().__init__(hass, _LOGGER, name=self._location, update_interval=timedelta(minutes=randrange(55, 65)))

    def get_forcasts(self, kind) -> list[weather.Forecast] | None:
        if kind in ["twice_daily", "hourly"]:
            if kind not in self.data:
                return None
            return self.data[kind]
        elif kind == "daily":
            if "twice_daily" not in self.data:
                return None
            return [f for f in self.data["twice_daily"] if f[weather.ATTR_FORECAST_IS_DAYTIME]]
        else:
            return None

    async def _async_update_data(self):
        data = self.data or {}

        if self._location is None:
            return data
        elif self._location == CONF_TRACK_HOME:
            self._latitude = self.hass.config.latitude
            self._longitude = self.hass.config.longitude
            self._location = await DataGovTw.town_village_point_query(self._latitude, self._longitude)

        _now = datetime.now().astimezone()
        # twice_daily
        data["twice_daily"] = [convet_cwa_to_ha_forcast(fc) for fc in await CWA.get_forcast_twice_daily(self._api_key, self._location) if fc[CWA.ATTR_StartTime] >= (_now - timedelta(hours=8))]
        # hourly
        data["hourly"] = [convet_cwa_to_ha_forcast(fc) for fc in await CWA.get_forcast_hourly(self._api_key, self._location) if fc[CWA.ATTR_DataTime] >= (_now - timedelta(minutes=45))]

        daily = data["twice_daily"][0]
        hourly = data["hourly"][0]

        data[weather.ATTR_FORECAST_CONDITION] = hourly[weather.ATTR_FORECAST_CONDITION]
        data[weather.ATTR_FORECAST_NATIVE_TEMP] = hourly[weather.ATTR_FORECAST_NATIVE_TEMP]
        data[weather.ATTR_FORECAST_NATIVE_APPARENT_TEMP] = hourly[weather.ATTR_FORECAST_NATIVE_APPARENT_TEMP]
        data[weather.ATTR_FORECAST_HUMIDITY] = hourly[weather.ATTR_FORECAST_HUMIDITY]
        data[weather.ATTR_FORECAST_NATIVE_DEW_POINT] = hourly[weather.ATTR_FORECAST_NATIVE_DEW_POINT]
        if weather.ATTR_FORECAST_NATIVE_WIND_SPEED in hourly:
            data[weather.ATTR_FORECAST_NATIVE_WIND_SPEED] = hourly[weather.ATTR_FORECAST_NATIVE_WIND_SPEED]
            data[weather.ATTR_FORECAST_WIND_BEARING] = hourly[weather.ATTR_FORECAST_WIND_BEARING]
        if weather.ATTR_FORECAST_UV_INDEX in daily:
            data[weather.ATTR_FORECAST_UV_INDEX] = daily[weather.ATTR_FORECAST_UV_INDEX]

        if self._latitude and self._longitude:
            res = await CWA.get_observation_now(self._api_key, self._latitude, self._longitude)
            condition = res[CWA.ATTR_Weather]
            data[weather.ATTR_FORECAST_CONDITION] = condition
            data["extra_attr"] = {
                CWA.ATTR_ObsTime: res[CWA.ATTR_ObsTime],
                CWA.ATTR_StationName: res[CWA.ATTR_StationName],
                CWA.ATTR_StationId: res[CWA.ATTR_StationId],
                CWA.ATTR_StationLatitude: res[CWA.ATTR_StationLatitude],
                CWA.ATTR_StationLongitude: res[CWA.ATTR_StationLongitude],
            }
            if "雨" in condition:
                data["icon"] = "mdi:weather-rainy"
            elif "雲" in condition or "陰" in condition:
                data["icon"] = "mdi:weather-cloudy"
            elif "晴" in condition:
                if res[CWA.ATTR_ObsTime].hour < 6 or res[CWA.ATTR_ObsTime].hour >= 18 :
                    data["icon"] = "mdi:weather-night"
                else:
                    data["icon"] = "mdi:weather-sunny"
            else:
                data["icon"] = "mdi:alert-circle-outline"

            data[weather.ATTR_FORECAST_PRESSURE] = res[CWA.ATTR_AirPressure]
            data[weather.ATTR_FORECAST_NATIVE_TEMP] = res[CWA.ATTR_AirTemperature]
            data[weather.ATTR_FORECAST_HUMIDITY] = res[CWA.ATTR_RelativeHumidity]
            data[weather.ATTR_FORECAST_NATIVE_WIND_SPEED] = res[CWA.ATTR_WindSpeed]
            data[weather.ATTR_FORECAST_WIND_BEARING] = res[CWA.ATTR_WindDirection]
            data[weather.ATTR_FORECAST_NATIVE_WIND_GUST_SPEED] = res[CWA.ATTR_PeakGustSpeed]
            data[weather.ATTR_FORECAST_UV_INDEX] = res[CWA.ATTR_UVIndex]

        return data
