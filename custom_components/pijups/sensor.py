"""The PiJuPS HAT integration - sensor platform implementation."""

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.hassio import (
    DOMAIN as HASSIO_DOMAIN,
    SERVICE_HOST_SHUTDOWN,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_DOMAIN,
    ATTR_SERVICE,
    EVENT_CALL_SERVICE,
    EVENT_HOMEASSISTANT_STOP,
    PERCENTAGE,
    RESTART_EXIT_CODE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfTemperature,
)
from homeassistant.components.homeassistant.const import (
    SERVICE_HOMEASSISTANT_RESTART,
)

from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN, Event, HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BASE,
    CONF_UPS_DELAY,
    CONF_UPS_WAKEON_DELTA,
    DEFAULT_FAST_SCAN_COUNT,
    DEFAULT_SLOW_SCAN_COUNT,
    DOMAIN,
    PIJU_SENSOR_BATTERY_CURRENT,
    PIJU_SENSOR_BATTERY_STATUS,
    PIJU_SENSOR_BATTERY_VOLTAGE,
    PIJU_SENSOR_CHARGE,
    PIJU_SENSOR_EXTERNAL_POWER,
    PIJU_SENSOR_IO_CURRENT,
    PIJU_SENSOR_IO_VOLTAGE,
    PIJU_SENSOR_POWER_INPUT_IO_STATUS,
    PIJU_SENSOR_POWER_INPUT_STATUS,
    PIJU_SENSOR_TEMPERATURE,
    SENSOR_ENTITY,
)
from .interface import PiJups, bat_status_enum, power_in_status_enum
from .pijuice import PiJuiceStatus

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = None  # value set in __init__.py async_setup_entry

BATTERY_STATUS_ICON_DICT = dict(
    zip(
        bat_status_enum,
        [
            "mdi:battery",
            "mdi:battery-charging",
            "mdi:battery-charging",
            "mdi:battery-off",
        ],
    )
)

POWER_IN_STATUS_ICON_DICT = dict(
    zip(
        power_in_status_enum,
        [
            "mdi:power-plug-off-outline",
            "mdi:power-plug-outline",
            "mdi:power-plug-outline",
            "mdi:power-plug",
        ],
    )
)

EXTERNAL_POWER_STATUS_ICON_DICT = dict(
    zip(
        [False, True],
        [
            "mdi:power-plug-off-outline",
            "mdi:power-plug",
        ],
    )
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create set-up interface to UPS and add sensors for passed config_entry in HA."""
    pijups: PiJups = hass.data[DOMAIN][config_entry.entry_id][BASE]
    await hass.async_add_executor_job(
        pijups.set_up_ups
    )  # setup RTC, clean faults and button events
    sensors = []
    for sensor in PiJuiceSensor.SENSOR_LIST:
        entity = PiJuiceSensor(hass, config_entry, sensor)
        sensors.append(entity)
    hass.data[DOMAIN][config_entry.entry_id][SENSOR_ENTITY] = sensors
    async_add_entities(sensors, True)
    _LOGGER.debug("async_setup_entry %s sensors added", len(sensors))

    # flag array to track callback event types and decide if shutdown sequence execution is needed
    services_noticed = [False, False]

    async def check_service_calls(event: Event) -> None:
        """Collect shutdown/re-start source information."""
        if (event.data.get(ATTR_DOMAIN) == HASSIO_DOMAIN) and (
            event.data.get(ATTR_SERVICE) == SERVICE_HOST_SHUTDOWN
        ):
            services_noticed[
                0
            ] = True  # explicit shutdown request via service (shutdown automation)
        if (event.data.get(ATTR_DOMAIN) == HOMEASSISTANT_DOMAIN) and (
            event.data.get(ATTR_SERVICE) == SERVICE_HOMEASSISTANT_RESTART
        ):
            services_noticed[1] = True  # GUI sourced re-start/re-boot requested
        _LOGGER.debug("check_service_calls exited--> %s %s", event, services_noticed)

    hass.bus.async_listen(EVENT_CALL_SERVICE, check_service_calls)

    async def process_ups_event(event: Event) -> None:
        """Process shutdown request."""
        _LOGGER.debug("homeassistant stop event received: %s", event)
        _LOGGER.debug(
            "UPS event status for %s:%s and %s:%s  %s, powered:%s, HASS return code:%s",
            HASSIO_DOMAIN,
            SERVICE_HOST_SHUTDOWN,
            HOMEASSISTANT_DOMAIN,
            SERVICE_HOMEASSISTANT_RESTART,
            services_noticed,
            pijups.powered,
            hass.exit_code,
        )

        delta = config_entry.options.get(CONF_UPS_WAKEON_DELTA)
        delay = config_entry.options.get(CONF_UPS_DELAY)

        power_off_needed = (
            (services_noticed[0] or not services_noticed[1])
            and not pijups.powered
            and pijups.piju_enabled
            and hass.exit_code != RESTART_EXIT_CODE
        )
        await hass.async_add_executor_job(
            pijups.process_power_off, delta, delay, power_off_needed
        )
        _LOGGER.debug("homeassistant stop event processing completed")

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, process_ups_event)
    await hass.async_add_executor_job(
        pijups.set_led_ha_active
    )  # set LED to indicate HA is running - set-up completed
    _LOGGER.debug("sensor SCAN_INTERVAL %s", SCAN_INTERVAL)
    _LOGGER.info(
        "PiJuice set-up completed for /dev/i2c-%d @ 0x%x. Versions: firmware %s, software %s",
        pijups.i2c_bus,
        pijups.i2c_address,
        pijups.fw_version,
        hass.data["integrations"][DOMAIN].version,
    )


@dataclass
class PiJuiceSensorEntityDescription(SensorEntityDescription):
    """A class that describes extra details for PiJuiceUPS sensor entities in addition to SensorEntityDescription."""

    icon_callback: Any = None  # routine to get icon depending on sensor status
    value_callback: Any = None  # routine to get sensor native value
    update_frequency: int = None  # frquencey rate to update sensor value (1 - on each update, 2 - every 2nd time,...)


class PiJuiceSensor(SensorEntity):
    """Implementation of PiJuiceUPS sensor."""

    # sensor icon selection routines
    def get_battery_status_icon(self):
        """PiJuiceUPS."""
        return BATTERY_STATUS_ICON_DICT.get(self._attr_native_value, self._attr_icon)

    def get_power_icon(self):
        """PiJuiceUPS."""
        return POWER_IN_STATUS_ICON_DICT.get(self._attr_native_value, self._attr_icon)

    def get_charge_icon(self):
        """PiJuiceUPS."""
        if self._attr_native_value > 90:
            return "mdi:battery"
        if self._attr_native_value > 70:
            return "mdi:battery-80"
        if self._attr_native_value > 50:
            return "mdi:battery-60"
        if self._attr_native_value > 30:
            return "mdi:battery-40"
        return "mdi:battery-20"

    def get_external_power_icon(self):
        """PiJuiceUPS."""
        return EXTERNAL_POWER_STATUS_ICON_DICT.get(
            self._attr_native_value, self._attr_icon
        )

    def get_static_icon(self):
        """PiJuiceUPS."""
        return self._attr_icon

    # sensor data conversion routines
    def get_battery_status(self):
        """Pi JuiceUPS ."""
        status = self._pijups.get_piju_status()
        if status is not None:
            self._attr_native_value = status.get("battery")

    def get_power_status(self):
        """PiJuiceUPS."""
        status = self._pijups.get_piju_status()
        if status is not None:
            self._attr_native_value = status.get("powerInput")

    def get_power_io_status(self):
        """PiJuiceUPS."""
        status = self._pijups.get_piju_status()
        if status is not None:
            self._attr_native_value = status.get("powerInput5vIo")

    def get_charge(self):
        """PiJuiceUPS."""
        charge = self._pijups.call_pijuice_with_error_check(
            self._pijups.status.GetChargeLevel
        )
        if charge is not None:
            self._attr_native_value = charge

    def get_temp(self):
        """PiJuiceUPS."""
        temperature = self._pijups.call_pijuice_with_error_check(
            self._pijups.status.GetBatteryTemperature
        )
        if temperature is not None:
            self._attr_native_value = temperature

    def get_battery_voltage(self):
        """Pi JuiceUPS ."""
        voltage = self._pijups.call_pijuice_with_error_check(
            self._pijups.status.GetBatteryVoltage
        )
        if voltage is not None:
            self._attr_native_value = voltage

    def get_io_voltage(self):
        """PiJuiceUPS."""
        voltage = self._pijups.call_pijuice_with_error_check(
            self._pijups.status.GetIoVoltage
        )
        if voltage is not None:
            self._attr_native_value = voltage

    def get_battery_current(self):
        """Pi JuiceUPS - get battery current value."""
        current = self._pijups.call_pijuice_with_error_check(
            self._pijups.status.GetBatteryCurrent
        )
        if current is not None:
            self._attr_native_value = current

    def get_io_current(self):
        """Pi JuiceUPS - get io current sensor value."""
        current = self._pijups.call_pijuice_with_error_check(
            self._pijups.status.GetIoCurrent
        )
        if current is not None:
            self._attr_native_value = current

    def get_external_power_status(self):
        """Pi JuiceUPS - get value for external power sensor."""
        status = self._pijups.get_piju_status()
        if status is not None:
            self._attr_native_value = self._pijups.powered

    SENSOR_LIST = [
        PiJuiceSensorEntityDescription(
            name=PIJU_SENSOR_BATTERY_STATUS,
            key="battery_status",
            device_class=SensorDeviceClass.ENUM,
            state_class=None,
            native_unit_of_measurement=None,
            icon="mdi:flash",
            icon_callback=get_battery_status_icon,
            value_callback=get_battery_status,
            update_frequency=DEFAULT_FAST_SCAN_COUNT,
            options=PiJuiceStatus.batStatusEnum,
            translation_key="battery_status",
        ),
        PiJuiceSensorEntityDescription(
            name=PIJU_SENSOR_TEMPERATURE,
            key="temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            icon="mdi:thermometer",
            icon_callback=get_static_icon,
            value_callback=get_temp,
            update_frequency=DEFAULT_SLOW_SCAN_COUNT,
        ),
        PiJuiceSensorEntityDescription(
            name=PIJU_SENSOR_POWER_INPUT_STATUS,
            key="power_input_status",
            device_class=SensorDeviceClass.ENUM,
            state_class=None,
            native_unit_of_measurement=None,
            icon="mdi:power-plug",
            icon_callback=get_power_icon,
            value_callback=get_power_status,
            update_frequency=DEFAULT_FAST_SCAN_COUNT,
            options=PiJuiceStatus.powerInStatusEnum,
            translation_key="power_input",
        ),
        PiJuiceSensorEntityDescription(
            name=PIJU_SENSOR_CHARGE,
            key="charge",
            device_class=SensorDeviceClass.BATTERY,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=PERCENTAGE,
            icon="mdi:battery",
            icon_callback=get_charge_icon,
            value_callback=get_charge,
            update_frequency=DEFAULT_SLOW_SCAN_COUNT,
        ),
        PiJuiceSensorEntityDescription(
            name=PIJU_SENSOR_BATTERY_VOLTAGE,
            key="battery_voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
            icon="mdi:flash",
            icon_callback=get_static_icon,
            value_callback=get_battery_voltage,
            update_frequency=DEFAULT_SLOW_SCAN_COUNT,
        ),
        PiJuiceSensorEntityDescription(
            name=PIJU_SENSOR_BATTERY_CURRENT,
            key="battery_current",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
            icon="mdi:current-dc",
            icon_callback=get_static_icon,
            value_callback=get_battery_current,
            update_frequency=DEFAULT_SLOW_SCAN_COUNT,
        ),
        PiJuiceSensorEntityDescription(
            name=PIJU_SENSOR_POWER_INPUT_IO_STATUS,
            key="power_input_io_status",
            device_class=SensorDeviceClass.ENUM,
            state_class=None,
            native_unit_of_measurement=None,
            icon="mdi:power-plug",
            icon_callback=get_power_icon,
            value_callback=get_power_io_status,
            update_frequency=DEFAULT_FAST_SCAN_COUNT,
            options=PiJuiceStatus.powerInStatusEnum,
            translation_key="power_input",
        ),
        PiJuiceSensorEntityDescription(
            name=PIJU_SENSOR_IO_VOLTAGE,
            key="io_voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
            icon="mdi:flash",
            icon_callback=get_static_icon,
            value_callback=get_io_voltage,
            update_frequency=DEFAULT_SLOW_SCAN_COUNT,
        ),
        PiJuiceSensorEntityDescription(
            name=PIJU_SENSOR_IO_CURRENT,
            key="io_current",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
            icon="mdi:current-dc",
            icon_callback=get_static_icon,
            value_callback=get_io_current,
            update_frequency=DEFAULT_SLOW_SCAN_COUNT,
        ),
        PiJuiceSensorEntityDescription(
            name=PIJU_SENSOR_EXTERNAL_POWER,
            key="external_power",
            device_class=SensorDeviceClass.ENUM,
            state_class=None,
            native_unit_of_measurement=None,
            icon="mdi:power-plug",
            icon_callback=get_external_power_icon,
            value_callback=get_external_power_status,
            update_frequency=DEFAULT_FAST_SCAN_COUNT,
            options=[True, False],
            translation_key="ext_power",
        ),
    ]

    def __init__(self, hass, config, sensor: PiJuiceSensorEntityDescription):
        """Initialize the sensor."""
        self.hass = hass
        self._pijups: PiJups = hass.data[DOMAIN][config.entry_id][BASE]
        self._config = config
        self.entity_description: PiJuiceSensorEntityDescription = sensor
        self._attr_state_class = sensor.state_class  # SensorEntity
        self._attr_native_unit_of_measurement = (
            sensor.native_unit_of_measurement
        )  # SensorEntity
        self._attr_unit_of_measurement = sensor.unit_of_measurement  # SensorEntity
        self._attr_name = self.entity_description.name
        self._attr_has_entity_name = True
        self._attr_icon = sensor.icon  # Entity
        self._attr_options = sensor.options  # Entity
        self._get_icon = sensor.icon_callback
        self._get_value = sensor.value_callback
        self._attr_native_value = None  # SensorEntity
        self._attr_max_rate = sensor.update_frequency
        self._attr_cur_rate = self._attr_max_rate - 1
        self._attr_device_info: DeviceInfo = self._pijups.piju_device_info  # Entity
        self._attr_unique_id = sensor.key

    @property
    def icon(self) -> str:  # Entity
        """Return the icon of the sensor."""
        icon_val = self._get_icon(self)
        return icon_val

    def update(self) -> None:
        """Set up the sensor."""
        self._attr_cur_rate = (self._attr_cur_rate + 1) % self._attr_max_rate
        if self._attr_cur_rate == 0 and self._pijups.piju_enabled:
            self._get_value(self)
