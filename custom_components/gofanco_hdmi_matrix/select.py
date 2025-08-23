import logging
from typing import Any, Dict, Optional

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_INFO, DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    # Create a select entity for each output
    for output in range(1, 5):  # Outputs 1-4
        entities.append(GofancoMatrixOutputSelect(coordinator, output))
    
    async_add_entities(entities)

class GofancoMatrixOutputSelect(CoordinatorEntity, SelectEntity):
    """Select entity for choosing input source for an output."""
    
    def __init__(self, coordinator, output: int):
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._output = output
        
        # Get output name from last status
        status = coordinator.data or {}
        output_name = status.get(f"nameout{output}", f"Output {output}")
        
        self._attr_name = f"{output_name} Input Source"
        self._attr_unique_id = f"{DOMAIN}_output_{output}_input_select"
        self._attr_icon = "mdi:video-input-hdmi"
        
        # Set up options - will be updated when coordinator data is available
        self._update_options()
    
    def _update_options(self):
        """Update the available options based on current device status."""
        if not self.coordinator.data:
            # Default options if no data available yet
            self._attr_options = [f"Input {i}" for i in range(1, 5)]
        else:
            # Use custom input names from device
            options = []
            for i in range(1, 5):
                input_name = self.coordinator.data.get(f"namein{i}", f"Input {i}")
                options.append(input_name)
            self._attr_options = options
    
    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return DEVICE_INFO
    
    @property
    def current_option(self) -> Optional[str]:
        """Return the currently selected input."""
        if not self.coordinator.data:
            return None
        
        current_input = self.coordinator.data.get(f"out{self._output}")
        if current_input:
            input_num = int(current_input)
            input_name = self.coordinator.data.get(f"namein{input_num}", f"Input {input_num}")
            return input_name
        
        return None
    
    async def async_select_option(self, option: str) -> None:
        """Select an input source."""
        if not self.coordinator.data:
            _LOGGER.error("No coordinator data available")
            return
        
        # Find the input number for the selected option
        input_num = None
        for i in range(1, 5):
            input_name = self.coordinator.data.get(f"namein{i}", f"Input {i}")
            if input_name == option:
                input_num = i
                break
        
        if input_num is None:
            _LOGGER.error("Could not find input number for option: %s", option)
            return
        
        success = await self.coordinator.api.async_set_output(self._output, input_num)
        
        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error(
                "Failed to set output %s to input %s (%s)",
                self._output,
                input_num,
                option,
            )
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}
        
        current_input = self.coordinator.data.get(f"out{self._output}")
        
        return {
            "output": self._output,
            "current_input_number": current_input,
            "output_name": self.coordinator.data.get(f"nameout{self._output}", f"Output {self._output}"),
            "available_inputs": {
                i: self.coordinator.data.get(f"namein{i}", f"Input {i}")
                for i in range(1, 5)
            },
        }
    
    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._update_options()
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_options()
        super()._handle_coordinator_update()
