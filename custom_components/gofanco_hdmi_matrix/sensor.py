SENSOR_PY = '''"""Sensor platform for Gofanco HDMI Matrix."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
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
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    # Create sensors for each output showing current input
    for output in range(1, 5):  # Outputs 1-4
        entities.append(GofancoMatrixOutputSensor(coordinator, output))
    
    # Power status sensor
    entities.append(GofancoMatrixPowerSensor(coordinator))
    
    async_add_entities(entities)

class GofancoMatrixOutputSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing which input is connected to an output."""
    
    def __init__(self, coordinator, output: int):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._output = output
        
        # Get output name from last status
        status = coordinator.data or {}
        output_name = status.get(f"nameout{output}", f"Output {output}")
        
        self._attr_name = f"{output_name} Current Input"
        self._attr_unique_id = f"{DOMAIN}_output_{output}_current_input"
        self._attr_icon = "mdi:video-input-hdmi"
    
    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return DEVICE_INFO
    
    @property
    def native_value(self) -> Optional[str]:
        """Return the current input for this output."""
        if not self.coordinator.data:
            return None
        
        current_input = self.coordinator.data.get(f"out{self._output}")
        if current_input:
            input_name = self.coordinator.data.get(f"namein{current_input}", f"Input {current_input}")
            return input_name
        
        return None
    
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
        }

class GofancoMatrixPowerSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing power status of the matrix."""
    
    def __init__(self, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self._attr_name = "Matrix Power Status"
        self._attr_unique_id = f"{DOMAIN}_power_status"
        self._attr_icon = "mdi:power"
    
    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return DEVICE_INFO
    
    @property
    def native_value(self) -> Optional[str]:
        """Return the power status."""
        if not self.coordinator.data:
            return None
        
        power_status = self.coordinator.data.get("powstatus")
        return "On" if power_status == "1" else "Off"
    
    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}
        
        return {
            "raw_power_status": self.coordinator.data.get("powstatus"),
        }
