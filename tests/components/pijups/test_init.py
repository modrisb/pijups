"""Test PiJups initilization path initiated from __init__.py."""
from unittest.mock import patch
from homeassistant.components.hassio import (
    DOMAIN as HASSIO_DOMAIN,
    SERVICE_HOST_SHUTDOWN,
)
from homeassistant.components.pijups.interface import PiJups
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import RESTART_EXIT_CODE, SERVICE_HOMEASSISTANT_RESTART
from homeassistant.core import (
    DOMAIN as HOMEASSISTANT_DOMAIN,
    HomeAssistant,
    ServiceCall,
)
from homeassistant.components.pijups.const import (
    CONF_UPS_WAKEON_DELTA,
)

from .smbus2 import SMBus

from tests.components.pijups import common


async def test_async_setup_entry_default(hass: HomeAssistant):
    """Test if PiJups loads for standard emulated h/w configuration with default configuration."""
    SMBus.SIM_BUS = 1

    async def run_test_async_setup_entry_default(_hass, _entry):
        pass

    await common.pijups_setup_and_run_test(
        hass, True, run_test_async_setup_entry_default
    )


async def test_async_setup_entry_default_with_conn_err(hass: HomeAssistant):
    """Test if PiJups loads for standard emulated h/w configuration with default configuration."""
    SMBus.SIM_BUS = 1
    SMBus.add_init_cmd_delays(0x7C, 6, 0.11)    # I2C_ADDRESS_CMD
    async def run_test_async_setup_entry_default_with_conn_err(_hass, _entry):
        pass

    await common.pijups_setup_and_run_test(
        hass, True, run_test_async_setup_entry_default_with_conn_err
    )


async def test_entry_setup_unload(hass):
    """Test if PiJups unloads for standard emulated h/w configuration with default configuration."""
    SMBus.SIM_BUS = 1

    async def run_test_entry_setup_unload(hass, entry):
        assert entry.state is ConfigEntryState.LOADED

        await hass.config_entries.async_unload(entry.entry_id)

        assert entry.state is ConfigEntryState.NOT_LOADED

    await common.pijups_setup_and_run_test(hass, True, run_test_entry_setup_unload)


async def test_with_bad_firmware(hass: HomeAssistant):
    """Test integration initialization with wrong firmware version - pre 1.0 ."""
    SMBus.SIM_BUS = 1
    SMBus.add_init_adjustments(
        0xFD, [0x01, 0x00]
    )  # set hat emulator to not supported firmware

    await common.pijups_setup_and_run_test(hass, False, None)


async def test_with_wrong_i2c_address(hass: HomeAssistant):
    """Test integration initialization with wrong i2c address read by PiJuice API."""
    SMBus.SIM_BUS = 1
    SMBus.add_init_adjustments(
        0x7C, [255, 0]
    )  # set hat emulator to return wrong i2c address

    await common.pijups_setup_and_run_test(hass, False, None)


async def pijups_shutdown(hass, hassio_restart, ha_restart, powered, return_code, bat_charge=None):
    """Test event listeners registered during initalization."""
    SMBus.SIM_BUS = 1

    async def async_none(call: ServiceCall):
        pass

    hass.services.async_register(
        HOMEASSISTANT_DOMAIN, SERVICE_HOMEASSISTANT_RESTART, async_none
    )
    await hass.async_block_till_done()

    hass.services.async_register(HASSIO_DOMAIN, SERVICE_HOST_SHUTDOWN, async_none)
    await hass.async_block_till_done()

    async def run_pijups_shutdown(hass, entry):
        pijups: PiJups = await common.get_pijups(hass, entry)
        pijups.interface.i2cbus.set_power(powered, powered)
        if bat_charge is not None:
            if bat_charge >= 0:
                pijups.interface.i2cbus._set_buff(0x41, [bat_charge, 0])
            else:
                pijups.interface.i2cbus.add_cmd_delays(0x41, 6, 0.11)    # CHARGE_LEVEL_CMD
        pijups.get_piju_status(True)

        await hass.async_block_till_done()

        if ha_restart:
            await hass.services.async_call(
                HOMEASSISTANT_DOMAIN,
                SERVICE_HOMEASSISTANT_RESTART,
                blocking=True,
            )
        if hassio_restart:
            await hass.services.async_call(
                HASSIO_DOMAIN,
                SERVICE_HOST_SHUTDOWN,
                blocking=True,
            )
        await hass.async_block_till_done()
        pijups.interface.i2cbus.set_write_log(True)
        await hass.async_stop(return_code)
        power_off_needed = (
            (hassio_restart or not ha_restart)
            and not powered
            and return_code != RESTART_EXIT_CODE
        )
        writes_received = pijups.interface.i2cbus.set_write_log(False)
        power_off_executed = (
            writes_received.get(99) is not None and writes_received.get(98) is not None
        )
        assert power_off_needed == power_off_executed

    await common.pijups_setup_and_run_test(hass, True, run_pijups_shutdown)


async def test_poff_req_from_service_no_ext_power_no_restart(hass):
    """Test power down sequence initiated from shutdown service with no external power and no restart explicitly requested."""
    await pijups_shutdown(hass, True, False, False, 0)


async def test_poff_req_from_service_no_ext_power_no_restart_79(hass):
    """Test power down sequence initiated from shutdown service with no external power and no restart explicitly requested, configured to use wakeon with readbale charge."""
    config_options = common.CONFIG_OPTIONS.copy()
    config_options[CONF_UPS_WAKEON_DELTA] = 0
    with patch("tests.components.pijups.common.CONFIG_OPTIONS", new=config_options):
        await pijups_shutdown(hass, True, False, False, 0, 79)


async def test_poff_req_from_service_no_ext_power_no_restart_no_charge(hass):
    """Test power down sequence initiated from shutdown service with no external power and no restart explicitly requested, configured to use wakeon with selective connection failure for charge read."""
    config_options = common.CONFIG_OPTIONS.copy()
    config_options[CONF_UPS_WAKEON_DELTA] = 0
    with patch("tests.components.pijups.common.CONFIG_OPTIONS", new=config_options):
        await pijups_shutdown(hass, True, False, False, 0, -1)


async def test_poff_req_from_service_no_ext_power_restart(hass):
    """Test power down sequence initiated from shutdown service with no external power and restart explicitly requested."""
    await pijups_shutdown(hass, True, False, False, RESTART_EXIT_CODE)


async def test_poff_req_from_service_ext_power_no_restart(hass):
    """Test power down sequence initiated from shutdown service with external power and no restart explicitly requested."""
    await pijups_shutdown(hass, True, False, True, 0)


async def test_poff_req_from_service_ext_power_restart(hass):
    """Test power down sequence initiated from shutdown service with external power and restart explicitly requested."""
    await pijups_shutdown(hass, False, True, True, RESTART_EXIT_CODE)


async def test_poff_req_from_ui_no_ext_power_no_restart(hass):
    """Test power down sequence initiated from UI with no external power and no restart explicitly requested."""
    await pijups_shutdown(hass, False, True, False, 0)


async def test_poff_req_from_ui_no_ext_power_restart(hass):
    """Test power down sequence initiated from UI with no external power and restart explicitly requested."""
    await pijups_shutdown(hass, False, True, False, RESTART_EXIT_CODE)


async def test_poff_req_from_ui_ext_power_no_restart(hass):
    """Test power down sequence initiated from UI with external power and no restart explicitly requested."""
    await pijups_shutdown(hass, False, True, True, 0)


async def test_poff_req_from_ui_ext_power_restart(hass):
    """Test power down sequence initiated from UI with external power and restart explicitly requested."""
    await pijups_shutdown(hass, False, True, True, RESTART_EXIT_CODE)
