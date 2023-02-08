"""The PiJuPS HAT integration - handle diagnostics."""
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant

from .const import BASE, CONF_I2C_ADDRESS, CONF_I2C_BUS, DOMAIN
from .sensor import PiJups

_LOGGER = logging.getLogger(__name__)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return await hass.async_add_executor_job(get_config_entry_diagnostics, hass, entry)


def get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry in sync mode."""
    pijups: PiJups = hass.data[DOMAIN][entry.entry_id][BASE]
    info: dict = {
        CONF_I2C_BUS: pijups.i2c_bus,
        CONF_I2C_ADDRESS: f"0x{pijups.i2c_address:02x}",
        "HAT EEPROM address": pijups.call_pijuice_with_error_check(
            pijups.config.GetIdEepromAddress
        ),
        "HAT Firmware version": pijups.fw_version,
        "Sensor scan interval": entry.data.get(CONF_SCAN_INTERVAL),
    }
    status = pijups.call_pijuice_with_error_check(pijups.status.GetStatus)
    info["Device status"] = status
    if status.get("isFault"):
        faults = pijups.call_pijuice_with_error_check(pijups.status.GetFaultStatus)
        info["Reported faults"] = faults
    if status.get("isButton"):
        buttons = pijups.call_pijuice_with_error_check(pijups.status.GetButtonEvents)
        info["Reported button events"] = buttons
    if pijups.fw_version < "1.6":
        info["Circular log"] = "Not available prior firmware version 1.6"
    else:
        info["Circular log settings"] = pijups.get_diag_log_config()
        info["Circular log contents"] = pijups.get_diag_log().get("data", [])
    profile_status = pijups.call_pijuice_with_error_check(
        pijups.config.GetBatteryProfileStatus, error_log_level=logging.INFO
    )
    info["HAT profile status"] = profile_status
    data = pijups.call_pijuice_with_error_check(
        pijups.config.GetBatteryProfile, error_log_level=logging.INFO
    )
    info["HAT battery profile"] = data
    data = pijups.call_pijuice_with_error_check(
        pijups.config.GetBatteryExtProfile, error_log_level=logging.INFO
    )
    info["HAT battery ext profile"] = data
    # power input configuration
    data = pijups.call_pijuice_with_error_check(
        pijups.config.GetPowerInputsConfig, error_log_level=logging.INFO
    )
    info["HAT power inputs"] = data
    data = pijups.call_pijuice_with_error_check(pijups.config.GetPowerRegulatorMode)
    info["HAT power regulator mode"] = data
    data = pijups.call_pijuice_with_error_check(pijups.config.GetRunPinConfig)
    info["HAT run pin configuration"] = data
    data = pijups.call_pijuice_with_error_check(
        pijups.config.GetButtonConfiguration, "SW1"
    )
    info["SW1 button configuration"] = data
    data = pijups.call_pijuice_with_error_check(
        pijups.config.GetButtonConfiguration, "SW2"
    )
    info["SW2 button configuration"] = data
    data = pijups.call_pijuice_with_error_check(
        pijups.config.GetButtonConfiguration, "SW3"
    )
    info["SW3 button configuration"] = data

    data = pijups.call_pijuice_with_error_check(
        pijups.power.GetPowerOff, error_log_level=logging.INFO
    )
    info["PowerOff configuration"] = data
    data = pijups.call_pijuice_with_error_check(
        pijups.power.GetWakeUpOnCharge, error_log_level=logging.INFO
    )
    info["WakeUpOnCharge configuration"] = data
    data = pijups.call_pijuice_with_error_check(
        pijups.power.GetSystemPowerSwitch, error_log_level=logging.INFO
    )
    info["SystemPowerSwitch configuration"] = data
    _LOGGER.debug("get_config_entry_diagnostics %s", info)
    return info
