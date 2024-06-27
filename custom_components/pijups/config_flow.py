"""The PiJuPS HAT integration - base configuration and options."""
import asyncio
import logging
import subprocess
import time
import threading
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, core, data_entry_flow, exceptions
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    BASE,
    CONF_ADDRESS_OPTIONS,
    CONF_BUS_OPTIONS,
    CONF_FIRMWARE_SELECTION,
    CONF_FLOW_DEVICE_RESERVED,
    CONF_FLOW_NO_DEVICE_FOUND,
    CONF_FW_UPGRADE_PATH,
    CONF_I2C_ADDRESS,
    CONF_I2C_BUS,
    CONF_UPS_DELAY,
    CONF_UPS_WAKEON_DELTA,
    DEFAULT_FW_UTILITY_NAME,
    DEFAULT_NAME,
    DEFAULT_NO_FIRMWARE_UPGRADE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UPS_DELAY,
    DEFAULT_UPS_WAKEON_DELTA,
    DOMAIN,
    FW_PAGE_COUNT_LINE_PREFIX,
    FW_PROCESSED_PAGE_LINE_PREFIX,
    FW_PROGRESS_INTERVAL,
)
from .sensor import PiJups

_LOGGER = logging.getLogger(__name__)


class PiJuConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """PiJuPS HAT configuration flow flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return PiJuOptionsFlowHandler(config_entry)

    def __init__(self):
        """Set initial values for PiJuConfigFlow."""
        self._bus_options = None
        self._address_options = None
        self.hass = core.async_get_hass()

    async def async_step_user(self, user_input: dict[str, Any] = None) -> FlowResult:
        """Run configuration step with i2c bus/address pair that may match Pijuice HAT device.

        HAT is automatically configured in case in single pair found. Configuration might be aborted if
        no HAT found or it is already used by another instance of integration.
        """
        _LOGGER.debug("async_step_user user_input=%s", user_input)
        if self._bus_options is None or self._address_options is None:
            configuration_options = PiJups.find_piju_bus_addr(self.hass)
            self._bus_options = configuration_options.get(CONF_BUS_OPTIONS, [])
            self._address_options = configuration_options.get(CONF_ADDRESS_OPTIONS, [])
        if len(self._bus_options) <= 0 or len(self._address_options) <= 0:
            return self.async_abort(reason=CONF_FLOW_NO_DEVICE_FOUND)

        if len(self._bus_options) == 1 and len(self._address_options) == 1:
            user_input = {
                CONF_I2C_BUS: self._bus_options[0],
                CONF_I2C_ADDRESS: self._address_options[0],
            }

        errors = {}

        if user_input is not None:
            unique_id = (
                f"i2c{user_input[CONF_I2C_BUS]}x{user_input[CONF_I2C_ADDRESS]:02x}"
            )
            await self.async_set_unique_id(unique_id)
            try:
                self._abort_if_unique_id_configured()
            except data_entry_flow.AbortFlow:
                return self.async_abort(reason=CONF_FLOW_DEVICE_RESERVED)
            return self.async_create_entry(
                title=DEFAULT_NAME,
                data=user_input,
                options={
                    CONF_UPS_DELAY: DEFAULT_UPS_DELAY,
                    CONF_UPS_WAKEON_DELTA: DEFAULT_UPS_WAKEON_DELTA,
                    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                },
            )

        device_configuration = self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_I2C_BUS, default=self._bus_options[0]): vol.In(
                        self._bus_options
                    ),
                    vol.Required(
                        CONF_I2C_ADDRESS, default=self._address_options[0]
                    ): vol.In(self._address_options),
                }
            ),
            errors=errors,
        )
        return device_configuration


class PiJuOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle PiJu HAT options configuration."""

    def __init__(self, config_entry):
        """Initialize PiJu options flow."""
        self.config_entry = config_entry
        self.init_input = None
        self.hass = core.async_get_hass()
        self.pijups: PiJups = self.hass.data[DOMAIN][config_entry.entry_id][BASE]
        self.fw_task = None
        self.default_options = None
        self.default_logging = None
        self.fw_options = None
        self.fw_page_count = None
        self.fw_processed_pages = None
        self.fw_progress_action = None
        self.fw_progress = threading.Event()

        self.fw_update_time = None

    @staticmethod
    def create_schema_from_defaults(schema, defaults):
        """Create flow schema from HAT device configuration received from h/w is a form of array of values/default/handlers dictionaries."""
        for name, default in defaults.items():
            if default.get("type") == "multi":
                schema_element = {
                    vol.Required(
                        name,
                        default=default.get("default"),
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=default.get("values"),
                            multiple=True,
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key=default.get("key"),
                        )
                    )
                }
            else:
                if default.get("key") is not None:
                    schema_element = {
                        vol.Required(
                            name,
                            default=default.get("default"),
                        ): SelectSelector(
                            SelectSelectorConfig(
                                options=default.get("values"),
                                mode=SelectSelectorMode.DROPDOWN,
                                translation_key=default.get("key"),
                            )
                        ),
                    }
                else:
                    schema_element = {
                        vol.Required(
                            name,
                            default=default.get("default"),
                        ): SelectSelector(
                            SelectSelectorConfig(
                                options=default.get("values"),
                                mode=SelectSelectorMode.DROPDOWN,
                            )
                        ),
                    }
            schema = {**schema, **schema_element}
        return schema

    @staticmethod
    def set_device_to_selections(defaults, user_input):
        """Configure HAT device as per required settings based on array of values/default/handlers dictionaries."""
        for name, default in defaults.items():
            requested_value = user_input.get(name, default.get("default"))
            if requested_value != default.get("default"):
                setter = default.get("setter")
                if setter is not None:
                    wrapper = default.get("wrapper")
                    if wrapper is not None:
                        wrapper(
                            setter,
                            requested_value,
                            error_log_level=logging.DEBUG,
                        )
                    else:
                        setter(requested_value)

    async def async_step_init(self, user_input: dict[str, Any] = None) -> FlowResult:
        """Handle 1st step of PiJu HAT options configuration."""
        _LOGGER.debug("async_step_init user_input=%s", user_input)
        if self.default_options is None:
            self.default_options = await self.hass.async_add_executor_job(
                self.pijups.get_piju_defaults, self.hass, self.config_entry
            )
        if self.default_logging is None:
            self.default_logging = await self.hass.async_add_executor_job(
                self.pijups.get_piju_logging_defaults, self.hass, self.config_entry
            )
        if self.fw_options is None:
            self.fw_options = await self.hass.async_add_executor_job(
                self.pijups.get_fw_file_list, self.hass, self.config_entry
            )

        errors = {}

        if user_input is not None:
            self.init_input = user_input
            # execute requested changes
            for defaults in (
                self.default_options,
                self.default_logging,
                self.fw_options,
            ):
                await self.hass.async_add_executor_job(
                    PiJuOptionsFlowHandler.set_device_to_selections,
                    defaults,
                    user_input,
                )

            if (
                len(self.fw_options[CONF_FIRMWARE_SELECTION]["values"]) <= 1
                or user_input.get(CONF_FIRMWARE_SELECTION)
                == DEFAULT_NO_FIRMWARE_UPGRADE
            ):
                return self.async_create_entry(title=DEFAULT_NAME, data=self.init_input)
            await asyncio.sleep(0.2)
            return await self.async_step_firmware_confirm()

        device_options_schema = {}
        for defaults in (
            self.default_options,
            self.default_logging,
        ):
            device_options_schema = PiJuOptionsFlowHandler.create_schema_from_defaults(
                device_options_schema, defaults
            )

        restart_option_schema = {
            vol.Required(
                CONF_UPS_DELAY,
                default=self.config_entry.options.get(
                    CONF_UPS_DELAY, DEFAULT_UPS_DELAY
                ),
            ): vol.All(int, vol.Range(min=1, max=254)),
            vol.Required(
                CONF_UPS_WAKEON_DELTA,
                default=self.config_entry.options.get(
                    CONF_UPS_WAKEON_DELTA, DEFAULT_UPS_WAKEON_DELTA
                ),
            ): vol.All(int, vol.Range(min=-1, max=254)),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                ),
            ): vol.All(int, vol.Range(min=5)),
        }
        options_schema = {**device_options_schema, **restart_option_schema}
        if len(self.fw_options[CONF_FIRMWARE_SELECTION]["values"]) > 1:
            options_schema = PiJuOptionsFlowHandler.create_schema_from_defaults(
                options_schema, self.fw_options
            )

        return_form = self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(options_schema),
            errors=errors,
        )
        return return_form

    async def async_step_firmware_confirm(
        self, user_input: dict[str, Any] = None
    ) -> FlowResult:
        """Validate the user input allows us to connect."""
        _LOGGER.warning("async_step_firmware_confirm user_input=%s", user_input)
        errors = {}
        if user_input is not None:
            self.fw_task = None
            self.fw_progress.clear()
            self.fw_task = self.hass.async_create_task(self.async_background_status())
            await asyncio.sleep(0.2)
            self.fw_progress.wait()
            self.fw_progress.clear()
            return await self.async_step_firmware_progress()
        return self.async_show_form(
            step_id="firmware_confirm",
            data_schema=vol.Schema({}),
            errors=errors,
        )

    async def async_step_firmware_progress(
        self, user_input: dict[str, Any] = None
    ) -> FlowResult:
        """Validate the user input allows us to connect."""
        _LOGGER.warning(
            "async_step_firmware_progress user_input=%s, pages %s, done %s",
            user_input,
            self.fw_page_count,
            self.fw_processed_pages,
        )
        if not self.fw_task.done():
            self.fw_progress.wait()
            self.fw_progress.clear()
            return self.async_show_progress(
                step_id="firmware_progress",
                progress_action=self.fw_progress_action,
                progress_task=self.fw_task,
            )

        ret_data = self.async_show_progress_done(next_step_id="firmware_finish")
        return ret_data

    async def async_background_status(self):
        """FW upgrade utlity execution monitor."""
        self.fw_progress.set()
        _LOGGER.debug("async_background_status started")
        self.pijups.piju_enabled = False  # disable requests to device
        fw_path_info = await self.hass.async_add_executor_job(
            self.pijups.get_fw_directory, self.hass, self.config_entry
        )
        fw_path = fw_path_info[CONF_FW_UPGRADE_PATH]["default"]
        fw_upgrade_process = subprocess.Popen(
            [
                fw_path + "/" + DEFAULT_FW_UTILITY_NAME,
                f"{self.pijups.i2c_address:02x}",
                fw_path + "/" + self.init_input[CONF_FIRMWARE_SELECTION],
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        #self.fw_task = fw_upgrade_process
        try:
            with fw_upgrade_process.stdout as pipe:
                for line in iter(pipe.readline, b""):
                    progress = line.decode()[:-1]
                    _LOGGER.debug("%s -> %s", DEFAULT_FW_UTILITY_NAME, progress)
                    if progress.startswith(FW_PAGE_COUNT_LINE_PREFIX):
                        self.fw_page_count = int(
                            progress[len(FW_PAGE_COUNT_LINE_PREFIX) :]
                        )
                        self.fw_update_time = time.time() - FW_PROGRESS_INTERVAL
                    if progress.startswith(FW_PROCESSED_PAGE_LINE_PREFIX):
                        self.fw_processed_pages = int(
                            progress[
                                len(FW_PROCESSED_PAGE_LINE_PREFIX) : progress.index(
                                    " ", len(FW_PROCESSED_PAGE_LINE_PREFIX)
                                )
                            ]
                        )
                    if self.fw_page_count is not None and self.fw_processed_pages is not None:
                        progress_action = f"fw_p_{int((self.fw_page_count - self.fw_processed_pages) * 10 / self.fw_page_count)}"
                    else:
                        progress_action = "fw_started"
                    if self.fw_progress_action != progress_action:
                        self.fw_progress_action = progress_action
                        self.fw_progress.set()
        finally:
            self.pijups.piju_enabled = True  # enable requests to device
            self.fw_progress.set()
            pass

    async def async_step_firmware_finish(
        self, user_input: dict[str, Any] = None
    ) -> FlowResult:
        """Validate the user input allows us to connect."""
        _LOGGER.debug("async_step_firmware_finish entry user_input %s", user_input)
        errors = {}
        if user_input is None:
            ret_val = self.async_show_form(
                step_id="firmware_finish",
                data_schema=vol.Schema({}),
                last_step=True,
                errors=errors,
            )
            self.fw_processed_pages = None
        else:
            ret_val = self.async_create_entry(title=DEFAULT_NAME, data=self.init_input)
        return ret_val


class AlreadyConfigured(exceptions.HomeAssistantError):
    """Error to indicate device is already configured."""
