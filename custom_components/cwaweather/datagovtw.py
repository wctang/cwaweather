# https://data.gov.tw/dataset/152915

from .utils import url_get
from xml.etree import ElementTree

class DataGovTw:
    async def town_village_point_query(session, lat, lon):
        res = await url_get(session, f"https://api.nlsc.gov.tw/other/TownVillagePointQuery/{lon}/{lat}", is_json = False)
        res = ElementTree.fromstring(res)

        city_name = res.find(".//ctyName")
        town_name = res.find(".//townName")

        if city_name is None or town_name is None:
            return None

        return city_name.text, town_name.text

