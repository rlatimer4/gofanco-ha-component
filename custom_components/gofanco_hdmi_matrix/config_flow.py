"""Config flow for HDMI Matrix Switcher."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

class HDMIMatrixConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HDMI Matrix Switcher."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            # You could add a step here to validate the host is reachable
            # and responds correctly before creating the entry.
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title=f"HDMI Matrix ({host})",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): cv.string,
            }),
            errors=errors,
        )
