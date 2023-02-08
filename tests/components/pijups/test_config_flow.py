"""Test the pijups config and config options flow."""
import asyncio
from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.pijups import interface
from homeassistant.components.pijups.const import (
    BASE,
    CONF_BATTERY_PROFILE,
    CONF_BATTERY_TEMP_SENSE_CONFIG,
    CONF_DIAG_LOG_CONFIG,
    CONF_FIRMWARE_SELECTION,
    CONF_UPS_DELAY,
    CONF_UPS_WAKEON_DELTA,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UPS_DELAY,
    DEFAULT_UPS_WAKEON_DELTA,
    DOMAIN,
)
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .smbus2 import SMBus

from tests.components.pijups import common, test_pijups_interface


async def test_setup_with_enabled_i2c(hass: HomeAssistant) -> None:
    """Test if configuration is created automatically if hat device is operational."""
    SMBus.SIM_BUS = 1
    with patch("homeassistant.components.pijups.pijuice.SMBus", new=SMBus):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"] == common.CONFIG_DATA
        assert result["options"] == common.CONFIG_OPTIONS


async def test_setup_with_disbled_i2c(hass: HomeAssistant) -> None:
    """Test for configuration abort in case no hat device is available."""
    SMBus.SIM_BUS = -1  # to fail i2c search
    with patch("homeassistant.components.pijups.pijuice.SMBus", new=SMBus):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "no_device_found"


async def test_setup_with_device_reserved(hass: HomeAssistant) -> None:
    """Test for configuration abort in case hat already in use."""
    SMBus.SIM_BUS = 1
    with patch("homeassistant.components.pijups.pijuice.SMBus", new=SMBus):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        instance_found = False
        for instance in hass.data.get(DOMAIN, []):
            pijups = hass.data[DOMAIN][instance][BASE]
            pijups.i2c_bus = -1  # hide already set-up hat bus
            pijups.i2c_address = -1  # hide already set-up hat address to get the same once more
            instance_found = True
        assert instance_found
        result2 = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result2["type"] == FlowResultType.ABORT
        assert result2["reason"] == "device_reserved"


async def test_setup_with_no_device_as_addr_already_in_use(hass: HomeAssistant) -> None:
    """Test for configuration abort in case hat already in use."""
    SMBus.SIM_BUS = 1
    with patch("homeassistant.components.pijups.pijuice.SMBus", new=SMBus):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        result2 = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result2["type"] == FlowResultType.ABORT
        assert result2["reason"] == "no_device_found"   # as 1st instance device is excluded from search


async def test_setup_with_several_devices(hass: HomeAssistant) -> None:
    """Test for configuration form to show up in case of several HATs found."""
    SMBus.SIM_BUS = (1, 2)
    with patch("homeassistant.components.pijups.pijuice.SMBus", new=SMBus):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM


async def test_entry_options(hass):
    """Test that we can set options on an entry."""
    SMBus.SIM_BUS = 1

    async def run_test_entry_options(hass, entry):
        result = await hass.config_entries.options.async_init(entry.entry_id)

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "init"
        assert result["errors"] == {}

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input=common.CONFIG_OPTIONS,
        )
        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["data"] == {
            CONF_UPS_DELAY: DEFAULT_UPS_DELAY,
            CONF_UPS_WAKEON_DELTA: DEFAULT_UPS_WAKEON_DELTA,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_DIAG_LOG_CONFIG: ["5VREG_ON"],
            CONF_BATTERY_PROFILE: "BP7X_1820",
            CONF_BATTERY_TEMP_SENSE_CONFIG: "ON_BOARD",
        }

    await common.pijups_setup_and_run_test(hass, True, run_test_entry_options)


async def test_entry_options_fw15(hass):
    """Test that we can set options on an entry with fw v1.5 and less: without logging options."""
    SMBus.SIM_BUS = 1
    SMBus.add_init_adjustments(0xFD, [0x15, 0x00])  # set hat emulator to fw v1.5

    async def run_test_entry_options_fw15(hass, entry):
        result = await hass.config_entries.options.async_init(entry.entry_id)

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "init"
        assert result["errors"] == {}

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input=common.CONFIG_OPTIONS,
        )
        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["data"] == {
            CONF_UPS_DELAY: DEFAULT_UPS_DELAY,
            CONF_UPS_WAKEON_DELTA: DEFAULT_UPS_WAKEON_DELTA,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_BATTERY_PROFILE: "BP7X_1820",
            CONF_BATTERY_TEMP_SENSE_CONFIG: "ON_BOARD",
        }

    await common.pijups_setup_and_run_test(hass, True, run_test_entry_options_fw15)


async def test_entry_options_with_update(hass):
    """Test that we can set options on an entry and send changes to device."""
    SMBus.SIM_BUS = 1

    async def run_test_entry_options_with_update(hass, entry):
        result = await hass.config_entries.options.async_init(entry.entry_id)

        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "init"
        assert result["errors"] == {}

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_UPS_DELAY: DEFAULT_UPS_DELAY,
                CONF_UPS_WAKEON_DELTA: DEFAULT_UPS_WAKEON_DELTA,
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_DIAG_LOG_CONFIG: ["5VREG_OFF", "WAKEUP_EVT"],
                CONF_BATTERY_PROFILE: "SNN5843_2300",
                CONF_BATTERY_TEMP_SENSE_CONFIG: "NTC",
            },
        )
        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["data"] == {
            CONF_UPS_DELAY: DEFAULT_UPS_DELAY,
            CONF_UPS_WAKEON_DELTA: DEFAULT_UPS_WAKEON_DELTA,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_DIAG_LOG_CONFIG: ["5VREG_OFF", "WAKEUP_EVT"],
            CONF_BATTERY_PROFILE: "SNN5843_2300",
            CONF_BATTERY_TEMP_SENSE_CONFIG: "NTC",
        }

    await common.pijups_setup_and_run_test(
        hass, True, run_test_entry_options_with_update
    )


async def test_entry_options_with_firmware_upgrade(hass: HomeAssistant):
    """Test PiJups interface settings for emulated h/w with default configuration.

    Check emulated sensor values, diagnostics log settings, h/w diagnostics log contents
    and basic device behaviour
    """
    SMBus.SIM_BUS = 1
    with patch(
        "homeassistant.components.pijups.interface.PiJups.get_fw_directory",
        new=test_pijups_interface.get_fw_directory,
    ):

        async def run_test_entry_options_with_firmware_upgrade(hass, entry):
            options_flow_result = await hass.config_entries.options.async_init(
                entry.entry_id
            )
            pijups: interface.PiJups = await common.get_pijups(hass, entry)

            fw_upgrade_confirmation = await hass.config_entries.options.async_configure(
                options_flow_result["flow_id"],
                user_input={
                    CONF_UPS_DELAY: DEFAULT_UPS_DELAY,
                    CONF_UPS_WAKEON_DELTA: DEFAULT_UPS_WAKEON_DELTA,
                    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    CONF_DIAG_LOG_CONFIG: ["5VREG_OFF"],
                    CONF_BATTERY_PROFILE: "SNN5843_2300",
                    CONF_BATTERY_TEMP_SENSE_CONFIG: "NTC",
                    CONF_FIRMWARE_SELECTION: "PiJuice-V1.6_2021_09_10.elf.binary",
                },
            )
            assert fw_upgrade_confirmation is not None
            assert fw_upgrade_confirmation["step_id"] == "firmware_confirm"
            fw_upgrade_inprogress = await hass.config_entries.options.async_configure(
                options_flow_result["flow_id"], user_input={}
            )
            assert pijups.piju_enabled
            assert fw_upgrade_inprogress is not None
            assert fw_upgrade_inprogress["step_id"] == "firmware_progress"
            assert fw_upgrade_inprogress["progress_action"] == "fw_started"
            await asyncio.sleep(0)
            assert not pijups.piju_enabled

            while True:
                await asyncio.sleep(3)
                fw_upgrade_done = await hass.config_entries.options.async_configure(
                    options_flow_result["flow_id"],
                )
                assert fw_upgrade_done is not None
                if fw_upgrade_done["step_id"] == "firmware_finish":
                    break
                assert not pijups.piju_enabled

            assert fw_upgrade_done["step_id"] == "firmware_finish"
            await hass.async_block_till_done()

            fw_upgrade_finished = await hass.config_entries.options.async_configure(
                options_flow_result["flow_id"],
            )
            assert fw_upgrade_finished is not None
            assert fw_upgrade_finished["type"] == FlowResultType.FORM
            assert fw_upgrade_finished["errors"] == {}

            fw_upgrade_finished_done = (
                await hass.config_entries.options.async_configure(
                    options_flow_result["flow_id"], user_input={}
                )
            )
            print("++++++", fw_upgrade_finished_done)
            assert fw_upgrade_finished_done is not None
            assert fw_upgrade_finished_done["type"] == FlowResultType.CREATE_ENTRY

        await common.pijups_setup_and_run_test(
            hass, True, run_test_entry_options_with_firmware_upgrade
        )
