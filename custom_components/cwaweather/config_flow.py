import re
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    ConfigEntry,
    OptionsFlow
)
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components import zone
from .cwa import CWA
from .moenv import MOENV
from .datagovtw import DataGovTw
from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_API_KEY_MOENV,
    CONF_LOCATION,
    TAIWAN_CITYS_TOWNS,
)

SELECT_ITEM_TRACK_PREFIX = "tracking: "
SELECT_ITEM_TRACK_REGEX = r'tracking:\s*(?P<name>.*\S)\s*\((?P<zone>zone\..*)\)'


def zone_info(hass, entity):
    if isinstance(entity, str):
        entity = hass.states.get(entity)
    if entity is None:
        return None
    return f"{SELECT_ITEM_TRACK_PREFIX}{entity.attributes["friendly_name"]} ({entity.entity_id})"


def _build_schema(hass, options: dict, is_options_flow: bool = False, show_advanced_options: bool = False) -> vol.Schema:
    options = options or {}

    taiwanlocations = []
    for entity in hass.states.async_all(zone.DOMAIN):
        taiwanlocations.append(zone_info(hass, entity))
    for k, v in TAIWAN_CITYS_TOWNS.items():
        taiwanlocations.extend(f"{k}-{vi}" for vi in v[1])

    spec = {
        vol.Required(CONF_API_KEY, description={"suggested_value": options.get(CONF_API_KEY, "")}): cv.string,
        vol.Required(CONF_API_KEY_MOENV, description={"suggested_value": options.get(CONF_API_KEY_MOENV, "")}): cv.string,
        vol.Required(CONF_LOCATION, description={"suggested_value": options.get(CONF_LOCATION, "")}): vol.In(taiwanlocations),
    }
    return vol.Schema(spec)

async def async_validate_input(hass, data, errors):
    session = async_get_clientsession(hass, verify_ssl=False)
    if not await CWA.check_api_key(session, data[CONF_API_KEY]):
        errors[CONF_API_KEY] = "invalid_api_key"
    if not await MOENV.check_api_key(session, data[CONF_API_KEY_MOENV]):
        errors[CONF_API_KEY_MOENV] = "invalid_api_key"

    name = data[CONF_LOCATION]
    if m := re.match(SELECT_ITEM_TRACK_REGEX, name):
        name = m['name']
        zone = m['zone']

        if (zoneentity := hass.states.get(zone)) is None:
            errors[CONF_LOCATION] = "Cant find tracking zone entity"
            return

        latitude = zoneentity.attributes.get("latitude")
        longitude = zoneentity.attributes.get("longitude")

        location = await DataGovTw.town_village_point_query(session, latitude, longitude)
        if location is None:
            errors[CONF_LOCATION] = "Cant find location infomation in Taiwan"
            return
    return name


class CWAWeatherConfigFlow(ConfigFlow, domain=DOMAIN):
    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return CWAWeatherOptionsFlow()

    async def async_step_user(self, user_input = None):
        errors = {}

        if user_input is not None:
            print(user_input, errors)
            name = await async_validate_input(self.hass, user_input, errors)
            print(user_input, errors)
            if not errors:
                return self.async_create_entry(title=name, data=user_input)

        return self.async_show_form(step_id="user", errors=errors, data_schema=_build_schema(self.hass, user_input))


class CWAWeatherOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input) -> ConfigFlowResult:
        errors = {}

        if user_input is not None:
            name = await async_validate_input(self.hass, user_input, errors)
            if not errors:
                self.hass.config_entries.async_update_entry(self.config_entry, title=name, data=user_input)
                return self.async_create_entry(title=name, data=user_input)

        else:
            user_input = {
                CONF_API_KEY: self.config_entry.data.get(CONF_API_KEY, ""),
                CONF_API_KEY_MOENV: self.config_entry.data.get(CONF_API_KEY_MOENV, ""),
                CONF_LOCATION: self.config_entry.data.get(CONF_LOCATION, ""),
            }
            if (loc := user_input.get(CONF_LOCATION)).startswith("zone."):
                user_input[CONF_LOCATION] = zone_info(self.hass, loc)

        return self.async_show_form(step_id="init", errors=errors, data_schema=_build_schema(self.hass, user_input, is_options_flow=True))
