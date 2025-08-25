"""Config flow for Gofanco HDMI Matrix integration."""
import asyncio
import ipaddress
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api import GofancoMatrixAPI
from .const import DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

def validate_ip(value: str) -> str:
    """Validate IP address format."""
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        raise vol.Invalid("Invalid IP address format")

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): validate_ip,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    }
)

async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect."""
    api = GofancoMatrixAPI(data[CONF_HOST])
    
    if not await api.async_test_connection():
        raise CannotConnect
    
    return {"title": data[CONF_NAME]}

class CannotConnect(Exception):
    """Error to indicate we cannot connect."""

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gofanco HDMI Matrix."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            await self.async_set_unique_id(f"{DOMAIN}_{user_input[CONF_HOST]}")
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
