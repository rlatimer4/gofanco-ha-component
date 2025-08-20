"""Select entities for the HDMI Matrix Switcher."""
import logging

import aiohttp
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HDMIMatrixCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select entities."""
    coordinator: HDMIMatrixCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        HDMIMatrixSelect(coordinator, i) for i in range(1, 5)
    ]
    
    async_add_entities(entities)


class HDMIMatrixSelect(CoordinatorEntity[HDMIMatrixCoordinator], SelectEntity):
    """Representation of an HDMI Matrix output select entity."""

    def __init__(self, coordinator: HDMIMatrixCoordinator, output_index: int) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._output_index = output_index
        self._attr_unique_id = f"{coordinator.host}_output_{output_index}"
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)},
            name="4x4 HDMI Matrix",
            manufacturer="WebUI Controlled",
            model="4x4 Matrix Switch",
            configuration_url=f"http://{coordinator.host}",
        )

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self.coordinator.data.get(f"nameout{self._output_index}", f"Output {self._output_index}")

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        if not self.coordinator.data:
            return None
        current_input = self.coordinator.data.get(f"out{self._output_index}")
        if current_input:
            return self.coordinator.data.get(f"namein{current_input}")
        return None

    @property
    def options(self) -> list[str]:
        """Return the list of available options."""
        if not self.coordinator.data:
            return []
        return [
            self.coordinator.data.get(f"namein{i}", f"Input {i}") for i in range(1, 5)
        ]

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        input_to_set = None
        for i in range(1, 5):
            if self.coordinator.data.get(f"namein{i}") == option:
                input_to_set = i
                break
        
        if input_to_set is None:
            _LOGGER.error("Could not find input for option %s", option)
            return

        url = f"http://{self.coordinator.host}/inform.cgi"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        payload = f"out{self._output_index}={input_to_set}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=payload, headers=headers) as response:
                    if response.status >= 400:
                        _LOGGER.error("Error switching input: %s", await response.text())
        except aiohttp.ClientError as err:
            _LOGGER.error("Error communicating with HDMI Matrix to switch input: %s", err)

        await self.coordinator.async_request_refresh()
