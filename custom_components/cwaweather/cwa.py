# https://opendata.cwa.gov.tw/index
# https://opendata.cwa.gov.tw/dataset/all?page=1
# https://opendata.cwa.gov.tw/dist/opendata-swagger.html
# https://opendata.cwa.gov.tw/opendatadoc/insrtuction/CWA_Data_Standard.pdf
# https://www.cwa.gov.tw/V8/C/D/Data_catalog.html
# https://opendata.cwa.gov.tw/dataset/forecast/F-D0047-001
#   https://opendata.cwa.gov.tw/opendatadoc/Forecast/F-D0047-001_093.pdf
# https://opendata.cwa.gov.tw/dataset/observation/O-A0001-001
# https://opendata.cwa.gov.tw/dataset/observation/O-A0002-002
# https://opendata.cwa.gov.tw/dataset/observation/O-A0003-001
#   https://opendata.cwa.gov.tw/opendatadoc/Observation/O-A0001-001.pdf
# https://opendata.cwa.gov.tw/opendatadoc/MFC/A0012-001.pdf



import logging
from datetime import datetime, timedelta
import re
import math
import urllib.parse
import asyncio
from pprint import pprint, pformat
from .utils import url_get
from .const import TAIWAN_CITYS_TOWNS

_LOGGER = logging.getLogger(__name__)

async def _api_v1(hass, dataid, params, is_json=True):
    return await url_get(hass, f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{dataid}?{urllib.parse.urlencode(params)}", is_json=is_json)

class CWA:
    ATTR_StartTime = "StartTime"
    ATTR_EndTime = "EndTime"
    ATTR_DataTime = "DataTime"
    ATTR_Temperature = "Temperature"
    ATTR_MaxTemperature = "MaxTemperature"
    ATTR_MinTemperature = "MinTemperature"
    ATTR_Weather = "Weather"
    ATTR_WeatherCode = "WeatherCode"
    ATTR_WeatherDescription = "WeatherDescription"
    ATTR_DewPoint = "DewPoint"
    ATTR_RelativeHumidity = "RelativeHumidity"
    ATTR_MaxApparentTemperature = "MaxApparentTemperature"
    ATTR_MinApparentTemperature = "MinApparentTemperature"
    ATTR_MaxComfortIndex = "MaxComfortIndex"
    ATTR_MaxComfortIndexDescription = "MaxComfortIndexDescription"
    ATTR_MinComfortIndex = "MinComfortIndex"
    ATTR_MinComfortIndexDescription = "MinComfortIndexDescription"
    ATTR_BeaufortScale = "BeaufortScale"
    ATTR_WindSpeed = "WindSpeed"
    ATTR_WindDirection = "WindDirection"
    ATTR_ProbabilityOfPrecipitation = "ProbabilityOfPrecipitation"
    ATTR_UVIndex = "UVIndex"
    ATTR_ApparentTemperature = "ApparentTemperature"
    ATTR_ComfortIndex = "ComfortIndex"
    ATTR_ComfortIndexDescription = "ComfortIndexDescription"

    ATTR_ObsTime = "ObsTime"
    ATTR_StationName = "StationName"
    ATTR_StationId = "StationId"
    ATTR_StationLatitude = "StationLatitude"
    ATTR_StationLongitude = "StationLongitude"

    ATTR_AirPressure = "AirPressure"
    ATTR_AirTemperature = "AirTemperature"
    ATTR_Precipitation = "Precipitation"
    ATTR_PeakGustSpeed = "PeakGustSpeed"
    ATTR_UVIndex = "UVIndex"


    @staticmethod
    async def get_forcast_twice_daily(hass, api_key, location):
        locs = [x for x in re.split(r"[\s\,\.\\\/\-\_\~\|]+", location) if len(x) > 0]
        if len(locs) == 1:
            dataid = f"F-D0047-091"
            lname = locs[0]
        elif len(locs) == 2:
            dataid = f"F-D0047-{TAIWAN_CITYS_TOWNS[locs[0]][0] + 2:03}"
            lname = locs[1]
        else:
            return None

        data = await _api_v1(hass, dataid, {"Authorization": api_key, "LocationName": lname})
        # _LOGGER.debug(pformat(data))

        locs = data["records"]["Locations"][0]
        loc = locs["Location"][0]
        we = loc["WeatherElement"]

        forcasts = []
        for item in we:
            itime = item["Time"]
            for it in itime:
                ist = datetime.fromisoformat(it[CWA.ATTR_StartTime])
                ien = datetime.fromisoformat(it[CWA.ATTR_EndTime])
                if (forcast := next((x for x in forcasts if x[CWA.ATTR_StartTime] == ist and x[CWA.ATTR_EndTime] == ien), None)) is None:
                    forcast = {CWA.ATTR_StartTime:ist, CWA.ATTR_EndTime:ien}
                    forcasts.append(forcast)

                forcast.update(it["ElementValue"][0])
        return forcasts


    @staticmethod
    async def get_forcast_hourly(hass, api_key, location):
        locs = [x for x in re.split(r"[\s\,\.\\\/\-\_\~\|]+", location) if len(x) > 0]
        if len(locs) == 1:
            dataid = f"F-D0047-089"
            lname = locs[0]
        elif len(locs) == 2:
            dataid = f"F-D0047-{TAIWAN_CITYS_TOWNS[locs[0]][0]:03}"
            lname = locs[1]
        else:
            return None

        data = await _api_v1(hass, dataid, {"Authorization": api_key, "LocationName": lname})
        # _LOGGER.debug(pformat(data))

        locs = data["records"]["Locations"][0]
        loc = locs["Location"][0]
        we = loc["WeatherElement"]

        if (item := next((x for x in we if x['ElementName'] == '溫度'), None)) is None:
            return None

        forcasts: list[dict] = []
        st = datetime.fromisoformat(item['Time'][0][CWA.ATTR_DataTime])
        ed = datetime.fromisoformat(item['Time'][-1][CWA.ATTR_DataTime])
        while st <= ed:
            forcasts.append({CWA.ATTR_DataTime: st})
            st += timedelta(hours=1)


        for item in we:
            itime = item["Time"]

            for it in itime:
                it[CWA.ATTR_DataTime] = datetime.fromisoformat(it[CWA.ATTR_DataTime if CWA.ATTR_DataTime in it else CWA.ATTR_StartTime])

            for forcast in forcasts:
                fot = forcast[CWA.ATTR_DataTime]
                it = next(it for it in itime if fot <= it[CWA.ATTR_DataTime])
                forcast.update(it["ElementValue"][0])

        return forcasts


    async def get_weather_warning(hass, api_key, location):
        locs = [x for x in re.split(r"[\s\,\.\\\/\-\_\~\|]+", location) if len(x) > 0]
        dataid = f"W-C0033-001"
        data = await _api_v1(hass, dataid, {"Authorization": api_key, "locationName": locs[0]})

        locs = data["records"]["location"][0]
        hazards = locs["hazardConditions"]['hazards']
        for haz in hazards:
            info = f"{haz['info']['phenomena']} {haz['info']['significance']}"
            startTime = haz['validTime']['startTime']
            endTime = haz['validTime']['endTime']
            return info, startTime, endTime


    @staticmethod
    def _parse_a000x(st):
        _attrs = [CWA.ATTR_AirPressure, CWA.ATTR_AirTemperature, CWA.ATTR_WindSpeed,
                    CWA.ATTR_WindDirection, CWA.ATTR_RelativeHumidity, CWA.ATTR_Precipitation, 'GustInfo/PeakGustSpeed',
                    'SunshineDuration', 'UVIndex', 'VisibilityDescription', 'Weather'
                    ]
        def parse_weatherelement(v0, par, r):
            for k, v in v0.items():
                if f'{par}{k}' in _attrs and v != '-99' and v != -99:
                    r[k] = v
                elif isinstance(v, dict):
                    parse_weatherelement(v, f'{par}{k}/', r)

        def parse_rainfallelement(v, r):
            for k in ['Now', 'Past10Min', 'Past1hr', 'Past3hr', 'Past6Hr', 'Past12hr', 'Past24hr', 'Past2days', 'Past3days']:
                if k in v:
                    r[f"Precipitation{k}"] = v[k]['Precipitation']

        r = {}
        for k in ["StationName", "StationId"]:
            r[k] = st[k]
        r["ObsTime"] = st["ObsTime"]['DateTime']

        geo = st["GeoInfo"]
        for k in ["StationAltitude", "CountyName", "TownName", "CountyCode", "TownCode"]:
            r[k] = geo[k]

        coord = next(x for x in geo['Coordinates'] if x['CoordinateName'] == 'WGS84')
        for k in ["StationLatitude", "StationLongitude"]:
            r[k] = coord[k]

        if "WeatherElement" in st:
            parse_weatherelement(st["WeatherElement"], "", r)
        if "RainfallElement" in st:
            parse_rainfallelement(st["RainfallElement"], r)
        return r

    @staticmethod
    async def get_observation_stations(hass, api_key):
        sts = []
        for dataid in ["O-A0003-001"]: # ["O-A0001-001", "O-A0002-001", "O-A0003-001"]:
            data = await _api_v1(hass, dataid, {"Authorization": api_key})
            # _LOGGER.debug(pformat(data))
            sts.extend(CWA._parse_a000x(st) for st in data["records"]["Station"])
        return sts

    @staticmethod
    async def get_rain_stations(hass, api_key):
        sts = []
        for dataid in ["O-A0002-001"]:
            data = await _api_v1(hass, dataid, {"Authorization": api_key})
            # _LOGGER.debug(pformat(data))
            sts.extend(CWA._parse_a000x(st) for st in data["records"]["Station"])
        return sts


    @staticmethod
    async def get_observation_now(hass, api_key, lat, lon):

        sts = await CWA.get_observation_stations(hass, api_key)
        sts2 = []
        for st in sts:
            dist = math.sqrt(math.pow(st['StationLatitude'] - lat, 2) + math.pow(st['StationLongitude'] - lon, 2))
            if dist < 0.15:
                st["_distance"] = dist
                sts2.append(st)


        _attrs = [CWA.ATTR_AirPressure, CWA.ATTR_AirTemperature, CWA.ATTR_RelativeHumidity, CWA.ATTR_Precipitation,
                  CWA.ATTR_WindSpeed, CWA.ATTR_WindDirection, CWA.ATTR_PeakGustSpeed, CWA.ATTR_UVIndex]
        res = {}
        for st in sorted(sts2, key=lambda x: x["_distance"]):
            if CWA.ATTR_Weather not in res and CWA.ATTR_Weather in st:
                res[CWA.ATTR_Weather] = st[CWA.ATTR_Weather]
                res[CWA.ATTR_ObsTime] = datetime.fromisoformat(st[CWA.ATTR_ObsTime])
                res[CWA.ATTR_StationName] = st[CWA.ATTR_StationName]
                res[CWA.ATTR_StationId] = st[CWA.ATTR_StationId]
                res[CWA.ATTR_StationLatitude] = st[CWA.ATTR_StationLatitude]
                res[CWA.ATTR_StationLongitude] = st[CWA.ATTR_StationLongitude]

            complete = True
            for attr in _attrs:
                if attr not in res:
                    if attr in st:
                        res[attr] = st[attr]
                    else:
                        complete = False
            if complete:
                break

        return res


async def main():
    from pprint import pprint
    from dotenv import load_dotenv
    import os
    import operator

    load_dotenv()
    API_KEY = os.getenv("API_KEY")
    POS_LAT = float(os.getenv("POS_LAT"))
    POS_LON = float(os.getenv("POS_LON"))
    location = os.getenv("POS_LOCATION")

    logging.basicConfig(level=logging.DEBUG)

    # data = await _api_v1('C-B0025-001', {"Authorization": API_KEY})
    # pprint(data)

    # forcasts = await CWA.get_forcast_twice_daily(None, API_KEY, location)
    # pprint(f"{forcasts[0]['StartTime']}")

    # forcasts = await CWA.get_forcast_hourly(None, API_KEY, location)
    # pprint(f"{forcasts[0]['DataTime']}")

    # await CWA.get_weather_warning(API_KEY, location)

    # res = await CWA.get_observation_now(API_KEY, POS_LAT, POS_LON)
    # pprint(res)


    sts = await CWA.get_observation_stations(None, API_KEY)
    for st in sts:
        st["_distance"] = math.sqrt(math.pow(st['StationLatitude'] - POS_LAT, 2) + math.pow(st['StationLongitude'] - POS_LON, 2))
    weathers = []
    for st in sorted(sts, key=operator.itemgetter("_distance")):
        if st["_distance"] > 0.3:
            break
        if CWA.ATTR_Weather in st:
            weathers.append(st[CWA.ATTR_Weather])
        print(f"{st["_distance"]} {st[CWA.ATTR_ObsTime]} {st["CountyName"]} {st["TownName"]} {st.get(CWA.ATTR_AirTemperature)} {st.get(CWA.ATTR_RelativeHumidity)} {st.get(CWA.ATTR_AirPressure)} {st.get(CWA.ATTR_Weather,""):4} {st[CWA.ATTR_StationName]}")

    CWA_WEATHER_CONDITION_TO_HASS = {
        "有霾": "FOG",
        "有靄": "FOG",
        "有霧": "FOG",

        "有雷": "LIGHTNING",
        "有閃電": "LIGHTNING",
        "有雷聲": "LIGHTNING",

        "有雨": "RAINY",
        "有陣雨": "RAINY",

        "有雨雪": "SNOWY_RAINY",
        "陣雨雪": "SNOWY_RAINY",

        "有大雪": "SNOWY",
        "有雪珠": "SNOWY",
        "有冰珠": "SNOWY",
        "有雷雪": "SNOWY",

        "有雹": "HAIL",
        "有雷雹": "HAIL",
        "大雷雹": "HAIL",

        "大雷雨": "LIGHTNING_RAINY",
        "有雷雨": "LIGHTNING_RAINY",

        "晴": "SUNNY",
        "多雲": "PARTLYCLOUDY",
        "陰": "CLOUDY",
    }
    from collections import Counter
    wss = list(map(lambda x: CWA_WEATHER_CONDITION_TO_HASS[x if len(x) <= 2 else x.replace("晴","").replace("多雲","").replace("陰","")], weathers))
    print(weathers)
    print(wss)
    print(Counter(wss).most_common(1)[0][0])
    _LOGGER.info(f"{weathers}")


    # data = await CWA.get_rain_stations(None, API_KEY)
    # pprint(data)


if __name__ == '__main__':
    asyncio.run(main())
