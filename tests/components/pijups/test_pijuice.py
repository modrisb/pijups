"""Test PiJups initilization path initiated from __init__.py."""
import time
from unittest.mock import patch
from homeassistant.components.hassio import (
    DOMAIN as HASSIO_DOMAIN,
    SERVICE_HOST_SHUTDOWN,
)
from homeassistant.components.pijups.interface import PiJups
import homeassistant.components.pijups.pijuice as pi
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


def test_pijuice_interface(hass: HomeAssistant):
    """Test if PiJups loads for standard emulated h/w configuration with default configuration."""
    SMBus.SIM_BUS = 1
    bus = 1
    address = 0x14
    with patch("homeassistant.components.pijups.pijuice.SMBus", new=SMBus):
        with pi.PiJuiceInterface(bus, address) as pin:
            assert pin.GetAddress() == address

def test_pijuice_status_functions(hass: HomeAssistant):
    """Test if PiJups loads for standard emulated h/w configuration with default configuration."""
    SMBus.SIM_BUS = 1
    bus = 1
    address = 0x14
    with patch("homeassistant.components.pijups.pijuice.SMBus", new=SMBus):
        with pi.PiJuice(bus, address) as pijuice:
            with pijuice.status:
                # STATUS_CMD = 0x40
                status = pijuice.status.GetStatus()
                assert status == {'data': {'isFault': True, 'isButton': True, 'battery': 'NORMAL', 'powerInput': 'NOT_PRESENT', 'powerInput5vIo': 'PRESENT'}, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x40, 1, 0.11)    # STATUS_CMD
                status = pijuice.status.GetStatus()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # CHARGE_LEVEL_CMD = 0x41
                status = pijuice.status.GetChargeLevel()
                assert status == {'data': 82, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x41, 1, 0.11)    # CHARGE_LEVEL_CMD
                status = pijuice.status.GetChargeLevel()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # FAULT_EVENT_CMD = 0x44
                faults_buff = pijuice.interface.i2cbus._get_buff(0x44)
                pijuice.interface.i2cbus._set_buff(0x44, [0b11101111, 0])
                status = pijuice.status.GetFaultStatus()
                assert status == {'data': {'button_power_off': True, 'forced_power_off': True, 'forced_sys_power_off': True, 'watchdog_reset': True, 'battery_profile_invalid': True, 'charging_temperature_fault': 'WARM'}, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus._set_buff(0x44, faults_buff)
                status_to_clear = pijuice.status.GetFaultStatus()
                assert status_to_clear == {'data': {'button_power_off': True, 'forced_power_off': True, 'forced_sys_power_off': True, 'watchdog_reset': True}, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x44, 1, 0.11)    # FAULT_EVENT_CMD
                status = pijuice.status.GetFaultStatus()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # FAULT_EVENT_CMD = 0x44 (w)
                status = pijuice.status.ResetFaultFlags(status_to_clear)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x44, 1, 0.11)    # FAULT_EVENT_CMD
                status = pijuice.status.ResetFaultFlags(status_to_clear)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # BUTTON_EVENT_CMD = 0x45
                button_buff = pijuice.interface.i2cbus._get_buff(0x45)
                pijuice.interface.i2cbus._set_buff(0x45, [0x77, 0x77, 0])
                status = pijuice.status.GetButtonEvents()
                assert status == {'data': {'SW1': 'UNKNOWN', 'SW2': 'UNKNOWN', 'SW3': 'UNKNOWN'}, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus._set_buff(0x45, button_buff)
                status = pijuice.status.GetButtonEvents()
                assert status == {'data': {'SW1': 'PRESS', 'SW2': 'NO_EVENT', 'SW3': 'NO_EVENT'}, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x45, 1, 0.11)    # BUTTON_EVENT_CMD
                status = pijuice.status.GetButtonEvents()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # BUTTON_EVENT_CMD = 0x45 (W)
                status = pijuice.status.AcceptButtonEvent("SW")
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.status.AcceptButtonEvent("SW1")
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x45, 1, 0.11)    # BUTTON_EVENT_CMD
                status = pijuice.status.AcceptButtonEvent("SW1")
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # BATTERY_TEMPERATURE_CMD = 0x47
                temp_buff = pijuice.interface.i2cbus._get_buff(0x47)
                temp_buff_variation = temp_buff.copy()
                temp_buff_variation[0] |= 0x80
                pijuice.interface.i2cbus._set_buff(0x47, temp_buff_variation)
                status = pijuice.status.GetBatteryTemperature()
                assert status == {'data': -80, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus._set_buff(0x47, temp_buff)
                status = pijuice.status.GetBatteryTemperature()
                assert status == {'data': 48, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x47, 1, 0.11)    # BATTERY_TEMPERATURE_CMD
                status = pijuice.status.GetBatteryTemperature()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # BATTERY_VOLTAGE_CMD = 0x49
                status = pijuice.status.GetBatteryVoltage()
                assert status == {'data': 4020, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x49, 1, 0.11)    # BATTERY_VOLTAGE_CMD
                status = pijuice.status.GetBatteryVoltage()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # BATTERY_CURRENT_CMD = 0x4B
                current_buff = pijuice.interface.i2cbus._get_buff(0x4B)
                current_buff_variation = current_buff.copy()
                current_buff_variation[1] |= 0x80
                pijuice.interface.i2cbus._set_buff(0x4B, current_buff_variation)
                status = pijuice.status.GetBatteryCurrent()
                assert status == {'data': -32756, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus._set_buff(0x4B, current_buff)
                status = pijuice.status.GetBatteryCurrent()
                assert status == {'data': 12, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x4B, 1, 0.11)    # BATTERY_CURRENT_CMD
                status = pijuice.status.GetBatteryCurrent()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # IO_VOLTAGE_CMD = 0x4D
                status = pijuice.status.GetIoVoltage()
                assert status == {'data': 5170, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x4D, 1, 0.11)    # IO_VOLTAGE_CMD
                status = pijuice.status.GetIoVoltage()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # IO_CURRENT_CMD = 0x4F
                status = pijuice.status.GetIoCurrent()
                assert status == {'data': -1134, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x4F, 1, 0.11)    # IO_CURRENT_CMD
                status = pijuice.status.GetIoCurrent()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # LED_STATE_CMD = 0x66
                status = pijuice.status.GetLedState("D")
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.status.GetLedState("D1")
                assert status == {'data': [0, 60, 100], 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x66, 1, 0.11)    # LED_STATE_CMD
                status = pijuice.status.GetLedState("D1")
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # LED_STATE_CMD = 0x66 (W)
                status = pijuice.status.SetLedState("D", [0, 60, 100])
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.status.SetLedState("D1", [10, 60, 100])
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x66, 1, 0.11)    # LED_STATE_CMD
                status = pijuice.status.SetLedState("D1", [10, 60, 100])
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # LED_BLINK_CMD = 0x68
                status = pijuice.status.GetLedBlink("D")
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.status.GetLedBlink("D1")
                assert status == {'data': {'count': 0, 'rgb1': [0, 0, 0], 'period1': 0, 'rgb2': [0, 0, 0], 'period2': 0}, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x68, 1, 0.11)    # LED_BLINK_CMD
                status = pijuice.status.GetLedBlink("D1")
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # LED_BLINK_CMD = 0x68 (W)
                status = pijuice.status.SetLedBlink("D", 0, [0, 0, 0], 0, [0, 0, 0], 0)
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.status.SetLedBlink("D1", 0, [0, 0, 0], 0, [0, 0, 0], 0)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x68, 1, 0.11)    # LED_BLINK_CMD
                status = pijuice.status.SetLedBlink("D1", 0, [0, 0, 0], 0, [0, 0, 0], 0)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # IO_PIN_ACCESS_CMD = 0x75
                status = pijuice.status.GetIoDigitalInput(3)
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.status.GetIoDigitalInput(1)
                assert status == {'data': 0, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x75, 1, 0.11)    # IO_PIN_ACCESS_CMD
                status = pijuice.status.GetIoDigitalInput(1)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # IO_PIN_ACCESS_CMD = 0x75
                status = pijuice.status.GetIoDigitalOutput(3)
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.status.GetIoDigitalOutput(1)
                assert status == {'data': 0, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x75, 1, 0.11)    # IO_PIN_ACCESS_CMD
                status = pijuice.status.GetIoDigitalOutput(1)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # IO_PIN_ACCESS_CMD = 0x75 (W)
                status = pijuice.status.SetIoDigitalOutput(3, 1)
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.status.SetIoDigitalOutput(1, 1)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x75, 1, 0.11)    # IO_PIN_ACCESS_CMD
                status = pijuice.status.SetIoDigitalOutput(1, 1)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # IO_PIN_ACCESS_CMD = 0x75
                status = pijuice.status.GetIoAnalogInput(3)
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.status.GetIoAnalogInput(1)
                assert status == {'data': 256, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x75, 1, 0.11)    # IO_PIN_ACCESS_CMD
                status = pijuice.status.GetIoAnalogInput(1)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # IO_PIN_ACCESS_CMD = 0x75
                status = pijuice.status.GetIoPWM(3)
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.status.GetIoPWM(1)
                assert status == {'data': 0.0, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x75, 1, 0.11)    # IO_PIN_ACCESS_CMD
                status = pijuice.status.GetIoPWM(1)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # IO_PIN_ACCESS_CMD = 0x75 (W)
                status = pijuice.status.SetIoPWM(3, 1)
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.status.SetIoPWM(1, "noduty")
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.status.SetIoPWM(1, 101)
                assert status == {'error': 'INVALID_DUTY_CYCLE'}
                status = pijuice.status.SetIoPWM(1, 1)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x75, 1, 0.11)    # IO_PIN_ACCESS_CMD
                status = pijuice.status.SetIoPWM(1, 1)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)


def test_pijuice_rtc_alarm_functions(hass: HomeAssistant):
    """Test if PiJups loads for standard emulated h/w configuration with default configuration."""
    SMBus.SIM_BUS = 1
    bus = 1
    address = 0x14
    with patch("homeassistant.components.pijups.pijuice.SMBus", new=SMBus):
        with pi.PiJuice(bus, address) as pijuice:
            with pijuice.rtcAlarm:
                # RTC_CTRL_STATUS_CMD = 0xC2
                alarm_flag = pijuice.interface.i2cbus._get_buff(0xC2)
                alarm_flag_variation = alarm_flag.copy()
                alarm_flag_variation[0] |= 0x05
                alarm_flag_variation[1] |= 0x01
                pijuice.interface.i2cbus._set_buff(0xC2, alarm_flag_variation)
                status = pijuice.rtcAlarm.GetControlStatus()
                assert status == {'data': {'alarm_wakeup_enabled': True, 'alarm_flag': True}, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus._set_buff(0xC2, alarm_flag)
                status = pijuice.rtcAlarm.GetControlStatus()
                assert status == {'data': {'alarm_wakeup_enabled': False, 'alarm_flag': False}, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus._set_buff(0xC2, alarm_flag)
                pijuice.interface.i2cbus.add_cmd_delays(0xC2, 1, 0.11)    # RTC_CTRL_STATUS_CMD
                status = pijuice.rtcAlarm.GetControlStatus()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # RTC_CTRL_STATUS_CMD = 0xC2 (W)
                alarm_flag = pijuice.interface.i2cbus._get_buff(0xC2)
                alarm_flag_variation = alarm_flag.copy()
                alarm_flag_variation[1] |= 0x01
                pijuice.interface.i2cbus._set_buff(0xC2, alarm_flag_variation)
                status = pijuice.rtcAlarm.ClearAlarmFlag()
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus._set_buff(0xC2, alarm_flag)
                status = pijuice.rtcAlarm.ClearAlarmFlag()
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0xC2, 1, 0.11)    # RTC_CTRL_STATUS_CMD
                status = pijuice.rtcAlarm.ClearAlarmFlag()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # RTC_CTRL_STATUS_CMD = 0xC2 (W)
                wake_conf = pijuice.interface.i2cbus._get_buff(0xC2)
                wake_conf_variation = wake_conf.copy()
                wake_conf_variation[0] |= 0x05
                pijuice.interface.i2cbus._set_buff(0xC2, wake_conf_variation)
                status = pijuice.rtcAlarm.SetWakeupEnabled(True)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus._set_buff(0xC2, wake_conf_variation)
                status = pijuice.rtcAlarm.SetWakeupEnabled(False)
                assert status == {'error': 'NO_ERROR'}
                wake_conf_variation[0] &= 0xfe
                pijuice.interface.i2cbus._set_buff(0xC2, wake_conf_variation)
                status = pijuice.rtcAlarm.SetWakeupEnabled(True)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus._set_buff(0xC2, wake_conf_variation)
                status = pijuice.rtcAlarm.SetWakeupEnabled(False)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus._set_buff(0xC2, wake_conf)
                status = pijuice.rtcAlarm.SetWakeupEnabled(False)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus._set_buff(0xC2, wake_conf)
                status = pijuice.rtcAlarm.SetWakeupEnabled(True)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0xC2, 1, 0.11)    # RTC_CTRL_STATUS_CMD
                status = pijuice.rtcAlarm.SetWakeupEnabled(True)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # RTC_TIME_CMD = 0xB0
                time_buff = pijuice.interface.i2cbus._get_buff(0xB0)
                time_buff_variation = time_buff.copy()
                time_buff_variation[2] |= 0b01000000
                pijuice.interface.i2cbus._set_buff(0xB0, time_buff_variation)
                status_time = pijuice.rtcAlarm.GetTime()
                assert status_time == {'data': {'second': 53, 'minute': 19, 'hour': '19 AM', 'weekday': 1, 'day': 18, 'month': 12, 'year': 2022, 'subsecond': 0, 'daylightsaving': 'NONE', 'storeoperation': False}, 'error': 'NO_ERROR'}
                time_buff_variation = time_buff.copy()
                time_buff_variation[2] &= 0b10111111
                pijuice.interface.i2cbus._set_buff(0xB0, time_buff_variation)
                status_time = pijuice.rtcAlarm.GetTime()
                assert status_time == {'data': {'second': 53, 'minute': 19, 'hour': 19, 'weekday': 1, 'day': 18, 'month': 12, 'year': 2022, 'subsecond': 0, 'daylightsaving': 'NONE', 'storeoperation': False}, 'error': 'NO_ERROR'}
                time_buff_variation = time_buff.copy()
                time_buff_variation[8] &= 0b11111100
                time_buff_variation[8] |= 0b00000110
                pijuice.interface.i2cbus._set_buff(0xB0, time_buff_variation)
                status_time = pijuice.rtcAlarm.GetTime()
                assert status_time == {'data': {'second': 53, 'minute': 19, 'hour': 19, 'weekday': 1, 'day': 18, 'month': 12, 'year': 2022, 'subsecond': 0, 'daylightsaving': 'SUB1H', 'storeoperation': True}, 'error': 'NO_ERROR'}
                time_buff_variation = time_buff.copy()
                time_buff_variation[8] &= 0b11111100
                time_buff_variation[8] |= 0b00000001
                pijuice.interface.i2cbus._set_buff(0xB0, time_buff_variation)
                status_time = pijuice.rtcAlarm.GetTime()
                assert status_time == {'data': {'second': 53, 'minute': 19, 'hour': 19, 'weekday': 1, 'day': 18, 'month': 12, 'year': 2022, 'subsecond': 0, 'daylightsaving': 'ADD1H', 'storeoperation': False}, 'error': 'NO_ERROR'}
                time_buff_variation = time_buff.copy()
                time_buff_variation[8] &= 0b11111100
                pijuice.interface.i2cbus._set_buff(0xB0, time_buff_variation)
                status_time = pijuice.rtcAlarm.GetTime()
                assert status_time == {'data': {'second': 53, 'minute': 19, 'hour': 19, 'weekday': 1, 'day': 18, 'month': 12, 'year': 2022, 'subsecond': 0, 'daylightsaving': 'NONE', 'storeoperation': False}, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus._set_buff(0xB0, time_buff)
                status_time = pijuice.rtcAlarm.GetTime()
                assert status_time == {'data': {'second': 53, 'minute': 19, 'hour': 19, 'weekday': 1, 'day': 18, 'month': 12, 'year': 2022, 'subsecond': 0, 'daylightsaving': 'NONE', 'storeoperation': False}, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0xB0, 1, 0.11)    # RTC_TIME_CMD
                status = pijuice.rtcAlarm.GetTime()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # RTC_TIME_CMD = 0xB0 (W)
                status = pijuice.rtcAlarm.SetTime(None)
                assert status == {'error': 'NO_ERROR'}
                time_parm = status_time['data'].copy()
                time_parm['second'] = "no_seconds"
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'INVALID_SECOND'}
                time_parm = status_time['data'].copy()
                time_parm['second'] = 61
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'INVALID_SECOND'}
                time_parm = status_time['data'].copy()
                time_parm['minute'] = "no_minutes"
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'INVALID_MINUTE'}
                time_parm = status_time['data'].copy()
                time_parm['minute'] = 61
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'INVALID_MINUTE'}
                time_parm = status_time['data'].copy()
                time_parm['hour'] = "no_hours"
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'INVALID_HOUR'}
                time_parm = status_time['data'].copy()
                time_parm['hour'] = "23"
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'NO_ERROR'}
                time_parm['hour'] = "25"
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'INVALID_HOUR'}
                time_parm['hour'] = 25
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'INVALID_HOUR'}
                time_parm['hour'] = "13 AM"
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'INVALID_HOUR'}
                time_parm['hour'] = "13 PM"
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'INVALID_HOUR'}
                time_parm['hour'] = "1 PM"
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'NO_ERROR'}
                time_parm['hour'] = "1 AM"
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'NO_ERROR'}
                time_parm = status_time['data'].copy()
                time_parm['weekday'] = "no_wd"
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'INVALID_WEEKDAY'}
                time_parm = status_time['data'].copy()
                time_parm['weekday'] = 8
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'INVALID_WEEKDAY'}
                time_parm = status_time['data'].copy()
                time_parm['day'] = "no_day"
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'INVALID_DAY'}
                time_parm = status_time['data'].copy()
                time_parm['day'] = 32
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'INVALID_DAY'}
                time_parm = status_time['data'].copy()
                time_parm['month'] = "no_month"
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'INVALID_MONTH'}
                time_parm = status_time['data'].copy()
                time_parm['month'] = 13
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'INVALID_MONTH'}
                time_parm = status_time['data'].copy()
                time_parm['year'] = "no_year"
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'INVALID_YEAR'}
                time_parm = status_time['data'].copy()
                time_parm['year'] = 3000
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'INVALID_YEAR'}
                time_parm = status_time['data'].copy()
                time_parm['subsecond'] = "no_subsecond"
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'INVALID_SUBSECOND'}
                time_parm = status_time['data'].copy()
                time_parm['subsecond'] = 256
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'INVALID_SUBSECOND'}
                time_parm = status_time['data'].copy()
                time_parm['daylightsaving'] = "SUB1H"
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'NO_ERROR'}
                time_parm = status_time['data'].copy()
                time_parm['daylightsaving'] = "ADD1H"
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'NO_ERROR'}
                time_parm = status_time['data'].copy()
                time_parm['storeoperation'] = True
                pijuice.interface.i2cbus.io_error_next_write_call()
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(4)
                pijuice.interface.i2cbus.io_error_next_read_call()
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(4)
                pijuice.interface.i2cbus.corrupt_data_next_read_call()
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'WRITE_FAILED'}
                time_parm = status_time['data'].copy()
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0xB0, 1, 0.11)    # RTC_TIME_CMD
                status = pijuice.rtcAlarm.SetTime(time_parm)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # RTC_ALARM_CMD = 0xB9
                alarm_buff = pijuice.interface.i2cbus._get_buff(0xB9)
                print("+++++", alarm_buff)
                alarm_buff_variation = alarm_buff.copy()
                alarm_buff_variation[1] |= 0x80
                pijuice.interface.i2cbus._set_buff(0xB9, alarm_buff_variation)
                alarm_time = pijuice.rtcAlarm.GetAlarm()
                assert alarm_time == {'data': {'second': 0, 'minute_period': 0, 'hour': 0, 'day': 0}, 'error': 'NO_ERROR'}
                alarm_buff_variation[1] &= 0x7f
                pijuice.interface.i2cbus._set_buff(0xB9, alarm_buff_variation)
                alarm_time = pijuice.rtcAlarm.GetAlarm()
                assert alarm_time == {'data': {'second': 0, 'minute': 0, 'hour': 0, 'day': 0}, 'error': 'NO_ERROR'}
                alarm_buff_variation = alarm_buff.copy()
                alarm_buff_variation[2] |= 0x80
                pijuice.interface.i2cbus._set_buff(0xB9, alarm_buff_variation)
                alarm_time = pijuice.rtcAlarm.GetAlarm()
                assert alarm_time == {'data': {'second': 0, 'minute': 0, 'hour': 'EVERY_HOUR', 'day': 0}, 'error': 'NO_ERROR'}
                alarm_buff_variation[2] &= 0x7f
                pijuice.interface.i2cbus._set_buff(0xB9, alarm_buff_variation)
                alarm_time = pijuice.rtcAlarm.GetAlarm()
                assert alarm_time == {'data': {'second': 0, 'minute': 0, 'hour': 0, 'day': 0}, 'error': 'NO_ERROR'}
                alarm_buff_variation[2] |= 0x40 | 0x80
                alarm_buff_variation[4] = 0xff
                alarm_buff_variation[5] = 0xff
                alarm_buff_variation[6] = 0xff
                pijuice.interface.i2cbus._set_buff(0xB9, alarm_buff_variation)
                alarm_time = pijuice.rtcAlarm.GetAlarm()
                assert alarm_time == {'data': {'second': 0, 'minute': 0, 'hour': 'EVERY_HOUR', 'day': 0}, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus._set_buff(0xB9, alarm_buff)
                alarm_time = pijuice.rtcAlarm.GetAlarm()
                assert alarm_time == {'data': {'second': 0, 'minute': 0, 'hour': 0, 'day': 0}, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0xB9, 1, 0.11)    # RTC_ALARM_CMD
                status = pijuice.rtcAlarm.GetAlarm()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # RTC_ALARM_CMD = 0xB9 (W)
                status = pijuice.rtcAlarm.SetAlarm(None)
                assert status == {'error': 'NO_ERROR'}
                alarm_time_variations = alarm_time['data'].copy()
                alarm_time_variations['second'] = "0s"
                status = pijuice.rtcAlarm.SetAlarm(alarm_time_variations)
                assert status == {"error": "INVALID_SECOND"}
                alarm_time_variations = alarm_time['data'].copy()
                alarm_time_variations['second'] = 61
                status = pijuice.rtcAlarm.SetAlarm(alarm_time_variations)
                assert status == {"error": "INVALID_SECOND"}
                alarm_time_variations = alarm_time['data'].copy()
                alarm_time_variations['minute'] = "0m"
                status = pijuice.rtcAlarm.SetAlarm(alarm_time_variations)
                assert status == {"error": "INVALID_MINUTE"}
                alarm_time_variations = alarm_time['data'].copy()
                alarm_time_variations['minute'] = 61
                status = pijuice.rtcAlarm.SetAlarm(alarm_time_variations)
                assert status == {"error": "INVALID_MINUTE"}
                alarm_time_variations = alarm_time['data'].copy()
                alarm_time_variations['minute_period'] = "0m"
                status = pijuice.rtcAlarm.SetAlarm(alarm_time_variations)
                assert status == {"error": "INVALID_MINUTE_PERIOD"}
                alarm_time_variations = alarm_time['data'].copy()
                alarm_time_variations['minute_period'] = 61
                status = pijuice.rtcAlarm.SetAlarm(alarm_time_variations)
                assert status == {"error": "INVALID_MINUTE_PERIOD"}
                status = pijuice.rtcAlarm.SetAlarm(alarm_time['data'])
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0xB9, 1, 0.11)    # RTC_ALARM_CMD
                status = pijuice.rtcAlarm.SetAlarm(alarm_time['data'])
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)


def test_pijuice_power_functions(hass: HomeAssistant):
    """Test if PiJups loads for standard emulated h/w configuration with default configuration."""
    SMBus.SIM_BUS = 1
    bus = 1
    address = 0x14
    with patch("homeassistant.components.pijups.pijuice.SMBus", new=SMBus):
        with pi.PiJuice(bus, address) as pijuice:
            with pijuice.power:
                # POWER_OFF_CMD = 0x62
                status = pijuice.power.GetPowerOff()
                assert status == {'data': [255], 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x62, 1, 0.11)    # POWER_OFF_CMD
                status = pijuice.power.GetPowerOff()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # POWER_OFF_CMD = 0x62 (W)
                status = pijuice.power.SetPowerOff(5)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x62, 1, 0.11)    # POWER_OFF_CMD
                status = pijuice.power.SetPowerOff(5)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # WAKEUP_ON_CHARGE_CMD = 0x63
                wake_conf = pijuice.interface.i2cbus._get_buff(0x63)
                pijuice.interface.i2cbus._set_buff(0x63, [0x7F, 0])
                status = pijuice.power.GetWakeUpOnCharge()
                assert status == {'data': 'DISABLED', 'non_volatile': False, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus._set_buff(0x63, wake_conf)
                status = pijuice.power.GetWakeUpOnCharge()
                assert status == {'data': 24, 'non_volatile': True, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x63, 1, 0.11)    # WAKEUP_ON_CHARGE_CMD
                status = pijuice.power.GetWakeUpOnCharge()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # WAKEUP_ON_CHARGE_CMD = 0x63 (W)
                status = pijuice.power.SetWakeUpOnCharge("DISABLED0")
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.power.SetWakeUpOnCharge("DISABLED")
                assert status == {'error': 'NO_ERROR'}
                status = pijuice.power.SetWakeUpOnCharge(5)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x63, 1, 0.11)    # WAKEUP_ON_CHARGE_CMD
                status = pijuice.power.SetWakeUpOnCharge(5)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # WATCHDOG_ACTIVATION_CMD = 0x61
                status = pijuice.power.GetWatchdog()
                assert status == {'data': 0, 'non_volatile': False, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x61, 1, 0.11)    # WATCHDOG_ACTIVATION_CMD
                status = pijuice.power.GetWatchdog()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # WATCHDOG_ACTIVATION_CMD = 0x61 (W)
                status = pijuice.power.SetWatchdog("no-wdg")
                assert status == {"error": "BAD_ARGUMENT"}
                status = pijuice.power.SetWatchdog(0x4000)
                assert status == {'error': 'NO_ERROR'}
                status = pijuice.power.SetWatchdog(15)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x61, 1, 0.11)    # WATCHDOG_ACTIVATION_CMD
                status = pijuice.power.SetWatchdog(15)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # SYSTEM_POWER_SWITCH_CTRL_CMD = 0x64
                status = pijuice.power.GetSystemPowerSwitch()
                assert status == {'data': 0, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x64, 1, 0.11)    # SYSTEM_POWER_SWITCH_CTRL_CMD
                status = pijuice.power.GetSystemPowerSwitch()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # SYSTEM_POWER_SWITCH_CTRL_CMD = 0x64 (W)
                status = pijuice.power.SetSystemPowerSwitch('no_ps')
                assert status == {"error": "BAD_ARGUMENT"}
                status = pijuice.power.SetSystemPowerSwitch(1)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x64, 1, 0.11)    # SYSTEM_POWER_SWITCH_CTRL_CMD
                status = pijuice.power.SetSystemPowerSwitch(1)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)


def test_pijuice_config_functions(hass: HomeAssistant):
    """Test if PiJups loads for standard emulated h/w configuration with default configuration."""
    SMBus.SIM_BUS = 1
    bus = 1
    address = 0x14
    with patch("homeassistant.components.pijups.pijuice.SMBus", new=SMBus):
        with pi.PiJuice(bus, address) as pijuice:
            with pijuice.config:
                # CHARGING_CONFIG_CMD = 0x51
                status = pijuice.config.GetChargingConfig()
                assert status == {'data': {'charging_enabled': True}, 'non_volatile': False, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x51, 1, 0.11)    # CHARGING_CONFIG_CMD
                status = pijuice.config.GetChargingConfig()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # CHARGING_CONFIG_CMD = 0x51 (W)
                status = pijuice.config.SetChargingConfig({'charging_enabled': 'none'})
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.config.SetChargingConfig({'charging_enabled_': True})
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.config.SetChargingConfig(False)
                assert status == {'error': 'NO_ERROR'}
                status = pijuice.config.SetChargingConfig(True)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x51, 1, 0.11)    # CHARGING_CONFIG_CMD
                status = pijuice.config.SetChargingConfig(True)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # BATTERY_PROFILE_ID_CMD = 0x52
                bat_prof = pijuice.interface.i2cbus._get_buff(0x52)
                bat_prof_wrong = bat_prof.copy()
                bat_prof_wrong[0] = 0xF0
                pijuice.interface.i2cbus._set_buff(0x52, bat_prof_wrong)
                status = pijuice.config.GetBatteryProfileStatus()
                assert status == {'data': {'validity': 'DATA_WRITE_NOT_COMPLETED'}, 'error': 'NO_ERROR'}
                bat_prof_wrong = bat_prof.copy()
                bat_prof_wrong[0] = 0x0E
                pijuice.interface.i2cbus._set_buff(0x52, bat_prof_wrong)
                status = pijuice.config.GetBatteryProfileStatus()
                assert status == {'data': {'validity': 'VALID', 'source': 'HOST', 'origin': 'PREDEFINED', 'profile': 'UNKNOWN'}, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus._set_buff(0x52, bat_prof)
                status = pijuice.config.GetBatteryProfileStatus()
                assert status == {'data': {'validity': 'VALID', 'source': 'HOST', 'origin': 'PREDEFINED', 'profile': 'BP7X_1820'}, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x52, 1, 0.11)    # BATTERY_PROFILE_ID_CMD
                status = pijuice.config.GetBatteryProfileStatus()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # BATTERY_PROFILE_ID_CMD = 0x52 (W)
                status = pijuice.config.SetBatteryProfile('wrong_profile')
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.config.SetBatteryProfile("DEFAULT")
                assert status == {'error': 'NO_ERROR'}
                status = pijuice.config.SetBatteryProfile("CUSTOM")
                assert status == {'error': 'NO_ERROR'}
                status = pijuice.config.SetBatteryProfile("BP7X_1820")
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x52, 1, 0.11)    # BATTERY_PROFILE_ID_CMD
                status = pijuice.config.SetBatteryProfile("BP7X_1820")
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # BATTERY_PROFILE_CMD = 0x53
                bat_prof = pijuice.interface.i2cbus._get_buff(0x53)
                bat_prof_wrong = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
                pijuice.interface.i2cbus._set_buff(0x53, bat_prof_wrong)
                status = pijuice.config.GetBatteryProfile()
                assert status == {"data": "INVALID", "error": "NO_ERROR"}
                pijuice.interface.i2cbus._set_buff(0x53, bat_prof)
                status = pijuice.config.GetBatteryProfile()
                assert status == {'data': {'capacity': 1820, 'chargeCurrent': 925, 'terminationCurrent': 50, 'regulationVoltage': 4180, 'cutoffVoltage': 3000, 'tempCold': 1, 'tempCool': 10, 'tempWarm': 45, 'tempHot': 59, 'ntcB': 3380, 'ntcResistance': 10000}, 'error': 'NO_ERROR'}
                set_profile_data = status['data']
                pijuice.interface.i2cbus.add_cmd_delays(0x53, 1, 0.11)    # BATTERY_PROFILE_CMD
                status = pijuice.config.GetBatteryProfile()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # BATTERY_PROFILE_CMD = 0x53 (W)
                wrong_profile = set_profile_data.copy()
                del wrong_profile['capacity']
                status = pijuice.config.SetCustomBatteryProfile(wrong_profile)
                assert status == {'error': 'BAD_ARGUMENT'}
                wrong_profile = set_profile_data.copy()
                wrong_profile['capacity'] = 0xffffffff
                status = pijuice.config.SetCustomBatteryProfile(wrong_profile)
                assert status == {'error': 'NO_ERROR'}
                status = pijuice.config.SetCustomBatteryProfile(set_profile_data)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x53, 1, 0.11)    # BATTERY_PROFILE_CMD
                status = pijuice.config.SetCustomBatteryProfile(set_profile_data)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # BATTERY_EXT_PROFILE_CMD = 0x54
                ext_prof = pijuice.interface.i2cbus._get_buff(0x54)
                ext_prof_wrong = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
                pijuice.interface.i2cbus._set_buff(0x54, ext_prof_wrong)
                status = pijuice.config.GetBatteryExtProfile()
                assert status == {"data": "INVALID", "error": "NO_ERROR"}
                ext_prof_wrong = ext_prof.copy()
                ext_prof_wrong[0] = 2
                pijuice.interface.i2cbus._set_buff(0x54, ext_prof_wrong)
                status = pijuice.config.GetBatteryExtProfile()
                pijuice.interface.i2cbus._set_buff(0x54, ext_prof)
                assert status == {'data': {'chemistry': 'UNKNOWN', 'ocv10': 3649, 'ocv50': 3800, 'ocv90': 4077, 'r10': 209.0, 'r50': 205.0, 'r90': 202.0}, 'error': 'NO_ERROR'}
                status = pijuice.config.GetBatteryExtProfile()
                assert status == {'data': {'chemistry': 'LIPO', 'ocv10': 3649, 'ocv50': 3800, 'ocv90': 4077, 'r10': 209.0, 'r50': 205.0, 'r90': 202.0}, 'error': 'NO_ERROR'}
                set_profile_data = status['data']
                pijuice.interface.i2cbus.add_cmd_delays(0x54, 1, 0.11)    # BATTERY_EXT_PROFILE_CMD
                status = pijuice.config.GetBatteryExtProfile()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # BATTERY_EXT_PROFILE_CMD = 0x54 (W)
                wrong_profile = set_profile_data.copy()
                del wrong_profile['chemistry']
                status = pijuice.config.SetCustomBatteryExtProfile(wrong_profile)
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.config.SetCustomBatteryExtProfile(set_profile_data)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x54, 1, 0.11)    # BATTERY_EXT_PROFILE_CMD
                status = pijuice.config.SetCustomBatteryExtProfile(set_profile_data)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # BATTERY_TEMP_SENSE_CONFIG_CMD = 0x5D
                status = pijuice.config.GetBatteryTempSenseConfig()
                assert status == {'data': 'ON_BOARD', 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus._set_buff(0x5D, [0x04, 0])
                status = pijuice.config.GetBatteryTempSenseConfig()
                assert status == {"error": "UNKNOWN_DATA"}
                pijuice.interface.i2cbus.add_cmd_delays(0x5D, 1, 0.11)    # BATTERY_TEMP_SENSE_CONFIG_CMD
                status = pijuice.config.GetBatteryTempSenseConfig()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # BATTERY_TEMP_SENSE_CONFIG_CMD = 0x5D (W)
                status = pijuice.config.SetBatteryTempSenseConfig('WRONG_BOARD')
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.config.SetBatteryTempSenseConfig('ON_BOARD')
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x5D, 1, 0.11)    # BATTERY_TEMP_SENSE_CONFIG_CMD
                status = pijuice.config.SetBatteryTempSenseConfig('ON_BOARD')
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # BATTERY_TEMP_SENSE_CONFIG_CMD = 0x5D
                status = pijuice.config.GetRsocEstimationConfig()
                assert status == {'data': 'AUTO_DETECT', 'error': 'NO_ERROR'}
                est_value = pijuice.interface.i2cbus._get_buff(0x5D)
                pijuice.interface.i2cbus._set_buff(0x5D, [0x20, 0])
                status = pijuice.config.GetRsocEstimationConfig()
                pijuice.interface.i2cbus._set_buff(0x5D, est_value)
                assert status == {"error": "UNKNOWN_DATA"}
                pijuice.interface.i2cbus.add_cmd_delays(0x5D, 1, 0.11)    # BATTERY_TEMP_SENSE_CONFIG_CMD
                status = pijuice.config.GetRsocEstimationConfig()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # BATTERY_TEMP_SENSE_CONFIG_CMD = 0x5D (W)
                status = pijuice.config.SetRsocEstimationConfig('NOT_SELECTED')
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.config.SetRsocEstimationConfig('DIRECT_BY_MCU')
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x5D, 1, 0.11)    # BATTERY_TEMP_SENSE_CONFIG_CMD
                status = pijuice.config.SetRsocEstimationConfig('DIRECT_BY_MCU')
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # POWER_INPUTS_CONFIG_CMD = 0x5E
                power_inputs = pijuice.config.GetPowerInputsConfig()
                assert power_inputs == {'data': {'precedence': '5V_GPIO', 'gpio_in_enabled': True, 'no_battery_turn_on': False, 'usb_micro_current_limit': '2.5A', 'usb_micro_dpm': '4.20V'}, 'non_volatile': False, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x5E, 1, 0.11)    # POWER_INPUTS_CONFIG_CMD
                status = pijuice.config.GetPowerInputsConfig()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # POWER_INPUTS_CONFIG_CMD = 0x5E (W)
                power_config = power_inputs['data']
                wrong_power_config = power_config.copy()
                del wrong_power_config['precedence']
                status = pijuice.config.SetPowerInputsConfig(wrong_power_config)
                assert status == {'error': 'BAD_ARGUMENT'}
                wrong_power_config = power_config.copy()
                wrong_power_config['usb_micro_current_limit'] = "3A"
                status = pijuice.config.SetPowerInputsConfig(wrong_power_config)
                assert status == {'error': 'INVALID_USB_MICRO_CURRENT_LIMIT'}
                wrong_power_config = power_config.copy()
                wrong_power_config['usb_micro_dpm'] = "1.1V"
                status = pijuice.config.SetPowerInputsConfig(wrong_power_config)
                assert status == {"error": "INVALID_USB_MICRO_DPM"}
                status = pijuice.config.SetPowerInputsConfig(power_config)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x5E, 1, 0.11)    # POWER_INPUTS_CONFIG_CMD
                status = pijuice.config.SetPowerInputsConfig(power_config)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # BUTTON_CONFIGURATION_CMD = 0x6E
                button_conf_buff = pijuice.interface.i2cbus._get_buff(0x6E)
                button_conf_buff_unkwn = button_conf_buff.copy()
                button_conf_buff_unkwn[0] |= 0xf0
                pijuice.interface.i2cbus._set_buff(0x6E, button_conf_buff_unkwn)
                button_conf = pijuice.config.GetButtonConfiguration("SW1")
                assert button_conf == {'data': {'PRESS': {'function': 'UNKNOWN', 'parameter': 0}, 'RELEASE': {'function': 'NO_FUNC', 'parameter': 0}, 'SINGLE_PRESS': {'function': 'HARD_FUNC_POWER_ON', 'parameter': 800}, 'DOUBLE_PRESS': {'function': 'NO_FUNC', 'parameter': 0}, 'LONG_PRESS1': {'function': 'SYS_FUNC_HALT', 'parameter': 10000}, 'LONG_PRESS2': {'function': 'HARD_FUNC_POWER_OFF', 'parameter': 20000}}, 'error': 'NO_ERROR'}
                button_conf_buff_unkwn = button_conf_buff.copy()
                button_conf_buff_unkwn[0] = 0x1f
                pijuice.interface.i2cbus._set_buff(0x6E, button_conf_buff_unkwn)
                button_conf = pijuice.config.GetButtonConfiguration("SW1")
                assert button_conf == {'data': {'PRESS': {'function': 'UNKNOWN', 'parameter': 0}, 'RELEASE': {'function': 'NO_FUNC', 'parameter': 0}, 'SINGLE_PRESS': {'function': 'HARD_FUNC_POWER_ON', 'parameter': 800}, 'DOUBLE_PRESS': {'function': 'NO_FUNC', 'parameter': 0}, 'LONG_PRESS1': {'function': 'SYS_FUNC_HALT', 'parameter': 10000}, 'LONG_PRESS2': {'function': 'HARD_FUNC_POWER_OFF', 'parameter': 20000}}, 'error': 'NO_ERROR'}
                button_conf_buff_unkwn = button_conf_buff.copy()
                button_conf_buff_unkwn[0] = 0x2f
                pijuice.interface.i2cbus._set_buff(0x6E, button_conf_buff_unkwn)
                button_conf = pijuice.config.GetButtonConfiguration("SW1")
                assert button_conf == {'data': {'PRESS': {'function': 'USER_FUNC15', 'parameter': 0}, 'RELEASE': {'function': 'NO_FUNC', 'parameter': 0}, 'SINGLE_PRESS': {'function': 'HARD_FUNC_POWER_ON', 'parameter': 800}, 'DOUBLE_PRESS': {'function': 'NO_FUNC', 'parameter': 0}, 'LONG_PRESS1': {'function': 'SYS_FUNC_HALT', 'parameter': 10000}, 'LONG_PRESS2': {'function': 'HARD_FUNC_POWER_OFF', 'parameter': 20000}}, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus._set_buff(0x6E, button_conf_buff)
                status = pijuice.config.GetButtonConfiguration("SW")
                assert status == {"error": "BAD_ARGUMENT"}
                button_conf = pijuice.config.GetButtonConfiguration("SW1")
                assert button_conf == {'data': {'PRESS': {'function': 'NO_FUNC', 'parameter': 0}, 'RELEASE': {'function': 'NO_FUNC', 'parameter': 0}, 'SINGLE_PRESS': {'function': 'HARD_FUNC_POWER_ON', 'parameter': 800}, 'DOUBLE_PRESS': {'function': 'NO_FUNC', 'parameter': 0}, 'LONG_PRESS1': {'function': 'SYS_FUNC_HALT', 'parameter': 10000}, 'LONG_PRESS2': {'function': 'HARD_FUNC_POWER_OFF', 'parameter': 20000}}, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x6E, 1, 0.11)    # BUTTON_CONFIGURATION_CMD
                status = pijuice.config.GetButtonConfiguration("SW1")
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # BUTTON_CONFIGURATION_CMD = 0x6E (W)
                button_config = button_conf['data']
                status = pijuice.config.SetButtonConfiguration("SW", button_config)
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.config.SetButtonConfiguration("SW1", button_config)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x6E, 1, 0.11)    # BUTTON_CONFIGURATION_CMD
                status = pijuice.config.SetButtonConfiguration("SW1", button_config)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # LED_CONFIGURATION_CMD = 0x6A
                led_mode = pijuice.interface.i2cbus._get_buff(0x6A)
                pijuice.interface.i2cbus._set_buff(0x6A, [0x05, 0, 0, 0, 0])
                status = pijuice.config.GetLedConfiguration("D1")
                assert status == {"error": "UNKNOWN_CONFIG"}
                pijuice.interface.i2cbus._set_buff(0x6A, led_mode)
                status = pijuice.config.GetLedConfiguration("D")
                assert status == {"error": "BAD_ARGUMENT"}
                led_conf = pijuice.config.GetLedConfiguration("D1")
                assert led_conf == {'data': {'function': 'CHARGE_STATUS', 'parameter': {'r': 60, 'g': 60, 'b': 100}}, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x6A, 1, 0.11)    # LED_CONFIGURATION_CMD
                status = pijuice.config.GetLedConfiguration("D1")
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # LED_CONFIGURATION_CMD = 0x6A (W)
                led_config = led_conf['data']
                status = pijuice.config.SetLedConfiguration("D", led_config)
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.config.SetLedConfiguration("D1", led_config)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x6A, 1, 0.11)    # LED_CONFIGURATION_CMD
                status = pijuice.config.SetLedConfiguration("D1", led_config)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # POWER_REGULATOR_CONFIG_CMD = 0x60
                reg_mode = pijuice.interface.i2cbus._get_buff(0x60)
                pijuice.interface.i2cbus._set_buff(0x60, [0x05, 0])
                status = pijuice.config.GetPowerRegulatorMode()
                assert status == {"error": "UNKNOWN_DATA"}
                pijuice.interface.i2cbus._set_buff(0x60, reg_mode)
                status = pijuice.config.GetPowerRegulatorMode()
                assert status == {'data': 'POWER_SOURCE_DETECTION', 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x60, 1, 0.11)    # POWER_REGULATOR_CONFIG_CMD
                status = pijuice.config.GetPowerRegulatorMode()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # POWER_REGULATOR_CONFIG_CMD = 0x60 (W)
                led_config = led_conf['data']
                status = pijuice.config.SetPowerRegulatorMode("wrong_power_mode")
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.config.SetPowerRegulatorMode("POWER_SOURCE_DETECTION")
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x60, 1, 0.11)    # POWER_REGULATOR_CONFIG_CMD
                status = pijuice.config.SetPowerRegulatorMode("POWER_SOURCE_DETECTION")
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # RUN_PIN_CONFIG_CMD = 0x5F
                pin_hw_conf = pijuice.interface.i2cbus._get_buff(0x5F)
                pijuice.interface.i2cbus._set_buff(0x5F, [0x04, 0])
                status = pijuice.config.GetRunPinConfig()
                assert status == {"error": "UNKNOWN_DATA"}
                pijuice.interface.i2cbus._set_buff(0x5F, pin_hw_conf)
                status = pijuice.config.GetRunPinConfig()
                assert status == {'data': 'NOT_INSTALLED', 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x5F, 1, 0.11)    # RUN_PIN_CONFIG_CMD
                status = pijuice.config.GetRunPinConfig()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # RUN_PIN_CONFIG_CMD = 0x5F (W)
                status = pijuice.config.SetRunPinConfig("wrong_pin_mode")
                assert status == {'error': 'BAD_ARGUMENT'}
                status = pijuice.config.SetRunPinConfig("INSTALLED")
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x5F, 1, 0.11)    # RUN_PIN_CONFIG_CMD
                status = pijuice.config.SetRunPinConfig("INSTALLED")
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # IO_CONFIGURATION_CMD = 0x72
                io_conf_buff = pijuice.interface.i2cbus._get_buff(0x72)
                io_conf_buff_unkwn = io_conf_buff.copy()
                io_conf_buff_unkwn[0] = 0x07
                pijuice.interface.i2cbus._set_buff(0x72, io_conf_buff_unkwn)
                status = pijuice.config.GetIoConfiguration(1)
                assert status == {'data': {'mode': 'UNKNOWN', 'pull': 'NOPULL', 'wakeup': 'FALLING_EDGE'}, 'non_volatile': False, 'error': 'NO_ERROR'}
                io_conf_buff_unkwn = io_conf_buff.copy()
                io_conf_buff_unkwn[0] = 0x30
                pijuice.interface.i2cbus._set_buff(0x72, io_conf_buff_unkwn)
                status = pijuice.config.GetIoConfiguration(1)
                assert status == {'data': {'mode': 'NOT_USED', 'pull': 'UNKNOWN', 'wakeup': 'FALLING_EDGE'}, 'non_volatile': False, 'error': 'NO_ERROR'}
                io_conf_buff_unkwn = io_conf_buff.copy()
                io_conf_buff_unkwn[0] = 0x03
                pijuice.interface.i2cbus._set_buff(0x72, io_conf_buff_unkwn)
                status = pijuice.config.GetIoConfiguration(1)
                assert status == {'data': {'mode': 'DIGITAL_OUT_PUSHPULL', 'pull': 'NOPULL', 'value': 53}, 'non_volatile': False, 'error': 'NO_ERROR'}
                io_conf_buff_unkwn = io_conf_buff.copy()
                io_conf_buff_unkwn[0] = 0x05
                pijuice.interface.i2cbus._set_buff(0x72, io_conf_buff_unkwn)
                status = pijuice.config.GetIoConfiguration(1)
                assert status == {'data': {'mode': 'PWM_OUT_PUSHPULL', 'pull': 'NOPULL', 'period': 87148, 'duty_cycle': 78.0}, 'non_volatile': False, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus._set_buff(0x72, io_conf_buff)
                io_conf = pijuice.config.GetIoConfiguration(1)
                assert io_conf == {'data': {'mode': 'NOT_USED', 'pull': 'NOPULL', 'wakeup': 'FALLING_EDGE'}, 'non_volatile': True, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x72, 1, 0.11)    # IO_CONFIGURATION_CMD
                status = pijuice.config.GetIoConfiguration(1)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # IO_CONFIGURATION_CMD = 0x72 (W)
                io_config_variants = {'mode': 'DIGITAL_IN', 'pull': 'NOPULL', 'wakeup': 'FALLING_EDGE'}
                status = pijuice.config.SetIoConfiguration(1, io_config_variants)
                assert status == {'error': 'NO_ERROR'}
                io_config_variants = {'mode': 'DIGITAL_OUT_PUSHPULL', 'pull': 'NOPULL', 'value': 53}
                status = pijuice.config.SetIoConfiguration(1, io_config_variants)
                assert status == {'error': 'NO_ERROR'}
                io_config_variants = {'mode': 'PWM_OUT_PUSHPULL', 'pull': 'NOPULL', 'period': 1}
                status = pijuice.config.SetIoConfiguration(1, io_config_variants)
                assert status == {"error": "INVALID_PERIOD"}
                io_config_variants = {'mode': 'PWM_OUT_PUSHPULL', 'pull': 'NOPULL', 'period': 87148, 'duty_cycle': -1}
                status = pijuice.config.SetIoConfiguration(1, io_config_variants)
                assert status == {"error": "INVALID_CONFIG"}
                io_config_variants = {'mode': 'PWM_OUT_PUSHPULL', 'pull': 'NOPULL', 'period': 87148, 'duty_cycle': 78.0}
                status = pijuice.config.SetIoConfiguration(1, io_config_variants)
                assert status == {'error': 'NO_ERROR'}
                io_config = io_conf['data']
                io_config_wrong = {}
                status = pijuice.config.SetIoConfiguration(1, io_config_wrong)
                assert status == {"error": "INVALID_CONFIG"}
                status = pijuice.config.SetIoConfiguration(1, io_config)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x72, 1, 0.11)    # IO_CONFIGURATION_CMD
                status = pijuice.config.SetIoConfiguration(1, io_config)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # I2C_ADDRESS_CMD = 0x7C
                status = pijuice.config.GetAddress(3)
                assert status == {"error": "BAD_ARGUMENT"}
                status = pijuice.config.GetAddress(1)
                assert status == {'data': '14', 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x7C, 1, 0.11)    # I2C_ADDRESS_CMD
                status = pijuice.config.GetAddress(1)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # I2C_ADDRESS_CMD = 0x7C (W)
                status = pijuice.config.SetAddress(3, 20)
                assert status == {"error": "BAD_ARGUMENT"}
                status = pijuice.config.SetAddress(1, "20x")
                assert status == {"error": "BAD_ARGUMENT"}
                status = pijuice.config.SetAddress(1, 21)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x7C, 1, 0.11)    # I2C_ADDRESS_CMD
                status = pijuice.config.SetAddress(1, 21)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # ID_EEPROM_WRITE_PROTECT_CTRL_CMD = 0x7E
                status = pijuice.config.GetIdEepromWriteProtect()
                assert status == {'data': True, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x7E, 1, 0.11)    # ID_EEPROM_WRITE_PROTECT_CTRL_CMD
                status = pijuice.config.GetIdEepromWriteProtect()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # ID_EEPROM_WRITE_PROTECT_CTRL_CMD = 0x7E (W)
                status = pijuice.config.SetIdEepromWriteProtect("false")
                assert status == {"error": "BAD_ARGUMENT"}
                status = pijuice.config.SetIdEepromWriteProtect(False)
                assert status == {'error': 'NO_ERROR'}
                status = pijuice.config.SetIdEepromWriteProtect(True)
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x7E, 1, 0.11)    # ID_EEPROM_WRITE_PROTECT_CTRL_CMD
                status = pijuice.config.SetIdEepromWriteProtect(True)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # ID_EEPROM_ADDRESS_CMD = 0x7F
                status = pijuice.config.GetIdEepromAddress()
                assert status == {'data': '50', 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x7F, 1, 0.11)    # ID_EEPROM_ADDRESS_CMD
                status = pijuice.config.GetIdEepromAddress()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # ID_EEPROM_ADDRESS_CMD = 0x7F (W)
                status = pijuice.config.SetIdEepromAddress("47")
                assert status == {"error": "BAD_ARGUMENT"}
                status = pijuice.config.SetIdEepromAddress("52")
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0x7F, 1, 0.11)    # ID_EEPROM_ADDRESS_CMD
                status = pijuice.config.SetIdEepromAddress("52")
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # RESET_TO_DEFAULT_CMD = 0xF0
                status = pijuice.config.SetDefaultConfiguration()
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0xF0, 1, 0.11)    # RESET_TO_DEFAULT_CMD
                status = pijuice.config.SetDefaultConfiguration()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # FIRMWARE_VERSION_CMD = 0xFD
                status = pijuice.config.GetFirmwareVersion()
                assert status == {'data': {'version': '1.6', 'variant': '0'}, 'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(0xFD, 1, 0.11)    # FIRMWARE_VERSION_CMD
                status = pijuice.config.GetFirmwareVersion()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)
                # RunTestCalibration = 248
                status = pijuice.config.RunTestCalibration()
                assert status == {'error': 'NO_ERROR'}
                pijuice.interface.i2cbus.add_cmd_delays(248, 1, 0.11)    # FIRMWARE_VERSION_CMD
                status = pijuice.config.RunTestCalibration()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(0.1)


def test_pijuice_different_transfer_issues(hass: HomeAssistant):
    """Test if PiJups loads for standard emulated h/w configuration with default configuration."""
    SMBus.SIM_BUS = 1
    bus = 1
    address = 0x14
    with patch("homeassistant.components.pijups.pijuice.SMBus", new=SMBus):
        with pi.PiJuice(bus, address) as pijuice:
            with pijuice.config:
                # IO_VOLTAGE_CMD = 0x4D
                pijuice.interface.i2cbus.manage_data_corruptions(True)
                status = pijuice.status.GetIoVoltage()
                pijuice.interface.i2cbus.manage_data_corruptions(False)
                assert status == {'error': 'DATA_CORRUPTED'}

                pijuice.interface.i2cbus.manage_chksum_calculations(True)
                pijuice.interface.i2cbus._set_buff(0x4D, [0xf0, 0x08, 0])
                status = pijuice.status.GetIoVoltage()
                pijuice.interface.i2cbus.manage_chksum_calculations(False)
                assert status == {'data': 2288, 'error': 'NO_ERROR'}

                # STATUS_CMD = 0x40
                pijuice.interface.i2cbus.io_error_next_read_call()
                status = pijuice.status.GetStatus()
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(4)

                # ID_EEPROM_ADDRESS_CMD = 0x7F (W)
                pijuice.interface.i2cbus.io_error_next_read_call()
                status = pijuice.config.SetIdEepromAddress("52")
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(4)
                pijuice.interface.i2cbus.corrupt_data_next_read_call()
                status = pijuice.config.SetIdEepromAddress("52")
                assert status == {'error': 'WRITE_FAILED'}
                time.sleep(0.1)
                pijuice.interface.i2cbus.io_error_next_write_call()
                status = pijuice.config.SetIdEepromAddress("52")
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(4)
                # I2C_ADDRESS_CMD = 0x7C (W)
                pijuice.interface.i2cbus.io_error_next_write_call()
                status = pijuice.config.SetAddress(1, 21)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(4)

                # CHARGING_CONFIG_CMD = 0x51 (W)
                pijuice.interface.i2cbus.io_error_next_read_call()
                status = pijuice.config.SetChargingConfig(False, non_volatile=False)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(4)
                pijuice.interface.i2cbus.corrupt_data_next_read_call()
                status = pijuice.config.SetChargingConfig(False, non_volatile=False)
                assert status == {'error': 'NO_ERROR'}
                time.sleep(0.1)
                pijuice.interface.i2cbus.io_error_next_write_call()
                status = pijuice.config.SetChargingConfig(False, non_volatile=False)
                assert status == {'error': 'COMMUNICATION_ERROR'}
                time.sleep(4)

def test_pijuice_different_independent_funcs(hass: HomeAssistant):
    """Test if PiJups loads for standard emulated h/w configuration with default configuration."""
    SMBus.SIM_BUS = 1
    bus = 1
    address = 0x14
    with patch("homeassistant.components.pijups.pijuice.SMBus", new=SMBus):
        with pi.PiJuice(bus, address) as pijuice:
            with pijuice.config:
                pijuice.config.SelectBatteryProfiles(0x15)
                assert len(pijuice.config.batteryProfiles) > 0
                pijuice.config.SelectBatteryProfiles(0x14)
                assert len(pijuice.config.batteryProfiles) > 0
                pijuice.config.SelectBatteryProfiles(0x13)
                assert len(pijuice.config.batteryProfiles) > 0
                pijuice.config.SelectBatteryProfiles(0x12)
                assert len(pijuice.config.batteryProfiles) > 0
            write_status = pijuice.interface.WriteDataVerify(0x5D, [0x00], "no_delay")
            assert write_status == {'error': 'NO_ERROR'}
            # STATUS_CMD = 0x40
            pijuice.interface.i2cbus.add_cmd_delays(0x40, 1, 0.11)    # STATUS_CMD
            status = pijuice.status.GetStatus()
            assert status == {'error': 'COMMUNICATION_ERROR'}
            status = pijuice.status.GetStatus()
            assert status == {'error': 'COMMUNICATION_ERROR'}
            time.sleep(0.1)
        version_info = pi.get_versions()
        assert len(version_info) > 0
