# https://data.gov.tw/dataset/152915

import asyncio
from .utils import url_get
from xml.etree import ElementTree

class DataGovTw:
    async def town_village_point_query(hass, lat, lon):
        res = await url_get(hass, f"https://api.nlsc.gov.tw/other/TownVillagePointQuery/{lon}/{lat}", is_json = False)
        res = ElementTree.fromstring(res)

        city_name = res.find(".//ctyName")
        town_name = res.find(".//townName")

        if city_name is None or town_name is None:
            return None

        return f"{city_name.text}-{town_name.text}"

