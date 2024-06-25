"""Test PiJups interface class methods."""
import asyncio
from datetime import datetime
from datetime import UTC
import os
from unittest.mock import patch

from homeassistant.components.pijups import interface
from homeassistant.components.pijups.const import (
    CONF_BATTERY_PROFILE,
    CONF_BATTERY_TEMP_SENSE_CONFIG,
    CONF_DIAG_LOG_CONFIG,
    CONF_FIRMWARE_SELECTION,
    CONF_FW_UPGRADE_PATH,
    DEFAULT_I2C_ADDRESS,
    DEFAULT_I2C_BUS,
    DEFAULT_SCAN_INTERVAL,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .smbus2 import SMBus

from tests.components.pijups import common


def get_fw_directory(self, _hass: HomeAssistant, _config_entry: ConfigEntry):
    """Prepare list of configurable items: current settings and setter methods to propagate settings to device."""
    defaults = {}
    fw_files_local = os.path.abspath(os.path.dirname(__file__) + "/")
    defaults[CONF_FW_UPGRADE_PATH] = {
        "default": fw_files_local,
        "values": [fw_files_local],
    }
    return defaults


async def test_interface_settings_ok(hass: HomeAssistant):
    """Test PiJups interface settings for emulated h/w with default configuration."""
    SMBus.SIM_BUS = 1

    async def run_test_interface_settings_ok(hass, entry):
        pijups: interface.PiJups = await common.get_pijups(hass, entry)
        assert pijups is not None

        assert pijups.i2c_address == DEFAULT_I2C_ADDRESS
        assert pijups.i2c_bus == DEFAULT_I2C_BUS
        assert pijups.piju_device_info is not None
        assert pijups.fw_version == "1.6"

        # emulation sets faults=True at integration startup, check for expected notifications
        # check removed due to HA functionality chnage
        #notifications = hass.states.async_all("persistent_notification")
        #assert len(notifications) == 1
        #assert notifications[0].attributes["title"] == "PiJuice HAT h/w faults reported"
        #assert (
        #    notifications[0].attributes["message"]
        #    == "Pi Supply PiJuice HAT {'button_power_off': True, 'forced_power_off': True, 'forced_sys_power_off': True, 'watchdog_reset': True}"
        #)

    await common.pijups_setup_and_run_test(hass, True, run_test_interface_settings_ok)


async def test_interface_settings_wrong(hass: HomeAssistant):
    """Test PiJups interface settings for emulating no h/w exists and standard configuration."""
    SMBus.SIM_BUS = 2

    await common.pijups_setup_and_run_test(hass, False, None)


async def test_interface_auto_search(hass: HomeAssistant):
    """Test PiJups support for valid PiJuice HAT devices."""
    SMBus.SIM_BUS = 1
    with patch("homeassistant.components.pijups.pijuice.SMBus", new=SMBus):
        device_addresses = interface.PiJups.find_piju_bus_addr(hass)
        assert device_addresses.get("bus_options") == [DEFAULT_I2C_BUS]
        assert device_addresses.get("address_options") == [DEFAULT_I2C_ADDRESS]


async def test_interface_configuration_options(hass: HomeAssistant):
    """Test PiJups interface settings for emulated h/w with default configuration.

    Check emulated sensor values, diagnostics log settings, h/w diagnostics log contents
    and basic device behaviour
    """
    SMBus.SIM_BUS = 1

    async def run_test_interface_configuration_options(hass, entry):
        pijups: interface.PiJups = await common.get_pijups(hass, entry)
        assert pijups is not None

        configuration_details = await hass.async_add_executor_job(
            pijups.get_piju_defaults, hass, entry
        )
        assert configuration_details.get(CONF_BATTERY_TEMP_SENSE_CONFIG) is not None
        assert (
            configuration_details[CONF_BATTERY_TEMP_SENSE_CONFIG].get("default")
            == "ON_BOARD"
        )
        assert configuration_details[CONF_BATTERY_TEMP_SENSE_CONFIG].get("values") == [
            "NOT_USED",
            "NTC",
            "ON_BOARD",
            "AUTO_DETECT",
        ]
        assert configuration_details.get(CONF_BATTERY_PROFILE) is not None
        assert configuration_details[CONF_BATTERY_PROFILE].get("default") == "BP7X_1820"
        assert configuration_details[CONF_BATTERY_PROFILE].get("values") == [
            "PJZERO_1000",
            "BP7X_1820",
            "SNN5843_2300",
            "PJLIPO_12000",
            "PJLIPO_5000",
            "PJBP7X_1600",
            "PJSNN5843_1300",
            "PJZERO_1200",
            "BP6X_1400",
            "PJLIPO_600",
            "PJLIPO_500",
            "PJLIPO_2500",
        ]

        configuration_details = await hass.async_add_executor_job(
            pijups.get_piju_logging_defaults, hass, entry
        )
        assert configuration_details.get(CONF_DIAG_LOG_CONFIG) is not None
        assert configuration_details[CONF_DIAG_LOG_CONFIG].get("default") == [
            "5VREG_ON"
        ]
        assert configuration_details[CONF_DIAG_LOG_CONFIG].get("values") == [
            "OTHER",
            "5VREG_ON",
            "5VREG_OFF",
            "WAKEUP_EVT",
            "ALARM_EVT",
            "MCU_RESET",
            "RESERVED2",
        ]
        assert configuration_details[CONF_DIAG_LOG_CONFIG].get("type") == "multi"

        diagnostic_log = await hass.async_add_executor_job(pijups.get_diag_log)
        assert diagnostic_log == {
            "data": [
                "5 ALARM_WRITE   2022-12-07 14:47:40.917968, Battery: 0.0%, 41.268V, 194C, NORMAL\n\tGPIO_INPUT: PRESENT, USB_MICRO_INPUT: PRESENT\n\tSTATUS: {'alarm_wakeup_enabled': False, 'alarm_flag': False}\n\tCONFIG: {'second': 14, 'minute': 52, 'hour': 1, 'day': 0}\n",
                "14 MCU_RESET   2022-12-07 14:47:40.917968, Battery: 77.6%, 4.001V, 52C, CHARGING_FROM_5V_IO\n\tGPIO_5V: REGULATOR: ON, 5.184V, -0.380A, PRESENT\n\tSTATE: POWER_ON\n\tWAKEUP_ON_CHARGE: 240\n",
                "4 MCU_RESET   2022-12-07 14:47:40.917968, Battery: 77.6%, 4.001V, 52C, CHARGING_FROM_5V_IO\n\tGPIO_5V: REGULATOR: ON, 5.184V, 0.380A, PRESENT\n\tSTATE: POWER_ON\n\tWAKEUP_ON_CHARGE: 240\n",
                "153 ALARM_EVT   2022-12-07 14:47:40.917968, Battery: 0.0%, 41.268V, 194C, NORMAL\n\tGPIO_INPUT: PRESENT, USB_MICRO_INPUT: PRESENT\n\tSTATUS: {'alarm_wakeup_enabled': False, 'alarm_flag': False}\n\tCONFIG: {'second': 14, 'minute': 52, 'hour': '2AM', 'day': 0}\n",
                "143 ALARM_EVT   2022-12-07 14:47:40.917968, Battery: 0.0%, 41.268V, 194C, NORMAL\n\tGPIO_INPUT: PRESENT, USB_MICRO_INPUT: PRESENT\n\tSTATUS: {'alarm_wakeup_enabled': False, 'alarm_flag': False}\n\tCONFIG: {'second': 14, 'minute': 52, 'hour': '12PM', 'day': 0}\n",
                "133 ALARM_EVT   2022-12-07 14:47:40.917968, Battery: 0.0%, 41.268V, 194C, NORMAL\n\tGPIO_INPUT: PRESENT, USB_MICRO_INPUT: PRESENT\n\tSTATUS: {'alarm_wakeup_enabled': False, 'alarm_flag': False}\n\tCONFIG: {'second': 14, 'minute': 52, 'hour': '12AM', 'day': 0}\n",
                "123 ALARM_EVT   2022-12-07 14:47:40.917968, Battery: 0.0%, 41.268V, 194C, NORMAL\n\tGPIO_INPUT: PRESENT, USB_MICRO_INPUT: PRESENT\n\tSTATUS: {'alarm_wakeup_enabled': False, 'alarm_flag': False}\n\tCONFIG: {'second': 14, 'minute': 52, 'hour': '0', 'day': 0}\n",
                "113 ALARM_EVT   2022-12-07 14:47:40.917968, Battery: 0.0%, 41.268V, 194C, NORMAL\n\tGPIO_INPUT: PRESENT, USB_MICRO_INPUT: PRESENT\n\tSTATUS: {'alarm_wakeup_enabled': False, 'alarm_flag': False}\n\tCONFIG: {'second': 14, 'minute': 52, 'hour': 0, 'weekday': 'EVERY_DAY'}\n",
                "103 ALARM_EVT   2022-12-07 14:47:40.917968, Battery: 0.0%, 41.268V, 194C, NORMAL\n\tGPIO_INPUT: PRESENT, USB_MICRO_INPUT: PRESENT\n\tSTATUS: {'alarm_wakeup_enabled': False, 'alarm_flag': False}\n\tCONFIG: {'second': 14, 'minute': 52, 'hour': 0, 'weekday': '1'}\n",
                "93 ALARM_EVT   2022-12-07 14:47:40.917968, Battery: 0.0%, 41.268V, 194C, NORMAL\n\tGPIO_INPUT: PRESENT, USB_MICRO_INPUT: PRESENT\n\tSTATUS: {'alarm_wakeup_enabled': False, 'alarm_flag': False}\n\tCONFIG: {'second': 14, 'minute': 52, 'hour': 0, 'day': 'EVERY_DAY'}\n",
                "83 ALARM_EVT   2022-12-07 14:47:40.917968, Battery: 0.0%, 41.268V, 194C, NORMAL\n\tGPIO_INPUT: PRESENT, USB_MICRO_INPUT: PRESENT\n\tSTATUS: {'alarm_wakeup_enabled': False, 'alarm_flag': False}\n\tCONFIG: {'second': 14, 'minute': 52, 'hour': 0, 'weekday': 0}\n",
                "73 ALARM_EVT   2022-12-07 14:47:40.917968, Battery: 0.0%, 41.268V, 194C, NORMAL\n\tGPIO_INPUT: PRESENT, USB_MICRO_INPUT: PRESENT\n\tSTATUS: {'alarm_wakeup_enabled': False, 'alarm_flag': False}\n\tCONFIG: {'second': 14, 'minute': 52, 'hour': 'EVERY_HOUR', 'day': 0}\n",
                "63 ALARM_EVT   2022-12-07 14:47:40.917968, Battery: 0.0%, 41.268V, 194C, NORMAL\n\tGPIO_INPUT: PRESENT, USB_MICRO_INPUT: PRESENT\n\tSTATUS: {'alarm_wakeup_enabled': False, 'alarm_flag': False}\n\tCONFIG: {'second': 14, 'minute': 52, 'hour': '', 'day': 0}\n",
                "53 ALARM_EVT   2022-12-07 14:47:40.917968, Battery: 0.0%, 41.268V, 194C, NORMAL\n\tGPIO_INPUT: PRESENT, USB_MICRO_INPUT: PRESENT\n\tSTATUS: {'alarm_wakeup_enabled': False, 'alarm_flag': False}\n\tCONFIG: {'second': 14, 'minute': 52, 'hour': '0 AM', 'day': 0}\n",
                "43 ALARM_EVT   2022-12-07 14:47:40.917968, Battery: 0.0%, 41.268V, 194C, NORMAL\n\tGPIO_INPUT: PRESENT, USB_MICRO_INPUT: PRESENT\n\tSTATUS: {'alarm_wakeup_enabled': False, 'alarm_flag': False}\n\tCONFIG: {'minute_period': 10, 'hour': 1, 'day': 0}\n",
                "33 ALARM_EVT   2022-12-07 14:47:40.917968, Battery: 0.0%, 41.268V, 194C, NORMAL\n\tGPIO_INPUT: PRESENT, USB_MICRO_INPUT: PRESENT\n\tSTATUS: {'alarm_wakeup_enabled': False, 'alarm_flag': False}\n\tCONFIG: {'minute': 52, 'hour': 1, 'day': 0}\n",
                "23 ALARM_EVT   2022-12-07 14:47:40.917968, Battery: 0.0%, 41.268V, 194C, NORMAL\n\tGPIO_INPUT: PRESENT, USB_MICRO_INPUT: PRESENT\n\tSTATUS: {'alarm_wakeup_enabled': True, 'alarm_flag': True}\n\tCONFIG: {'second': 14, 'minute': 52, 'hour': 1, 'day': 0}\n",
                "3 ALARM_EVT   2022-12-07 14:47:40.917968, Battery: 0.0%, 41.268V, 194C, NORMAL\n\tGPIO_INPUT: PRESENT, USB_MICRO_INPUT: PRESENT\n\tSTATUS: {'alarm_wakeup_enabled': False, 'alarm_flag': False}\n\tCONFIG: {'second': 14, 'minute': 52, 'hour': 1, 'day': 0}\n",
                "2 5VREG_OFF 2022-12-07 14:47:40.917968, SoC:80.0%, 9C, GPIO_5V: 0.000V, 0A\n\t-battery: ['3.985', '2.728', '3.693', '2.400', '2.834', '2.444', '3.365', '2.276']\n\t-current: ['0.000', '0.000', '0.000', '0.000', '0.000', '0.000', '0.000', '0.000']\n",
                "1 5VREG_ON  2022-12-07 14:47:40.917968, NO ENOUGHR POWER\n\t-battery: ['4.038', '2.347', '4.393', '2.267', '3.985', '2.728', '3.693', '2.400', '2.834', '2.444']\n\t-5V GPIO: ['3.197', '0.026', '0.000', '0.000', '0.000', '0.000', '0.000', '0.000', '0.000', '0.000']\n",
                "30 WAKEUP_EVT   {'second': 40, 'minute': 47, 'hour': '2 AM', 'weekday': 4, 'day': 7, 'month': 12, 'year': 2022, 'subsecond': 0.91796875}, Battery: 77.6%, 4.001V, 52C, CHARGING_FROM_5V_IO\n\tGPIO_5V: REGULATOR: ON, 5.184V, 0.380A, PRESENT\n\tTRIGGERS:  ON_CHARGE\n\tWAKEUP_ON_CHARGE: 240\n",
                "20 WAKEUP_EVT   {'second': 40, 'minute': 47, 'hour': 14, 'weekday': 4, 'day': 7, 'month': 13, 'year': 2022, 'subsecond': 0.91796875}, Battery: 77.6%, 4.001V, 52C, CHARGING_FROM_5V_IO\n\tGPIO_5V: REGULATOR: ON, 5.184V, 0.380A, PRESENT\n\tTRIGGERS:  ON_CHARGE\n\tWAKEUP_ON_CHARGE: 240\n",
                "10 WAKEUP_EVT   2022-12-07 14:47:40.917968, Battery: 77.6%, 4.001V, 52C, CHARGING_FROM_5V_IO\n\tGPIO_5V: REGULATOR: ON, 5.184V, -0.380A, PRESENT\n\tTRIGGERS:  ON_CHARGE\n\tWAKEUP_ON_CHARGE: 240\n",
                "0 WAKEUP_EVT   2022-12-07 14:47:40.917968, Battery: 77.6%, 4.001V, 52C, CHARGING_FROM_5V_IO\n\tGPIO_5V: REGULATOR: ON, 5.184V, 0.380A, PRESENT\n\tTRIGGERS:  ON_CHARGE\n\tWAKEUP_ON_CHARGE: 240\n",
            ],
            "error": "NO_ERROR",
        }

        #   set_up_ups(self) checks
        rtc_time = await hass.async_add_executor_job(
            pijups.call_pijuice_with_error_check, pijups.rtcalarm.GetTime
        )
        assert rtc_time is not None
        time_now = datetime.now(UTC)
        time_set = datetime(
            rtc_time["year"],
            rtc_time["month"],
            rtc_time["day"],
            rtc_time["hour"],
            rtc_time["minute"],
            rtc_time["second"],
            0,
            tzinfo=UTC,
        )
        assert (time_now - time_set).total_seconds() < 5

        status_after_setup = await hass.async_add_executor_job(
            pijups.get_piju_status, True
        )
        assert status_after_setup is not None
        assert status_after_setup.get("isFault") is False
        assert status_after_setup.get("isButton") is False

        faults_data = await hass.async_add_executor_job(
            pijups.call_pijuice_with_error_check, pijups.status.GetFaultStatus
        )
        assert faults_data is not None
        assert faults_data == {}

        button_events = await hass.async_add_executor_job(
            pijups.call_pijuice_with_error_check, pijups.status.GetButtonEvents
        )
        assert button_events is not None
        assert button_events.get("SW1") == "NO_EVENT"
        assert button_events.get("SW2") == "NO_EVENT"
        assert button_events.get("SW3") == "NO_EVENT"

        # configuration related
        firmware_directory = await hass.async_add_executor_job(
            pijups.get_fw_directory, hass, entry
        )
        assert firmware_directory is not None
        assert firmware_directory.get(CONF_FW_UPGRADE_PATH) is not None
        assert firmware_directory.get(CONF_FW_UPGRADE_PATH).get("default") is not None
        assert firmware_directory.get(CONF_FW_UPGRADE_PATH).get("values") is not None

        firmware_files = await hass.async_add_executor_job(
            pijups.get_fw_file_list, hass, entry
        )
        assert firmware_files is not None
        assert firmware_files.get(CONF_FIRMWARE_SELECTION) is not None
        assert firmware_files.get(CONF_FIRMWARE_SELECTION).get("default") is not None
        assert firmware_files.get(CONF_FIRMWARE_SELECTION).get("values") is not None

        #   LED related
        await hass.async_add_executor_job(pijups.set_led_ha_active)
        led2_now = await hass.async_add_executor_job(
            pijups.call_pijuice_with_error_check,
            pijups.config.GetLedConfiguration,
            "D2",
        )
        assert led2_now is not None
        assert led2_now == interface.LED_HA_RUNNING

        await hass.async_add_executor_job(pijups.set_led_in_transition)
        led2_now = await hass.async_add_executor_job(
            pijups.call_pijuice_with_error_check,
            pijups.config.GetLedConfiguration,
            "D2",
        )
        assert led2_now is not None
        assert led2_now == interface.LED_ON_STATUS_IN_PROCESS

        await hass.async_add_executor_job(pijups.set_led_ha_inactive)
        led2_now = await hass.async_add_executor_job(
            pijups.call_pijuice_with_error_check,
            pijups.config.GetLedConfiguration,
            "D2",
        )
        assert led2_now is not None
        assert led2_now == interface.LED_ON_STATUS_DOWN

        await hass.async_add_executor_job(pijups.set_led_ha_active)
        led2_now = await hass.async_add_executor_job(
            pijups.call_pijuice_with_error_check,
            pijups.config.GetLedConfiguration,
            "D2",
        )
        assert led2_now is not None
        assert led2_now == interface.LED_HA_RUNNING

    await common.pijups_setup_and_run_test(
        hass, True, run_test_interface_configuration_options
    )


async def test_interface_configuration_options_firmware(hass: HomeAssistant):
    """Test PiJups interface settings for emulated h/w with default configuration.

    Check emulated sensor values, diagnostics log settings, h/w diagnostics log contents
    and basic device behaviour
    """
    SMBus.SIM_BUS = 1

    async def run_test_interface_configuration_options_firmware(hass, entry):
        pijups: interface.PiJups = await common.get_pijups(hass, entry)
        assert pijups is not None

        with patch(
            "homeassistant.components.pijups.interface.PiJups.get_fw_directory",
            new=get_fw_directory,
        ):
            fw_directory_details = await hass.async_add_executor_job(
                pijups.get_fw_directory, hass, entry
            )
            assert fw_directory_details is not None
            assert fw_directory_details.get(CONF_FW_UPGRADE_PATH) is not None
            assert (
                fw_directory_details.get(CONF_FW_UPGRADE_PATH).get("default")
                is not None
            )
            fw_file_details = await hass.async_add_executor_job(
                pijups.get_fw_file_list, hass, entry
            )
            assert fw_file_details is not None
            assert fw_file_details == {
                CONF_FIRMWARE_SELECTION: {
                    "default": "No firmware upgrade",
                    "values": [
                        "No firmware upgrade",
                        "PiJuice-V1.6_2021_09_10.elf.binary",
                    ],
                }
            }

    await common.pijups_setup_and_run_test(
        hass, True, run_test_interface_configuration_options_firmware
    )


async def test_interface_status_function(hass: HomeAssistant):
    """Test PiJups interface settings for emulated h/w with default configuration.

    Check emulated HA status handling
    """
    SMBus.SIM_BUS = 1

    async def run_test_interface_status_function(hass, entry):
        pijups: interface.PiJups = await common.get_pijups(hass, entry)
        assert pijups is not None

        #   check status caching
        pijups.interface.i2cbus.set_power(True, True)  # set to powered
        initial_status = await hass.async_add_executor_job(pijups.get_piju_status, True)
        assert pijups.powered
        pijups.interface.i2cbus.set_power(False, False)  # set to no external power
        changed_status = await hass.async_add_executor_job(pijups.get_piju_status)
        assert initial_status == changed_status
        await asyncio.sleep(DEFAULT_SCAN_INTERVAL)
        changed_status = await hass.async_add_executor_job(pijups.get_piju_status)
        assert initial_status != changed_status
        assert not pijups.powered

        # check power status per power source status
        hw_status = [0, 0]
        for p_state in range(0, 16):
            hw_status[0] = p_state << 4
            pijups.interface.i2cbus._set_buff(0x40, hw_status)
            await hass.async_add_executor_job(pijups.get_piju_status, True)
            #   powered if have at least one source in 'PRESENT' mode (0b11 denotes this state)
            expected_power_state = (p_state & 0b1100) == 0b1100 or (
                p_state & 0b0011
            ) == 0b0011
            assert pijups.powered == expected_power_state

    await common.pijups_setup_and_run_test(
        hass, True, run_test_interface_status_function
    )


async def test_interface_button_event(hass: HomeAssistant):
    """Test PiJups interface settings for emulated h/w with default configuration.

    Check emulated button events handling
    """
    SMBus.SIM_BUS = 1

    async def run_test_interface_button_event(hass, entry):
        pijups: interface.PiJups = await common.get_pijups(hass, entry)
        assert pijups is not None

        button_events_flags = [1, 0, 0]  # PRESS on SW1
        pijups.interface.i2cbus._set_buff(0x45, button_events_flags)
        button_events = await hass.async_add_executor_job(
            pijups.call_pijuice_with_error_check, pijups.status.GetButtonEvents
        )
        assert button_events
        assert button_events.get("SW1") == "PRESS"
        status_with_button_event_flag = await hass.async_add_executor_job(
            pijups.get_piju_status, True
        )
        assert status_with_button_event_flag
        assert status_with_button_event_flag.get("isButton") is True
        status_without_button_event_flag = await hass.async_add_executor_job(
            pijups.get_piju_status, True
        )
        assert status_without_button_event_flag
        assert status_without_button_event_flag.get("isButton") is False
        button_events = await hass.async_add_executor_job(
            pijups.call_pijuice_with_error_check, pijups.status.GetButtonEvents
        )
        assert button_events
        assert button_events.get("SW1") == "NO_EVENT"

    await common.pijups_setup_and_run_test(hass, True, run_test_interface_button_event)


async def test_interface_fault_event(hass: HomeAssistant):
    """Test PiJups interface settings for emulated h/w with default configuration.

    Check HA faults handling
    """
    SMBus.SIM_BUS = 1

    async def run_test_interface_fault_event(hass, entry):
        pijups: interface.PiJups = await common.get_pijups(hass, entry)
        assert pijups is not None

        fault_events_flags = [0b11101111, 0]  # all faults on
        pijups.interface.i2cbus._set_buff(0x44, fault_events_flags)
        fault_events = await hass.async_add_executor_job(
            pijups.call_pijuice_with_error_check, pijups.status.GetFaultStatus
        )
        assert fault_events
        status_with_fault_event_flag = await hass.async_add_executor_job(
            pijups.get_piju_status, True
        )
        assert status_with_fault_event_flag
        assert status_with_fault_event_flag.get("isFault") is True
        fault_accept = await hass.async_add_executor_job(
            pijups.call_pijuice_with_error_check,
            pijups.status.ResetFaultFlags,
            fault_events,
        )
        assert fault_accept == {}
        status_with_fault_event_flag = await hass.async_add_executor_job(
            pijups.get_piju_status, True
        )
        assert status_with_fault_event_flag.get("isFault") is True
        fault_events = await hass.async_add_executor_job(
            pijups.call_pijuice_with_error_check, pijups.status.GetFaultStatus
        )
        fault_events_flags = [0, 0]  # all faults on
        pijups.interface.i2cbus._set_buff(0x44, fault_events_flags)
        status_without_fault_event_flag = await hass.async_add_executor_job(
            pijups.get_piju_status, True
        )
        assert status_without_fault_event_flag
        assert status_without_fault_event_flag.get("isFault") is False
        fault_events = await hass.async_add_executor_job(
            pijups.call_pijuice_with_error_check, pijups.status.GetFaultStatus
        )
        assert fault_events == {}

    await common.pijups_setup_and_run_test(hass, True, run_test_interface_fault_event)


def sync_wake_with_kwd_prm(pijups: interface.PiJups, on_charge_level):
    """Call with kwd paramater for task."""
    return pijups.call_pijuice_with_error_check(
        pijups.power.SetWakeUpOnCharge, on_charge_level, non_volatile=True
    )


async def test_interface_wrapper(hass: HomeAssistant):
    """Test PiJups interface settings for emulated h/w with default configuration.

    Check PiJups wrapper handler functionality
    """
    SMBus.SIM_BUS = 1

    async def run_test_interface_wrapper(hass, entry):
        pijups: interface.PiJups = await common.get_pijups(hass, entry)
        assert pijups is not None

        # different parametrization types
        #    def call_pijuice_with_error_check(self, piju_function, *args, error_log_level=logging.DEBUG, non_volatile=None):
        on_charge_level = 21
        wake_on_charge_set = await hass.async_add_executor_job(
            sync_wake_with_kwd_prm, pijups, on_charge_level
        )
        assert wake_on_charge_set is not None
        wake_on_charge = pijups.call_pijuice_with_error_check(
            pijups.power.GetWakeUpOnCharge
        )
        wake_on_charge = await hass.async_add_executor_job(
            pijups.call_pijuice_with_error_check, pijups.power.GetWakeUpOnCharge
        )
        assert wake_on_charge is not None
        assert wake_on_charge.get("data") == on_charge_level
        assert wake_on_charge.get("non_volatile") is True
        pijups.interface.i2cbus.enable_delay(0.2)
        await hass.async_block_till_done()
        wake_on_charge = await hass.async_add_executor_job(
            pijups.call_pijuice_with_error_check, pijups.power.GetWakeUpOnCharge
        )
        assert wake_on_charge is None
        pijups.interface.i2cbus.enable_delay(0)

    await common.pijups_setup_and_run_test(hass, True, run_test_interface_wrapper)
