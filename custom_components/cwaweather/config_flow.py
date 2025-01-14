from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    ConfigEntry,
    OptionsFlow
)
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import selector, TextSelector, TextSelectorConfig, TextSelectorType

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_NAME,
    CONF_LOCATION,
    CONF_TRACK_HOME,
    TAIWAN_CITYS_TOWNS,
)

def _build_schema(hass, options: dict, is_options_flow: bool = False, show_advanced_options: bool = False) -> vol.Schema:
    options = options or {}

    taiwanlocations = [CONF_TRACK_HOME]
    for k, v in TAIWAN_CITYS_TOWNS.items():
        taiwanlocations.extend(f"{k}-{vi}" for vi in v[1])

    spec = {
        vol.Required(CONF_API_KEY, default=options.get(CONF_API_KEY, "")): cv.string,
        vol.Optional(CONF_NAME, description={"suggested_value": hass.config.location_name}): cv.string,
        vol.Required(CONF_LOCATION, default=options.get(CONF_LOCATION, CONF_TRACK_HOME)): vol.In(taiwanlocations),
    }
    return vol.Schema(spec)

class CWAWeatherConfigFlow(ConfigFlow, domain=DOMAIN):
    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return CWAWeatherOptionsFlow()

    async def async_step_user(self, user_input = None):
        errors = {}

        if user_input is not None:
            name = user_input.get(CONF_NAME) or user_input.get(CONF_LOCATION)
            return self.async_create_entry(title=name, data=user_input)

        return self.async_show_form(step_id="user", errors=errors, data_schema=_build_schema(self.hass, user_input))



class CWAWeatherOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input = None) -> ConfigFlowResult:
        if user_input is not None:
            name = user_input.get(CONF_NAME) or user_input.get(CONF_LOCATION)
            self.hass.config_entries.async_update_entry(self.config_entry, title=name, data=user_input)
            return self.async_create_entry(title=name, data=user_input)

        else:
            user_input = self.config_entry.data

        return self.async_show_form(step_id="init", data_schema=_build_schema(self.hass, user_input, is_options_flow=True))
