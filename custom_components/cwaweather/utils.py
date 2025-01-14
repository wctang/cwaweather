import logging
import asyncio
import async_timeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

# async def _aio_call(url, timeout = 10):
#     async with aiohttp.ClientSession() as session:
#         async with async_timeout.timeout(timeout):
#             async with session.get(url) as response:
#                 response.raise_for_status()
#                 return await response.json()

# _data_cache = {}
# async def _api_v1(dataid, params):
#     url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{dataid}?{urllib.parse.urlencode(params)}"

#     ts = datetime.now().timestamp()
#     _to_delete = [k for k, (t, r) in _data_cache.items() if ts - t >= 60]
#     for k in _to_delete:
#         del _data_cache[k]

#     while True:
#         if url in _data_cache:
#             t, r = _data_cache[url]
#             if r is None:
#                 _LOGGER.debug("%s wait...", url)
#                 await asyncio.sleep(.5)
#                 continue
#             else:
#                 _LOGGER.debug("%s cached", url)
#                 data = r
#                 break
#         else:
#             _data_cache[url] = (ts, None)
#             data = await _aio_call(url)
#             _data_cache[url] = (ts, data)
#             _LOGGER.debug("%s fetched", url)
#             break

#     return copy.deepcopy(data)


async def url_get(hass, url, is_json = True, verify_ssl = False):
    _LOGGER.debug(url)
    session = async_get_clientsession(hass, verify_ssl=verify_ssl)
    async with session.get(url) as response:
        if is_json:
            return await response.json()
        else:
            return await response.text()
