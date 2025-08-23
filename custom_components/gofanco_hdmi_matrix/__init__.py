INIT_PY = '''"""The Gofanco HDMI Matrix integration."""
import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GofancoMatrixAPI
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SELECT, Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Gofanco HDMI Matrix from a config entry."""
    host = entry.data[CONF_HOST]
    name = entry.data[CONF_NAME]
    
    api = GofancoMatrixAPI(host)
    
    coordinator = GofancoMatrixDataUpdateCoordinator(hass, api, name)
    
    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok

class GofancoMatrixDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""
    
    def __init__(self, hass: HomeAssistant, api: GofancoMatrixAPI, name: str):
        """Initialize."""
        self.api = api
        self.name = name
        
        super().__init__(
            hass,
            _LOGGER,
            name="Gofanco HDMI Matrix",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
    
    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.api.async_get_status()
        except Exception as exception:
            raise UpdateFailed(f"Error communicating with API: {exception}")
