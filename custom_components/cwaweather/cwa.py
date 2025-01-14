# https://opendata.cwa.gov.tw/index
# https://opendata.cwa.gov.tw/dataset/all?page=1
# https://opendata.cwa.gov.tw/dist/opendata-swagger.html
# https://opendata.cwa.gov.tw/opendatadoc/insrtuction/CWA_Data_Standard.pdf
# https://www.cwa.gov.tw/V8/C/D/Data_catalog.html
# https://opendata.cwa.gov.tw/dataset/forecast/F-D0047-001
# https://opendata.cwa.gov.tw/dataset/observation/O-A0001-001
# https://opendata.cwa.gov.tw/dataset/observation/O-A0002-002
# https://opendata.cwa.gov.tw/dataset/observation/O-A0003-001
# https://opendata.cwa.gov.tw/opendatadoc/MFC/A0012-001.pdf



import logging
from datetime import datetime, timedelta
import re
import math
import urllib.parse
import asyncio
from .utils import url_get
from .const import TAIWAN_CITYS_TOWNS

_LOGGER = logging.getLogger(__name__)

async def _api_v1(hass, dataid, params):
    return await url_get(hass, f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{dataid}?{urllib.parse.urlencode(params)}")

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

        locs = data["records"]["Locations"][0]
        loc = locs["Location"][0]
        we = loc["WeatherElement"]

        forcasts = []
        for item in we:
            itime = item["Time"]
            ename = item["ElementName"]
            for it in itime:
                ist = datetime.fromisoformat(it[CWA.ATTR_StartTime])
                ien = datetime.fromisoformat(it[CWA.ATTR_EndTime])
                forcast = next((x for x in forcasts if x[CWA.ATTR_StartTime] == ist and x[CWA.ATTR_EndTime] == ien), None)
                if forcast is None:
                    forcast = {CWA.ATTR_StartTime:ist, CWA.ATTR_EndTime:ien}
                    forcasts.append(forcast)

                itv = it["ElementValue"][0]
                match ename:
                    case '平均溫度':
                        forcast[CWA.ATTR_Temperature] = itv[CWA.ATTR_Temperature]
                    case '最高溫度':
                        forcast[CWA.ATTR_MaxTemperature] = itv[CWA.ATTR_MaxTemperature]
                    case '最低溫度':
                        forcast[CWA.ATTR_MinTemperature] = itv[CWA.ATTR_MinTemperature]
                    case '天氣現象':
                        forcast[CWA.ATTR_Weather] = itv[CWA.ATTR_Weather]
                        forcast[CWA.ATTR_WeatherCode] = itv[CWA.ATTR_WeatherCode]
                    case '天氣預報綜合描述':
                        forcast[CWA.ATTR_WeatherDescription] = itv[CWA.ATTR_WeatherDescription]
                    case '平均露點溫度':
                        forcast[CWA.ATTR_DewPoint] = itv[CWA.ATTR_DewPoint]
                    case '平均相對濕度':
                        forcast[CWA.ATTR_RelativeHumidity] = itv[CWA.ATTR_RelativeHumidity]
                    case '最高體感溫度':
                        forcast[CWA.ATTR_MaxApparentTemperature] = itv[CWA.ATTR_MaxApparentTemperature]
                    case '最低體感溫度':
                        forcast[CWA.ATTR_MinApparentTemperature] = itv[CWA.ATTR_MinApparentTemperature]
                    case '最大舒適度指數':
                        forcast[CWA.ATTR_MaxComfortIndex] = itv[CWA.ATTR_MaxComfortIndex]
                        forcast[CWA.ATTR_MaxComfortIndexDescription] = itv[CWA.ATTR_MaxComfortIndexDescription]
                    case '最小舒適度指數':
                        forcast[CWA.ATTR_MinComfortIndex] = itv[CWA.ATTR_MinComfortIndex]
                        forcast[CWA.ATTR_MinComfortIndexDescription] = itv[CWA.ATTR_MinComfortIndexDescription]
                    case '風速':
                        forcast[CWA.ATTR_BeaufortScale] = itv[CWA.ATTR_BeaufortScale]
                        forcast[CWA.ATTR_WindSpeed] = itv[CWA.ATTR_WindSpeed]
                    case '風向':
                        forcast[CWA.ATTR_WindDirection] = itv[CWA.ATTR_WindDirection]
                    case '12小時降雨機率':
                        forcast[CWA.ATTR_ProbabilityOfPrecipitation] = itv[CWA.ATTR_ProbabilityOfPrecipitation]
                    case '紫外線指數':
                        forcast[CWA.ATTR_UVIndex] = itv[CWA.ATTR_UVIndex]

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
            ename = item["ElementName"]

            for it in itime:
                it[CWA.ATTR_DataTime] = datetime.fromisoformat(it[CWA.ATTR_DataTime if CWA.ATTR_DataTime in it else CWA.ATTR_StartTime])

            for forcast in forcasts:
                fot = forcast[CWA.ATTR_DataTime]
                it = None
                for it_ in itime:
                    if fot < it_[CWA.ATTR_DataTime]:
                        break
                    it = it_

                itv = it["ElementValue"][0]
                match ename:
                    case '溫度':
                        forcast[CWA.ATTR_Temperature] = itv[CWA.ATTR_Temperature]
                    case '露點溫度':
                        forcast[CWA.ATTR_DewPoint] = itv[CWA.ATTR_DewPoint]
                    case '相對濕度':
                        forcast[CWA.ATTR_RelativeHumidity] = itv[CWA.ATTR_RelativeHumidity]
                    case '體感溫度':
                        forcast[CWA.ATTR_ApparentTemperature] = itv[CWA.ATTR_ApparentTemperature]
                    case '舒適度指數':
                        forcast[CWA.ATTR_ComfortIndex] = itv[CWA.ATTR_ComfortIndex]
                        forcast[CWA.ATTR_ComfortIndexDescription] = itv[CWA.ATTR_ComfortIndexDescription]
                    case '風速':
                        forcast[CWA.ATTR_BeaufortScale] = itv[CWA.ATTR_BeaufortScale]
                        forcast[CWA.ATTR_WindSpeed] = itv[CWA.ATTR_WindSpeed]
                    case '風向':
                        forcast[CWA.ATTR_WindDirection] = itv[CWA.ATTR_WindDirection]
                    case '天氣現象':
                        forcast[CWA.ATTR_Weather] = itv[CWA.ATTR_Weather]
                        forcast[CWA.ATTR_WeatherCode] = itv[CWA.ATTR_WeatherCode]
                    case '3小時降雨機率':
                        forcast[CWA.ATTR_ProbabilityOfPrecipitation] = itv[CWA.ATTR_ProbabilityOfPrecipitation]
                    case '天氣預報綜合描述':
                        forcast[CWA.ATTR_WeatherDescription] = itv[CWA.ATTR_WeatherDescription]

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
            print(info, startTime, endTime)


    async def get_observation_now(hass, api_key, lat, lon):
        sts = []
        for dataid in ["O-A0001-001", "O-A0003-001"]: # ["O-A0001-001", "O-A0002-001", "O-A0003-001"]:
            data = await _api_v1(hass, dataid, {"Authorization": api_key})
            # _LOGGER.debug(pformat(data))
            for station in data["records"]["Station"]:
                coord = next(x for x in station["GeoInfo"]['Coordinates'] if x['CoordinateName'] == 'WGS84')
                dist = math.sqrt(math.pow(coord['StationLatitude'] - lat, 2) + math.pow(coord['StationLongitude'] - lon, 2))
                if dist < 0.15:
                    station["_distance"] = dist
                    station["_lat"] = coord['StationLatitude']
                    station["_lon"] = coord['StationLongitude']
                    sts.append(station)

        if len(sts) == 0:
            return None

        # 'SunshineDuration': 0.0,
        # 'UVIndex': 0.0,
        # 'VisibilityDescription': '>30',

        res = {}
        sts.sort(key=lambda x: x["_distance"])
        for station in sts:
            # geo =
            we = station['WeatherElement']

            if CWA.ATTR_AirPressure not in res and we[CWA.ATTR_AirPressure] >= 0:
                res[CWA.ATTR_AirPressure] = we[CWA.ATTR_AirPressure]
            if CWA.ATTR_AirTemperature not in res and we[CWA.ATTR_AirTemperature] >= 0:
                res[CWA.ATTR_AirTemperature] = we[CWA.ATTR_AirTemperature]
            if CWA.ATTR_RelativeHumidity not in res and we[CWA.ATTR_RelativeHumidity] >= 0:
                res[CWA.ATTR_RelativeHumidity] = we[CWA.ATTR_RelativeHumidity]
            if CWA.ATTR_Precipitation not in res and we['Now'][CWA.ATTR_Precipitation] >= 0:
                res[CWA.ATTR_Precipitation] = we['Now'][CWA.ATTR_Precipitation]
            if CWA.ATTR_WindSpeed not in res and we[CWA.ATTR_WindSpeed] >= 0:
                res[CWA.ATTR_WindSpeed] = we[CWA.ATTR_WindSpeed]
            if CWA.ATTR_WindDirection not in res and we[CWA.ATTR_WindDirection] >= 0: # W = 270°, NW = 315°
                res[CWA.ATTR_WindDirection] = we[CWA.ATTR_WindDirection]
            if CWA.ATTR_PeakGustSpeed not in res and we['GustInfo'][CWA.ATTR_PeakGustSpeed] >= 0:
                res[CWA.ATTR_PeakGustSpeed] = we['GustInfo'][CWA.ATTR_PeakGustSpeed]
            # if wind_gust_direction is None and we['GustInfo']['Occurred_at']['WindDirection'] >= 0:
            #     wind_gust_direction = we['GustInfo']['Occurred_at']['WindDirection']
            if CWA.ATTR_Weather not in res and we[CWA.ATTR_Weather] != '-99':
                res[CWA.ATTR_Weather] = we[CWA.ATTR_Weather]
                res[CWA.ATTR_ObsTime] = datetime.fromisoformat(station[CWA.ATTR_ObsTime]['DateTime'])
                res[CWA.ATTR_StationName] = station[CWA.ATTR_StationName]
                res[CWA.ATTR_StationId] = station[CWA.ATTR_StationId]
                res[CWA.ATTR_StationLatitude] = station["_lat"]
                res[CWA.ATTR_StationLongitude] = station["_lon"]
            if CWA.ATTR_UVIndex not in res and CWA.ATTR_UVIndex in we and we[CWA.ATTR_UVIndex] >= 0:
                res[CWA.ATTR_UVIndex] = we[CWA.ATTR_UVIndex]


            if CWA.ATTR_AirPressure in res \
                    and CWA.ATTR_AirTemperature in res \
                    and CWA.ATTR_RelativeHumidity in res \
                    and CWA.ATTR_Precipitation in res \
                    and CWA.ATTR_WindSpeed in res \
                    and CWA.ATTR_WindDirection in res \
                    and CWA.ATTR_PeakGustSpeed in res \
                    and CWA.ATTR_Weather in res \
                    and CWA.ATTR_UVIndex in res:
                break

        return res


async def main():
    from pprint import pprint
    from dotenv import load_dotenv
    import os

    load_dotenv()
    API_KEY = os.getenv("API_KEY")
    POS_LAT = float(os.getenv("POS_LAT"))
    POS_LON = float(os.getenv("POS_LON"))

    logging.basicConfig(level=logging.DEBUG)

    # data = await _api_v1('C-B0025-001', {"Authorization": API_KEY})
    # pprint(data)

    # forcasts = await CWA.get_forcast_twice_daily(API_KEY, location)
    # pprint(forcasts)

    # forcasts = await CWA.get_forcast_hourly(API_KEY, location)
    # pprint(forcasts)

    # await CWA.get_weather_warning(API_KEY, location)

    res = await CWA.get_observation_now(API_KEY, POS_LAT, POS_LON)
    pprint(res)


if __name__ == '__main__':
    asyncio.run(main())
