# https://opendata.cwa.gov.tw/opendatadoc/insrtuction/CWA_Data_Standard.pdf
# https://opendata.cwa.gov.tw/opendatadoc/Forecast/F-D0047-001_093.pdf
# https://opendata.cwa.gov.tw/opendatadoc/Opendata_City.pdf
# https://opendata.cwa.gov.tw/dist/opendata-swagger.html
# https://opendata.cwa.gov.tw/opendatadoc/MFC/A0012-001.pdf
# https://e-service.cwa.gov.tw/wdps/obs/state.htm
# https://data.gov.tw/dataset/152915

import logging
from pprint import pformat
from datetime import datetime, timedelta
import re
import math
import copy
import urllib.parse
import asyncio
import aiohttp
import async_timeout
from .datagovtw import DataGovTw

_LOGGER = logging.getLogger(__name__)

# F-D0047-{loccode}
CWA_COUNTY_CODE = {
    '宜蘭縣': 1, # 001 宜蘭縣未來3天天氣預報 003 宜蘭縣未來1週天氣預報
    '桃園市': 5, # 005 桃園市未來3天天氣預報 007 桃園市未來1週天氣預報
    '新竹縣': 9, # 009 新竹縣未來3天天氣預報 011 新竹縣未來1週天氣預報
    '苗栗縣': 13, # 013 苗栗縣未來3天天氣預報 015 苗栗縣未來1週天氣預報
    '彰化縣': 17, # 017 彰化縣未來3天天氣預報 019 彰化縣未來1週天氣預報
    '南投縣': 21, # 021 南投縣未來3天天氣預報 023 南投縣未來1週天氣預報
    '雲林縣': 25, # 025 雲林縣未來3天天氣預報 027 雲林縣未來1週天氣預報
    '嘉義縣': 29, # 029 嘉義縣未來3天天氣預報 031 嘉義縣未來1週天氣預報
    '屏東縣': 33, # 033 屏東縣未來3天天氣預報 035 屏東縣未來1週天氣預報
    '臺東縣': 37, # 037 臺東縣未來3天天氣預報 039 臺東縣未來1週天氣預報
    '花蓮縣': 41, # 041 花蓮縣未來3天天氣預報 043 花蓮縣未來1週天氣預報
    '澎湖縣': 45, # 045 澎湖縣未來3天天氣預報 047 澎湖縣未來1週天氣預報
    '基隆市': 49, # 049 基隆市未來3天天氣預報 051 基隆市未來1週天氣預報
    '新竹市': 53, # 053 新竹市未來3天天氣預報 055 新竹市未來1週天氣預報
    '嘉義市': 57, # 057 嘉義市未來3天天氣預報 059 嘉義市未來1週天氣預報
    '臺北市': 61, # 061 臺北市未來3天天氣預報 063 臺北市未來1週天氣預報
    '高雄市': 65, # 065 高雄市未來3天天氣預報 067 高雄市未來1週天氣預報
    '新北市': 69, # 069 新北市未來3天天氣預報 071 新北市未來1週天氣預報
    '臺中市': 73, # 073 臺中市未來3天天氣預報 075 臺中市未來1週天氣預報
    '臺南市': 77, # 077 臺南市未來3天天氣預報 079 臺南市未來1週天氣預報
    '連江縣': 81, # 081 連江縣未來3天天氣預報 083 連江縣未來1週天氣預報
    '金門縣': 85, # 085 金門縣未來3天天氣預報 087 金門縣未來1週天氣預報
    '臺灣': 89, # 089 臺灣未來3天天氣預報 091 臺灣未來1週天氣預報
}


async def _aio_call(url, timeout = 10):
    async with aiohttp.ClientSession() as session:
        async with async_timeout.timeout(timeout):
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()

_data_cache = {}
async def _api_v1(dataid, params):
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{dataid}?{urllib.parse.urlencode(params)}"

    ts = datetime.now().timestamp()
    _to_delete = [k for k, (t, r) in _data_cache.items() if ts - t >= 60]
    for k in _to_delete:
        del _data_cache[k]

    while True:
        if url in _data_cache:
            t, r = _data_cache[url]
            if r is None:
                _LOGGER.debug("%s wait...", url)
                await asyncio.sleep(.5)
                continue
            else:
                _LOGGER.debug("%s cached", url)
                data = r
                break
        else:
            _data_cache[url] = (ts, None)
            data = await _aio_call(url)
            _data_cache[url] = (ts, data)
            _LOGGER.debug("%s fetched", url)
            break

    return copy.deepcopy(data)

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
    ATTR_AirPressure = "AirPressure"
    ATTR_AirTemperature = "AirTemperature"
    ATTR_Precipitation = "Precipitation"
    ATTR_PeakGustSpeed = "PeakGustSpeed"


    @staticmethod
    async def get_forcast_twice_daily(api_key, location):
        locs = [x for x in re.split(r"[\s\,\.\\\/\-\_\~\|]+", location) if len(x) > 0]
        if len(locs) == 1:
            fname = f"F-D0047-091"
            lname = locs[0]
        elif len(locs) == 2:
            fname = f"F-D0047-{CWA_COUNTY_CODE[locs[0]] + 2:03}"
            lname = locs[1]
        else:
            return None

        data = await _api_v1(fname, {"Authorization": api_key, "LocationName": lname})

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
    async def get_forcast_hourly(api_key, location):
        locs = [x for x in re.split(r"[\s\,\.\\\/\-\_\~\|]+", location) if len(x) > 0]
        if len(locs) == 1:
            fname = f"F-D0047-089"
            lname = locs[0]
        elif len(locs) == 2:
            fname = f"F-D0047-{CWA_COUNTY_CODE[locs[0]]:03}"
            lname = locs[1]
        else:
            return None

        data = await _api_v1(fname, {"Authorization": api_key, "LocationName": lname})

        locs = data["records"]["Locations"][0]
        loc = locs["Location"][0]
        we = loc["WeatherElement"]

        if (item := next((x for x in we if x['ElementName'] == '溫度'), None)) is None:
            return None
        # forcasts = [{CWA.ATTR_DataTime: datetime.fromisoformat(x[CWA.ATTR_DataTime])} for x in item['Time']]
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


    async def get_weather_warning(api_key, location):
        locs = [x for x in re.split(r"[\s\,\.\\\/\-\_\~\|]+", location) if len(x) > 0]
        fname = f"W-C0033-001"
        data = await _api_v1(fname, {"Authorization": api_key, "locationName": locs[0]})

        locs = data["records"]["location"][0]
        hazards = locs["hazardConditions"]['hazards']
        for haz in hazards:
            info = f"{haz['info']['phenomena']} {haz['info']['significance']}"
            startTime = haz['validTime']['startTime']
            endTime = haz['validTime']['endTime']
            print(info, startTime, endTime)


    async def get_observation_now(api_key, lat, lon):
        # latitude = 22.6197092
        # long = 120.3602682

        data = {}
        fname = "O-A0001-001"
        data[fname] = await _api_v1(fname, {"Authorization": api_key})
        fname = "O-A0003-001"
        data[fname] = await _api_v1(fname, {"Authorization": api_key})


        sts = []
        for fname in ["O-A0001-001", "O-A0003-001"]: # ["O-A0001-001", "O-A0002-001", "O-A0003-001"]:
            for station in data[fname]["records"]["Station"]:
                geoinfo = station["GeoInfo"]
                coord = next(x for x in geoinfo['Coordinates'] if x['CoordinateName'] == 'WGS84')
                dist = math.sqrt(math.pow(coord['StationLatitude'] - lat, 2) + math.pow(coord['StationLongitude'] - lon, 2))
                if dist < 0.15:
                    station["_distance"] = dist
                    sts.append(station)

        # 'SunshineDuration': 0.0,
        # 'UVIndex': 0.0,
        # 'VisibilityDescription': '>30',

        sts = sorted(sts, key=lambda x: x["_distance"])
        res = {}
        for station in sts:
            # geo = station["GeoInfo"]
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
            if CWA.ATTR_WindDirection not in res and we[CWA.ATTR_WindDirection] >= 0:
                res[CWA.ATTR_WindDirection] = we[CWA.ATTR_WindDirection]
            if CWA.ATTR_PeakGustSpeed not in res and we['GustInfo'][CWA.ATTR_PeakGustSpeed] >= 0:
                res[CWA.ATTR_PeakGustSpeed] = we['GustInfo'][CWA.ATTR_PeakGustSpeed]
            # if wind_gust_direction is None and we['GustInfo']['Occurred_at']['WindDirection'] >= 0:
            #     wind_gust_direction = we['GustInfo']['Occurred_at']['WindDirection']
            if CWA.ATTR_Weather not in res and we[CWA.ATTR_Weather] != '-99':
                res[CWA.ATTR_Weather] = we[CWA.ATTR_Weather]
                res[CWA.ATTR_ObsTime] = datetime.fromisoformat(station[CWA.ATTR_ObsTime]['DateTime'])

            # print(geo["CountyName"], geo["TownName"], station["StationId"], station["StationName"], we['Weather'], we['AirPressure'], we['AirTemperature'], we['RelativeHumidity'], we['Now']['Precipitation'], station["_distance"])

            if CWA.ATTR_AirPressure in res \
                    and CWA.ATTR_AirTemperature in res \
                    and CWA.ATTR_RelativeHumidity in res \
                    and CWA.ATTR_Precipitation in res \
                    and CWA.ATTR_WindSpeed in res \
                    and CWA.ATTR_WindDirection in res \
                    and CWA.ATTR_PeakGustSpeed in res \
                    and CWA.ATTR_Weather in res:
                break

        # print(weather, air_pressure, air_temperature, relative_humidity, precipitation, wind_speed, wind_direction, wind_gust_speed)
        return res



async def main():
    FORMAT = '%(asctime)s %(funcName)s %(levelname)s:%(message)s'
    logging.basicConfig(level=logging.DEBUG, format=FORMAT)


    API_KEY = 'CWA-0C30CC81-5EBC-458E-9069-E2B933290048'


    # latitude = 22.6197092
    # long = 120.3602682
    # location = await DataGovTw.town_village_point_query(latitude, long)
    # # location = " \\  / _ --  新竹市 , , , / \\ _ - ~  北區 // ...."

    data = await _api_v1('C-B0025-001', {"Authorization": API_KEY})
    print(pformat(data))



    # forcasts = await CWA.get_forcast_twice_daily(API_KEY, location)
    # logging.info(pformat(forcasts))

    # forcasts = await CWA.get_forcast_hourly(API_KEY, location)
    # logging.info(pformat(forcasts))

    # await CWA.get_weather_warning(API_KEY, location)

    # res = await CWA.get_observation_now(API_KEY, latitude, long)
    # print(res)





if __name__ == '__main__':
    asyncio.run(main())
