# https://data.gov.tw/dataset/152915

import asyncio
import aiohttp
import async_timeout
from xml.etree import ElementTree

async def _aio_call(url, is_json: bool):
    async with aiohttp.ClientSession() as session:
        async with async_timeout.timeout(10):
            async with session.get(url) as response:
                response.raise_for_status()
                if is_json:
                    return await response.json()
                else:
                    return await response.text()


class DataGovTw:
     async def town_village_point_query(lat, lon):
        res = await _aio_call(f"https://api.nlsc.gov.tw/other/TownVillagePointQuery/{lon}/{lat}", False)
        res = ElementTree.fromstring(res)

        city_name = res.find(".//ctyName")
        town_name = res.find(".//townName")

        if city_name is None or town_name is None:
            return None

        return f"{city_name.text}-{town_name.text}"

