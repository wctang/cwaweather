# https://data.moenv.gov.tw/swagger/

import logging
import urllib.parse
import asyncio
from dataclasses import dataclass
from .utils import url_get

async def _api_v2(session, dataset, params, is_json=True):
    return await url_get(session, f"https://data.moenv.gov.tw/api/v2/{dataset}?{urllib.parse.urlencode(params)}", is_json=is_json)


@dataclass
class AQIStation:
    aqi: int = None
    co: float = None
    co_8hr: float = None
    county: str = None
    latitude: float = None
    longitude: float = None
    no: float = None
    no2: int = None
    nox: float = None
    o3: int = None
    o3_8hr: int = None
    pm10: int = None
    pm10_avg: int = None
    pm2_5: int = None
    pm2_5_avg: int = None
    pollutant: str = None
    publishtime: str = None
    siteid: str = None
    sitename: str = None
    so2: float = None
    so2_avg: float = None
    status: str = None
    wind_direc: int = None
    wind_speed: float = None
    _distance: float = None

class MOENV:
    @staticmethod
    async def get_aqi_hourly(session, api_key) -> list[AQIStation]:
        dataid = "AQX_P_432"
        data = await _api_v2(session, dataid, {"api_key": api_key})
        res = []
        for rec in  data["records"]:
            s = AQIStation()
            for k, v in rec.items():
                if v in ['', '-']:
                    continue
                if k in s.__annotations__ or (k := k.replace(".", "_")) in s.__annotations__:
                    if s.__annotations__[k] == int:
                        setattr(s, k, int(v))
                    elif s.__annotations__[k] == float:
                        setattr(s, k, float(v))
                    else:
                        setattr(s, k, v)
            res.append(s)
        return res


async def main():
    from pprint import pprint, pformat
    from dotenv import load_dotenv
    import os
    import aiohttp
    import operator

    load_dotenv()
    API_KEY = os.getenv("MOENV_KEY")
    POS_LAT = float(os.getenv("POS_LAT"))
    POS_LON = float(os.getenv("POS_LON"))
    location = os.getenv("POS_LOCATION")

    logging.basicConfig(level=logging.DEBUG)


    async with aiohttp.ClientSession() as session:
        # dataid = "AQX_P_238"
        # data = await _api_v2(session, dataid, {"api_key": API_KEY})
        # records = data["records"]
        # pprint(records)

        res: list[AQIStation] = await MOENV.get_aqi_hourly(session, API_KEY)
        for re in res:
            if re.sitename == "鳳山":
                print(re)


if __name__ == '__main__':
    asyncio.run(main())
