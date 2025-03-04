import logging
import math
import re
from pprint import pprint
from operator import attrgetter
from datetime import timedelta, datetime
from dataclasses import dataclass
from collections import Counter
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_state_change_event, Event, EventStateChangedData
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.components import weather
from homeassistant.const import (
    UV_INDEX
)
from .cwa import CWA
from .moenv import MOENV, AQIStation
from .datagovtw import DataGovTw
from .const import (
    DOMAIN,
    MANUFACTURER,
    MODEL_NAME,
    HOME_URL,
    CONF_API_KEY,
    CONF_API_KEY_MOENV,
    CONF_LOCATION,
    CONF_LATITUDE,
    CONF_LONGITUDE,
)

_LOGGER = logging.getLogger(__name__)

# https://opendata.cwa.gov.tw/opendatadoc/MFC/A0012-001.pdf
CWA_WEATHER_SYMBOL_TO_HASS = [
    (weather.ATTR_CONDITION_HAIL, ()),
    (weather.ATTR_CONDITION_SNOWY_RAINY, ('23', '37')),
    (weather.ATTR_CONDITION_SNOWY, ('42')),
    (weather.ATTR_CONDITION_LIGHTNING_RAINY, ('15', '16', '17', '18', '21', '22', '33', '34', '35', '36', '41')),
    (weather.ATTR_CONDITION_LIGHTNING, ()),
    (weather.ATTR_CONDITION_POURING, ()),
    (weather.ATTR_CONDITION_RAINY, ('08', '09', '10', '11', '12', '13', '14', '19', '20', '29', '30', '31', '32', '38', '39')),
    (weather.ATTR_CONDITION_FOG, ('24', '25', '26', '27', '28')),
    (weather.ATTR_CONDITION_CLOUDY, ('05', '06', '07')),
    (weather.ATTR_CONDITION_PARTLYCLOUDY, ('03', '04')),
    (weather.ATTR_CONDITION_SUNNY, ('01', '02')),
    (weather.ATTR_CONDITION_WINDY, ()),
    (weather.ATTR_CONDITION_EXCEPTIONAL, ()),
    (weather.ATTR_CONDITION_WINDY_VARIANT, ()),
]

# https://opendata.cwa.gov.tw/opendatadoc/Observation/O-A0001-001.pdf
# 雲量 + 天氣現象
# 雲量 = 晴 / 多雲 / 陰
# 天氣現象 = - / 有霾 / 有靄 / 有閃電 / 有雷聲 / 有霧 / 有雨 / 有雨雪 / 有大雪 / 有雪珠 / 有冰珠 / 有陣雨 / 陣雨雪 / 有雹 / 有雷雨 / 有雷雪 / 有雷雨 / 有雷雹 / 大雷雨 / 有雷雨 / 大雷雹 / 有雷
CWA_WEATHER_CONDITION_TO_HASS = {
    "有霾": weather.ATTR_CONDITION_FOG,
    "有靄": weather.ATTR_CONDITION_FOG,
    "有霧": weather.ATTR_CONDITION_FOG,

    "有雷": weather.ATTR_CONDITION_LIGHTNING,
    "有閃電": weather.ATTR_CONDITION_LIGHTNING,
    "有雷聲": weather.ATTR_CONDITION_LIGHTNING,

    "有雨": weather.ATTR_CONDITION_RAINY,
    "有陣雨": weather.ATTR_CONDITION_RAINY,

    "有雨雪": weather.ATTR_CONDITION_SNOWY_RAINY,
    "陣雨雪": weather.ATTR_CONDITION_SNOWY_RAINY,

    "有大雪": weather.ATTR_CONDITION_SNOWY,
    "有雪珠": weather.ATTR_CONDITION_SNOWY,
    "有冰珠": weather.ATTR_CONDITION_SNOWY,
    "有雷雪": weather.ATTR_CONDITION_SNOWY,

    "有雹": weather.ATTR_CONDITION_HAIL,
    "有雷雹": weather.ATTR_CONDITION_HAIL,
    "大雷雹": weather.ATTR_CONDITION_HAIL,

    "大雷雨": weather.ATTR_CONDITION_LIGHTNING_RAINY,
    "有雷雨": weather.ATTR_CONDITION_LIGHTNING_RAINY,

    "晴": weather.ATTR_CONDITION_SUNNY,
    "多雲": weather.ATTR_CONDITION_PARTLYCLOUDY,
    "陰": weather.ATTR_CONDITION_CLOUDY,
}

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

def _forecast_weather_to_ha_condition(fc):
    wc = fc[CWA.ATTR_WeatherCode]
    for id, cos in CWA_WEATHER_SYMBOL_TO_HASS:
        if wc in cos:
            if id == weather.ATTR_CONDITION_SUNNY:
                hour = fc[CWA.ATTR_DataTime if CWA.ATTR_DataTime in fc else CWA.ATTR_StartTime].hour
                if hour >= 18 or hour <= 5:
                    return weather.ATTR_CONDITION_CLEAR_NIGHT
            return id

    _LOGGER.debug(f"{fc[CWA.ATTR_WeatherCode]} = {fc[CWA.ATTR_Weather]}")
    return fc[CWA.ATTR_Weather]


def _observe_weather_to_ha_condition(weathers, _now):
    wss = []
    for x in weathers:
        if len(x) <= 2:
            wss.append(CWA_WEATHER_CONDITION_TO_HASS[x])
        else:
            wss.append(CWA_WEATHER_CONDITION_TO_HASS[x.replace("晴","").replace("多雲","").replace("陰","")])

    mm = Counter(wss).most_common(1)
    if len(mm) == 0:
        return None

    res = mm[0][0]
    if res == weather.ATTR_CONDITION_SUNNY and (_now.hour >= 18 or _now.hour <= 5):
        res = weather.ATTR_CONDITION_CLEAR_NIGHT
    return res


def convet_cwa_to_ha_forcast(fc) -> weather.Forecast:
    def _convert_to(f, k1, fc, k2, is_number = True):
        if k2 in fc:
            f[k1] = fc[k2] if not is_number else float(fc[k2].replace("<","").replace(">","").replace("=",""))

    forcast: weather.Forecast = {
        weather.ATTR_FORECAST_TIME: fc[CWA.ATTR_DataTime if CWA.ATTR_DataTime in fc else CWA.ATTR_StartTime],
        weather.ATTR_FORECAST_CONDITION: _forecast_weather_to_ha_condition(fc),
    }

    _convert_to(forcast, weather.ATTR_FORECAST_HUMIDITY, fc, CWA.ATTR_RelativeHumidity)
    _convert_to(forcast, weather.ATTR_FORECAST_NATIVE_APPARENT_TEMP, fc, CWA.ATTR_ApparentTemperature)
    _convert_to(forcast, weather.ATTR_FORECAST_NATIVE_DEW_POINT, fc, CWA.ATTR_DewPoint)
    _convert_to(forcast, weather.ATTR_FORECAST_NATIVE_WIND_SPEED, fc, CWA.ATTR_WindSpeed)
    _convert_to(forcast, weather.ATTR_FORECAST_UV_INDEX, fc, CWA.ATTR_UVIndex)
    if CWA.ATTR_ProbabilityOfPrecipitation in fc:
        forcast[weather.ATTR_FORECAST_PRECIPITATION_PROBABILITY] = 0 if fc[CWA.ATTR_ProbabilityOfPrecipitation] == '-' else int(fc[CWA.ATTR_ProbabilityOfPrecipitation])
    if CWA.ATTR_MinTemperature in fc and CWA.ATTR_MaxTemperature in fc:
        forcast[weather.ATTR_FORECAST_NATIVE_TEMP] = int(fc[CWA.ATTR_MaxTemperature])
        forcast[weather.ATTR_FORECAST_NATIVE_TEMP_LOW] = int(fc[CWA.ATTR_MinTemperature])
    else:
        forcast[weather.ATTR_FORECAST_NATIVE_TEMP] = int(fc[CWA.ATTR_Temperature])
    if CWA.ATTR_EndTime in fc:
        forcast[weather.ATTR_FORECAST_IS_DAYTIME] = fc[CWA.ATTR_EndTime].hour == 18
    if CWA.ATTR_WindDirection in fc and fc[CWA.ATTR_WindDirection] in CWA_WIND_DIRECTION_TO_HASS:
        forcast[weather.ATTR_FORECAST_WIND_BEARING] = CWA_WIND_DIRECTION_TO_HASS[fc[CWA.ATTR_WindDirection]]

    # extra attributes
    forcast[CWA.ATTR_Weather] = fc[CWA.ATTR_Weather]
    forcast[CWA.ATTR_WeatherDescription] = fc[CWA.ATTR_WeatherDescription]
    if CWA.ATTR_ComfortIndexDescription in fc:
        forcast[CWA.ATTR_ComfortIndexDescription] = fc[CWA.ATTR_ComfortIndexDescription]
    return forcast


@dataclass
class CWAWeatherData:
    hourly: list[weather.Forecast] = None
    twice_daily: list[weather.Forecast] = None
    forecast_time: datetime = None

    condition: str = None
    native_temperature: float = None
    native_apparent_temperature: float = None
    humidity: float = None
    native_dew_point: float = None
    native_wind_speed: float = None
    wind_bearing: float = None
    uv_index: float = None
    native_pressure: float = None

    aqi_publishtime: datetime = None
    aqi_station: AQIStation = None
    aqi_extra_attributes: dict = None


class CWAWeatherCoordinator(DataUpdateCoordinator[CWAWeatherData]):
    native_temperature_unit = weather.UnitOfTemperature.CELSIUS
    native_wind_speed_unit = weather.UnitOfSpeed.METERS_PER_SECOND
    native_pressure_unit = weather.UnitOfPressure.HPA
    uv_index_unit = UV_INDEX

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        name = config_entry.title
        super().__init__(hass, _LOGGER, config_entry=config_entry, name=name, update_interval=timedelta(minutes=10)) # check every 10 minutes
        _LOGGER.info("%s, %s, %s", name, config_entry.entry_id, config_entry.data)

        self.extra_attributes_weather = {}
        self.device_info = DeviceInfo(
            name=name,
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, config_entry.entry_id)},
            manufacturer=MANUFACTURER,
            model=MODEL_NAME,
            configuration_url=HOME_URL,
        )
        self._force_refresh = False

        self._api_key = config_entry.data.get(CONF_API_KEY)
        self._api_key_moenv = config_entry.data.get(CONF_API_KEY_MOENV)

        location = config_entry.data.get(CONF_LOCATION)
        if location and location.startswith("zone."):
            if (zoneentity := hass.states.get(location)) is None:
                raise Exception(f"Cant find tracking zone entity: {location}")

            self._latitude = zoneentity.attributes.get("latitude")
            self._longitude = zoneentity.attributes.get("longitude")
            async_track_state_change_event(hass, location, self._watched_entity_change)
        else:
            self._latitude = config_entry.data.get(CONF_LATITUDE)
            self._longitude = config_entry.data.get(CONF_LONGITUDE)

        if self._latitude and self._longitude:
            self._city = None
            self._town = None
        elif (locs := re.split(r"[\s\,\.\\\/\-\_\~\|]+", location)):
            self._city = locs[0]
            self._town = locs[1]
        else:
            raise Exception(f"Cant find tracking zone entity: {location}")


    async def _watched_entity_change(self, event: Event[EventStateChangedData]) -> None:
        newstate = event.data["new_state"]
        if newstate.attributes.get("latitude") == self._latitude and newstate.attributes.get("longitude") == self._longitude:
            return

        _LOGGER.info("update location: ", newstate)
        self._latitude = newstate.attributes.get("latitude")
        self._longitude = newstate.attributes.get("longitude")
        self._city = None
        self._town = None
        await self.async_refresh()


    async def _async_update_data(self):
        data = self.data or CWAWeatherData()

        _now = datetime.now().astimezone()
        session = async_get_clientsession(self.hass, verify_ssl=False)

        if (self._city is None or self._town is None) and self._latitude and self._longitude:
            # get city and town by lat and lon
            res = await DataGovTw.town_village_point_query(session, self._latitude, self._longitude)
            if res:
                self._city = res[0]
                self._town = res[1]
            else:
                _LOGGER.warning(f"Cant get location from lat,long: {self._latitude}, {self._longitude}")
                return data

            self._force_refresh = True

        # refresh forecasts
        # 發布時機：每日 05:30、11:30、17:30、23:30,  更新頻率：每 6 小時
        if self._force_refresh or data.forecast_time is None or _now > (data.forecast_time + timedelta(hours=5.8)):
            # get forecast by city-town
            res = await CWA.get_forcast_hourly(session, self._api_key, self._city, self._town)
            if self._latitude is None and self._longitude is None:
                self._latitude = res["Latitude"]
                self._longitude = res["Longitude"]
                _LOGGER.info(f"Update location '{self._city}-{self._town}' positon as ({self._latitude},{self._longitude})")
            data.hourly = [convet_cwa_to_ha_forcast(fc) for fc in res["Forecasts"]]
            data.forecast_time = data.hourly[0][weather.ATTR_FORECAST_TIME]

            res = await CWA.get_forcast_twice_daily(session, self._api_key, self._city, self._town)
            data.twice_daily = [convet_cwa_to_ha_forcast(fc) for fc in res["Forecasts"]]
            self._force_refresh = False
            _LOGGER.debug(f"refresh forecasts '{self._city}-{self._town}', {_now}, {data.hourly[0][weather.ATTR_FORECAST_TIME]}")

        hourly = next(f for f in data.hourly if f[weather.ATTR_FORECAST_TIME] > (_now - timedelta(hours=1)))
        daily = next(f for f in data.twice_daily if f[weather.ATTR_FORECAST_TIME] > (_now - timedelta(hours=12)))

        data.condition = hourly[weather.ATTR_FORECAST_CONDITION]
        data.native_temperature = hourly[weather.ATTR_FORECAST_NATIVE_TEMP]
        data.native_apparent_temperature = hourly[weather.ATTR_FORECAST_NATIVE_APPARENT_TEMP]
        data.humidity = hourly[weather.ATTR_FORECAST_HUMIDITY]
        data.native_dew_point = hourly[weather.ATTR_FORECAST_NATIVE_DEW_POINT]
        if weather.ATTR_FORECAST_NATIVE_WIND_SPEED in hourly:
            data.native_wind_speed = hourly[weather.ATTR_FORECAST_NATIVE_WIND_SPEED]
            data.wind_bearing = hourly[weather.ATTR_FORECAST_WIND_BEARING]
        if weather.ATTR_FORECAST_UV_INDEX in daily:
            data.uv_index = daily[weather.ATTR_FORECAST_UV_INDEX]

        self.extra_attributes_weather["forecast_weather"] = hourly[CWA.ATTR_Weather]
        # self.extra_attributes_weather[CWA.ATTR_WeatherCode] = hourly[CWA.ATTR_WeatherCode]
        self.extra_attributes_weather["forecast_weather_description"] = hourly[CWA.ATTR_WeatherDescription]
        if CWA.ATTR_ComfortIndexDescription in hourly:
            self.extra_attributes_weather["forecast_comfort_description"] = hourly[CWA.ATTR_ComfortIndexDescription]

        if self._latitude and self._longitude:
            # get observation by lat and lon
            sts: list[CWA.Station] = await CWA.get_observation_stations(session, self._api_key)
            for st in sts:
                st._distance = math.sqrt(math.pow(st.StationLatitude - self._latitude, 2) + math.pow(st.StationLongitude - self._longitude, 2))

            weathers = []
            has_station = False
            has_persure = False
            for st in sorted(sts, key=attrgetter("_distance")):
                if st._distance > 0.3:
                    break

                if st.Weather is not None:
                    weathers.append(st.Weather)

                if not has_persure and st.AirPressure is not None:
                    has_persure = True
                    data.native_pressure = st.AirPressure

                if not has_station and st.AirTemperature is not None and st.RelativeHumidity is not None:
                    has_station = True
                    # _LOGGER.debug(f"refresh observation {self._location}")
                    data.native_temperature = st.AirTemperature
                    data.humidity = st.RelativeHumidity

                    self.extra_attributes_weather["station_name"] = st.StationName
                    self.extra_attributes_weather["station_id"] = st.StationId
                    self.extra_attributes_weather["latitude"] = st.StationLatitude
                    self.extra_attributes_weather["longitude"] = st.StationLongitude
                    self.extra_attributes_weather["station_air_temperature"] = st.AirTemperature
                    self.extra_attributes_weather["station_relative_humidity"] = st.RelativeHumidity
                    if st.ObsTime is not None:
                        self.extra_attributes_weather["station_obs_time"] = st.ObsTime
                    if st.Weather is not None:
                        self.extra_attributes_weather["station_weather"] = st.Weather

            self.extra_attributes_weather["station_weathers"] = ",".join(weathers)
            condition = _observe_weather_to_ha_condition(weathers, _now)
            if condition:
                if condition == weather.ATTR_CONDITION_SUNNY:
                    if _now.hour >= 18 or _now.hour <= 5:
                        condition = weather.ATTR_CONDITION_CLEAR_NIGHT
                data.condition = condition

            if data.aqi_station is None or _now > data.aqi_publishtime + timedelta(hours=1.1):
                sts: list[AQIStation] = await MOENV.get_aqi_hourly(session, self._api_key_moenv)
                for st in sts:
                    st._distance = math.sqrt(math.pow(float(st.latitude) - self._latitude, 2) + math.pow(float(st.longitude) - self._longitude, 2))

                for st in sorted(sts, key=attrgetter("_distance")):
                    if st.aqi is not None:
                        data.aqi_station = st
                        data.aqi_publishtime = datetime.strptime(st.publishtime, '%Y/%m/%d %H:%M:%S').astimezone()
                        _LOGGER.debug(f"refresh aqi {_now}, {data.aqi_publishtime}")

                        data.aqi_extra_attributes = data.aqi_extra_attributes or {}
                        data.aqi_extra_attributes["siteid"] = st.siteid
                        data.aqi_extra_attributes["sitename"] = st.sitename
                        data.aqi_extra_attributes["county"] = st.county
                        data.aqi_extra_attributes["latitude"] = st.latitude
                        data.aqi_extra_attributes["longitude"] = st.longitude
                        data.aqi_extra_attributes["publishtime"] = st.publishtime
                        data.aqi_extra_attributes["pollutant"] = st.pollutant
                        data.aqi_extra_attributes["station_aqi"] = st.aqi
                        data.aqi_extra_attributes["station_pm25"] = st.pm2_5
                        data.aqi_extra_attributes["station_pm10"] = st.pm10
                        break
        return data


    def get_forcasts(self, kind) -> list[weather.Forecast] | None:
        _now = datetime.now().astimezone()
        if kind == "hourly":
            if self.data.hourly is not None:
                return [f for f in self.data.hourly if f[weather.ATTR_FORECAST_TIME] >= (_now - timedelta(minutes=45))]

        elif kind == "twice_daily":
            if self.data.twice_daily is not None:
                return [f for f in self.data.twice_daily if f[weather.ATTR_FORECAST_TIME] >= (_now - timedelta(hours=8))]

        elif kind == "daily":
            if self.data.twice_daily is not None:
                return [f for f in self.data.twice_daily if f[weather.ATTR_FORECAST_TIME] >= (_now - timedelta(hours=8)) and f[weather.ATTR_FORECAST_IS_DAYTIME]]

        return None
