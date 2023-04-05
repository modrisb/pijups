# PiJups - Home Assistant PiJuice Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs) (https://github.com/modrisb/pijups/releases)


PiJups exposes [PiJuice](https://github.com/PiSupply/PiJuice) sensor values in [Home Assistant](https://home-assistant.io) and allows to use this HAT in HA automations to handle battery low cases and other.

## Sensors supported
* Battery status
* Power input status
* Power input I/O status
* Charge in %
* Temperature (native format)
* Battery voltage
* Battery current
* I/O voltage
* I/O current
* External Power

## Prerequisite
Enable I2C bus on the host system, like described in : https://www.home-assistant.io/common-tasks/os/#enable-i2c<br>

## Manual installation 
1. Inside the `custom_components` directory, create a new folder called `pijups`.
2. Download all files from the `custom_components/pijuice/` repository to this directory `custom_components/pijups`.
3. Install integration from Home Assistant Settings/Devices & Services/Add Integration. HAT should be detected automatically within ~ 20s.

HACS might be used for installation too - check repository 'PiJuice Hat'.

## Configuration
Parameters for hardware configuration, default values reflect current HAT's settings: 
1. Battery temperature sense source selection - impacts HAT temperature sensor.
2. Battery battery profile. This impacts HAT funstionaly - battery charge options, by default set to smallest by capacity battery.

Parameters for HAT circular log configuration - select events to store in log. Default selections corresponf to HAT's current settings.

Parameters to control integration behaviour on shutdown/restart and sensor polling rate: 
1. Power Off Delay, specifies time HAT will delay switch off power, this gives time to HA to perform software shutdown actions. Default - 120s might be too much for most cases, need to measure time needed. Noticed ~ 1 minute run time uses ~ 1% of battery charge, but this may vary per hardware.
2. Wake On Delta specifies HAT action after power is resumed. -1 forces reboot right after power is resumed, any positive value is added to charge % and reboot should happen when battery reaches this level after power resume. Idea to always have capacity to do shutdown without data loss.
3. Sensor refresh interval in seconds. This time period applies to Battery status, Power input status, Power input I/O status and External Power, others are updated every 6th cycle. Integration need to be reloaded to start using new scan interval value, HA restart works too.


## Example automation
Automation example below is triggered by battery status change and in case of no external power and battery capacity below specified limit initiates HA shutdown and then HAT switch off:
```
alias: UPS
description: ""
trigger:
  - platform: state
    entity_id:
      - sensor.pijups_charge
condition:
  - condition: and
    conditions:
      - condition: state
        entity_id: sensor.pijups_power_input_io_status
        state: NOT_PRESENT
      - condition: state
        entity_id: sensor.ppijups_power_input_status
        state: NOT_PRESENT
      - condition: numeric_state
        entity_id: sensor.pijups_charge
        below: 25
action:
  - delay:
      hours: 0
      minutes: 0
      seconds: 10
      milliseconds: 0
  - service: hassio.host_shutdown
    data: {}
mode: single
```

## Credits
[PiJuice](https://pi-supply.com/) : PiJuice Pi supply hardware/software platform to support Raspberry Pi, Arduino. PiJups uses PiJuice API with very little changes, see published pull request on github<br>
[Home Assistant](https://github.com/home-assistant) : Home Assistant open-source powerful domotic plateform.<br>
[HACS](https://hacs.xyz/) : Home Assistant Community Store gives you a powerful UI to handle downloads of all your custom needs.<br>
[smbus2 library](https://pypi.org/project/smbus2) : PyPI library for I2C access
