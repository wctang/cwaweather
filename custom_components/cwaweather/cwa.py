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
from dataclasses import dataclass
from .utils import url_get, parse_element
from .const import TAIWAN_CITYS_TOWNS

_LOGGER = logging.getLogger(__name__)

async def _api_v1(session, dataid, params, is_json=True):
    return await url_get(session, f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{dataid}?{urllib.parse.urlencode(params)}", is_json=is_json)

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
    async def get_forcast_twice_daily(session, api_key, location):
        locs = [x for x in re.split(r"[\s\,\.\\\/\-\_\~\|]+", location) if len(x) > 0]
        if len(locs) == 1:
            dataid = f"F-D0047-091"
            lname = locs[0]
        elif len(locs) == 2:
            dataid = f"F-D0047-{TAIWAN_CITYS_TOWNS[locs[0]][0] + 2:03}"
            lname = locs[1]
        else:
            return None

        data = await _api_v1(session, dataid, {"Authorization": api_key, "LocationName": lname})
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

        return {
            "Latitude": float(loc["Latitude"]),
            "Longitude": float(loc["Longitude"]),
            "LocationName": loc["LocationName"],
            "Forecasts": forcasts
        }


    @staticmethod
    async def get_forcast_hourly(session, api_key, location):
        locs = [x for x in re.split(r"[\s\,\.\\\/\-\_\~\|]+", location) if len(x) > 0]
        if len(locs) == 1:
            dataid = f"F-D0047-089"
            lname = locs[0]
        elif len(locs) == 2:
            dataid = f"F-D0047-{TAIWAN_CITYS_TOWNS[locs[0]][0]:03}"
            lname = locs[1]
        else:
            return None

        data = await _api_v1(session, dataid, {"Authorization": api_key, "LocationName": lname})
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

        return {
            "Latitude": float(loc["Latitude"]),
            "Longitude": float(loc["Longitude"]),
            "LocationName": loc["LocationName"],
            "Forecasts": forcasts
        }


    async def get_weather_warning(session, api_key, location):
        locs = [x for x in re.split(r"[\s\,\.\\\/\-\_\~\|]+", location) if len(x) > 0]
        dataid = f"W-C0033-001"
        data = await _api_v1(session, dataid, {"Authorization": api_key, "locationName": locs[0]})

        locs = data["records"]["location"][0]
        hazards = locs["hazardConditions"]['hazards']
        for haz in hazards:
            info = f"{haz['info']['phenomena']} {haz['info']['significance']}"
            startTime = haz['validTime']['startTime']
            endTime = haz['validTime']['endTime']
            return info, startTime, endTime

    @dataclass
    class Station:
        _distance: float = None
        StationName: str = None
        StationId: str = None
        ObsTime: str = None
        CountyName: str = None
        TownName: str = None
        CountyCode: str = None
        TownCode: str = None
        StationLatitude: str = None
        StationLongitude: str = None
        StationAltitude: str = None
        AirPressure: str = None
        AirTemperature: str = None
        WindSpeed: str = None
        WindDirection: str = None
        RelativeHumidity: str = None
        Precipitation: str = None
        PeakGustSpeed: str = None
        SunshineDuration: str = None
        UVIndex: str = None
        VisibilityDescription: str = None
        Weather: str = None
        PrecipitationNow: str = None
        PrecipitationPast10Min: str = None
        PrecipitationPast1hr: str = None
        PrecipitationPast3hr: str = None
        PrecipitationPast6Hr: str = None
        PrecipitationPast12hr: str = None
        PrecipitationPast24hr: str = None
        PrecipitationPast2days: str = None
        PrecipitationPast3days: str = None

        def __repr__(self):
            res = []
            for k, v in self.__dict__.items():
                if v is not None:
                    res.append(f"{k}={v}")
            return f'{{{" ".join(res)}}}'


    @staticmethod
    def _parse_a000x(st):
        _attrs = [CWA.ATTR_AirPressure, CWA.ATTR_AirTemperature, CWA.ATTR_WindSpeed,
                    CWA.ATTR_WindDirection, CWA.ATTR_RelativeHumidity, CWA.ATTR_Precipitation, 'GustInfo/PeakGustSpeed',
                    'SunshineDuration', 'UVIndex', 'VisibilityDescription', 'Weather']

        def parse_rainfallelement(v, r):
            for k in ['Now', 'Past10Min', 'Past1hr', 'Past3hr', 'Past6Hr', 'Past12hr', 'Past24hr', 'Past2days', 'Past3days']:
                if k in v:
                    r.__setattr__(f"Precipitation{k}", v[k]['Precipitation'])

        r = CWA.Station()
        for k in ["StationName", "StationId"]:
            r.__setattr__(k, st[k])
        r.ObsTime = st["ObsTime"]['DateTime']

        geo = st["GeoInfo"]
        for k in ["StationAltitude", "CountyName", "TownName", "CountyCode", "TownCode"]:
            r.__setattr__(k, geo[k])

        coord = next(x for x in geo['Coordinates'] if x['CoordinateName'] == 'WGS84')
        for k in ["StationLatitude", "StationLongitude"]:
            r.__setattr__(k, coord[k])

        if "WeatherElement" in st:
            parse_element(_attrs, st["WeatherElement"], r)
        if "RainfallElement" in st:
            parse_rainfallelement(st["RainfallElement"], r)
        return r


    @staticmethod
    async def get_observation_stations(session, api_key) -> list[Station]:
        sts = []
        for dataid in ["O-A0003-001"]: # ["O-A0001-001", "O-A0002-001", "O-A0003-001"]:
            data = await _api_v1(session, dataid, {"Authorization": api_key})
            # _LOGGER.debug(pformat(data))
            sts.extend(CWA._parse_a000x(st) for st in data["records"]["Station"])
        return sts

    @staticmethod
    async def get_rain_stations(session, api_key):
        sts = []
        for dataid in ["O-A0002-001"]:
            data = await _api_v1(session, dataid, {"Authorization": api_key})
            # _LOGGER.debug(pformat(data))
            sts.extend(CWA._parse_a000x(st) for st in data["records"]["Station"])
        return sts

    @dataclass
    class Area:
        AreaDesc: str = None
        AreaIntensity: str = None
        CountyName: str = None

    @dataclass
    class Earthquake:
        EarthquakeNo: str = None
        MagnitudeValue: str = None
        EpicenterLatitude: str = None
        EpicenterLongitude: str = None
        Location: str = None
        FocalDepth: str = None
        OriginTime: str = None
        ReportContent: str = None
        ReportImageURI: str = None
        Web: str = None
        areas: list = None

    @staticmethod
    async def get_earthquake_reports(session, api_key) -> list[Earthquake]:
        _attrs = ["EarthquakeInfo/EarthquakeMagnitude/MagnitudeValue",
                  "EarthquakeInfo/Epicenter/EpicenterLatitude", "EarthquakeInfo/Epicenter/EpicenterLongitude", "EarthquakeInfo/Epicenter/Location",
                  "EarthquakeInfo/FocalDepth", "EarthquakeInfo/OriginTime",
                  "EarthquakeNo", "ReportContent", 'ReportImageURI', 'Web']

        _attrs2 = ["AreaDesc", 'AreaIntensity', 'CountyName']

        res = []
        for dataid in ["E-A0015-001", "E-A0016-001"]:
            data = await _api_v1(session, dataid, {"Authorization": api_key})
            for da in data["records"]["Earthquake"]:
                r = parse_element(_attrs, da, CWA.Earthquake())
                r.areas = [parse_element(_attrs2, area, CWA.Area()) for area in da['Intensity']['ShakingArea']]
                res.append(r)
        return res

    @dataclass
    class Typhoon:
        cwaTyphoonName: str = None
        typhoonName: str = None
        year: str = None

    @staticmethod
    async def get_cyclone_reports(session, api_key) -> list[Typhoon]:
        _attrs = ["cwaTyphoonName", "typhoonName", "year"]
        res = []
        for dataid in ["W-C0034-005"]:
            data = await _api_v1(session, dataid, {"Authorization": api_key})

            for da in data["records"]["tropicalCyclones"]["tropicalCyclone"]:
                r = parse_element(_attrs, da, CWA.Typhoon())
            #     r['areas'] = [parse_element(_attrs2, area) for area in eq['Intensity']['ShakingArea']]
                res.append(r)
        return res


    @staticmethod
    async def get_observation_now(session, api_key, lat, lon):
        sts = await CWA.get_observation_stations(session, api_key)
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
    from pprint import pprint, pformat
    from dotenv import load_dotenv
    import os
    import aiohttp
    import operator

    load_dotenv()
    API_KEY = os.getenv("API_KEY")
    POS_LAT = float(os.getenv("POS_LAT"))
    POS_LON = float(os.getenv("POS_LON"))
    location = os.getenv("POS_LOCATION")

    logging.basicConfig(level=logging.DEBUG)

    async with aiohttp.ClientSession() as session:
        # dataid = "C-B0025-001"
        # dataid = "E-A0015-001"
        # dataid = "E-A0016-001"
        # dataid = "W-C0033-001"
        # dataid = "W-C0033-002"
        # dataid = "W-C0034-005"
        # data = await _api_v1(session, dataid, {"Authorization": API_KEY})
        # pprint(data)

        # forcasts = await CWA.get_forcast_twice_daily(session, API_KEY, location)
        # pprint(forcasts['Forecasts'][0])

        # forcasts = await CWA.get_forcast_hourly(session, API_KEY, location)
        # pprint(forcasts['Forecasts'][0])

        # await CWA.get_weather_warning(API_KEY, location)

        # res = await CWA.get_observation_now(session, API_KEY, POS_LAT, POS_LON)
        # pprint(res)

        # res = await CWA.get_earthquake_reports(session, API_KEY)
        # for r in res:
        #     pprint(r.ReportContent)

        # res = await CWA.get_cyclone_reports(session, API_KEY)
        # pprint(res)

        sts = await CWA.get_observation_stations(session, API_KEY)
        pprint(sts)
        # for st in sts:
        #     print(f"{st.ObsTime} {st.CountyName} {st.TownName} {st.AirTemperature} {st.RelativeHumidity} {st.AirPressure} {st.Weather} {st.StationName}")

        # data = await CWA.get_rain_stations(session, API_KEY)
        # pprint(data)


if __name__ == '__main__':
    asyncio.run(main())
