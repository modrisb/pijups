"""Test PiJups sensor registration and entity class."""
from homeassistant.components.pijups import sensor
from homeassistant.components.pijups.const import DOMAIN, SENSOR_ENTITY
from homeassistant.components.pijups.interface import PiJups
from homeassistant.core import HomeAssistant

from .smbus2 import SMBus

from tests.components.pijups import common

EMULATED_SENSOR_VALUES = {
    "Charge": 82,
    "Battery status": "NORMAL",
    "Temperature": 48,
    "Power input status": "NOT_PRESENT",
    "Battery voltage": 4020,
    "Battery current": 12,
    "Power input IO status": "PRESENT",
    "IO voltage": 5170,
    "IO current": -1134,
    "External Power": True,
}

CHARGE_LEVELS_AND_ICONS = [
    ["Charge", 0x41, [91, 0], "mdi:battery"],
    ["Charge", 0x41, [90, 0], "mdi:battery-80"],
    ["Charge", 0x41, [71, 0], "mdi:battery-80"],
    ["Charge", 0x41, [70, 0], "mdi:battery-60"],
    ["Charge", 0x41, [51, 0], "mdi:battery-60"],
    ["Charge", 0x41, [50, 0], "mdi:battery-40"],
    ["Charge", 0x41, [31, 0], "mdi:battery-40"],
    ["Charge", 0x41, [30, 0], "mdi:battery-20"],
    ["Charge", 0x41, [00, 0], "mdi:battery-20"],
]

BATTERY_STATUS_AND_ICONS = [
    ["Battery status", 0x40, [0x00, 0], "mdi:battery"],
    ["Battery status", 0x40, [0x04, 0], "mdi:battery-charging"],
    ["Battery status", 0x40, [0x08, 0], "mdi:battery-charging"],
    ["Battery status", 0x40, [0x0C, 0], "mdi:battery-off"],
]

POWER_STATUS_AND_ICONS = [
    ["Power input status", 0x40, [0x00, 0], "mdi:power-plug-off-outline"],
    ["Power input status", 0x40, [0x10, 0], "mdi:power-plug-outline"],
    ["Power input status", 0x40, [0x20, 0], "mdi:power-plug-outline"],
    ["Power input status", 0x40, [0x30, 0], "mdi:power-plug"],
]

IO_POWER_STATUS_AND_ICONS = [
    ["Power input IO status", 0x40, [0x00, 0], "mdi:power-plug-off-outline"],
    ["Power input IO status", 0x40, [0x40, 0], "mdi:power-plug-outline"],
    ["Power input IO status", 0x40, [0x80, 0], "mdi:power-plug-outline"],
    ["Power input IO status", 0x40, [0xC0, 0], "mdi:power-plug"],
]


async def test_pijups_sensor_initial_states(hass: HomeAssistant):
    """Test we clean up on home assistant stop."""
    SMBus.SIM_BUS = 1

    async def run_test_pijups_sensor_initial_states(hass, entry):
        await hass.async_block_till_done()

        assert hass.states.async_entity_ids_count() >= len(
            sensor.PiJuiceSensor.SENSOR_LIST
        )

        sensor_entities = hass.data[DOMAIN][entry.entry_id][SENSOR_ENTITY]
        for entity in sensor_entities:
            assert entity.native_value is not None
            assert EMULATED_SENSOR_VALUES.get(entity.name) == entity.native_value

    await common.pijups_setup_and_run_test(
        hass, True, run_test_pijups_sensor_initial_states
    )


def get_sensor_entity_by_name(hass, entry, sensor_name):
    """Get specific entity object by entity name."""
    sensor_entities = hass.data[DOMAIN][entry.entry_id][SENSOR_ENTITY]
    for entity in sensor_entities:
        if entity.name == sensor_name:
            return entity
    return None


def update_sensor_values(hass, entry, pijups: PiJups):
    """Run update for all sensor entities."""
    sensor_entities = hass.data[DOMAIN][entry.entry_id][SENSOR_ENTITY]
    pijups.get_piju_status(True)
    for entity in sensor_entities:
        entity._get_value(entity)


async def test_pijups_charge_level_icon(hass):
    """Test PiJups entity icon dependency on charge level."""
    SMBus.SIM_BUS = 1

    async def run_test_pijups_charge_level_icon(hass, entry):
        pijups: PiJups = await common.get_pijups(hass, entry)

        charge_sensor = get_sensor_entity_by_name(
            hass, entry, CHARGE_LEVELS_AND_ICONS[0][0]
        )
        assert charge_sensor is not None
        for _cl in CHARGE_LEVELS_AND_ICONS:
            pijups.interface.i2cbus._set_buff(_cl[1], _cl[2])
            await hass.async_add_executor_job(update_sensor_values, hass, entry, pijups)
            assert charge_sensor.icon == _cl[3]

    await common.pijups_setup_and_run_test(
        hass, True, run_test_pijups_charge_level_icon
    )


async def test_pijups_external_power_icon(hass):
    """Test PiJups entity icon dependency on external power settings."""
    SMBus.SIM_BUS = 1

    async def run_test_pijups_external_power_icon(hass, entry):
        pijups: PiJups = await common.get_pijups(hass, entry)

        ext_power_sensor = get_sensor_entity_by_name(hass, entry, "External Power")
        assert ext_power_sensor is not None

        assert ext_power_sensor.icon == "mdi:power-plug"

        pijups.interface.i2cbus.set_power(False, False)
        await hass.async_add_executor_job(update_sensor_values, hass, entry, pijups)

        assert ext_power_sensor.icon == "mdi:power-plug-off-outline"

    await common.pijups_setup_and_run_test(
        hass, True, run_test_pijups_external_power_icon
    )


async def test_pijups_battery_status_icon(hass):
    """Test PiJups entity icon dependency on battery status."""
    SMBus.SIM_BUS = 1

    async def run_test_pijups_battery_status_icon(hass, entry):
        pijups: PiJups = await common.get_pijups(hass, entry)

        battery_sensor = get_sensor_entity_by_name(
            hass, entry, BATTERY_STATUS_AND_ICONS[0][0]
        )
        assert battery_sensor is not None
        for _cl in BATTERY_STATUS_AND_ICONS:
            pijups.interface.i2cbus._set_buff(_cl[1], _cl[2])
            await hass.async_add_executor_job(update_sensor_values, hass, entry, pijups)
            assert battery_sensor.icon == _cl[3]

    await common.pijups_setup_and_run_test(
        hass, True, run_test_pijups_battery_status_icon
    )


async def test_pijups_power_status_icon(hass):
    """Test PiJups entity icon dependency per power source states."""
    SMBus.SIM_BUS = 1

    async def run_test_pijups_power_status_icon(hass, entry):
        pijups: PiJups = await common.get_pijups(hass, entry)

        power_sensor = get_sensor_entity_by_name(
            hass, entry, POWER_STATUS_AND_ICONS[0][0]
        )
        assert power_sensor is not None
        for _cl in POWER_STATUS_AND_ICONS:
            pijups.interface.i2cbus._set_buff(_cl[1], _cl[2])
            await hass.async_add_executor_job(update_sensor_values, hass, entry, pijups)
            assert power_sensor.icon == _cl[3]

        power_sensor = get_sensor_entity_by_name(
            hass, entry, IO_POWER_STATUS_AND_ICONS[0][0]
        )
        assert power_sensor is not None
        for _cl in IO_POWER_STATUS_AND_ICONS:
            pijups.interface.i2cbus._set_buff(_cl[1], _cl[2])
            await hass.async_add_executor_job(update_sensor_values, hass, entry, pijups)
            assert power_sensor.icon == _cl[3]

    await common.pijups_setup_and_run_test(
        hass, True, run_test_pijups_power_status_icon
    )


async def test_pijups_check_disable_status(hass):
    """Test PiJups entity icon dependency on battery status."""
    SMBus.SIM_BUS = 1

    async def run_test_pijups_check_disable_status(hass, entry):
        pijups: PiJups = await common.get_pijups(hass, entry)

        charge_sensor = get_sensor_entity_by_name(
            hass, entry, CHARGE_LEVELS_AND_ICONS[0][0]
        )
        charge_sensor._attr_max_rate = 1
        charge_sensor._attr_cur_rate = 0
        assert charge_sensor is not None
        assert pijups.piju_enabled

        cl_0 = CHARGE_LEVELS_AND_ICONS[0]
        pijups.interface.i2cbus._set_buff(cl_0[1], cl_0[2])
        await hass.async_add_executor_job(update_sensor_values, hass, entry, pijups)
        cl_0_value = charge_sensor._attr_native_value

        pijups.piju_enabled = False
        for _cl in CHARGE_LEVELS_AND_ICONS:
            pijups.interface.i2cbus._set_buff(_cl[1], _cl[2])
            await hass.async_add_executor_job(charge_sensor.update)
            assert charge_sensor._attr_native_value == cl_0_value

    await common.pijups_setup_and_run_test(
        hass, True, run_test_pijups_check_disable_status
    )
