import logging
import asyncio
import async_timeout
from datetime import datetime
import copy
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


async def _url_get(hass, url, is_json = True, verify_ssl = False, timeout = 10):
    session = async_get_clientsession(hass, verify_ssl=verify_ssl)
    async with async_timeout.timeout(timeout):
        async with session.get(url) as response:
            response.raise_for_status()
            if is_json:
                return await response.json()
            else:
                return await response.text()


_data_cache = {}
def _cache_clean():
    ts = datetime.now().timestamp()
    for k in [k for k, (t, r) in _data_cache.items() if ts - t >= 60]:
        del _data_cache[k]
    return ts

async def _cache_hit_or_fetch(url, ts, hass, is_json, verify_ssl, timeout):
    if url not in _data_cache:
        _data_cache[url] = (ts, None)
        try:
            data = await _url_get(hass, url, is_json, verify_ssl, timeout)
            _data_cache[url] = (ts, data)
            _LOGGER.debug("%s fetched", url)
            return copy.deepcopy(data)
        except:
            del _data_cache[url]

    _, data = _data_cache[url]
    if data is not None:
        _LOGGER.debug("%s cached", url)
        return copy.deepcopy(data)

    return False

async def url_get(hass, url, is_json = True, verify_ssl = False, timeout = 10):
    ts = _cache_clean()
    while True:
        if data := await _cache_hit_or_fetch(url, ts, hass, is_json, verify_ssl, timeout):
            return data

        _LOGGER.debug("%s wait...", url)
        await asyncio.sleep(.5)
        # _cache_clean()
