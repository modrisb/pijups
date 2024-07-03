"""The PiJuPS HAT integration - setup."""
from __future__ import annotations

from datetime import timedelta
import importlib
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant

from .const import BASE, DOMAIN
from .sensor import PiJups

_LOGGER = logging.getLogger(__name__)

#  List of platforms to support. There should be a matching .py file for each,
#  eg <cover.py> and <sensor.py>
PLATFORMS: list[Platform] = [Platform.SENSOR]

def get_local_platform_module(platform, name):
    return importlib.import_module("." + platform, name)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PiJups from a config entry."""
    # Store an instance of the "connecting" class that does the work of speaking
    # with your actual devices.
    hass.data.setdefault(DOMAIN, {})

    pijups: PiJups = PiJups(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = {BASE: pijups}
    await hass.async_add_executor_job(pijups.configure_device, hass, entry)
    # set scan interval to integration configuration for all integrated platforms
    for platform in PLATFORMS:
        module = await hass.async_add_executor_job(get_local_platform_module, platform, __name__)
        if "SCAN_INTERVAL" in dir(module):
            module.SCAN_INTERVAL = timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL)
            )

    # This creates each HA object for each platform your device requires.
    # It's done by calling the `async_setup_entry` function in each platform module.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("async_setup_entry completed")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    _LOGGER.debug("async_unload_entry completed")
    return unload_ok
