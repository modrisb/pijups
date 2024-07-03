"""The PiJuPS HAT integration - interface to PiJuice API."""

from datetime import datetime
from datetime import UTC
import logging
import os
import re
import time

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    BASE,
    CONF_ADDRESS_OPTIONS,
    CONF_BATTERY_PROFILE,
    CONF_BATTERY_TEMP_SENSE_CONFIG,
    CONF_BUS_OPTIONS,
    CONF_DIAG_LOG_CONFIG,
    CONF_FIRMWARE_SELECTION,
    CONF_FW_UPGRADE_PATH,
    CONF_I2C_ADDRESS,
    CONF_I2C_ADDRESSES_TO_SEARCH,
    CONF_I2C_BUS,
    CONF_I2C_BUSES_TO_SEARCH,
    CONF_MANUFACTURER,
    CONF_MODEL,
    DEFAULT_FW_UTILITY_NAME,
    DEFAULT_FW_FILE_NAME,
    DEFAULT_NAME,
    DEFAULT_NO_FIRMWARE_UPGRADE,
    DOMAIN,
    MAX_WAKEON_DELTA,
)
from .pijuice import PiJuice, PiJuiceConfig, PiJuiceStatus
from .pijuice_log import LOG_ENABLE_LIST, LOGGING_CMD, GetPiJuiceLog

bat_status_enum = PiJuiceStatus.batStatusEnum
power_in_status_enum = PiJuiceStatus.powerInStatusEnum

_LOGGER = logging.getLogger(__name__)


class PiJups:
    """PiJuice interface handling class."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize interface internal structures."""
        self.hass = hass
        self.i2c_address = int(entry.data.get(CONF_I2C_ADDRESS))
        self.i2c_bus = int(entry.data.get(CONF_I2C_BUS))
        self.config_entry = entry
        self.pijups = None
        self.interface = None
        self.status = None
        self.config = None
        self.power = None
        self.rtcalarm = None
        self.powered = None
        self.fw_version = None
        self.piju_device_info = None
        self.piju_enabled = True
        self.piju_status = None
        self.piju_status_read_at = None
        _LOGGER.debug(
            "Initializing PiJups unique_id=%s i2c_bus=%d i2c_address=0x%x",
            entry.unique_id,
            self.i2c_bus,
            self.i2c_address,
        )

    def configure_device(self, hass: HomeAssistant, entry: ConfigEntry):
        """Prepare HAT interface (including limited device protocol verification: address and firmare version checks)."""
        self.pijups = PiJuice(self.i2c_bus, self.i2c_address)
        self.interface = self.pijups.interface
        self.status = self.pijups.status
        self.config = self.pijups.config
        self.power = self.pijups.power
        self.rtcalarm = self.pijups.rtcAlarm
        sleep_time = 0.05
        time.sleep(sleep_time)
        # check configured i2c address and one recognized by PiJuice API
        for _tr in (1, 2, 3, 4, 5):
            hex_addr = self.call_pijuice_with_error_check(
                self.pijups.config.GetAddress, self.i2c_bus
            )
            if hex_addr is not None:
                hex_addr = int(hex_addr, 16)
                break
            sleep_time = sleep_time * 2
            time.sleep(sleep_time)

        if self.i2c_address == hex_addr:
            fw_version = self.call_pijuice_with_error_check(
                self.pijups.config.GetFirmwareVersion
            )
            if fw_version is not None:
                self.fw_version = fw_version.get("version")
            if self.fw_version is None or self.fw_version < "1.0":
                _LOGGER.critical(
                    "%s firmware version must be 1.0 or higher, but got %s, exiting",
                    CONF_MODEL,
                    self.fw_version,
                )
                raise BlockingIOError

        if self.i2c_address != hex_addr:
            _LOGGER.critical(
                "I2c addresses does not match: selected 0x%x, read 0x%s, check system/PiJuice set-up",
                self.i2c_address,
                hex_addr,
            )
            raise BlockingIOError

        self.piju_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=DEFAULT_NAME,
            sw_version=self.fw_version,
            manufacturer=CONF_MANUFACTURER,
            model=CONF_MODEL,
        )
        self.set_led_in_transition()
        self.get_piju_status(True)

        return True

    def get_piju_status(self, force_update=False):
        """Get cached HAT status, use scan interval as caching time parameter."""
        time_now = datetime.now(UTC)
        if force_update or (
            time_now - self.piju_status_read_at
        ).total_seconds() * 1.1 > self.config_entry.options.get(CONF_SCAN_INTERVAL):
            status = self.call_pijuice_with_error_check(self.status.GetStatus)
            if status is not None:
                self.powered = (
                    status.get("powerInput") == PiJuiceStatus.powerInStatusEnum[3]
                    or status.get("powerInput5vIo")
                    == PiJuiceStatus.powerInStatusEnum[3]
                )
                self.piju_status = status
                self.piju_status_read_at = time_now
                self.process_buttons()
        else:
            status = self.piju_status
        return status

    @staticmethod
    def find_piju_bus_addr(hass: HomeAssistant):
        """Search for PiJuice UPS Hat on i2c bus. Checking buses 1 and 2 and.

        addresses from 0 to 0xff. device is considered to be UPS Hat if
        PiJuice API function GetAddress returns the same address as tested.
        """
        # get already installed instances
        used_resources = []
        for instance in hass.data.get(DOMAIN, []):
            pijups: PiJups = hass.data[DOMAIN][instance][BASE]
            used_resources.append((pijups.i2c_bus, pijups.i2c_address))
        bus_options = []
        address_options = []
        for bus in CONF_I2C_BUSES_TO_SEARCH:
            for addr in CONF_I2C_ADDRESSES_TO_SEARCH:
                if (bus, addr) in used_resources:
                    continue
                try:
                    juice_interface = PiJuice(bus, addr)
                    actual_addr = int(
                        juice_interface.config.GetAddress(bus).get("data", "100"), 16
                    )
                    if actual_addr == addr:
                        _LOGGER.debug(
                            "find_piju_bus_addr bus=%s matching address=0x%x", bus, addr
                        )
                        bus_options.append(bus)
                        address_options.append(actual_addr)
                except Exception as error:  # pylint: disable=broad-except
                    _LOGGER.info(
                        "Error while searching HAT bus %s, addr %s, %s",
                        bus,
                        addr,
                        error,
                    )
                    break
        _LOGGER.debug("find_piju_bus_addr used resources %s", used_resources)
        _LOGGER.debug(
            "find_piju_bus_addr exit: busses %s, addresses %s",
            bus_options,
            address_options,
        )
        return {CONF_BUS_OPTIONS: bus_options, CONF_ADDRESS_OPTIONS: address_options}

    def get_piju_defaults(self, hass: HomeAssistant, config_entry: ConfigEntry):
        """Prepare list of configurable items: current settings and setter methods to propagate settings to device."""
        defaults = {}
        # add temperature sense configuration data to defaults
        temp_sense_config = self.call_pijuice_with_error_check(
            self.config.GetBatteryTempSenseConfig
        )
        if temp_sense_config is not None:
            defaults[CONF_BATTERY_TEMP_SENSE_CONFIG] = {
                "wrapper": self.call_pijuice_with_error_check,
                "default": temp_sense_config,
                "values": PiJuiceConfig.batteryTempSenseOptions,
                "key": CONF_BATTERY_TEMP_SENSE_CONFIG,
                "setter": self.config.SetBatteryTempSenseConfig,
            }
        # add battery profile configuration data to default
        battery_profile = self.call_pijuice_with_error_check(
            self.config.GetBatteryProfileStatus
        )
        if battery_profile is not None:
            defaults[CONF_BATTERY_PROFILE] = {
                "wrapper": self.call_pijuice_with_error_check,
                "default": battery_profile.get("profile"),
                "values": PiJuiceConfig.batteryProfiles,
                "key": CONF_BATTERY_PROFILE,
                "setter": self.config.SetBatteryProfile,
            }
        _LOGGER.debug("get_piju_defaults exit with defaults %s", defaults)
        return defaults

    def get_piju_logging_defaults(self, hass: HomeAssistant, config_entry: ConfigEntry):
        """Prepare list of configurable items: current settings and setter methods to propagate settings to device."""
        defaults = {}
        if self.fw_version < "1.6":
            _LOGGER.warning(
                "Diagnostic logging supported starting from firmware version 1.6, installed %s",
                self.fw_version,
            )
            return defaults
        # get diagnostics logging settings
        current_logs = self.get_diag_log_config()
        defaults[CONF_DIAG_LOG_CONFIG] = {
            "default": current_logs,
            "values": LOG_ENABLE_LIST,
            "key": CONF_DIAG_LOG_CONFIG,
            "setter": self.set_diag_log_config,
            "type": "multi",
        }
        _LOGGER.debug("get_piju_logging_defaults exit with defaults %s", defaults)
        return defaults

    def get_diag_log_config(self):
        """Get HAT diagnostics log configuration selections."""
        ret = self.pijups.interface.WriteData(LOGGING_CMD, [0x02])
        time.sleep(0.1)
        ret = self.pijups.interface.ReadData(LOGGING_CMD, 31)
        current_logs = []
        if ret["error"] == "NO_ERROR" and ret["data"][1] == 0 and ret["data"][2] == 1:
            msk = 0x01
            for i in range(0, len(LOG_ENABLE_LIST) - 1):
                if msk & ret["data"][3]:
                    current_logs.append(LOG_ENABLE_LIST[i])
                msk <<= 1
        _LOGGER.debug("get_diag_log_config exit %s", current_logs)
        return current_logs

    def set_diag_log_config(self, cfg_list):
        """Set selected HAT diagnostics log parameters."""
        config = 0x00
        for i in range(0, len(LOG_ENABLE_LIST) - 1):
            if LOG_ENABLE_LIST[i] in cfg_list:
                config |= 0x01 << i
        ret = self.pijups.interface.WriteData(LOGGING_CMD, [0x01, config])
        time.sleep(0.1)
        _LOGGER.debug("set_diag_log_config exit %s", ret)
        return ret

    def get_diag_log(self):
        """Get HAT diagnostic entry data."""
        self.pijups.interface.WriteData(LOGGING_CMD, [0])
        time.sleep(0.01)
        ret = GetPiJuiceLog(self.pijups.interface)
        if ret["error"] != "NO_ERROR":
            time.sleep(0.5)
            self.pijups.interface.WriteData(LOGGING_CMD, [0])
            time.sleep(0.01)
            ret = GetPiJuiceLog(self.pijups.interface)
        _LOGGER.debug("get_diag_log exit %s", ret)
        return ret

    def get_fw_directory(self, hass: HomeAssistant, config_entry: ConfigEntry):
        """Prepare list of configurable items: current settings and setter methods to propagate settings to device."""
        defaults = {}
        fw_files_local = os.path.abspath(os.path.dirname(__file__) + "/../")
        defaults[CONF_FW_UPGRADE_PATH] = {
            "default": fw_files_local,
            "values": [fw_files_local],
        }
        _LOGGER.debug("get_fw_directory exit with defaults %s", defaults)
        return defaults

    def get_fw_file_list(self, hass: HomeAssistant, config_entry: ConfigEntry):
        """Prepare list of configurable items: current settings and setter methods to propagate settings to device."""
        defaults = {}
        fw_path = self.get_fw_directory(hass, config_entry)[CONF_FW_UPGRADE_PATH][
            "default"
        ]
        fw_files_local = os.listdir(fw_path)
        fw_exe_pat = re.compile("^" + DEFAULT_FW_UTILITY_NAME + "$")
        fw_bin_pat = re.compile("^" + DEFAULT_FW_FILE_NAME + "$")
        exe_files = [s for s in fw_files_local if fw_exe_pat.match(s)]
        bin_files = [s for s in fw_files_local if fw_bin_pat.match(s)]
        fw_file_list = [DEFAULT_NO_FIRMWARE_UPGRADE]
        pijups: PiJups = hass.data[DOMAIN][config_entry.entry_id][BASE]
        if len(exe_files) > 0 and len(bin_files) > 0 and pijups.i2c_bus == 1:
            fw_file_list.extend(bin_files)
        defaults[CONF_FIRMWARE_SELECTION] = {
            "default": fw_file_list[0],
            "values": fw_file_list,
        }
        _LOGGER.debug("get_fw_file_list exit with defaults %s", defaults)
        return defaults

    def set_up_ups(self):
        """Set UPS RTC to UTC time, clean faults and button events."""
        t_curr = datetime.now(UTC)
        t_pi = {
            "second": t_curr.second,
            "minute": t_curr.minute,
            "hour": t_curr.hour,
            "weekday": (t_curr.weekday() + 1) % 7 + 1,
            "day": t_curr.day,
            "month": t_curr.month,
            "year": t_curr.year,
            "subsecond": t_curr.microsecond // 1000000,
        }
        self.call_pijuice_with_error_check(self.rtcalarm.SetTime, t_pi)

        # clear faults if any
        status = self.call_pijuice_with_error_check(self.status.GetStatus)
        if status is not None:
            if status.get("isFault"):
                faults = self.call_pijuice_with_error_check(self.status.GetFaultStatus)
                _LOGGER.warning(
                    "%s %s faults '%s'",
                    self.piju_device_info["manufacturer"],
                    self.piju_device_info["model"],
                    faults,
                )
                persistent_notification.create(
                    self.hass,
                    f"{self.piju_device_info['manufacturer']} {self.piju_device_info['model']} {faults}",
                    title=f"{self.piju_device_info['model']} h/w faults reported",
                    notification_id="hw_faults",
                )
                self.call_pijuice_with_error_check(self.status.ResetFaultFlags, faults)

        _LOGGER.debug("Set_up_ups completed")

    def call_pijuice_with_error_check(
        self, piju_function, *args, error_log_level=logging.DEBUG, non_volatile=None
    ):
        """Wrap PiJuice API calls with retries if needed, log level might be set too."""
        _LOGGER.debug(
            "%s: %d %s %s", piju_function.__name__, len(args), args, error_log_level
        )
        for tries in (0, 1, 2, 3, 4, 5):
            if tries > 1:
                time.sleep(0.05)
            if non_volatile is None:
                return_data = piju_function(*args)
            else:
                return_data = piju_function(*args, non_volatile=non_volatile)
            if return_data["error"] != "NO_ERROR":
                int_log_level = logging.WARNING if tries == 2 else logging.INFO
                _LOGGER.log(
                    int_log_level,
                    "PiJuice i2c communication failure for %s(%i) with error %s",
                    piju_function.__name__,
                    tries,
                    return_data["error"],
                )
                #if (
                #    return_data["error"] != "COMMUNICATION_ERROR"
                #    and return_data["error"] != "WRITE_FAILED"
                #    and return_data["error"] != "DATA_CORRUPTED"
                #):
                #    return None
            else:
                if isinstance(return_data.get("data", {}), dict):  # "<class 'dict'>":
                    for piju_key in return_data.keys():
                        if piju_key not in ("data", "error"):
                            return_data["data"][piju_key] = return_data[piju_key]
                    return_data = return_data.get("data", {})
                else:
                    extra_keys_in_return_data = False
                    for piju_key in return_data.keys():
                        if piju_key not in ("data", "error"):
                            extra_keys_in_return_data = True
                            break
                    if not extra_keys_in_return_data:
                        return_data = return_data.get("data", {})
                _LOGGER.log(
                    error_log_level, "%s @ %s", piju_function.__name__, return_data
                )
                return return_data
        return None

    def process_power_off(self, wakeon_delta, poweroff_delay, off_service_requested):
        """Handle power off/restart request."""
        self.set_led_in_transition()
        if off_service_requested:
            _LOGGER.debug("Executing switch off sequence")
            if wakeon_delta >= 0:
                charge_data = self.call_pijuice_with_error_check(
                    self.status.GetChargeLevel
                )
                if charge_data is not None:
                    charge = charge_data + wakeon_delta
                else:
                    charge = MAX_WAKEON_DELTA
                wakeup = MAX_WAKEON_DELTA if charge >= MAX_WAKEON_DELTA - 1 else charge
            else:
                wakeup = 0
            _LOGGER.info(
                "Setting charge on level to %s%%, switch off delay to %ss",
                wakeup,
                poweroff_delay,
            )
            self.call_pijuice_with_error_check(
                self.power.SetWakeUpOnCharge, wakeup, non_volatile=True
            )
            self.call_pijuice_with_error_check(self.power.SetPowerOff, poweroff_delay)
            self.set_led_ha_inactive()
        else:
            _LOGGER.info("Switch off sequence execution bypassed")

    def set_led_ha_active(self):
        """Set HAT led D2 to indicate HA is running with Pijups integration initialized."""
        self.call_pijuice_with_error_check(
            self.config.SetLedConfiguration, "D2", LED_HA_RUNNING
        )

    def set_led_in_transition(self):
        """Set HAT led D2 to indicate power state transition in progress (usually short time period)."""
        self.call_pijuice_with_error_check(
            self.config.SetLedConfiguration, "D2", LED_ON_STATUS_IN_PROCESS
        )

    def set_led_ha_inactive(self):
        """Set HAT led D2 to indicate HAT is going to be switched off."""
        self.call_pijuice_with_error_check(
            self.config.SetLedConfiguration, "D2", LED_ON_STATUS_DOWN
        )

    def process_buttons(self):
        """Routine to handle button events: cleans up any event noticed."""
        if self.piju_status.get("isButton"):
            buttons = self.call_pijuice_with_error_check(self.status.GetButtonEvents)
            _LOGGER.debug("Buttons %s", buttons)
            self.call_pijuice_with_error_check(self.status.AcceptButtonEvent, "SW1")
            self.call_pijuice_with_error_check(self.status.AcceptButtonEvent, "SW2")
            self.call_pijuice_with_error_check(self.status.AcceptButtonEvent, "SW3")


LED_HA_RUNNING = {
    "function": "USER_LED",
    "parameter": {
        "r": 0,
        "g": 9,
        "b": 0,
    },
}

LED_ON_STATUS_IN_PROCESS = {
    "function": "USER_LED",
    "parameter": {
        "r": 9,
        "g": 0,
        "b": 0,
    },
}

LED_ON_STATUS_DOWN = {
    "function": "USER_LED",  # "CHARGE_STATUS",
    "parameter": {
        "r": 0,
        "g": 0,
        "b": 9,
    },
}
