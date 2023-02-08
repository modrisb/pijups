"""Test PiJups diagnostics implementation."""

from homeassistant.components.pijups import diagnostics
from homeassistant.components.pijups.const import CONF_I2C_ADDRESS, CONF_I2C_BUS
from homeassistant.components.pijups.interface import PiJups
from homeassistant.core import HomeAssistant

from .smbus2 import SMBus

from tests.components.pijups import common


def check_diag_log(diag_log):
    """Assert existance of mandatory keys in diagnostics report."""
    assert diag_log.get(CONF_I2C_BUS) is not None
    assert diag_log.get(CONF_I2C_ADDRESS) is not None
    assert diag_log.get("HAT EEPROM address") is not None
    assert diag_log.get("HAT Firmware version") is not None
    assert diag_log.get("Device status") is not None
    assert diag_log.get("HAT profile status") is not None
    assert diag_log.get("HAT battery profile") is not None
    assert diag_log.get("HAT battery ext profile") is not None
    assert diag_log.get("HAT power inputs") is not None
    assert diag_log.get("HAT power regulator mode") is not None
    assert diag_log.get("HAT run pin configuration") is not None
    assert diag_log.get("PowerOff configuration") is not None
    assert diag_log.get("WakeUpOnCharge configuration") is not None
    assert diag_log.get("SystemPowerSwitch configuration") is not None


async def test_with_fw16_plus(hass: HomeAssistant):
    """Test diagnostics log content for hat fw version starting from 1.6."""
    SMBus.SIM_BUS = 1
    SMBus.add_init_cmd_delays(0xF6, 6, 0.11)    # LOGGING_CMD

    async def run_test_with_fw16_plus(hass, entry):
        pijups: PiJups = await common.get_pijups(hass, entry)
        button_events_flags = [1, 0, 0]  # PRESS on SW1
        pijups.interface.i2cbus._set_buff(0x45, button_events_flags)
        fault_events_flags = [0b11101111, 0]  # all faults on
        pijups.interface.i2cbus._set_buff(0x44, fault_events_flags)
        diag_log = await diagnostics.async_get_config_entry_diagnostics(hass, entry)

        # assert mandatory for v1.6 keys in diagnostics report
        assert diag_log.get("Circular log") is None
        assert diag_log.get("Circular log settings") is not None
        assert diag_log.get("Circular log contents") is not None

        check_diag_log(diag_log)

    await common.pijups_setup_and_run_test(hass, True, run_test_with_fw16_plus)


async def test_with_fw15_minus(hass: HomeAssistant):
    """Test diagnostics log content for hat fw version before 1.6."""
    SMBus.SIM_BUS = 1
    SMBus.add_init_adjustments(0xFD, [0x15, 0x00])  # set hat emulator to fw v1.5

    async def run_test_with_fw15_minus(hass, entry):
        diag_log = await diagnostics.async_get_config_entry_diagnostics(hass, entry)

        # assert mandatory for v1.5 keys in diagnostics report
        assert diag_log.get("Circular log") is not None
        assert diag_log.get("Circular log settings") is None
        assert diag_log.get("Circular log contents") is None

        check_diag_log(diag_log)

    await common.pijups_setup_and_run_test(hass, True, run_test_with_fw15_minus)
