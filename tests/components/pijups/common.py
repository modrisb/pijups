"""Test PiJups initilization path initiated from __init__.py."""
from unittest.mock import patch

from homeassistant.components.pijups.const import (
    BASE,
    CONF_I2C_ADDRESS,
    CONF_I2C_BUS,
    CONF_UPS_DELAY,
    CONF_UPS_WAKEON_DELTA,
    DEFAULT_I2C_ADDRESS,
    DEFAULT_I2C_BUS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UPS_DELAY,
    DEFAULT_UPS_WAKEON_DELTA,
    DOMAIN,
)
from homeassistant.components.pijups.interface import PiJups
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant

from .smbus2 import SMBus

from tests.common import MockConfigEntry

CONFIG_DATA = {CONF_I2C_BUS: DEFAULT_I2C_BUS, CONF_I2C_ADDRESS: DEFAULT_I2C_ADDRESS}

CONFIG_OPTIONS = {
    CONF_UPS_DELAY: DEFAULT_UPS_DELAY,
    CONF_UPS_WAKEON_DELTA: DEFAULT_UPS_WAKEON_DELTA,
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
}

I2C_CMD_EXECUTION_TIMEOUT = 0.11
I2C_CMD_EXCEPTION_TIMEOUT = 4

# pytest tests/components/pijups/
# pytest tests/components/pijups/ --cov=homeassistant.components.pijups --cov-report term-missing -vv


async def pijups_setup_and_run_test(
    hass: HomeAssistant, expected_entry_setup, run_test_case
):
    """Test if PiJups loads for standard emulated h/w configuration with default configuration."""
    with patch("homeassistant.components.pijups.pijuice.SMBus", new=SMBus):
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id=f"i2c{CONF_I2C_BUS}x{DEFAULT_I2C_ADDRESS}",
            data=CONFIG_DATA,
            options=CONFIG_OPTIONS,
        )

        # Load config_entry.
        entry.add_to_hass(hass)
        assert (
            await hass.config_entries.async_setup(entry.entry_id)
            == expected_entry_setup
        )

        if expected_entry_setup:
            await run_test_case(hass, entry)


async def get_pijups(hass: HomeAssistant, entry) -> PiJups:
    """Read PiJups interface object with wait for initilization completion."""
    await hass.async_block_till_done()
    pijups: PiJups = hass.data[DOMAIN][entry.entry_id][BASE]
    return pijups
