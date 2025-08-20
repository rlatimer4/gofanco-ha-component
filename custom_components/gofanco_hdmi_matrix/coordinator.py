"""DataUpdateCoordinator for the HDMI Matrix Switcher."""
import asyncio
import json
import logging
from datetime import timedelta

import aiohttp
import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class HDMIMatrixCoordinator(DataUpdateCoordinator):
    """Coordinates updates from the HDMI Matrix."""

    def __init__(self, hass: HomeAssistant, host: str):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.host = host
        self.api_url = f"http://{self.host}/inform.cgi"

    async def _async_update_data(self):
        """Fetch data from the HDMI Matrix."""
        headers = {"Content-Type": "application/json;charset=UTF-8"}
        payload = '{"param1":"1"}'
        
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.api_url, data=payload, headers=headers) as response:
                        # The device may return a non-200 status but still have valid JSON
                        # We read the text and attempt to parse it regardless of status
                        raw_text = await response.text()
                        if not raw_text:
                            raise UpdateFailed("Empty response from HDMI Matrix")
                        # Use hass.async_add_executor_job for the blocking json.loads call
                        return await self.hass.async_add_executor_job(json.loads, raw_text)

        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            raise UpdateFailed(f"Error communicating with HDMI Matrix: {err}")
        except json.JSONDecodeError as err:
            raise UpdateFailed(f"Invalid JSON received from HDMI Matrix: {err} - Response was: {raw_text}")
