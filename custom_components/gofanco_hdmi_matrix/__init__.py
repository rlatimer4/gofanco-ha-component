"""The Gofanco HDMI Matrix integration."""
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import HomeAssistant

from .api import GofancoMatrixAPI
from .const import DOMAIN
from .coordinator import GofancoMatrixDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SELECT]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Gofanco HDMI Matrix from a config entry."""
    host = entry.data[CONF_HOST]
    name = entry.data[CONF_NAME]
    
    api = GofancoMatrixAPI(host)
    
    coordinator = GofancoMatrixDataUpdateCoordinator(hass, api, name)
    
    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Drain any in-flight device request before HA exits. Abandoning a
    # request mid-conversation hangs or RSTs the device's single-threaded
    # web server, which is what crashed it on HA restarts/updates.
    async def _async_on_hass_stop(event) -> None:
        await api.async_shutdown()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_on_hass_stop)
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.api.async_shutdown()

    return unload_ok
