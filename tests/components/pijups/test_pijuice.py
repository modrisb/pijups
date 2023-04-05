"""Test PiJups initilization path initiated from __init__.py."""
import time
import inspect
from unittest.mock import patch
import homeassistant.components.pijups.pijuice as pi
from homeassistant.core import (
    HomeAssistant,
)

from .smbus2 import SMBus

from tests.components.pijups import common

STATUS_FUNC_TESTS = [
    {
        "cmd": 0x40, "func": "GetStatus", "type": "r", "data_buffer": [0b11000011, 0],
        "ret": {"data": {'isFault': True, 'isButton': True, 'battery': 'NORMAL', 'powerInput': 'NOT_PRESENT', 'powerInput5vIo': 'PRESENT'},
        "error": 'NO_ERROR'},
        "cmd_delay": 0, "write_err": False, "read_err": False,
        "next_read_buffer": None,
    },
    {
        "cmd": 0x40, "func": "GetStatus", "ret": {"error": 'COMMUNICATION_ERROR'}, "parm": (),
        "cmd_delay": 1,
    },
    {
        "cmd": 0x40, "func": "GetStatus", "ret": {"error": 'COMMUNICATION_ERROR'}, "parm": (),
        "read_err": True,
    },
    {
        "cmd": 0x40, "func": "GetStatus", "data_buffer": [0b11000011, 0],
        "ret": {"data": {'isFault': True, 'isButton': True, 'battery': 'NORMAL', 'powerInput': 'NOT_PRESENT', 'powerInput5vIo': 'PRESENT'},
        "error": 'NO_ERROR'}, "parm": (),
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x40, "func": "GetStatus", "data_buffer": [0b11000011, 0],
        "ret": {'error': 'DATA_CORRUPTED'}, "parm": (),
        "checksum_err": True,
    },
    {
        "cmd": 0x41, "func": "GetChargeLevel", "data_buffer": [82, 0],
        "ret":{"data": 82, "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x41, "func": "GetChargeLevel", "data_buffer": [82, 0],
        "ret": {'error': 'DATA_CORRUPTED'},
        "checksum_err": True,
    },
    {
        "cmd": 0x41, "func": "GetChargeLevel", "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x44, "func": "GetFaultStatus", "data_buffer": [0b11101111, 0],
        "ret": {"data": {'button_power_off': True, 'forced_power_off': True, 'forced_sys_power_off': True, 'watchdog_reset': True, 'battery_profile_invalid': True, 'charging_temperature_fault': 'WARM'},
        "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x44, "func": "GetFaultStatus", "data_buffer": [0b10101111, 0],
        "ret": {"data": {'button_power_off': True, 'forced_power_off': True, 'forced_sys_power_off': True, 'watchdog_reset': True, 'battery_profile_invalid': True, 'charging_temperature_fault': 'COOL'},
        "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x44, "func": "GetFaultStatus", "data_buffer": [0b01101111, 0],
        "ret": {"data": {'button_power_off': True, 'forced_power_off': True, 'forced_sys_power_off': True, 'watchdog_reset': True, 'battery_profile_invalid': True, 'charging_temperature_fault': 'SUSPEND'},
        "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x44, "func": "GetFaultStatus", "data_buffer": [0b00101111, 0],
        "ret": {"data": {'button_power_off': True, 'forced_power_off': True, 'forced_sys_power_off': True, 'watchdog_reset': True, 'battery_profile_invalid': True},
        "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x44, "func": "GetFaultStatus", "data_buffer": [0b00001111, 0],
        "ret": {"data": {'button_power_off': True, 'forced_power_off': True, 'forced_sys_power_off': True, 'watchdog_reset': True},
        "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x44, "func": "GetFaultStatus", "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": True,
    },
    {
        "cmd": 0x44, "func": "GetFaultStatus",
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x44, "func": "GetFaultStatus", "data_buffer": [0b00001111, 0],
        "ret": {"data": {'button_power_off': True, 'forced_power_off': True, 'forced_sys_power_off': True, 'watchdog_reset': True},
        "error": 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x44, "func": "GetFaultStatus", "data_buffer": [0b00001111, 0], "parm": (),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x44, "func": "GetFaultStatus", "data_buffer": [0b00001111, 0], "parm": (),
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },
    {
        "cmd": 0x44, "func": "GetFaultStatus", "ret": {"error": 'COMMUNICATION_ERROR'}, "parm": (),
        "cmd_delay": 1,
    },
    {
        "cmd": 0x44, "func": "ResetFaultFlags", "type": "w", "data_buffer_before": [0b11111111, 0], "data_buffer": [0b11110000, 0],
        "parm": ({'button_power_off': True, 'forced_power_off': True, 'forced_sys_power_off': True, 'watchdog_reset': True},),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x44, "func": "ResetFaultFlags", "type": "w", "data_buffer_before": [0b11111111, 0], "data_buffer": [0b11111111, 0],
        "parm": ({'unknown_fault': True},),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x44, "func": "ResetFaultFlags", "type": "w", "ret": {"error": 'COMMUNICATION_ERROR'}, "parm": ({"button_power_off": True},),
        "write_err": True,
    },
    {
        "cmd": 0x44, "func": "ResetFaultFlags", "type": "w", "ret": {"error": 'COMMUNICATION_ERROR'}, "parm": ({"button_power_off": True},),
        "cmd_delay": 1,
    },
    {
        "cmd": 0x45, "func": "GetButtonEvents", "data_buffer": [0x77, 0x77, 0], "parm": (),
        "ret": {"data": {'SW1': 'UNKNOWN', 'SW2': 'UNKNOWN', 'SW3': 'UNKNOWN'},
        "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x45, "func": "GetButtonEvents", "data_buffer": [0, 0, 0], "parm": (),
        "ret": {"data": {'SW1': 'NO_EVENT', 'SW2': 'NO_EVENT', 'SW3': 'NO_EVENT'},
        "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x45, "func": "GetButtonEvents", "data_buffer": [1, 0, 0], "parm": (),
        "ret": {"data": {'SW1': 'PRESS', 'SW2': 'NO_EVENT', 'SW3': 'NO_EVENT'},
        "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x45, "func": "GetButtonEvents", "data_buffer": [2, 0, 0], "parm": (),
        "ret": {"data": {'SW1': 'RELEASE', 'SW2': 'NO_EVENT', 'SW3': 'NO_EVENT'},
        "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x45, "func": "GetButtonEvents", "data_buffer": [3, 0, 0], "parm": (),
        "ret": {"data": {'SW1': 'SINGLE_PRESS', 'SW2': 'NO_EVENT', 'SW3': 'NO_EVENT'},
        "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x45, "func": "GetButtonEvents", "data_buffer": [4, 0, 0], "parm": (),
        "ret": {"data": {'SW1': 'DOUBLE_PRESS', 'SW2': 'NO_EVENT', 'SW3': 'NO_EVENT'},
        "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x45, "func": "GetButtonEvents", "data_buffer": [5, 0, 0], "parm": (),
        "ret": {"data": {'SW1': 'LONG_PRESS1', 'SW2': 'NO_EVENT', 'SW3': 'NO_EVENT'},
        "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x45, "func": "GetButtonEvents", "data_buffer": [6, 0, 0], "parm": (),
        "ret": {"data": {'SW1': 'LONG_PRESS2', 'SW2': 'NO_EVENT', 'SW3': 'NO_EVENT'},
        "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x45, "func": "GetButtonEvents", "data_buffer": [7, 0, 0], "parm": (),
        "ret": {"data": {'SW1': 'UNKNOWN', 'SW2': 'NO_EVENT', 'SW3': 'NO_EVENT'},
        "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x45, "func": "GetButtonEvents", "ret": {"error": 'COMMUNICATION_ERROR'}, "parm": (),
        "cmd_delay": 1,
    },
    {
        "cmd": 0x45, "func": "GetButtonEvents", "ret": {"error": 'COMMUNICATION_ERROR'}, "parm": (),
        "read_err": 1,
    },
    {
        "cmd": 0x45, "func": "AcceptButtonEvent", "type": "w", "data_buffer": [0x77, 0x77, 0],
        "parm": ("SW17",),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x45, "func": "AcceptButtonEvent", "type": "w", "data_buffer_before": [0xFF, 0xFF, 0], "data_buffer": [0xF0, 0xFF, 0],
        "parm": ('SW1',),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x45, "func": "AcceptButtonEvent", "type": "w", "data_buffer_before": [0xFF, 0xFF, 0], "data_buffer": [0x0F, 0xFF, 0],
        "parm": ('SW2',),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x45, "func": "AcceptButtonEvent", "type": "w", "data_buffer_before": [0xFF, 0xFF, 0], "data_buffer": [0xFF, 0xF0, 0],
        "parm": ('SW3',),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x45, "func": "AcceptButtonEvent", "type": "w", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": ('SW1',),
        "cmd_delay": 1,
    },
    {
        "cmd": 0x45, "func": "AcceptButtonEvent", "type": "w", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": ('SW1',),
        "write_err": True,
    },
    {
        "cmd": 0x47, "func": "GetBatteryTemperature", "type": "r", "data_buffer": [48, 255, 0],
        "ret": {'data': 48, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x47, "func": "GetBatteryTemperature", "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x47, "func": "GetBatteryTemperature", "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": True,
    },
    {
        "cmd": 0x47, "func": "GetBatteryTemperature", "data_buffer": [0x80, 255, 0],
        "ret": {'data': -128, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x47, "func": "GetBatteryTemperature", "data_buffer": [48, 255, 0],
        "ret": {'error': 'DATA_CORRUPTED'},
        "checksum_err": True,
    },
    {
        "cmd": 0x49, "func": "GetBatteryVoltage", "type": "r", "data_buffer": [180, 15, 0],
        "ret": {'data': 4020, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x49, "func": "GetBatteryVoltage", "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x49, "func": "GetBatteryVoltage", "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": True,
    },
    {
        "cmd": 0x49, "func": "GetBatteryVoltage", "data_buffer": [0x80, 15, 0],
        "ret": {'data': 3968, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x49, "func": "GetBatteryVoltage", "data_buffer": [180, 15, 0],
        "ret": {'error': 'DATA_CORRUPTED'},
        "checksum_err": True,
    },
    {
        "cmd": 0x4B, "func": "GetBatteryCurrent", "type": "r", "data_buffer": [12, 0, 0],
        "ret": {'data': 12, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x4B, "func": "GetBatteryCurrent", "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x4B, "func": "GetBatteryCurrent", "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": True,
    },
    {
        "cmd": 0x4B, "func": "GetBatteryCurrent", "data_buffer": [12, 0x80, 0],
        "ret": {'data': -32756, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x4B, "func": "GetBatteryCurrent", "data_buffer": [12, 0, 0],
        "ret": {'error': 'DATA_CORRUPTED'},
        "checksum_err": True,
    },
    {
        "cmd": 0x4D, "func": "GetIoVoltage", "type": "r", "data_buffer": [50, 20, 0],
        "ret": {'data': 5170, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x4D, "func": "GetIoVoltage", "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x4D, "func": "GetIoVoltage", "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": True,
    },
    {
        "cmd": 0x4D, "func": "GetIoVoltage", "data_buffer": [0x80, 20, 0],
        "ret": {'data': 5248, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x4D, "func": "GetIoVoltage", "data_buffer": [50, 20, 0],
        "ret": {'error': 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x4F, "func": "GetIoCurrent", "type": "r", "data_buffer": [146, 251, 0],
        "ret": {'data': -1134, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x4F, "func": "GetIoCurrent", "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x4F, "func": "GetIoCurrent", "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": True,
    },
    {
        "cmd": 0x4F, "func": "GetIoCurrent", "data_buffer": [0x80, 251, 0],
        "ret": {'data': -1152, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x4F, "func": "GetIoCurrent", "data_buffer": [146, 251, 0],
        "ret": {'error': 'DATA_CORRUPTED'},
        "checksum_err": True,
    },


    {
        "cmd": 0x66, "func": "SetLedState", "type": "w", "data_buffer": [0, 60, 100, 0],
        "parm": ("C1", [10, 60, 100]),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x66, "func": "SetLedState", "type": "w", "data_buffer_before": [0, 60, 100, 0], "data_buffer": [0xF0, 0xFF, 0, 0],
        "parm": ('D1', [0xF0, 0xFF, 0]),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x67, "func": "SetLedState", "type": "w", "data_buffer_before": [0, 60, 100, 0], "data_buffer": [0xFF, 0xF0, 11, 0],
        "parm": ('D2', [0xFF, 0xF0, 11]),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x66, "func": "SetLedState", "type": "w", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": ('D1', [0xF0, 0xFF, 0]),
        "cmd_delay": 1,
    },
    {
        "cmd": 0x66, "func": "SetLedState", "type": "w", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": ('D1', [0xF0, 0xFF, 0]),
        "write_err": True,
    },
    {
        "cmd": 0x66, "func": "GetLedState", "type": "r", "data_buffer": [0, 60, 100, 0],
        "parm": ('D',),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x66, "func": "GetLedState", "type": "r", "data_buffer": [0, 60, 100, 0],
        "parm": ('D1',),
        "ret": {'data': [0, 60, 100], 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x67, "func": "GetLedState", "type": "r", "data_buffer": [0, 15, 0, 0],
        "parm": ('D2',),
        "ret": {'data': [0, 15, 0], 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x66, "func": "GetLedState", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": ('D1',),
        "cmd_delay": 1,
    },
    {
        "cmd": 0x66, "func": "GetLedState", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": ('D1',),
        "read_err": True,
    },
    {
        "cmd": 0x66, "func": "GetLedState", "data_buffer": [0, 60, 100, 0],
        "parm": ('D1',),
        "ret": {'data': [0, 60, 100], 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x66, "func": "GetLedState", "data_buffer": [0, 60, 100, 0],
        "parm": ('D1',),
        "ret": {'error': 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x68, "func": "SetLedBlink", "type": "w", "data_buffer": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "parm": ("D", 0, [0, 0, 0], 0, [0, 0, 0], 0),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x68, "func": "SetLedBlink", "type": "w", "data_buffer_before": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "data_buffer": [1, 2, 3, 4, 5, 6, 7, 8, 9, 0],
        "parm": ('D1', 1, [2, 3, 4], 50, [6, 7, 8], 90),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x69, "func": "SetLedBlink", "type": "w", "data_buffer_before": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "data_buffer": [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
        "parm": ('D2', 9, [8, 7, 6], 50, [4, 3, 2], 10),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x68, "func": "SetLedBlink", "type": "w", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": ('D1', 0, [0, 0, 0], 0, [0, 0, 0], 0),
        "cmd_delay": 1,
    },
    {
        "cmd": 0x68, "func": "SetLedBlink", "type": "w", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": ('D1', 0, [0, 0, 0], 0, [0, 0, 0], 0),
        "write_err": True,
    },
    {
        "cmd": 0x68, "func": "GetLedBlink", "type": "r", "data_buffer": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "parm": ('D',),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x68, "func": "GetLedBlink", "type": "r", "data_buffer": [1, 2, 3, 4, 5, 6, 7, 8, 9, 0],
        "parm": ('D1',),
        "ret": {'data': {'count': 1, 'rgb1': [2, 3, 4], 'period1': 50, 'rgb2': [6, 7, 8], 'period2': 90}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x69, "func": "GetLedBlink", "type": "r", "data_buffer": [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
        "parm": ('D2',),
        "ret": {'data': {'count': 9, 'rgb1': [8, 7, 6], 'period1': 50, 'rgb2': [4, 3, 2], 'period2': 10}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x68, "func": "GetLedBlink", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": ('D1',),
        "cmd_delay": 1,
    },
    {
        "cmd": 0x68, "func": "GetLedBlink", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": ('D1',),
        "read_err": True,
    },
    {
        "cmd": 0x68, "func": "GetLedBlink", "data_buffer": [1, 2, 3, 4, 5, 6, 7, 8, 9, 0],
        "parm": ('D1',),
        "ret": {'data': {'count': 1, 'rgb1': [2, 3, 4], 'period1': 50, 'rgb2': [6, 7, 8], 'period2': 90}, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x68, "func": "GetLedBlink", "data_buffer": [1, 2, 3, 4, 5, 6, 7, 8, 9, 0],
        "parm": ('D1',),
        "ret": {'error': 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x75, "func": "SetIoDigitalOutput", "type": "w", "data_buffer": [117, 53, 0],
        "parm": (3, 3),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x75, "func": "SetIoDigitalOutput", "type": "w", "data_buffer_before": [117, 53, 0], "data_buffer": [0, 1, 0],
        "parm": (1, 1),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x75, "func": "SetIoDigitalOutput", "type": "w", "data_buffer_before": [117, 53, 0], "data_buffer": [0, 0, 0],
        "parm": (1, 0),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x7A, "func": "SetIoDigitalOutput", "type": "w", "data_buffer_before": [117, 53, 0], "data_buffer": [0, 0, 0],
        "parm": (2, 0),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x7A, "func": "SetIoDigitalOutput", "type": "w", "data_buffer_before": [117, 53, 0], "data_buffer": [0, 1, 0],
        "parm": (2, 1),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x75, "func": "SetIoDigitalOutput", "type": "w", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": (1, 1),
        "cmd_delay": 1,
    },
    {
        "cmd": 0x75, "func": "SetIoDigitalOutput", "type": "w", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": (1, 1),
        "write_err": True,
    },
    {
        "cmd": 0x75, "func": "GetIoDigitalInput", "type": "r", "data_buffer": [117, 53, 0],
        "parm": (3,),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x75, "func": "GetIoDigitalInput", "type": "r", "data_buffer": [117, 0x01, 0],
        "parm": (1,),
        "ret": {'data': 0, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x7A, "func": "GetIoDigitalInput", "type": "r", "data_buffer": [0, 0x01, 0],
        "parm": (2,),
        "ret": {'data': 0, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x75, "func": "GetIoDigitalInput", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": (1,),
        "cmd_delay": 1,
    },
    {
        "cmd": 0x75, "func": "GetIoDigitalInput", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": (1,),
        "read_err": True,
    },
    {
        "cmd": 0x75, "func": "GetIoDigitalInput", "data_buffer": [0, 60, 100, 0],
        "parm": (1,),
        "ret": {'data': 0, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x75, "func": "GetIoDigitalInput", "data_buffer": [0, 60, 100, 0],
        "parm": (1,),
        "ret": {'error': 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x75, "func": "GetIoDigitalOutput", "type": "r", "data_buffer": [0, 0, 0],
        "parm": (3,),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x75, "func": "GetIoDigitalOutput", "type": "r", "data_buffer": [1, 0x01, 0],
        "parm": (1,),
        "ret": {'data': 1, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x7A, "func": "GetIoDigitalOutput", "type": "r", "data_buffer": [1, 0x01, 0],
        "parm": (2,),
        "ret": {'data': 1, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x75, "func": "GetIoDigitalOutput", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": (1,),
        "cmd_delay": 1,
    },
    {
        "cmd": 0x75, "func": "GetIoDigitalOutput", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": (1,),
        "read_err": True,
    },
    {
        "cmd": 0x75, "func": "GetIoDigitalOutput", "data_buffer": [1, 0x02, 0],
        "parm": (1,),
        "ret": {'data': 0, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x75, "func": "GetIoDigitalOutput", "data_buffer": [1, 0x01, 0],
        "parm": (1,),
        "ret": {'error': 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x75, "func": "GetIoAnalogInput", "type": "r", "data_buffer": [0, 0, 0],
        "parm": (3,),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x75, "func": "GetIoAnalogInput", "type": "r", "data_buffer": [1, 0x01, 0],
        "parm": (1,),
        "ret": {'data': 257, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x7A, "func": "GetIoAnalogInput", "type": "r", "data_buffer": [1, 0x01, 0],
        "parm": (2,),
        "ret": {'data': 257, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x75, "func": "GetIoAnalogInput", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": (1,),
        "cmd_delay": 1,
    },
    {
        "cmd": 0x75, "func": "GetIoAnalogInput", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": (1,),
        "read_err": True,
    },
    {
        "cmd": 0x75, "func": "GetIoAnalogInput", "data_buffer": [1, 0x02, 0],
        "parm": (1,),
        "ret": {'data': 513, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x75, "func": "GetIoAnalogInput", "data_buffer": [1, 0x01, 0],
        "parm": (1,),
        "ret": {'error': 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x75, "func": "SetIoPWM", "type": "w", "data_buffer": [117, 53, 0],
        "parm": (3, 10),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x75, "func": "SetIoPWM", "type": "w", "data_buffer": [117, 53, 0],
        "parm": (1, "d"),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x75, "func": "SetIoPWM", "type": "w", "data_buffer": [117, 53, 0],
        "parm": (1, 110),
        "ret": {"error": 'INVALID_DUTY_CYCLE'},
    },
    {
        "cmd": 0x75, "func": "SetIoPWM", "type": "w", "data_buffer_before": [117, 53, 0], "data_buffer": [255, 127, 0],
        "parm": (1, 50),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x75, "func": "SetIoPWM", "type": "w", "data_buffer_before": [117, 53, 0], "data_buffer": [0, 0, 0],
        "parm": (1, 0),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x7A, "func": "SetIoPWM", "type": "w", "data_buffer_before": [117, 53, 0], "data_buffer": [255, 127, 0],
        "parm": (2, 50),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x7A, "func": "SetIoPWM", "type": "w", "data_buffer_before": [117, 53, 0], "data_buffer": [10, 23, 0],
        "parm": (2, 9),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x75, "func": "SetIoPWM", "type": "w", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": (1, 1),
        "cmd_delay": 1,
    },
    {
        "cmd": 0x75, "func": "SetIoPWM", "type": "w", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": (1, 1),
        "write_err": True,
    },

    {
        "cmd": 0x75, "func": "GetIoPWM", "type": "r", "class": "status",
        "data_buffer": [117, 53, 0],
        "parm": (3, ),
        "ret": {'error': 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x75, "func": "GetIoPWM", "type": "r", "class": "status",
        "data_buffer": [255, 127, 0],
        "parm": (1, ),
        "ret": {'data': 50.0, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x7A, "func": "GetIoPWM", "type": "r", "class": "status",
        "data_buffer": [10, 23, 0],
        "parm": (2, ),
        "ret": {'data': 8.0, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x75, "func": "GetIoPWM", "type": "r", "class": "status",
        "data_buffer": [117, 53, 0],
        "parm": (1, ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x75, "func": "GetIoPWM", "type": "r", "class": "status",
        "data_buffer": [117, 53, 0],
        "parm": (1, ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": True,
    },
    {
        "cmd": 0x75, "func": "GetIoPWM", "type": "r", "class": "status",
        "data_buffer": [130, 53, 0],
        "parm": (1, ),
        "ret": {'data': 20.0, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x75, "func": "GetIoPWM", "class": "status",
        "data_buffer": [117, 53, 0],
        "parm": (1, ),
        "ret": {'error': 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0xC2, "func": "GetControlStatus", "type": "r", "class": "rtcAlarm", "data_buffer": [0, 0, 0],
        "ret": {'data': {'alarm_wakeup_enabled': False, 'alarm_flag': False}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xC2, "func": "GetControlStatus", "type": "r", "class": "rtcAlarm", "data_buffer": [0x05, 0x01, 0],
        "ret": {'data': {'alarm_wakeup_enabled': True, 'alarm_flag': True}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xC2, "func": "GetControlStatus", "type": "r", "class": "rtcAlarm", "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0xC2, "func": "GetControlStatus", "type": "r", "class": "rtcAlarm", "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": True,
    },
    {
        "cmd": 0xC2, "func": "GetControlStatus", "type": "r", "class": "rtcAlarm", "data_buffer": [0x05, 0x01, 0],
        "ret": {'data': {'alarm_wakeup_enabled': True, 'alarm_flag': True}, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0xC2, "func": "GetControlStatus", "class": "rtcAlarm", "data_buffer": [1, 0x01, 0],
        "ret": {'error': 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0xC2, "func": "ClearAlarmFlag", "type": "w", "class": "rtcAlarm",
        "data_buffer_before": [0x01, 0xFF, 0], "data_buffer": [0x01, 0xFE, 0],
        "ret": {'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xC2, "func": "ClearAlarmFlag", "type": "w", "class": "rtcAlarm",
        "data_buffer_before": [0x01, 0xFE, 0], "data_buffer": [0x01, 0xFE, 0],
        "ret": {'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xC2, "func": "ClearAlarmFlag", "type": "w", "class": "rtcAlarm", "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0xC2, "func": "ClearAlarmFlag", "type": "w", "class": "rtcAlarm", "ret": {"error": 'COMMUNICATION_ERROR'},
        "data_buffer_before": [0x01, 0xFF, 0], "data_buffer": [0x01, 0xFE, 0],
        "write_err": True,
    },
    {
        "cmd": 0xC2, "func": "ClearAlarmFlag", "type": "w", "class": "rtcAlarm", "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": True,
    },
    {
        "cmd": 0xC2, "func": "ClearAlarmFlag", "type": "w", "class": "rtcAlarm",
        "data_buffer_before": [0x05, 0x01, 0], "data_buffer": [0x05, 0x00, 0],
        "ret": {'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0xC2, "func": "ClearAlarmFlag", "type": "w", "class": "rtcAlarm", "data_buffer": [1, 0x01, 0],
        "ret": {'error': 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0xC2, "func": "SetWakeupEnabled", "type": "w", "class": "rtcAlarm",
        "data_buffer_before": [0x05, 0x00, 0], "data_buffer": [0x05, 0x00, 0],
        "parm": (1,),
        "ret": {'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xC2, "func": "SetWakeupEnabled", "type": "w", "class": "rtcAlarm",
        "data_buffer_before": [0x05, 0xFE, 0], "data_buffer": [0x04, 0xFE, 0],
        "parm": (0,),
        "ret": {'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xC2, "func": "SetWakeupEnabled", "type": "w", "class": "rtcAlarm",
        "data_buffer_before": [0x00, 0x00, 0], "data_buffer": [0x05, 0x00, 0],
        "parm": (1,),
        "ret": {'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xC2, "func": "SetWakeupEnabled", "type": "w", "class": "rtcAlarm",
        "data_buffer_before": [0x00, 0x00, 0], "data_buffer": [0x00, 0x00, 0],
        "parm": (0,),
        "ret": {'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xC2, "func": "SetWakeupEnabled", "type": "w", "class": "rtcAlarm", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": (1,),
        "cmd_delay": 1,
    },
    {
        "cmd": 0xC2, "func": "SetWakeupEnabled", "type": "w", "class": "rtcAlarm", "ret": {"error": 'COMMUNICATION_ERROR'},
        "data_buffer_before": [0x01, 0xFF, 0], "data_buffer": [0x01, 0xFE, 0],
        "parm": (1,),
        "write_err": True,
    },
    {
        "cmd": 0xC2, "func": "SetWakeupEnabled", "type": "w", "class": "rtcAlarm", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": (1,),
        "read_err": True,
    },
    {
        "cmd": 0xC2, "func": "SetWakeupEnabled", "type": "w", "class": "rtcAlarm",
        "data_buffer_before": [0x05, 0x00, 0], "data_buffer": [0x05, 0x00, 0],
        "ret": {'error': 'NO_ERROR'},
        "parm": (1,),
        "recoverable_checksum": True,
    },
    {
        "cmd": 0xC2, "func": "SetWakeupEnabled", "type": "w", "class": "rtcAlarm",
        "data_buffer_before": [0x05, 0x00, 0], "data_buffer": [0x40, 0x00, 0],
        "ret": {'error': 'DATA_CORRUPTED'},
        "parm": (1,),
        "checksum_err": True,
    },

    {
        "cmd": 0xB0, "func": "GetTime", "type": "r", "class": "rtcAlarm", "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0xB0, "func": "GetTime", "type": "r", "class": "rtcAlarm", "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": True,
    },
    {
        "cmd": 0xB0, "func": "GetTime", "type": "r", "class": "rtcAlarm", "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 0, 0],
        "ret": {'error': 'DATA_CORRUPTED'},
        "checksum_err": True,
    },
    {
        "cmd": 0xB0, "func": "GetTime", "type": "r", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 0, 0],
        "ret": {'data': {'second': 53, 'minute': 19, 'hour': 19, 'weekday': 1, 'day': 18, 'month': 12, 'year': 2022,
                         'subsecond': 0, 'daylightsaving': 'NONE', 'storeoperation': False}, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0xB0, "func": "GetTime", "type": "r", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 0, 0],
        "ret": {'data': {'second': 53, 'minute': 19, 'hour': 19, 'weekday': 1, 'day': 18, 'month': 12, 'year': 2022,
                         'subsecond': 0, 'daylightsaving': 'NONE', 'storeoperation': False}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xB0, "func": "GetTime", "type": "r", "class": "rtcAlarm",
        "data_buffer": [83, 25, 9 | 0x40, 1, 24, 18, 34, 240, 0, 0],
        "ret": {'data': {'second': 53, 'minute': 19, 'hour': "9 AM", 'weekday': 1, 'day': 18, 'month': 12, 'year': 2022,
                         'subsecond': 0, 'daylightsaving': 'NONE', 'storeoperation': False}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xB0, "func": "GetTime", "type": "r", "class": "rtcAlarm",
        "data_buffer": [83, 25, 9 | 0x60, 1, 24, 18, 34, 240, 0, 0],
        "ret": {'data': {'second': 53, 'minute': 19, 'hour': "9 PM", 'weekday': 1, 'day': 18, 'month': 12, 'year': 2022,
                         'subsecond': 0, 'daylightsaving': 'NONE', 'storeoperation': False}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xB0, "func": "GetTime", "type": "r", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "ret": {'data': {'second': 53, 'minute': 19, 'hour': 19, 'weekday': 1, 'day': 18, 'month': 12, 'year': 2022,
                         'subsecond': 0, 'daylightsaving': 'SUB1H', 'storeoperation': False}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xB0, "func": "GetTime", "type": "r", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 1, 0],
        "ret": {'data': {'second': 53, 'minute': 19, 'hour': 19, 'weekday': 1, 'day': 18, 'month': 12, 'year': 2022,
                         'subsecond': 0, 'daylightsaving': 'ADD1H', 'storeoperation': False}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xB0, "func": "GetTime", "type": "r", "class": "rtcAlarm",   # 10
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 4, 0],
        "ret": {'data': {'second': 53, 'minute': 19, 'hour': 19, 'weekday': 1, 'day': 18, 'month': 12, 'year': 2022,
                         'subsecond': 0, 'daylightsaving': 'NONE', 'storeoperation': True}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": ({'second': 53},),
        "cmd_delay": 1,
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm", "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": ({'second': 53},),
        "write_err": True,
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm", "ret": {"error": 'WRITE_FAILED'},
        "parm": ({'second': 53, 'minute': 19, 'hour': 19, 'weekday': 1, 'day': 18, 'month': 12, 'year': 2022,
                'subsecond': 0, 'daylightsaving': 'NONE', 'storeoperation': False},),
        "corrupt": True,
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "ret": {"error": 'WRITE_FAILED'},
        "parm": ({'second': 53, 'minute': 19, 'hour': 19, 'weekday': 1, 'day': 18, 'month': 12, 'year': 2022,
                'subsecond': 0, 'daylightsaving': 'NONE', 'storeoperation': False},),
        "next_read_buffer": [83+3, 25, 25, 1, 24, 18, 34, 240, 0, 0],
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "ret": {"error": 'WRITE_FAILED'},
        "parm": ({'second': 53, 'minute': 19, 'hour': 19, 'weekday': 1, 'day': 18, 'month': 12, 'year': 2022,
                'subsecond': 0, 'daylightsaving': 'NONE', 'storeoperation': False},),
        "next_read_buffer": [83+1, 25+1, 25, 1, 24, 18, 34, 240, 0, 0],
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 0, 0, 0],
        "ret": {"error": 'NO_ERROR'},
        "parm": ({'second': 53, 'minute': 19, 'hour': 19, 'weekday': 1, 'day': 18, 'month': 12, 'year': 2022,
                'subsecond': 0, 'daylightsaving': 'NONE', 'storeoperation': False},),
        "next_read_buffer": [83+1, 25, 25, 1, 24, 18, 34, 240, 0, 0],
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'second': "s53"},),
        "ret": {"error": 'INVALID_SECOND'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'second': 61},),
        "ret": {"error": 'INVALID_SECOND'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'minute': "s53"},),
        "ret": {"error": 'INVALID_MINUTE'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'minute': 61},),
        "ret": {"error": 'INVALID_MINUTE'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'hour': "0 AM"},),
        "ret": {"error": 'INVALID_HOUR'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",   # 20
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'hour': "13 AM"},),
        "ret": {"error": 'INVALID_HOUR'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'hour': "0 PM"},),
        "ret": {"error": 'INVALID_HOUR'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'hour': "13 PM"},),
        "ret": {"error": 'INVALID_HOUR'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'hour': "25"},),
        "ret": {"error": 'INVALID_HOUR'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'hour': "h25"},),
        "ret": {"error": 'INVALID_HOUR'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'hour': 25},),
        "ret": {"error": 'INVALID_HOUR'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",   # 25
        "data_buffer": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "parm": ({},),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",   # 26
        "data_buffer": [0, 0, 65, 0, 0, 0, 0, 0, 0, 0],
        "parm": ({'hour': "1 AM"},),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0, 97, 0, 0, 0, 0, 0, 0, 0],
        "parm": ({'hour': "1 PM"},),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0, 0x23, 0, 0, 0, 0, 0, 0, 0],
        "parm": ({'hour': "23"},),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'weekday': 25},),
        "ret": {"error": 'INVALID_WEEKDAY'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",   # 30
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'weekday': "w25"},),
        "ret": {"error": 'INVALID_WEEKDAY'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'day': 33},),
        "ret": {"error": 'INVALID_DAY'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'day': "d25"},),
        "ret": {"error": 'INVALID_DAY'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'month': 33},),
        "ret": {"error": 'INVALID_MONTH'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'month': "d25"},),
        "ret": {"error": 'INVALID_MONTH'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'year': "y33"},),
        "ret": {"error": 'INVALID_YEAR'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'year': 100},),
        "ret": {"error": 'INVALID_YEAR'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'subsecond': "s33"},),
        "ret": {"error": 'INVALID_SUBSECOND'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [83, 25, 25, 1, 24, 18, 34, 240, 2, 0],
        "parm": ({'subsecond': 257},),
        "ret": {"error": 'INVALID_SUBSECOND'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",   # 40
        "data_buffer": [0, 0, 0, 0, 0, 0, 0, 0, 2, 0],
        "parm": ({'daylightsaving': "SUB1H"},),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
        "parm": ({'daylightsaving': "ADD1H"},),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0, 0, 0, 0, 0, 0, 0, 4, 0],
        "parm": ({'storeoperation': True},),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0xB0, "func": "SetTime", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0, 0, 0, 0, 0, 0, 0, 4, 0],
        "parm": ({'storeoperation': True},),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": True,
    },

    {
        "cmd": 0xB9, "func": "GetAlarm", "type": "r", "class": "rtcAlarm", "ret": {"error": 'COMMUNICATION_ERROR'}, # 44
        "cmd_delay": 1,
    },
    {
        "cmd": 0xB9, "func": "GetAlarm", "type": "r", "class": "rtcAlarm", "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": True,
    },
    {
        "cmd": 0xB9, "func": "GetAlarm", "type": "r", "class": "rtcAlarm", "data_buffer": [0, 0, 0, 0, 255, 255, 255, 0, 255, 0],
        "ret": {'error': 'DATA_CORRUPTED'},
        "checksum_err": True,
    },
    {
        "cmd": 0xB9, "func": "GetAlarm", "type": "r", "class": "rtcAlarm",
        "data_buffer": [128, 0, 0, 0, 255, 255, 255, 0, 255, 0],
        "ret": {'data': {'minute': 0, 'hour': 0, 'day': 0}, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0xB9, "func": "GetAlarm", "type": "r", "class": "rtcAlarm",
        "data_buffer": [0, 0 | 0x80, 0, 0, 255, 255, 255, 0, 255, 0],
        "ret": {'data': {'second': 0, 'minute_period': 0, 'hour': 0, 'day': 0}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xB9, "func": "GetAlarm", "type": "r", "class": "rtcAlarm",
        "data_buffer": [0, 0, 0 | 0x40, 0, 255, 255, 255, 0, 255, 0],
        "ret": {'data': {'second': 0, 'minute': 0, 'hour': '0 AM', 'day': 0}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xB9, "func": "GetAlarm", "type": "r", "class": "rtcAlarm",
        "data_buffer": [0, 0, 0 | 0x60, 0, 255, 255, 255, 0, 255, 0],
        "ret": {'data': {'second': 0, 'minute': 0, 'hour': '0 PM', 'day': 0}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xB9, "func": "GetAlarm", "type": "r", "class": "rtcAlarm",
        "data_buffer": [0, 0, 0 | 0x80, 0, 255, 255, 255, 0, 255, 0],
        "ret": {'data': {'second': 0, 'minute': 0, 'hour': 'EVERY_HOUR', 'day': 0}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xB9, "func": "GetAlarm", "type": "r", "class": "rtcAlarm",
        "data_buffer": [0, 0, 0 | 0x80 | 0x40, 0, 0x01, 0x10, 0, 0, 255, 0],   # 9
        "ret": {'data': {'second': 0, 'minute': 0, 'hour': '12AM;12PM', 'day': 0}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xB9, "func": "GetAlarm", "type": "r", "class": "rtcAlarm",
        "data_buffer": [0, 0, 0 | 0x80 | 0x40, 0, 0x02, 0x00, 0x01, 0, 255, 0],   # 10
        "ret": {'data': {'second': 0, 'minute': 0, 'hour': '2AM;5PM', 'day': 0}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xB9, "func": "GetAlarm", "type": "r", "class": "rtcAlarm",
        "data_buffer": [0, 0, 0 | 0x80, 0, 0x01, 0x80, 0, 0, 255, 0],   # 9
        "ret": {'data': {'second': 0, 'minute': 0, 'hour': '0;15', 'day': 0}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xB9, "func": "GetAlarm", "type": "r", "class": "rtcAlarm",
        "data_buffer": [0, 0, 0, 0x40, 255, 255, 255, 0, 255, 0],
        "ret": {'data': {'second': 0, 'minute': 0, 'hour': 0, 'weekday': 0}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xB9, "func": "GetAlarm", "type": "r", "class": "rtcAlarm",
        "data_buffer": [0, 0, 0, 0x40 | 0x03, 255, 255, 255, 0, 0, 0],
        "ret": {'data': {'second': 0, 'minute': 0, 'hour': 0, 'weekday': 3}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xB9, "func": "GetAlarm", "type": "r", "class": "rtcAlarm",
        "data_buffer": [0, 0, 0, 0x80 | 0x40 | 0x03, 255, 255, 255, 0, 0xff, 0],
        "ret": {'data': {'second': 0, 'minute': 0, 'hour': 0, 'weekday': 'EVERY_DAY'}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xB9, "func": "GetAlarm", "type": "r", "class": "rtcAlarm",
        "data_buffer": [0, 0, 0, 0x80 | 0x40 | 0x03, 255, 255, 255, 0, 0x18, 0],
        "ret": {'data': {'second': 0, 'minute': 0, 'hour': 0, 'weekday': '3;4'}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xB9, "func": "GetAlarm", "type": "r", "class": "rtcAlarm",
        "data_buffer": [0, 0, 0, 0x00 | 0x03, 255, 255, 255, 0, 0x18, 0],
        "ret": {'data': {'second': 0, 'minute': 0, 'hour': 0, 'day': 3}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xB9, "func": "GetAlarm", "type": "r", "class": "rtcAlarm",
        "data_buffer": [0, 0, 0, 0x80 | 0x03, 255, 255, 255, 0, 0x18, 0],
        "ret": {'data': {'second': 0, 'minute': 0, 'hour': 0, 'day': 'EVERY_DAY'}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",  # 18
        "data_buffer": [0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0x00, 0xFF, 0],
        "ret": {"error": 'NO_ERROR'},
        "parm": ({},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0x00, 0xFF, 0],
        "ret": {"error": 'INVALID_SECOND'},
        "parm": ({"second": "s61"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",  # 20
        "data_buffer": [0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0x00, 0xFF, 0],
        "ret": {"error": 'INVALID_SECOND'},
        "parm": ({"second": 61},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [89, 128, 128, 128, 0xFF, 0xFF, 0xFF, 0x00, 0xFF, 0],
        "ret": {"error": 'NO_ERROR'},
        "parm": ({"second": 59},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0x00, 0xFF, 0],
        "ret": {"error": 'INVALID_MINUTE'},
        "parm": ({"minute": "m61"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0x00, 0xFF, 0],
        "ret": {"error": 'INVALID_MINUTE'},
        "parm": ({"minute": 61},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",  # 24
        "data_buffer": [0, 89, 128, 128, 0xFF, 0xFF, 0xFF, 0x00, 0xFF, 0],
        "ret": {"error": 'NO_ERROR'},
        "parm": ({"minute": 59},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0x00, 0xFF, 0],
        "ret": {"error": 'INVALID_MINUTE_PERIOD'},
        "parm": ({"minute_period": "m61"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF, 0x00, 0xFF, 0],
        "ret": {"error": 'INVALID_MINUTE_PERIOD'},
        "parm": ({"minute_period": 61},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 128, 128, 0xFF, 0xFF, 0xFF, 59, 0xFF, 0],
        "ret": {"error": 'NO_ERROR'},
        "parm": ({"minute_period": 59},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 128, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'NO_ERROR'},
        "parm": ({"hour": "EVERY_HOUR"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 128, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'INVALID_HOUR'},
        "parm": ({"hour": "xAM;2PM"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",  # 30
        "data_buffer": [0, 0x80, 0x80, 128, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'INVALID_HOUR'},
        "parm": ({"hour": "1AM;xPM"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 128, 2, 64, 0, 0, 0xFF, 0],
        "ret": {"error": 'NO_ERROR'},
        "parm": ({"hour": "1AM;2PM"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 128, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'INVALID_HOUR'},
        "parm": ({"hour": "x13;14"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 128, 0, 96, 0, 0, 0xFF, 0],
        "ret": {"error": 'NO_ERROR'},
        "parm": ({"hour": "13;14"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 128, 0, 96, 0, 0, 0xFF, 0],
        "ret": {"error": 'INVALID_HOUR'},
        "parm": ({"hour": "13;x14"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 128, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'INVALID_HOUR'},
        "parm": ({"hour": "xAM"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 65, 128, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],    # 1AM
        "ret": {"error": 'NO_ERROR'},
        "parm": ({"hour": "1AM"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 128, 1, 16, 0, 0, 0xFF, 0],
        "ret": {"error": 'NO_ERROR'},
        "parm": ({"hour": "13AM;13PM"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 128, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'INVALID_HOUR'},
        "parm": ({"hour": "xPM"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 97, 128, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],    # 1PM
        "ret": {"error": 'NO_ERROR'},
        "parm": ({"hour": "1 PM"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",  # 40
        "data_buffer": [0, 0x80, 0x80, 128, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'INVALID_HOUR'},
        "parm": ({"hour": "x13"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 19, 128, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'NO_ERROR'},
        "parm": ({"hour": "13"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 19, 128, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'NO_ERROR'},
        "parm": ({"hour": 13},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 192, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'NO_ERROR'},
        "parm": ({"weekday": "EVERY_DAY"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 66, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'NO_ERROR'},
        "parm": ({"weekday": "2"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 66, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'INVALID_WEEKDAY'},
        "parm": ({"weekday": "x2"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 66, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'INVALID_WEEKDAY'},
        "parm": ({"weekday": "x2;3"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 66, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'INVALID_WEEKDAY'},
        "parm": ({"weekday": "2;x3"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 66, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'NO_ERROR'},
        "parm": ({"weekday": 2},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 192, 0xFF, 0xFF, 0xFF, 0, 12, 0],
        "ret": {"error": 'NO_ERROR'},
        "parm": ({"weekday": "2;3"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",  # 50
        "data_buffer": [0, 0x80, 0x80, 128, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'NO_ERROR'},
        "parm": ({"day": "EVERY_DAY"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 192, 0xFF, 0xFF, 0xFF, 0, 12, 0],
        "ret": {"error": 'INVALID_DAY_OF_MONTH'},
        "parm": ({"day": "d1"},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 1, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'NO_ERROR'},
        "parm": ({"day": 1},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 1, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": ({"day": 1},),
        "write_err": True,
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 1, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "parm": ({"day": 1},),
        "read_err": True,
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x80, 1, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "next_read_buffer": [1, 0x80, 0x80, 1, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "ret": {"error": 'WRITE_FAILED'},
        "parm": ({"day": 1},),
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",  # 56
        "data_buffer": [0, 0x80, 0x61, 128, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "next_read_buffer": [0, 0x80, 0x13, 128, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "parm": ({"hour": "1PM"},),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0xB9, "func": "SetAlarm", "type": "w", "class": "rtcAlarm",
        "data_buffer": [0, 0x80, 0x01, 128, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "next_read_buffer": [0, 0x80, 0x41, 128, 0xFF, 0xFF, 0xFF, 0, 0xFF, 0],
        "parm": ({"hour": 1},),
        "ret": {"error": 'NO_ERROR'},
    },

    {
        "cmd": 0x62, "func": "SetPowerOff", "type": "w", "class": "power",
        "data_buffer": [130, 0],
        "parm": (130,),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x62, "func": "SetPowerOff", "type": "w", "class": "power",
        "data_buffer": [130, 0],
        "parm": (130,),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0x62, "func": "SetPowerOff", "type": "w", "class": "power",
        "data_buffer": [130, 0],
        "parm": (130,),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x62, "func": "GetPowerOff", "type": "r", "class": "power",
        "data_buffer": [130, 0],
        "ret": {"data": [130], "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x62, "func": "GetPowerOff", "type": "r", "class": "power",
        "data_buffer": [130, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x62, "func": "GetPowerOff", "type": "r", "class": "power",
        "data_buffer": [130, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0x62, "func": "GetPowerOff", "type": "r", "class": "power",
        "data_buffer": [130, 0],
        "ret": {"data": [130], "error": 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x62, "func": "GetPowerOff", "type": "r", "class": "power",
        "data_buffer": [130, 0],
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x63, "func": "SetWakeUpOnCharge", "type": "w", "class": "power",
        "data_buffer": [152, 0],
        "parm": ("not_DISABLED",),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x63, "func": "SetWakeUpOnCharge", "type": "w", "class": "power",    # 10
        "data_buffer": [152, 0],
        "parm": (152,),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x63, "func": "SetWakeUpOnCharge", "type": "w", "class": "power",
        "data_buffer": [99, 0],
        "parm": (99,),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x63, "func": "SetWakeUpOnCharge", "type": "w", "class": "power",
        "data_buffer": [99 | 0x80, 0],
        "parm": (99, True),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x63, "func": "SetWakeUpOnCharge", "type": "w", "class": "power",
        "data_buffer": [127, 0],
        "parm": ("DISABLED",),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x63, "func": "SetWakeUpOnCharge", "type": "w", "class": "power",
        "data_buffer": [0xff, 0],
        "parm": ("DISABLED", True),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x63, "func": "SetWakeUpOnCharge", "type": "w", "class": "power",
        "data_buffer": [99, 0],
        "parm": (9, ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0x63, "func": "SetWakeUpOnCharge", "type": "w", "class": "power",
        "data_buffer": [1, 0],
        "parm": (1,),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x63, "func": "GetWakeUpOnCharge", "type": "r", "class": "power",
        "data_buffer": [0xff, 0],
        "ret": {"data": "DISABLED", "non_volatile": True, "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x63, "func": "GetWakeUpOnCharge", "type": "r", "class": "power",
        "data_buffer": [0x7f, 0],
        "ret": {"data": "DISABLED", "non_volatile": False, "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x63, "func": "GetWakeUpOnCharge", "type": "r", "class": "power",
        "data_buffer": [0xe4, 0],
        "ret": {"data": 100, "non_volatile": True, "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x63, "func": "GetWakeUpOnCharge", "type": "r", "class": "power",
        "data_buffer": [0x64, 0],
        "ret": {"data": 100, "non_volatile": False, "error": 'NO_ERROR'},
    },
    {
        "cmd": 0x63, "func": "GetWakeUpOnCharge", "type": "r", "class": "power",
        "data_buffer": [0xff, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x63, "func": "GetWakeUpOnCharge", "type": "r", "class": "power",    # 20
        "data_buffer": [0xff, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0x63, "func": "GetWakeUpOnCharge", "type": "r", "class": "power",
        "data_buffer": [0xe4, 0],
        "ret": {"data": 100, "non_volatile": True, "error": 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x63, "func": "GetWakeUpOnCharge", "type": "r", "class": "power",
        "data_buffer": [0xff, 0],
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x61, "func": "SetWatchdog", "type": "w", "class": "power",
        "data_buffer": [0, 0, 0],
        "parm": ("minutes",),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x61, "func": "SetWatchdog", "type": "w", "class": "power",
        "data_buffer": [4, 80, 0],
        "parm": (0x4000+17,),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x61, "func": "SetWatchdog", "type": "w", "class": "power",
        "data_buffer": [255, 63, 0],
        "parm": (0x3fff,),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x61, "func": "SetWatchdog", "type": "w", "class": "power",
        "data_buffer": [255, 63 | 0x80, 0],
        "parm": (0x3fff, True),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x61, "func": "SetWatchdog", "type": "w", "class": "power",
        "data_buffer": [0, 0, 0],
        "parm": (9, ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0x61, "func": "SetWatchdog", "type": "w", "class": "power",
        "data_buffer": [0, 0, 0],
        "parm": (1,),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x61, "func": "GetWatchdog", "type": "r", "class": "power",
        "data_buffer": [0xff, 0xcf, 0],
        "ret": {'data': 16380, 'non_volatile': True, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x61, "func": "GetWatchdog", "type": "r", "class": "power",
        "data_buffer": [0xff, 0x3f, 0],
        "ret": {'data': 16383, 'non_volatile': False, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x61, "func": "GetWatchdog", "type": "r", "class": "power",  # 30
        "data_buffer": [0, 0, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x61, "func": "GetWatchdog", "type": "r", "class": "power",
        "data_buffer": [0, 0, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0x61, "func": "GetWatchdog", "type": "r", "class": "power",    # 30
        "data_buffer": [0xff, 0x3f, 0],
        "ret": {'data': 16383, 'non_volatile': False, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x61, "func": "GetWatchdog", "type": "r", "class": "power",
        "data_buffer": [0, 0, 0],
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x64, "func": "SetSystemPowerSwitch", "type": "w", "class": "power",
        "data_buffer": [0, 0],
        "parm": ("ps",),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x64, "func": "SetSystemPowerSwitch", "type": "w", "class": "power", # 35
        "data_buffer": [2, 0],
        "parm": (200,),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x64, "func": "SetSystemPowerSwitch", "type": "w", "class": "power",
        "data_buffer": [0, 0],
        "parm": (9, ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0x64, "func": "SetSystemPowerSwitch", "type": "w", "class": "power",
        "data_buffer": [0, 0],
        "parm": (1,),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x64, "func": "GetSystemPowerSwitch", "type": "r", "class": "power",
        "data_buffer": [0x80, 0],
        "ret": {'data': 12800, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x64, "func": "GetSystemPowerSwitch", "type": "r", "class": "power",
        "data_buffer": [0, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x64, "func": "GetSystemPowerSwitch", "type": "r", "class": "power",
        "data_buffer": [0, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0x64, "func": "GetSystemPowerSwitch", "type": "r", "class": "power",    # 30
        "data_buffer": [0x81, 0],
        "ret": {'data': 12900, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x64, "func": "GetSystemPowerSwitch", "type": "r", "class": "power",
        "data_buffer": [0, 0],
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x51, "func": "SetChargingConfig", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": ("pcc", ),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x51, "func": "SetChargingConfig", "type": "w", "class": "config",
        "data_buffer": [1, 0],
        "parm": ({"charging_enabled": "nTrue"},),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x51, "func": "SetChargingConfig", "type": "w", "class": "config",
        "data_buffer": [129, 0],
        "parm": (True, True),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x51, "func": "SetChargingConfig", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": (False,),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x51, "func": "SetChargingConfig", "type": "w", "class": "config",
        "data_buffer": [128, 0],
        "parm": (False, True),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x51, "func": "SetChargingConfig", "type": "w", "class": "config",
        "data_buffer": [1, 0],
        "parm": ({"charging_enabled": True},),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x51, "func": "SetChargingConfig", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": ({"charging_enabled": False},),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x51, "func": "SetChargingConfig", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": (True, ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0x51, "func": "SetChargingConfig", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": (True, ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": True,
    },
    {
        "cmd": 0x51, "func": "SetChargingConfig", "type": "w", "class": "config",
        "data_buffer": [1, 0],
        "parm": (True, ),
        'next_read_buffer': [0xff, 0],
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x51, "func": "SetChargingConfig", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": (True,),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x51, "func": "GetChargingConfig", "type": "r", "class": "config",
        "data_buffer": [0x80, 0],
        "ret": {'data': {'charging_enabled': False}, 'non_volatile': True, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x51, "func": "GetChargingConfig", "type": "r", "class": "config",
        "data_buffer": [0x81, 0],
        "ret": {'data': {'charging_enabled': True}, 'non_volatile': True, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x51, "func": "GetChargingConfig", "type": "r", "class": "config",
        "data_buffer": [0x00, 0],
        "ret": {'data': {'charging_enabled': False}, 'non_volatile': False, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x51, "func": "GetChargingConfig", "type": "r", "class": "config",
        "data_buffer": [0x01, 0],
        "ret": {'data': {'charging_enabled': True}, 'non_volatile': False, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x51, "func": "GetChargingConfig", "type": "r", "class": "config",
        "data_buffer": [0, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x51, "func": "GetChargingConfig", "type": "r", "class": "config",
        "data_buffer": [0, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0x51, "func": "GetChargingConfig", "type": "r", "class": "config",    # 30
        "data_buffer": [0x81, 0],
        "ret": {'data': {'charging_enabled': True}, 'non_volatile': True, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x51, "func": "GetChargingConfig", "type": "r", "class": "config",
        "data_buffer": [0, 0],
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x52, "func": "SelectBatteryProfiles", "type": "r", "class": "config",
        "data_buffer": [0, 0],
        "parm": (0x15,),
        "ret": None,
    },
    {
        "cmd": 0x52, "func": "SelectBatteryProfiles", "type": "r", "class": "config",
        "data_buffer": [0, 0],
        "parm": (0x14,),
        "ret": None,
    },
    {
        "cmd": 0x52, "func": "SelectBatteryProfiles", "type": "r", "class": "config",
        "data_buffer": [0, 0],
        "parm": (0x13,),
        "ret": None,
    },
    {
        "cmd": 0x52, "func": "SelectBatteryProfiles", "type": "r", "class": "config",
        "data_buffer": [0, 0],
        "parm": (0x12,),
        "ret": None,
    },
    {
        "cmd": 0x52, "func": "SelectBatteryProfiles", "type": "r", "class": "config",
        "data_buffer": [0, 0],
        "parm": (0x16,),
        "ret": None,
    },

    {
        "cmd": 0x52, "func": "SetBatteryProfile", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": ("bad profile", ),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x52, "func": "SetBatteryProfile", "type": "w", "class": "config",
        "data_buffer": [0xff, 0],
        "parm": ("DEFAULT", ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x52, "func": "SetBatteryProfile", "type": "w", "class": "config",
        "data_buffer": [0x0f, 0],
        "parm": ("CUSTOM", ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x52, "func": "SetBatteryProfile", "type": "w", "class": "config",
        "data_buffer": [0x01, 0],
        "parm": ("BP7X_1820", ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x52, "func": "SetBatteryProfile", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": ("DEFAULT", ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0x52, "func": "SetBatteryProfile", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": ("DEFAULT", ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },

    {
        "cmd": 0x52, "func": "GetBatteryProfileStatus", "type": "r", "class": "config",
        "data_buffer": [0xf0, 0],
        "ret": {"data": {"validity": "DATA_WRITE_NOT_COMPLETED"}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x52, "func": "GetBatteryProfileStatus", "type": "r", "class": "config",
        "data_buffer": [0x0f, 0],
        "ret": {'data': {"validity": "VALID", "source": "HOST", "origin": "CUSTOM", "profile": "UNKNOWN"}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x52, "func": "GetBatteryProfileStatus", "type": "r", "class": "config",
        "data_buffer": [0x1f, 0],
        "ret": {'data': {"validity": "VALID", "source": "DIP_SWITCH", "origin": "CUSTOM", "profile": "UNKNOWN"}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x52, "func": "GetBatteryProfileStatus", "type": "r", "class": "config",
        "data_buffer": [0x5f, 0],
        "ret": {'data': {"validity": "INVALID", "source": "DIP_SWITCH", "origin": "CUSTOM", "profile": "UNKNOWN"}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x52, "func": "GetBatteryProfileStatus", "type": "r", "class": "config",
        "data_buffer": [0x6f, 0],
        "ret": {'data': {"validity": "INVALID", "source": "RESISTOR", "origin": "CUSTOM", "profile": "UNKNOWN"}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x52, "func": "GetBatteryProfileStatus", "type": "r", "class": "config",
        "data_buffer": [0x01, 0],
        "ret": {'data': {"validity": "VALID", "source": "HOST", "origin": "PREDEFINED", "profile": "BP7X_1820"}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x52, "func": "GetBatteryProfileStatus", "type": "r", "class": "config",
        "data_buffer": [0, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x52, "func": "GetBatteryProfileStatus", "type": "r", "class": "config",
        "data_buffer": [0, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0x52, "func": "GetBatteryProfileStatus", "type": "r", "class": "config",
        "data_buffer": [0xcf, 0],
        "ret": {'data': {'validity': 'INVALID', 'source': 'HOST', 'origin': 'CUSTOM', 'profile': 'UNKNOWN'}, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x52, "func": "GetBatteryProfileStatus", "type": "r", "class": "config",
        "data_buffer": [0, 0],
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x53, "func": "GetBatteryProfile", "type": "r", "class": "config",
        "data_buffer": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "ret": {"data": "INVALID", "error": "NO_ERROR"},
    },
    {
        "cmd": 0x53, "func": "GetBatteryProfile", "type": "r", "class": "config",
        "data_buffer": [28, 7, 5, 0, 34, 150, 1, 10, 45, 59, 52, 13, 232, 3, 0],
        "ret": {"data": {"capacity": 1820, "chargeCurrent": 925, "terminationCurrent": 50, "regulationVoltage": 4180,
            "cutoffVoltage": 3000, "tempCold": 1, "tempCool": 10, "tempWarm": 45,
            "tempHot": 59, "ntcB": 3380, "ntcResistance": 10000}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x53, "func": "GetBatteryProfile", "type": "r", "class": "config",
        "data_buffer": [0xff, 0xff, 5, 0, 34, 150, 1, 10, 45, 59, 52, 13, 232, 3, 0],
        "ret": {"data": {"capacity": 4294967295, "chargeCurrent": 925, "terminationCurrent": 50, "regulationVoltage": 4180,
            "cutoffVoltage": 3000, "tempCold": 1, "tempCool": 10, "tempWarm": 45,
            "tempHot": 59, "ntcB": 3380, "ntcResistance": 10000}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x53, "func": "GetBatteryProfile", "type": "r", "class": "config",
        "data_buffer": [28, 7, 5, 0, 34, 150, 1, 10, 45, 59, 52, 13, 232, 3, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x53, "func": "GetBatteryProfile", "type": "r", "class": "config",
        "data_buffer": [28, 7, 5, 0, 34, 150, 1, 10, 45, 59, 52, 13, 232, 3, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0x53, "func": "GetBatteryProfile", "type": "r", "class": "config",
        "data_buffer": [0xff, 0xff, 5, 0, 34, 150, 1, 10, 45, 59, 52, 13, 232, 3, 0],
        "ret": {"data": {"capacity": 4294967295, "chargeCurrent": 925, "terminationCurrent": 50, "regulationVoltage": 4180,
            "cutoffVoltage": 3000, "tempCold": 1, "tempCool": 10, "tempWarm": 45,
            "tempHot": 59, "ntcB": 3380, "ntcResistance": 10000}, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x53, "func": "GetBatteryProfile", "type": "r", "class": "config",
        "data_buffer": [0, 0],
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x53, "func": "SetCustomBatteryProfile", "type": "w", "class": "config",
        "data_buffer": [28, 7, 5, 0, 34, 150, 1, 10, 45, 59, 52, 13, 232, 3, 0],
        "parm": ({"nocapacity": 4294967295, "chargeCurrent": 925, "terminationCurrent": 50, "regulationVoltage": 4180,
            "cutoffVoltage": 3000, "tempCold": 1, "tempCool": 10, "tempWarm": 45,
            "tempHot": 59, "ntcB": 3380, "ntcResistance": 10000}, ),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x53, "func": "SetCustomBatteryProfile", "type": "w", "class": "config",
        "data_buffer": [28, 7, 5, 0, 34, 150, 1, 10, 45, 59, 52, 13, 232, 3, 0],
        "parm": ({"capacity": 1820, "chargeCurrent": 925, "terminationCurrent": 50, "regulationVoltage": 4180,
            "cutoffVoltage": 3000, "tempCold": 1, "tempCool": 10, "tempWarm": 45,
            "tempHot": 59, "ntcB": 3380, "ntcResistance": 10000}, ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x53, "func": "SetCustomBatteryProfile", "type": "w", "class": "config",
        "data_buffer": [0xff, 0xff, 5, 0, 34, 150, 1, 10, 45, 59, 52, 13, 232, 3, 0],
        "parm": ({"capacity": 4294967295, "chargeCurrent": 925, "terminationCurrent": 50, "regulationVoltage": 4180,
            "cutoffVoltage": 3000, "tempCold": 1, "tempCool": 10, "tempWarm": 45,
            "tempHot": 59, "ntcB": 3380, "ntcResistance": 10000}, ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x53, "func": "SetCustomBatteryProfile", "type": "w", "class": "config",
        "data_buffer": [28, 7, 5, 0, 34, 150, 1, 10, 45, 59, 52, 13, 232, 3, 0],
        "parm": ({"capacity": 1820, "chargeCurrent": 925, "terminationCurrent": 50, "regulationVoltage": 4180,
            "cutoffVoltage": 3000, "tempCold": 1, "tempCool": 10, "tempWarm": 45,
            "tempHot": 59, "ntcB": 3380, "ntcResistance": 10000}, ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0x53, "func": "SetCustomBatteryProfile", "type": "w", "class": "config",
        "data_buffer": [28, 7, 5, 0, 34, 150, 1, 10, 45, 59, 52, 13, 232, 3, 0],
        "parm": ({"capacity": 1820, "chargeCurrent": 925, "terminationCurrent": 50, "regulationVoltage": 4180,
            "cutoffVoltage": 3000, "tempCold": 1, "tempCool": 10, "tempWarm": 45,
            "tempHot": 59, "ntcB": 3380, "ntcResistance": 10000}, ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },

    {
        "cmd": 0x54, "func": "GetBatteryExtProfile", "type": "r", "class": "config",
        "data_buffer": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "ret": {"data": "INVALID", "error": "NO_ERROR"},
    },
    {
        "cmd": 0x54, "func": "GetBatteryExtProfile", "type": "r", "class": "config",
        "data_buffer": [0, 65, 14, 216, 14, 237, 15, 164, 81, 20, 80, 232, 78, 255, 255, 255, 255, 0],
        "ret": {"data": {'chemistry': 'LIPO', 'ocv10': 3649, 'ocv50': 3800, 'ocv90': 4077, 'r10': 209.0,
                         'r50': 205.0, 'r90': 202.0}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x54, "func": "GetBatteryExtProfile", "type": "r", "class": "config",
        "data_buffer": [0, 65, 14, 216, 14, 237, 15, 164, 81, 20, 80, 232, 78, 255, 255, 255, 255, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },
    {
        "cmd": 0x54, "func": "GetBatteryExtProfile", "type": "r", "class": "config",
        "data_buffer": [0, 65, 14, 216, 14, 237, 15, 164, 81, 20, 80, 232, 78, 255, 255, 255, 255, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0x54, "func": "GetBatteryExtProfile", "type": "r", "class": "config",
        "data_buffer": [0x80, 65, 14, 216, 14, 237, 15, 164, 81, 20, 80, 232, 78, 255, 255, 255, 255, 0],
        "ret": {"data": {'chemistry': 'UNKNOWN', 'ocv10': 3649, 'ocv50': 3800, 'ocv90': 4077, 'r10': 209.0,
                         'r50': 205.0, 'r90': 202.0}, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x54, "func": "GetBatteryExtProfile", "type": "r", "class": "config",
        "data_buffer": [0, 65, 14, 216, 14, 237, 15, 164, 81, 20, 80, 232, 78, 255, 255, 255, 255, 0],
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x54, "func": "SetCustomBatteryExtProfile", "type": "w", "class": "config",
        "data_buffer": [0, 65, 14, 216, 14, 237, 15, 164, 81, 20, 80, 232, 78, 255, 255, 255, 255, 0],
        "parm": ({'no chemistry': 'LIPO', 'ocv10': 3649, 'ocv50': 3800, 'ocv90': 4077, 'r10': 209.0,
                         'r50': 205.0, 'r90': 202.0}, ),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x54, "func": "SetCustomBatteryExtProfile", "type": "w", "class": "config",
        "data_buffer": [0, 65, 14, 216, 14, 237, 15, 164, 81, 20, 80, 232, 78, 255, 255, 255, 255, 0],
        "parm": ({'chemistry': 'LIPO', 'ocv10': "n3649", 'ocv50': 3800, 'ocv90': 4077, 'r10': 209.0,
                         'r50': 205.0, 'r90': 202.0}, ),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x54, "func": "SetCustomBatteryExtProfile", "type": "w", "class": "config",
        "data_buffer": [0, 65, 14, 216, 14, 237, 15, 164, 81, 20, 80, 232, 78, 255, 255, 255, 255, 0],
        "parm": ({'chemistry': 'Mg', 'ocv10': "n3649", 'ocv50': 3800, 'ocv90': 4077, 'r10': 209.0,
                         'r50': 205.0, 'r90': 202.0}, ),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x54, "func": "SetCustomBatteryExtProfile", "type": "w", "class": "config",
        "data_buffer": [0, 65, 14, 216, 14, 237, 15, 164, 81, 20, 80, 232, 78, 255, 255, 255, 255, 0],
        "parm": ({'chemistry': 'LIPO', 'ocv10': 3649, 'ocv50': 3800, 'ocv90': 4077, 'r10': 209.0,
                         'r50': 205.0, 'r90': 202.0}, ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x54, "func": "SetCustomBatteryExtProfile", "type": "w", "class": "config",
        "data_buffer": [0, 65, 14, 216, 14, 237, 15, 164, 81, 20, 80, 232, 78, 255, 255, 255, 255, 0],
        "parm": ({'chemistry': 'LIPO', 'ocv10': 3649, 'ocv50': 3800, 'ocv90': 4077, 'r10': 209.0,
                         'r50': 205.0, 'r90': 202.0}, ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0x54, "func": "SetCustomBatteryExtProfile", "type": "w", "class": "config",
        "data_buffer": [0, 65, 14, 216, 14, 237, 15, 164, 81, 20, 80, 232, 78, 255, 255, 255, 255, 0],
        "parm": ({'chemistry': 'LIPO', 'ocv10': 3649, 'ocv50': 3800, 'ocv90': 4077, 'r10': 209.0,
                         'r50': 205.0, 'r90': 202.0}, ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },

    {
        "cmd": 0x5D, "func": "GetBatteryTempSenseConfig", "type": "r", "class": "config",
        "data_buffer": [0x7f, 0],
        "ret": {"error": "UNKNOWN_DATA"},
    },
    {
        "cmd": 0x5D, "func": "GetBatteryTempSenseConfig", "type": "r", "class": "config",
        "data_buffer": [2, 0],
        "ret": {"data": "ON_BOARD", 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x5D, "func": "GetBatteryTempSenseConfig", "type": "r", "class": "config",
        "data_buffer": [2, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0x5D, "func": "GetBatteryTempSenseConfig", "type": "r", "class": "config",
        "data_buffer": [0x82, 0],
       "ret": {"data": "ON_BOARD", 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x5D, "func": "GetBatteryTempSenseConfig", "type": "r", "class": "config",
        "data_buffer": [2, 0],
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x5D, "func": "SetBatteryTempSenseConfig", "type": "w", "class": "config",
        'data_buffer_before': [0xf0, 0], "data_buffer": [0xf3, 0],
        "parm": ("AUTO_DETECT", ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x5D, "func": "SetBatteryTempSenseConfig", "type": "w", "class": "config",
        'data_buffer_before': [0xf0, 0], "data_buffer": [0xf3, 0],
        "parm": ("no AUTO_DETECT", ),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x5D, "func": "SetBatteryTempSenseConfig", "type": "w", "class": "config",
        'data_buffer_before': [0xf0, 0], "data_buffer": [0xf3, 0],
        "parm": ("AUTO_DETECT", ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0x5D, "func": "SetBatteryTempSenseConfig", "type": "w", "class": "config",
        'data_buffer_before': [0xf0, 0], "data_buffer": [0xf3, 0],
        "parm": ("AUTO_DETECT", ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },

    {
        "cmd": 0x5D, "func": "GetRsocEstimationConfig", "type": "r", "class": "config",
        "data_buffer": [0xf0, 0],
        "ret": {"error": "UNKNOWN_DATA"},
    },
    {
        "cmd": 0x5D, "func": "GetRsocEstimationConfig", "type": "r", "class": "config",
        "data_buffer": [0xdf, 0],
        "ret": {"data": "DIRECT_BY_MCU", 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x5D, "func": "GetRsocEstimationConfig", "type": "r", "class": "config",
        "data_buffer": [0x1f, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0x5D, "func": "GetRsocEstimationConfig", "type": "r", "class": "config",
        "data_buffer": [0xdf, 0],
       "ret": {"data": "DIRECT_BY_MCU", 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x5D, "func": "GetRsocEstimationConfig", "type": "r", "class": "config",
        "data_buffer": [0x1f, 0],
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x5D, "func": "SetRsocEstimationConfig", "type": "w", "class": "config",
        'data_buffer_before': [0xff, 0], "data_buffer": [0xcf, 0],
        "parm": ("AUTO_DETECT", ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x5D, "func": "SetRsocEstimationConfig", "type": "w", "class": "config",
        'data_buffer_before': [0xff, 0], "data_buffer": [0xcf, 0],
        "parm": ("no AUTO_DETECT", ),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x5D, "func": "SetRsocEstimationConfig", "type": "w", "class": "config",
        'data_buffer_before': [0xff, 0], "data_buffer": [0xcf, 0],
        "parm": ("AUTO_DETECT", ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0x5D, "func": "SetRsocEstimationConfig", "type": "w", "class": "config",
        'data_buffer_before': [0xff, 0], "data_buffer": [0xcf, 0],
        "parm": ("AUTO_DETECT", ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },

    {
        "cmd": 0x5E, "func": "SetPowerInputsConfig", "type": "w", "class": "config",
        'data_buffer_before': [0, 0], "data_buffer": [11, 0],
        "parm": ({'precedence': '5V_GPIO', 'gpio_in_enabled': True, 'no_battery_turn_on': False,
                         'usb_micro_current_limit': '2.5A', 'usb_micro_dpm': '4.20V'}, ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x5E, "func": "SetPowerInputsConfig", "type": "w", "class": "config",
        'data_buffer_before': [0, 0], "data_buffer": [0x8b, 0],
        "parm": ({'precedence': '5V_GPIO', 'gpio_in_enabled': True, 'no_battery_turn_on': False,
                         'usb_micro_current_limit': '2.5A', 'usb_micro_dpm': '4.20V'}, True),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x5E, "func": "SetPowerInputsConfig", "type": "w", "class": "config",
        'data_buffer_before': [0, 0], "data_buffer": [11, 0],
        "parm": ({'precedence': '5V_GPIO', 'gpio_in_enabled': True, 'no_battery_turn_on': False,
                         'usb_micro_current_limit': '2.5A', 'usb_micro_dpm': '14.20V'}, ),
        "ret": {"error": 'INVALID_USB_MICRO_DPM'},
    },
    {
        "cmd": 0x5E, "func": "SetPowerInputsConfig", "type": "w", "class": "config",
        'data_buffer_before': [0, 0], "data_buffer": [11, 0],
        "parm": ({'precedence': '5V_GPIO', 'gpio_in_enabled': True, 'no_battery_turn_on': False,
                         'usb_micro_current_limit': '3.5A', 'usb_micro_dpm': '4.20V'}, ),
        "ret": {"error": 'INVALID_USB_MICRO_CURRENT_LIMIT'},
    },
    {
        "cmd": 0x5E, "func": "SetPowerInputsConfig", "type": "w", "class": "config",
        'data_buffer_before': [0xff, 0], "data_buffer": [11, 0],
        "parm": ("no AUTO_DETECT", ),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x5E, "func": "SetPowerInputsConfig", "type": "w", "class": "config",
        'data_buffer_before': [0xff, 0], "data_buffer": [11, 0],
        "parm": ({'precedence': '5V_GPIO', 'gpio_in_enabled': True, 'no_battery_turn_on': False,
                         'usb_micro_current_limit': '2.5A', 'usb_micro_dpm': '4.20V'}, ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0x5E, "func": "SetPowerInputsConfig", "type": "w", "class": "config",
        'data_buffer_before': [0xff, 0], "data_buffer": [11, 0],
        "parm": ({'precedence': '5V_GPIO', 'gpio_in_enabled': True, 'no_battery_turn_on': False,
                         'usb_micro_current_limit': '2.5A', 'usb_micro_dpm': '4.20V'}, ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },

    {
        "cmd": 0x5E, "func": "GetPowerInputsConfig", "type": "r", "class": "config",
        "data_buffer": [11, 0],
        "ret": {"data": {'precedence': '5V_GPIO', 'gpio_in_enabled': True, 'no_battery_turn_on': False,
                         'usb_micro_current_limit': '2.5A', 'usb_micro_dpm': '4.20V'}, 'non_volatile': False, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x5E, "func": "GetPowerInputsConfig", "type": "r", "class": "config",
        "data_buffer": [11, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0x5E, "func": "GetPowerInputsConfig", "type": "r", "class": "config",
        "data_buffer": [0x8b, 0],
        "ret": {"data": {'precedence': '5V_GPIO', 'gpio_in_enabled': True, 'no_battery_turn_on': False,
                         'usb_micro_current_limit': '2.5A', 'usb_micro_dpm': '4.20V'}, 'non_volatile': True, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x5E, "func": "GetPowerInputsConfig", "type": "r", "class": "config",
        "data_buffer": [11, 0],
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x6E, "func": "GetButtonConfiguration", "type": "r", "class": "config",
        "data_buffer": [0, 0, 0, 0, 1, 8, 0, 0, 17, 100, 2, 200, 0],
        "parm": ("SW1", ),
        "ret": {"data": {'PRESS': {'function': 'NO_FUNC', 'parameter': 0},
                         'RELEASE': {'function': 'NO_FUNC', 'parameter': 0},
                         'SINGLE_PRESS': {'function': 'HARD_FUNC_POWER_ON', 'parameter': 800},
                         'DOUBLE_PRESS': {'function': 'NO_FUNC', 'parameter': 0},
                         'LONG_PRESS1': {'function': 'SYS_FUNC_HALT', 'parameter': 10000},
                         'LONG_PRESS2': {'function': 'HARD_FUNC_POWER_OFF', 'parameter': 20000}}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x6F, "func": "GetButtonConfiguration", "type": "r", "class": "config",
        "data_buffer": [0, 0, 0, 0, 1, 8, 0, 0, 17, 100, 2, 200, 0],
        "parm": ("SW2", ),
        "ret": {"data": {'PRESS': {'function': 'NO_FUNC', 'parameter': 0},
                         'RELEASE': {'function': 'NO_FUNC', 'parameter': 0},
                         'SINGLE_PRESS': {'function': 'HARD_FUNC_POWER_ON', 'parameter': 800},
                         'DOUBLE_PRESS': {'function': 'NO_FUNC', 'parameter': 0},
                         'LONG_PRESS1': {'function': 'SYS_FUNC_HALT', 'parameter': 10000},
                         'LONG_PRESS2': {'function': 'HARD_FUNC_POWER_OFF', 'parameter': 20000}}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x70, "func": "GetButtonConfiguration", "type": "r", "class": "config",
        "data_buffer": [0, 0, 0, 0, 1, 8, 0, 0, 17, 100, 2, 200, 0],
        "parm": ("SW3", ),
        "ret": {"data": {'PRESS': {'function': 'NO_FUNC', 'parameter': 0},
                         'RELEASE': {'function': 'NO_FUNC', 'parameter': 0},
                         'SINGLE_PRESS': {'function': 'HARD_FUNC_POWER_ON', 'parameter': 800},
                         'DOUBLE_PRESS': {'function': 'NO_FUNC', 'parameter': 0},
                         'LONG_PRESS1': {'function': 'SYS_FUNC_HALT', 'parameter': 10000},
                         'LONG_PRESS2': {'function': 'HARD_FUNC_POWER_OFF', 'parameter': 20000}}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x6E, "func": "GetButtonConfiguration", "type": "r", "class": "config",
        "data_buffer": [0, 0, 0, 0, 1, 8, 0, 0, 17, 100, 2, 200, 0],
        "parm": ("SW", ),
        "ret": {'error': 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x6E, "func": "GetButtonConfiguration", "type": "r", "class": "config",
        "data_buffer": [0, 0, 0, 0, 1, 8, 0, 0, 17, 100, 2, 200, 0],
        "parm": ("SW1", ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0x6E, "func": "GetButtonConfiguration", "type": "r", "class": "config",
        "data_buffer": [200, 0, 0, 0, 0x0f, 8, 0x2f, 1, 17, 100, 2, 0, 0],
        "parm": ("SW1", ),
        "ret": {"data": {'PRESS': {'function': 'UNKNOWN', 'parameter': 0},
                         'RELEASE': {'function': 'NO_FUNC', 'parameter': 0},
                         'SINGLE_PRESS': {'function': 'UNKNOWN', 'parameter': 800},
                         'DOUBLE_PRESS': {'function': 'USER_FUNC15', 'parameter': 100},
                         'LONG_PRESS1': {'function': 'SYS_FUNC_HALT', 'parameter': 10000},
                         'LONG_PRESS2': {'function': 'HARD_FUNC_POWER_OFF', 'parameter': 0}}, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x6E, "func": "GetButtonConfiguration", "type": "r", "class": "config",
        "data_buffer": [0, 0, 0, 0, 1, 8, 0, 0, 17, 100, 2, 200, 0],
        "parm": ("SW1", ),
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x6E, "func": "SetButtonConfiguration", "type": "w", "class": "config",
        "data_buffer": [33, 0, 0, 0, 20, 8, 47, 1, 17, 100, 2, 0, 0],
        "parm": ("SW1",{'PRESS': {'function': 'USER_FUNC1', 'parameter': 0},
                         'RELEASE': {'function': 'NO_FUNC', 'parameter': 0},
                         'SINGLE_PRESS': {'function': 'SYS_FUNC_REBOOT', 'parameter': 800},
                         'DOUBLE_PRESS': {'function': 'USER_FUNC15', 'parameter': 100},
                         'LONG_PRESS1': {'function': 'SYS_FUNC_HALT', 'parameter': 10000},
                         'LONG_PRESS2': {'function': 'HARD_FUNC_POWER_OFF', 'parameter': 0}} ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x6F, "func": "SetButtonConfiguration", "type": "w", "class": "config",
        "data_buffer": [33, 0, 0, 0, 20, 8, 47, 1, 17, 100, 2, 0, 0],
        "parm": ("SW2",{'PRESS': {'function': 'USER_FUNC1', 'parameter': 0},
                         'RELEASE': {'function': 'NO_FUNC', 'parameter': 0},
                         'SINGLE_PRESS': {'function': 'SYS_FUNC_REBOOT', 'parameter': 800},
                         'DOUBLE_PRESS': {'function': 'USER_FUNC15', 'parameter': 100},
                         'LONG_PRESS1': {'function': 'SYS_FUNC_HALT', 'parameter': 10000},
                         'LONG_PRESS2': {'function': 'HARD_FUNC_POWER_OFF', 'parameter': 0}} ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x70, "func": "SetButtonConfiguration", "type": "w", "class": "config",
        "data_buffer": [33, 0, 0, 0, 20, 8, 47, 1, 17, 100, 2, 0, 0],
        "parm": ("SW3",{'PRESS': {'function': 'USER_FUNC1', 'parameter': 0},
                         'RELEASE': {'function': 'NO_FUNC', 'parameter': 0},
                         'SINGLE_PRESS': {'function': 'SYS_FUNC_REBOOT', 'parameter': 800},
                         'DOUBLE_PRESS': {'function': 'USER_FUNC15', 'parameter': 100},
                         'LONG_PRESS1': {'function': 'SYS_FUNC_HALT', 'parameter': 10000},
                         'LONG_PRESS2': {'function': 'HARD_FUNC_POWER_OFF', 'parameter': 0}} ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x6E, "func": "SetButtonConfiguration", "type": "w", "class": "config",
        "data_buffer": [33, 0, 0, 0, 20, 8, 47, 1, 17, 100, 2, 0, 0],
        "parm": ("SW",{'PRESS': {'function': 'USER_FUNC1', 'parameter': 0},
                         'SINGLE_PRESS': {'function': 'SYS_FUNC_REBOOT', 'parameter': 800},
                         'DOUBLE_PRESS': {'function': 'USER_FUNC15', 'parameter': 100},
                         'LONG_PRESS1': {'function': 'SYS_FUNC_HALT', 'parameter': 10000},
                         'LONG_PRESS2': {'function': 'HARD_FUNC_POWER_OFF', 'parameter': 0}} ),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x6E, "func": "SetButtonConfiguration", "type": "w", "class": "config",
        "data_buffer": [33, 0, 0, 0, 20, 8, 47, 1, 17, 100, 2, 0, 0],
        "parm": ("SW1",{'PRESS': {'function': 'USER_FUNC1', 'parameter': 0},
                         'RELEASE': {'function': 'NO_FUNC', 'parameter': 0},
                         'SINGLE_PRESS': {'function': 'SYS_FUNC_REBOOT', 'parameter': 800},
                         'DOUBLE_PRESS': {'function': 'USER_FUNC15', 'parameter': 100},
                         'LONG_PRESS1': {'function': 'SYS_FUNC_HALT', 'parameter': 10000},
                         'LONG_PRESS2': {'function': 'HARD_FUNC_POWER_OFF', 'parameter': 0}} ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0x6E, "func": "SetButtonConfiguration", "type": "w", "class": "config",
        "data_buffer": [33, 0, 0, 0, 20, 8, 47, 1, 17, 100, 2, 0, 0],
        "parm": ("SW1",{'PRESS': {'function': 'USER_FUNC1', 'parameter': 0},
                         'RELEASE': {'function': 'NO_FUNC', 'parameter': 0},
                         'SINGLE_PRESS': {'function': 'SYS_FUNC_REBOOT', 'parameter': 800},
                         'DOUBLE_PRESS': {'function': 'USER_FUNC15', 'parameter': 100},
                         'LONG_PRESS1': {'function': 'SYS_FUNC_HALT', 'parameter': 10000},
                         'LONG_PRESS2': {'function': 'HARD_FUNC_POWER_OFF', 'parameter': 0}} ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },

    {
        "cmd": 0x6A, "func": "GetLedConfiguration", "type": "r", "class": "config",
        "data_buffer": [1, 60, 60, 100, 0],
        "parm": ("D1", ),
        "ret": {"data": {'function': 'CHARGE_STATUS', 'parameter': {'r': 60, 'g': 60, 'b': 100}}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x6B, "func": "GetLedConfiguration", "type": "r", "class": "config",
        "data_buffer": [1, 160, 60, 100, 0],
        "parm": ("D2", ),
        "ret": {"data": {'function': 'CHARGE_STATUS', 'parameter': {'r': 160, 'g': 60, 'b': 100}}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x6A, "func": "GetLedConfiguration", "type": "r", "class": "config",
        "data_buffer": [4, 60, 60, 100, 0],
        "parm": ("D1", ),
        "ret": {'error': 'UNKNOWN_CONFIG'},
    },
    {
        "cmd": 0x6A, "func": "GetLedConfiguration", "type": "r", "class": "config",
        "data_buffer": [1, 60, 60, 100, 0],
        "parm": ("D", ),
        "ret": {'error': 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x6A, "func": "GetLedConfiguration", "type": "r", "class": "config",
        "data_buffer": [1, 60, 60, 100, 0],
        "parm": ("D1", ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0x6A, "func": "GetLedConfiguration", "type": "r", "class": "config",
        "data_buffer": [1|0x80, 60, 60, 100, 0],
        "parm": ("D1", ),
        "ret": {'error': 'UNKNOWN_CONFIG'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x6A, "func": "GetLedConfiguration", "type": "r", "class": "config",
        "data_buffer": [1, 60, 60, 100, 0],
        "parm": ("D1", ),
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x6A, "func": "SetLedConfiguration", "type": "w", "class": "config",
        "data_buffer": [1, 60, 60, 100, 0],
        "parm": ("D1", {'function': 'CHARGE_STATUS', 'parameter': {'r': 60, 'g': 60, 'b': 100}} ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x6B, "func": "SetLedConfiguration", "type": "w", "class": "config",
        "data_buffer": [1, 160, 60, 100, 0],
        "parm": ("D2", {'function': 'CHARGE_STATUS', 'parameter': {'r': 160, 'g': 60, 'b': 100}} ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x6A, "func": "SetLedConfiguration", "type": "w", "class": "config",
        "data_buffer": [1, 60, 60, 100, 0],
        "parm": ("D", {'function': 'CHARGE_STATUS', 'parameter': {'r': 60, 'g': 60, 'b': 100}} ),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x6A, "func": "SetLedConfiguration", "type": "w", "class": "config",
        "data_buffer": [1, 60, 60, 100, 0],
        "parm": ("D1", {'function': 'CHARGE_STATUS', 'parameter': {'r': 60, 'g': 60, 'b': 100}} ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0x6A, "func": "SetLedConfiguration", "type": "w", "class": "config",
        "data_buffer": [1, 60, 60, 100, 0],
        "parm": ("D1", {'function': 'CHARGE_STATUS', 'parameter': {'r': 60, 'g': 60, 'b': 100}} ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },

    {
        "cmd": 0x60, "func": "GetPowerRegulatorMode", "type": "r", "class": "config",
        "data_buffer": [0, 0],
        "ret": {"data": "POWER_SOURCE_DETECTION", 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x60, "func": "GetPowerRegulatorMode", "type": "r", "class": "config",
        "data_buffer": [3, 0],
        "ret": {'error': 'UNKNOWN_DATA'},
    },
    {
        "cmd": 0x60, "func": "GetPowerRegulatorMode", "type": "r", "class": "config",
        "data_buffer": [0, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0x60, "func": "GetPowerRegulatorMode", "type": "r", "class": "config",
        "data_buffer": [3, 0],
        "ret": {'error': 'UNKNOWN_DATA'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x60, "func": "GetPowerRegulatorMode", "type": "r", "class": "config",
        "data_buffer": [0, 0],
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x60, "func": "SetPowerRegulatorMode", "type": "w", "class": "config",
        "data_buffer": [1, 0],
        "parm": ("LDO", ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x60, "func": "SetPowerRegulatorMode", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": ("wrong mode", ),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x60, "func": "SetPowerRegulatorMode", "type": "w", "class": "config",
        "data_buffer": [1, 0],
        "parm": ("LDO", ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0x60, "func": "SetPowerRegulatorMode", "type": "w", "class": "config",
        "data_buffer": [1, 0],
        "parm": ("LDO", ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },

    {
        "cmd": 0x5F, "func": "GetRunPinConfig", "type": "r", "class": "config",
        "data_buffer": [1, 0],
        "ret": {"data": "INSTALLED", 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x5F, "func": "GetRunPinConfig", "type": "r", "class": "config",
        "data_buffer": [2, 0],
        "ret": {'error': 'UNKNOWN_DATA'},
    },
    {
        "cmd": 0x5F, "func": "GetRunPinConfig", "type": "r", "class": "config",
        "data_buffer": [0, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0x5F, "func": "GetRunPinConfig", "type": "r", "class": "config",
        "data_buffer": [0x80, 0],
        "ret": {'error': 'UNKNOWN_DATA'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x5F, "func": "GetRunPinConfig", "type": "r", "class": "config",
        "data_buffer": [0, 0],
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x5F, "func": "SetRunPinConfig", "type": "w", "class": "config",
        "data_buffer": [1, 0],
        "parm": ("INSTALLED", ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x5F, "func": "SetRunPinConfig", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": ("NOT_INSTALLED", ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x5F, "func": "SetRunPinConfig", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": ("wrong mode", ),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x5F, "func": "SetRunPinConfig", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": ("NOT_INSTALLED", ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0x5F, "func": "SetRunPinConfig", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": ("NOT_INSTALLED", ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },

    {
        "cmd": 0x72, "func": "SetIoConfiguration", "type": "w", "class": "config",
        "data_buffer": [2, 1, 0, 0, 0, 0],
        "parm": (1, {'mode': 'DIGITAL_IN', 'pull': 'NOPULL', 'wakeup': 'FALLING_EDGE'}, ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x72, "func": "SetIoConfiguration", "type": "w", "class": "config",
        "data_buffer": [3, 1, 0, 0, 0, 0],
        "parm": (1, {'mode': 'DIGITAL_OUT_PUSHPULL', 'pull': 'NOPULL', 'value': 53}, ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x72, "func": "SetIoConfiguration", "type": "w", "class": "config",
        "data_buffer": [5, 53, 170, 172, 199, 0],
        "parm": (1, {'mode': 'PWM_OUT_PUSHPULL', 'pull': 'NOPULL', 'period': 1}, ),
        "ret": {"error": 'INVALID_PERIOD'},
    },
    {
        "cmd": 0x72, "func": "SetIoConfiguration", "type": "w", "class": "config",
        "data_buffer": [5, 53, 170, 172, 199, 0],
        "parm": (1, {'mode': 'PWM_OUT_PUSHPULL', 'pull': 'NOPULL', 'period': 87148, 'duty_cycle': -1}, ),
        "ret": {"error": 'INVALID_CONFIG'},
    },
    {
        "cmd": 0x72, "func": "SetIoConfiguration", "type": "w", "class": "config",
        "data_buffer": [5, 53, 170, 172, 199, 0],
        "parm": (1, {'pull': 'NOPULL', 'period': 87148, 'duty_cycle': 78.0}, ),
        "ret": {"error": 'INVALID_CONFIG'},
    },
    {
        "cmd": 0x72, "func": "SetIoConfiguration", "type": "w", "class": "config",
        "data_buffer": [5, 53, 170, 172, 199, 0],
        "parm": (1, {'mode': 'PWM_OUT_PUSHPULL', 'pull': 'NOPULL', 'period': 87148, 'duty_cycle': 78.0}, ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x77, "func": "SetIoConfiguration", "type": "w", "class": "config",
        "data_buffer": [5, 53, 170, 172, 199, 0],
        "parm": (2, {'mode': 'PWM_OUT_PUSHPULL', 'pull': 'NOPULL', 'period': 87148, 'duty_cycle': 78.0}, ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x72, "func": "SetIoConfiguration", "type": "w", "class": "config",
        "data_buffer": [5 | 0x80, 53, 170, 172, 199, 0],
        "parm": (1, {'mode': 'PWM_OUT_PUSHPULL', 'pull': 'NOPULL', 'period': 87148, 'duty_cycle': 78.0}, True),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x72, "func": "SetIoConfiguration", "type": "w", "class": "config",
        "data_buffer": [128, 53, 170, 178, 201, 0],
        "parm": (1, {'mode': 'PWM_OUT_PUSHPULL', 'pull': 'NOPULL', 'period': 87148, 'duty_cycle': 78.0}, ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0x72, "func": "SetIoConfiguration", "type": "w", "class": "config",
        "data_buffer": [128, 53, 170, 178, 201, 0],
        "parm": (1, {'mode': 'PWM_OUT_PUSHPULL', 'pull': 'NOPULL', 'period': 87148, 'duty_cycle': 78.0}, ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },

    {
        "cmd": 0x72, "func": "GetIoConfiguration", "type": "r", "class": "config",
        "data_buffer": [0x07, 53, 170, 178, 201, 0],
        "parm": (1, ),
        "ret": {"data": {'mode': 'UNKNOWN', 'pull': 'NOPULL', 'wakeup': 'FALLING_EDGE'}, 'non_volatile': False, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x72, "func": "GetIoConfiguration", "type": "r", "class": "config",  # 10
        "data_buffer": [0x30, 53, 170, 178, 201, 0],
        "parm": (1, ),
        "ret": {"data": {'mode': 'NOT_USED', 'pull': 'UNKNOWN', 'wakeup': 'FALLING_EDGE'}, 'non_volatile': False, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x72, "func": "GetIoConfiguration", "type": "r", "class": "config",
        "data_buffer": [0x03, 53, 170, 178, 201, 0],
        "parm": (1, ),
        "ret": {"data": {'mode': 'DIGITAL_OUT_PUSHPULL', 'pull': 'NOPULL', 'value': 53}, 'non_volatile': False, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x72, "func": "GetIoConfiguration", "type": "r", "class": "config",
        "data_buffer": [0x05, 53, 170, 178, 201, 0],
        "parm": (1, ),
        "ret": {"data": {'mode': 'PWM_OUT_PUSHPULL', 'pull': 'NOPULL', 'period': 87148, 'duty_cycle': 78.0}, 'non_volatile': False, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x72, "func": "GetIoConfiguration", "type": "r", "class": "config",
        "data_buffer": [0x87, 53, 170, 178, 201, 0],
        "parm": (1, ),
        "ret": {"data": {'mode': 'UNKNOWN', 'pull': 'NOPULL', 'wakeup': 'FALLING_EDGE'}, 'non_volatile': True, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x77, "func": "GetIoConfiguration", "type": "r", "class": "config",
        "data_buffer": [0x87, 53, 170, 178, 201, 0],
        "parm": (2, ),
        "ret": {"data": {'mode': 'UNKNOWN', 'pull': 'NOPULL', 'wakeup': 'FALLING_EDGE'}, 'non_volatile': True, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x72, "func": "GetIoConfiguration", "type": "r", "class": "config",
        "data_buffer": [128, 53, 170, 178, 201, 0],
        "parm": (1, ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0x72, "func": "GetIoConfiguration", "type": "r", "class": "config",
        "data_buffer": [128, 53, 170, 178, 201, 0],
        "parm": (1, ),
        "ret": {'data': {'mode': 'NOT_USED', 'pull': 'NOPULL', 'wakeup': 'FALLING_EDGE'}, 'non_volatile': True, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x72, "func": "GetIoConfiguration", "type": "r", "class": "config",
        "data_buffer": [128, 53, 170, 178, 201, 0],
        "parm": (1, ),
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x7C, "func": "GetAddress", "type": "r", "class": "config",
        "data_buffer": [20, 0],
        "parm": (1, ),
        "ret": {"data": "14", 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x7D, "func": "GetAddress", "type": "r", "class": "config",
        "data_buffer": [0x20, 0],
        "parm": (2, ),
        "ret": {"data": "20", 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x7C, "func": "GetAddress", "type": "r", "class": "config",
        "data_buffer": [20, 0],
        "parm": (3, ),
        "ret": {'error': 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x7C, "func": "GetAddress", "type": "r", "class": "config",
        "data_buffer": [20, 0],
        "parm": (1, ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0x7C, "func": "GetAddress", "type": "r", "class": "config",
        "data_buffer": [128, 0],
        "parm": (1, ),
        "ret": {"data": "80", 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x7C, "func": "GetAddress", "type": "r", "class": "config",
        "data_buffer": [20, 0],
        "parm": (1, ),
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x7C, "func": "SetAddress", "type": "w", "class": "config",
        "data_buffer": [20, 0],
        "parm": (1, "14" ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x7D, "func": "SetAddress", "type": "w", "class": "config",
        "data_buffer": [0x20, 0],
        "parm": (2, "20" ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x7C, "func": "SetAddress", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": (1, "wrong addr", ),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x7C, "func": "SetAddress", "type": "w", "class": "config",
        "data_buffer": [20, 0],
        "parm": (3, "14", ),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x7C, "func": "SetAddress", "type": "w", "class": "config",
        "data_buffer": [20, 0],
        "parm": (1, "14", ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0x7C, "func": "SetAddress", "type": "w", "class": "config",
        "data_buffer": [20, 0],
        "parm": (1, "14", ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },

    {
        "cmd": 0x7E, "func": "GetIdEepromWriteProtect", "type": "r", "class": "config",
        "data_buffer": [1, 0],
        "ret": {"data": True, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x7E, "func": "GetIdEepromWriteProtect", "type": "r", "class": "config",
        "data_buffer": [20, 0],
        "ret": {"data": False, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x7E, "func": "GetIdEepromWriteProtect", "type": "r", "class": "config",
        "data_buffer": [1, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0x7E, "func": "GetIdEepromWriteProtect", "type": "r", "class": "config",
        "data_buffer": [0x80, 0],
        "ret": {"data": False, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x7E, "func": "GetIdEepromWriteProtect", "type": "r", "class": "config",
        "data_buffer": [1, 0],
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x7E, "func": "SetIdEepromWriteProtect", "type": "w", "class": "config",
        "data_buffer": [1, 0],
        "parm": (True, ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x7E, "func": "SetIdEepromWriteProtect", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": (False, ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x7E, "func": "SetIdEepromWriteProtect", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": ("bor treu", ),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x7E, "func": "SetIdEepromWriteProtect", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": (False, ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0x7E, "func": "SetIdEepromWriteProtect", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": (False, ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },

    {
        "cmd": 0x7F, "func": "GetIdEepromAddress", "type": "r", "class": "config",
        "data_buffer": [0x50, 0],
        "ret": {"data": "50", 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x7F, "func": "GetIdEepromAddress", "type": "r", "class": "config",
        "data_buffer": [0x52, 0],
        "ret": {"data": "52", 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0x7F, "func": "GetIdEepromAddress", "type": "r", "class": "config",
        "data_buffer": [0x52, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0x7F, "func": "GetIdEepromAddress", "type": "r", "class": "config",
        "data_buffer": [0x52, 0],
        "ret": {"data": "52", 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0x7F, "func": "GetIdEepromAddress", "type": "r", "class": "config",
        "data_buffer": [0x52, 0],
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0x7F, "func": "SetIdEepromAddress", "type": "w", "class": "config",
        "data_buffer": [0x52, 0],
        "parm": ("52", ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x7F, "func": "SetIdEepromAddress", "type": "w", "class": "config",
        "data_buffer": [0x50, 0],
        "parm": ("50", ),
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0x7F, "func": "SetIdEepromAddress", "type": "w", "class": "config",
        "data_buffer": [0, 0],
        "parm": ("bor treu", ),
        "ret": {"error": 'BAD_ARGUMENT'},
    },
    {
        "cmd": 0x7F, "func": "SetIdEepromAddress", "type": "w", "class": "config",
        "data_buffer": [0x50, 0],
        "parm": ("50", ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0x7F, "func": "SetIdEepromAddress", "type": "w", "class": "config",
        "data_buffer": [0x50, 0],
        "parm": ("50", ),
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },

    {
        "cmd": 0xF0, "func": "SetDefaultConfiguration", "type": "w", "class": "config",
        "data_buffer": [0xAA, 0x55, 0x0A, 0xA3, 0],
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0xF0, "func": "SetDefaultConfiguration", "type": "w", "class": "config",
        "data_buffer": [0xAA, 0x55, 0x0A, 0xA3, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0xF0, "func": "SetDefaultConfiguration", "type": "w", "class": "config",
        "data_buffer": [0xAA, 0x55, 0x0A, 0xA3, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },

    {
        "cmd": 0xFD, "func": "GetFirmwareVersion", "type": "r", "class": "config",
        "data_buffer": [22, 0, 0],
        "ret": {"data": {'version': '1.6', 'variant': '0'}, 'error': 'NO_ERROR'},
    },
    {
        "cmd": 0xFD, "func": "GetFirmwareVersion", "type": "r", "class": "config",
        "data_buffer": [22, 0, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "read_err": 1,
    },
    {
        "cmd": 0xFD, "func": "GetFirmwareVersion", "type": "r", "class": "config",
        "data_buffer": [22, 0, 0],
        "ret": {"data": {'version': '1.6', 'variant': '0'}, 'error': 'NO_ERROR'},
        "recoverable_checksum": True,
    },
    {
        "cmd": 0xFD, "func": "GetFirmwareVersion", "type": "r", "class": "config",
        "data_buffer": [22, 0, 0],
        "ret": {"error": 'DATA_CORRUPTED'},
        "checksum_err": True,
    },

    {
        "cmd": 0xF8, "func": "RunTestCalibration", "type": "w", "class": "config",
        "data_buffer": [0x55, 0x26, 0xA0, 0x2B, 0],
        "ret": {"error": 'NO_ERROR'},
    },
    {
        "cmd": 0xF8, "func": "RunTestCalibration", "type": "w", "class": "config",
        "data_buffer": [0x55, 0x26, 0xA0, 0x2B, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "write_err": True,
    },
    {
        "cmd": 0xF8, "func": "RunTestCalibration", "type": "w", "class": "config",
        "data_buffer": [0x55, 0x26, 0xA0, 0x2B, 0],
        "ret": {"error": 'COMMUNICATION_ERROR'},
        "cmd_delay": 1,
    },

]

def ex_test_list(ex_fun_name, test_list):
    list_index = 0
    sub_list_index = 0
    for test in test_list:
        list_index += 1
        cmd_str = f"{test['cmd']:02X}"
        if ex_fun_name is None or cmd_str in ex_fun_name:
            sub_list_index += 1
            ex_1_test(test, list_index, sub_list_index)

def ex_1_test(test, index_in_list, index_in_subset):
    SMBus.SIM_BUS = 1
    bus = 1
    address = 0x14
    with patch("homeassistant.components.pijups.pijuice.SMBus", new=SMBus):
        with pi.PiJuice(bus, address) as pijuice:
            cmd = test['cmd']
            data_buffer = test.get('data_buffer')
            data_buffer_before = test.get('data_buffer_before')
            cmd_delay = test.get('cmd_delay', 0)
            next_read_buffer = test.get('next_read_buffer', None)
            read_err = test.get('read_err', False)
            write_err = test.get('write_err', False)
            corrupt = test.get('corrupt', False)
            recoverable_checksum = test.get('recoverable_checksum', False)
            checksum_err = test.get('checksum_err', False)
            parm = test.get('parm', ())
            fun_class = test.get('class', "status")
            type = test.get('type', "r")
            ret_exp = test.get('ret')
            func = test['func']
            if type == "r":
                pijuice.interface.i2cbus._set_buff(cmd, data_buffer)
            if type == "w" and data_buffer_before is not None:
                pijuice.interface.i2cbus._set_buff(cmd, data_buffer_before)
            pijuice.interface.i2cbus.add_cmd_delays(cmd, cmd_delay, common.I2C_CMD_EXECUTION_TIMEOUT)
            if read_err:
                pijuice.interface.i2cbus.io_error_next_read_call()
            if corrupt:
                pijuice.interface.i2cbus.corrupt_data_next_read_call()
            if write_err:
                pijuice.interface.i2cbus.io_error_next_write_call()
            pijuice.interface.i2cbus.io_buffer_next_read_call(cmd, next_read_buffer)
            pijuice.interface.i2cbus.manage_chksum_calculations(recoverable_checksum)
            pijuice.interface.i2cbus.manage_data_corruptions(checksum_err)
            sub_obj = getattr(pijuice, fun_class)
            with sub_obj:
                read_fun = getattr(sub_obj, func)
            ret = read_fun(*parm)
            if read_err or write_err:
                time.sleep(common.I2C_CMD_EXCEPTION_TIMEOUT)
            if cmd_delay >0:
                time.sleep(common.I2C_CMD_EXECUTION_TIMEOUT)
            assert ret == ret_exp, f"{func} @{index_in_list}/{index_in_subset}"
            if type == "w":
                if ret == {'error': 'NO_ERROR'}:
                    curr_buff = pijuice.interface.i2cbus._get_buff(cmd)
                    if data_buffer is not None:
                        assert data_buffer[:-1] == curr_buff[:-1], f"{func} @{index_in_list}/{index_in_subset}"
            pass

def test_pijuice_interface(hass: HomeAssistant):
    """Test if PiJups loads for standard emulated h/w configuration with default configuration."""
    SMBus.SIM_BUS = 1
    bus = 1
    address = 0x14
    with patch("homeassistant.components.pijups.pijuice.SMBus", new=SMBus):
        with pi.PiJuiceInterface(bus, address) as pin:
            assert pin.GetAddress() == address

def test_pijuice_status_0x40(hass: HomeAssistant):
    """Test GetStatus function."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_status_0x41(hass: HomeAssistant):
    """Test GetChargeLevel functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_status_0x44(hass: HomeAssistant):
    """Test GetFaultStatus/ResetFaultFlags functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_status_0x45(hass: HomeAssistant):
    """Test GetButtonEvents/AcceptButtonEvent functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_status_0x47(hass: HomeAssistant):
    """Test GetBatteryTemperature function."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_status_0x49(hass: HomeAssistant):
    """Test GetBatteryVoltage function."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_status_0x4B(hass: HomeAssistant):
    """Test GetBatteryCurrent function."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_status_0x4D(hass: HomeAssistant):
    """Test GetIoVoltage function."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_status_0x4F(hass: HomeAssistant):
    """Test GetIoCurrent function."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_status_0x66_0x67(hass: HomeAssistant):
    """Test SetLedState/GetLedState functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_status_0x68_0x69(hass: HomeAssistant):
    """Test SetLedBlink/GetLedBlink function."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_status_0x75_0x7A(hass: HomeAssistant):
    """Test SetIoPWM/GetIoPWM functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_rtcAlarm_0xC2(hass: HomeAssistant):
    """Test GetControlStatus/ClearAlarmFlag/SetWakeupEnabled functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_rtcAlarm_0xB0(hass: HomeAssistant):
    """Test GetTime/SetTime functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_rtcAlarm_0xB9(hass: HomeAssistant):
    """Test GetAlarm/SetAlarm functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_power_0x62(hass: HomeAssistant):
    """Test SetPowerOff/GetPowerOff functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_power_0x63(hass: HomeAssistant):
    """Test SetWakeUpOnCharge/GetWakeUpOnCharge functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_power_0x61(hass: HomeAssistant):
    """Test SetWatchdog/GetWatchdog functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_power_0x64(hass: HomeAssistant):
    """Test SetSystemPowerSwitch/GetSystemPowerSwitch functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_config_0x51(hass: HomeAssistant):
    """Test SetChargingConfig/GetChargingConfig functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_config_0x52(hass: HomeAssistant):
    """Test SetBatteryProfile/GetBatteryProfileStatus functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_config_0x53(hass: HomeAssistant):
    """Test GetBatteryProfile/SetCustomBatteryProfile functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_config_0x54(hass: HomeAssistant):
    """Test GetBatteryExtProfile/SetCustomBatteryExtProfile functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_config_0x5D(hass: HomeAssistant):
    """Test GetRsocEstimationConfig/SetRsocEstimationConfig functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_config_0x5E(hass: HomeAssistant):
    """Test SetPowerInputsConfig/GetPowerInputsConfig functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_config_0x6E_0x6F_0x70(hass: HomeAssistant):
    """Test GetButtonConfiguration/SetButtonConfiguration functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_config_0x6A_0x6B(hass: HomeAssistant):
    """Test GetLedConfiguration/SetLedConfiguration functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_config_0x60(hass: HomeAssistant):
    """Test GetPowerRegulatorMode/SetPowerRegulatorMode functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_config_0x5F(hass: HomeAssistant):
    """Test GetRunPinConfig/SetRunPinConfig functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_config_0x72_0x77(hass: HomeAssistant):
    """Test SetIoConfiguration/GetIoConfiguration functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_config_0x7C_0x7D(hass: HomeAssistant):
    """Test GetAddress/SetAddress functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_config_0x7E(hass: HomeAssistant):
    """Test GetIdEepromWriteProtect/SetIdEepromWriteProtect functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_config_0x7F(hass: HomeAssistant):
    """Test GetIdEepromAddress/SetIdEepromAddress functions."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_config_0xF0(hass: HomeAssistant):
    """Test SetDefaultConfiguration function."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_config_0xFD(hass: HomeAssistant):
    """Test GetFirmwareVersion function."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_config_0xF8(hass: HomeAssistant):
    """Test RunTestCalibration function."""
    ex_test_list(inspect.stack()[0][3], STATUS_FUNC_TESTS)

def test_pijuice_different_independent_funcs(hass: HomeAssistant):
    """Test if PiJups loads for standard emulated h/w configuration with default configuration."""
    SMBus.SIM_BUS = 1
    bus = 1
    address = 0x14
    with patch("homeassistant.components.pijups.pijuice.SMBus", new=SMBus):
        with pi.PiJuice(bus, address) as pijuice:
             # check for default timeout in case of wrong delay calling in parameter
            write_status = pijuice.interface.WriteDataVerify(0x5D, [0x00], "no_delay")
            assert write_status == {'error': 'NO_ERROR'}
            # STATUS_CMD = 0x40 - run one failing request followed by another within 4s
            pijuice.interface.i2cbus.add_cmd_delays(0x40, 1, common.I2C_CMD_EXECUTION_TIMEOUT)    # STATUS_CMD
            status = pijuice.status.GetStatus()
            assert status == {'error': 'COMMUNICATION_ERROR'}
            status = pijuice.status.GetStatus()
            assert status == {'error': 'COMMUNICATION_ERROR'}
            time.sleep(common.I2C_CMD_EXCEPTION_TIMEOUT)
        version_info, firmware_version, os_version = pi.get_versions()
        assert len(version_info) > 0
        assert len(firmware_version) > 0
        assert len(os_version) > 0
        SMBus.SIM_BUS = 2
        version_info, firmware_version, os_version = pi.get_versions()
        assert len(version_info) > 0
        assert firmware_version is None
        assert len(os_version) > 0
