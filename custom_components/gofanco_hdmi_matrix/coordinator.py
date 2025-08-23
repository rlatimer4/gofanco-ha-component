import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GofancoMatrixAPI
from .const import UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

class GofancoMatrixDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""
    
    def __init__(self, hass: HomeAssistant, api: GofancoMatrixAPI, name: str):
        """Initialize the coordinator."""
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
