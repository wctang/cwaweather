from datetime import timedelta, datetime
import logging
import math
import operator
from collections import Counter
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event, Event, EventStateChangedData
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.components import weather
from .cwa import CWA
from .datagovtw import DataGovTw


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

    res = Counter(wss).most_common(1)[0][0]
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
    return forcast


class CWAWeatherCoordinator(DataUpdateCoordinator):
    _attr_native_temperature_unit = weather.UnitOfTemperature.CELSIUS
    _attr_native_wind_speed_unit = weather.UnitOfSpeed.METERS_PER_SECOND

    def __init__(self, hass: HomeAssistant, api_key: str, location: str):
        super().__init__(hass, _LOGGER, name=location, update_interval=timedelta(minutes=10)) # check every 10 minutes
        self.data = {}
        self.extra_attributes = {}
        self._api_key = api_key

        self._force_refresh = False

        if location.startswith("zone."):
            if (zoneentity := self.hass.states.get(location)) is None:
                _LOGGER.error("Cant find tracking zone entity: %s", location)
                return

            self._tracking = location
            self._latitude = zoneentity.attributes.get("latitude")
            self._longitude = zoneentity.attributes.get("longitude")
            self._location = None

        else:
            self._location = location
            self._tracking = None
            self._latitude = None
            self._longitude = None
            self.extra_attributes["location"] = self._location

        if self._tracking:
            self.extra_attributes["tracking"] = self._tracking
            async_track_state_change_event(hass, self._tracking, self._watched_entity_change)


    async def _update_tracking_location(self) -> None:
        self._location = await DataGovTw.town_village_point_query(self.hass, self._latitude, self._longitude)
        self.extra_attributes["latitude"] = self._latitude
        self.extra_attributes["longitude"] = self._longitude
        self.extra_attributes["location"] = self._location
        self._force_refresh = True

    async def _watched_entity_change(self, event: Event[EventStateChangedData]) -> None:
        newstate = event.data["new_state"]
        if newstate.attributes.get("latitude") == self._latitude and newstate.attributes.get("longitude") == self._longitude:
            return

        print("update location: ", newstate)
        self._latitude = newstate.attributes.get("latitude")
        self._longitude = newstate.attributes.get("longitude")
        await self._update_tracking_location()
        await self.async_refresh()

    async def _async_update_data(self):
        data = self.data or {}
        extra_attr = self.extra_attributes

        if self._location is None:
            await self._update_tracking_location()
            if self._location is None:
                return data

        _now = datetime.now().astimezone()

        # refresh forecasts
        # 發布時機：每日 05:30、11:30、17:30、23:30,  更新頻率：每 6 小時
        if self._force_refresh or (datas := data.get("hourly", None)) is None or _now > (datas[0][weather.ATTR_FORECAST_TIME] + timedelta(hours=5.8)):
            res = await CWA.get_forcast_hourly(self.hass, self._api_key, self._location)
            if self._latitude is None and self._longitude is None:
                self._latitude = res["Latitude"]
                self._longitude = res["Longitude"]
                print("Update location '%s' positon as (%s,%s)", self._location, self._latitude, self._longitude)
            data["hourly"] = [convet_cwa_to_ha_forcast(fc) for fc in res["Forecasts"]]
            data["twice_daily"] = [convet_cwa_to_ha_forcast(fc) for fc in await CWA.get_forcast_twice_daily(self.hass, self._api_key, self._location)]
            self._force_refresh = False
            print(f"refresh forecasts {self._location}, {_now}, {data["hourly"][0][weather.ATTR_FORECAST_TIME]}")

        hourly = next(f for f in data["hourly"] if f[weather.ATTR_FORECAST_TIME] > (_now - timedelta(hours=1)))
        daily = next(f for f in data["twice_daily"] if f[weather.ATTR_FORECAST_TIME] > (_now - timedelta(hours=12)))

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

        extra_attr["forecast_weather"] = hourly[CWA.ATTR_Weather]
        # extra_attr[CWA.ATTR_WeatherCode] = hourly[CWA.ATTR_WeatherCode]
        extra_attr["forecast_weather_description"] = hourly[CWA.ATTR_WeatherDescription]

        if self._latitude and self._longitude:
            sts = await CWA.get_observation_stations(self.hass, self._api_key)
            for st in sts:
                st["_distance"] = math.sqrt(math.pow(st['StationLatitude'] - self._latitude, 2) + math.pow(st['StationLongitude'] - self._longitude, 2))

            weathers = []
            has_station = False
            has_persure = False
            for st in sorted(sts, key=operator.itemgetter("_distance")):
                if st["_distance"] > 0.3:
                    break

                if CWA.ATTR_Weather in st:
                    weathers.append(st[CWA.ATTR_Weather])

                if not has_persure and CWA.ATTR_AirPressure in st:
                    has_persure = True
                    data[weather.ATTR_FORECAST_PRESSURE] = st[CWA.ATTR_AirPressure]

                if not has_station and CWA.ATTR_AirTemperature in st and CWA.ATTR_RelativeHumidity in st:
                    has_station = True
                    print(f"refresh observation {self._location}, {_now}, {st[CWA.ATTR_ObsTime]}")
                    data[weather.ATTR_FORECAST_NATIVE_TEMP] = st[CWA.ATTR_AirTemperature]
                    data[weather.ATTR_FORECAST_HUMIDITY] = st[CWA.ATTR_RelativeHumidity]

                    extra_attr["station_name"] = st[CWA.ATTR_StationName]
                    extra_attr["station_id"] = st[CWA.ATTR_StationId]
                    extra_attr["station_latitude"] = st[CWA.ATTR_StationLatitude]
                    extra_attr["station_longitude"] = st[CWA.ATTR_StationLongitude]
                    extra_attr["station_air_temperature"] = st[CWA.ATTR_AirTemperature]
                    extra_attr["station_relative_humidity"] = st[CWA.ATTR_RelativeHumidity]
                    if CWA.ATTR_ObsTime in st:
                        extra_attr["station_obs_time"] = st[CWA.ATTR_ObsTime]
                    if CWA.ATTR_Weather in st:
                        extra_attr["station_weather"] = st[CWA.ATTR_Weather]

            extra_attr["station_weathers"] = ",".join(weathers)
            condition = _observe_weather_to_ha_condition(weathers, _now)
            if condition == weather.ATTR_CONDITION_SUNNY:
                if _now.hour >= 18 or _now.hour <= 5:
                    condition = weather.ATTR_CONDITION_CLEAR_NIGHT
            data[weather.ATTR_FORECAST_CONDITION] = condition
        return data

    def get_forcasts(self, kind) -> list[weather.Forecast] | None:
        _now = datetime.now().astimezone()
        if kind == "hourly":
            if (fos := self.data.get("hourly", None)) is not None:
                fos = [f for f in fos if f[weather.ATTR_FORECAST_TIME] >= (_now - timedelta(minutes=45))]
            return fos
        elif kind == "twice_daily":
            if (fos := self.data.get("twice_daily", None)) is not None:
                fos = [f for f in fos if f[weather.ATTR_FORECAST_TIME] >= (_now - timedelta(hours=8))]
            return fos
        elif kind == "daily":
            if (fos := self.data.get("twice_daily", None)) is not None:
                fos = [f for f in fos if f[weather.ATTR_FORECAST_TIME] >= (_now - timedelta(hours=8)) and f[weather.ATTR_FORECAST_IS_DAYTIME]]
            return fos
        else:
            return None
