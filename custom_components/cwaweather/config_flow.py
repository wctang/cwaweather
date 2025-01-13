from typing import Any
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    ConfigEntry,
    OptionsFlow
)
import voluptuous as vol

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_LOCATION,
    CONF_NAME,
)
from .cwa import CWA_COUNTY_CODE

def _build_schema(options: dict, is_options_flow: bool = False, show_advanced_options: bool = False) -> vol.Schema:
    options = options or {}
    spec = {
        vol.Required(CONF_API_KEY, default=options.get(CONF_API_KEY, "")): str,
        vol.Optional(CONF_NAME, default=options.get(CONF_NAME, "")): str,
        vol.Required(CONF_LOCATION, default=options.get(CONF_LOCATION, "")): vol.In(CWA_COUNTY_CODE.keys())
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

        return self.async_show_form(step_id="user", errors=errors, data_schema=_build_schema(user_input))


class CWAWeatherOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input = None) -> ConfigFlowResult:
        print("async_step_init")
        if user_input is not None:
            name = user_input.get(CONF_NAME, user_input.get(CONF_LOCATION))
            self.hass.config_entries.async_update_entry(self.config_entry, title=name, data=user_input)
            return self.async_create_entry(title=name, data=user_input)

        else:
            user_input = self.config_entry.data

        return self.async_show_form(step_id="init", data_schema=_build_schema(user_input, is_options_flow=True))


