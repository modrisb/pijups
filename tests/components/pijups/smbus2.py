"""Implement PiJuice h/w behaviour via smbus2 SMBus class."""
import logging
import time

_LOGGER = logging.getLogger(__name__)

STATUS_CMD = 0x40
CHARGE_LEVEL_CMD = 0x41
FAULT_EVENT_CMD = 0x44
BUTTON_EVENT_CMD = 0x45
BATTERY_TEMPERATURE_CMD = 0x47
BATTERY_VOLTAGE_CMD = 0x49
BATTERY_CURRENT_CMD = 0x4B
IO_VOLTAGE_CMD = 0x4D
IO_CURRENT_CMD = 0x4F
I2C_ADDRESS_CMD = 0x7C
LOGGING_CMD = 0xF6  # 246

LOGGING_CONFIG = 0x42
LOGGING_TYPE = 0
LOGGING_TYPE_RESPONSE = [0] * 32
LOGGING_TYPE_RESPONSE[2] = 1
LOGGING_BUFFER_INDEX = 0
CMD_NSUPP_RESPONSE = [0, 255]


class SMBus:
    """Implement read_i2c_block_data, write_i2c_block_data functions for use with PiJuice API."""

    SIM_BUS = 1
    SIM_ADDR = 0x14
    INIT_ADJUSTMENTS = {}
    INIT_CMD_DELAYS = {}

    @staticmethod
    def add_init_adjustments(cmd, data):
        """Implement response changes in default bahaviour during connection open."""
        SMBus.INIT_ADJUSTMENTS[cmd] = data

    @staticmethod
    def add_init_cmd_delays(cmd, counter, time_out):
        SMBus.INIT_CMD_DELAYS[cmd] = [counter, time_out]

    def __init__(self, bus=1):
        """Create a new PiJuice instance.

        Bus is an optional parameter that
        specifies the I2C bus number to use, for example 1 would use device
        /dev/i2c-1.  If bus is not specified then the open function should be
        called to open the bus.
        """
        self.bus = bus
        self.addr = None
        self.write_log_on = False
        self.write_log = {}
        if isinstance(SMBus.SIM_BUS, int):
            supp_busses = (SMBus.SIM_BUS,)
        else:
            supp_busses = SMBus.SIM_BUS
        if self.bus not in supp_busses:
            raise BlockingIOError
        self.logging_config = None
        self.logging_type = None
        self.logging_type_response = None
        self.logging_buffer_index = None
        self.read_write_delay = 0
        self.err_sim = {}
        self.signal_error_next_read_call = False
        self.signal_error_next_write_call = False
        self.corrupt_next_read_call = False
        self.simulate_recoverable_chksum_issue = False
        self.simulate_data_curruption = False
        self.temp_read_cmd = 0
        self.temp_read_cmd_buff = None
        self.reset_device()

    def io_buffer_next_read_call(self, cmd, data):
        if data is not None:
            self.temp_read_cmd = cmd
            self.temp_read_cmd_buff = data.copy()

    def io_error_next_read_call(self):
        self.signal_error_next_read_call = True

    def corrupt_data_next_read_call(self):
        self.corrupt_next_read_call = True

    def io_error_next_write_call(self):
        self.signal_error_next_write_call = True

    def manage_chksum_calculations(self, simulation_on):
        self.simulate_recoverable_chksum_issue = simulation_on

    def manage_data_corruptions(self, simulation_on):
        self.simulate_data_curruption = simulation_on

    def add_cmd_delays(self, cmd, counter, time_out):
        self.err_sim[cmd] = [counter, time_out]
        #_LOGGER.info(f"add_cmd_delays {cmd:02x} {self.err_sim[cmd]}")

    def enable_delay(self, io_delay):
        """Enable delay in read/write responses."""
        self.read_write_delay = io_delay

    def set_write_log(self, log_status=False):
        """Enable write call tracking and returns recently captured call data."""
        self.write_log_on = log_status
        write_log = self.write_log
        self.write_log = {}
        return write_log

    def reset_device(self):
        """Reset data buffers to initial state and applies initial adjustments."""
        self.logging_config = LOGGING_CONFIG
        self.logging_type = LOGGING_TYPE
        self.logging_type_response = LOGGING_TYPE_RESPONSE.copy()
        self.logging_buffer_index = LOGGING_BUFFER_INDEX

        self.logging_type_response = [0] * 32
        self.logging_type_response[2] = 1
        self.logging_buffers = [
            [
                0,
                6,      # [ 1] WAKEUP_EVT
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] triggers
                200,    # [11] status
                9,      # [12] GPIO_5V REGULATOR
                240,    # [13] wkupOnChargeCfg
                0,      # [14] wkupOnChargeCfg
                194,    # [15] battery charge
                52,     # [16] temperature
                161,    # [17] batVolt
                15,     # [18] batVolt
                64,     # [19] gpio5V
                20,     # [20] gpio5V
                124,    # [21] curr5Vgpio
                1,      # [22] curr5Vgpio
                0,      # [23]
                0,      # [24]
                0,      # [25]
                0,      # [26]
                0,      # [27]
                0,      # [28]
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                10,
                6,      # [ 1] WAKEUP_EVT
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] triggers
                200,    # [11] status
                9,      # [12] GPIO_5V REGULATOR
                240,    # [13] wkupOnChargeCfg
                0,      # [14] wkupOnChargeCfg
                194,    # [15] battery charge
                52,     # [16] temperature
                161,    # [17] batVolt
                15,     # [18] batVolt
                64,     # [19] gpio5V
                20,     # [20] gpio5V
                0x84,   # [21] curr5Vgpio - negative current
                0xfe,   # [22] curr5Vgpio
                0,      # [23]
                0,      # [24]
                0,      # [25]
                0,      # [26]
                0,      # [27]
                0,      # [28]
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                20,
                6,      # [ 1] WAKEUP_EVT
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                0x13,   # [ 7] GetDateTime buf[5] month wrong month to rise exception
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] triggers
                200,    # [11] status
                9,      # [12] GPIO_5V REGULATOR
                240,    # [13] wkupOnChargeCfg
                0,      # [14] wkupOnChargeCfg
                194,    # [15] battery charge
                52,     # [16] temperature
                161,    # [17] batVolt
                15,     # [18] batVolt
                64,     # [19] gpio5V
                20,     # [20] gpio5V
                124,    # [21] curr5Vgpio
                1,      # [22] curr5Vgpio
                0,      # [23]
                0,      # [24]
                0,      # [25]
                0,      # [26]
                0,      # [27]
                0,      # [28]
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                30,
                6,      # [ 1] WAKEUP_EVT
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                0x42,   # [ 4] GetDateTime buf[2] hour and flags: 2AM
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] triggers
                200,    # [11] status
                9,      # [12] GPIO_5V REGULATOR
                240,    # [13] wkupOnChargeCfg
                0,      # [14] wkupOnChargeCfg
                194,    # [15] battery charge
                52,     # [16] temperature
                161,    # [17] batVolt
                15,     # [18] batVolt
                64,     # [19] gpio5V
                20,     # [20] gpio5V
                124,    # [21] curr5Vgpio
                1,      # [22] curr5Vgpio
                0,      # [23]
                0,      # [24]
                0,      # [25]
                0,      # [26]
                0,      # [27]
                0,      # [28]
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                1,
                4,      # 5VREG_ON
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] NO ENOUGHR POWER flag 0x01
                200,    # [11] battery
                9,      # [12] battery
                240,    # [13] battery
                0,      # [14] battery
                194,    # [15] battery
                52,     # [16] battery
                161,    # [17] battery
                15,     # [18] battery
                64,     # [19] battery
                20,     # [20] battery
                124,    # [21] reg5v
                1,      # [22] reg5v
                0,      # [23] reg5v
                0,      # [24] reg5v
                0,      # [25] reg5v
                0,      # [26] reg5v
                0,      # [27] reg5v
                0,      # [28] reg5v
                0,      # [29] reg5v
                0,      # [30] reg5v
                115,    # [31]
            ],
            [
                2,
                5,      # 5VREG_OFF
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] triggers
                200,    # [11] SoC %
                9,      # [12] SoC C
                240,    # [13] curr5Vgpio
                0,      # [14] gpio5V
                194,    # [15] batSignal
                52,     # [16] batSignal
                161,    # [17] batSignal
                15,     # [18] batSignal
                64,     # [19] batSignal
                20,     # [20] batSignal
                124,    # [21] batSignal
                1,      # [22] batSignal
                0,      # [23] curr5vSignal
                0,      # [24] curr5vSignal
                0,      # [25] curr5vSignal
                0,      # [26] curr5vSignal
                0,      # [27] curr5vSignal
                0,      # [28] curr5vSignal
                0,      # [29] curr5vSignal
                0,      # [30] curr5vSignal
                115,    # [31]
            ],
            [
                3,
                7,      # ALARM_EVT
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] GetAlarmStatus buf[0] wakeup_enabled if 0x01) and 0x04 on
                200,    # [11] GetAlarmStatus buf[1] alarm_flag if 0x01
                0,      # [12]
                240,    # [13] status
                0,      # [14] battery charge
                194,    # [15] temperature
                52,     # [16] batVolt
                161,    # [17] batVolt
                0,      # [18]
                0,      # [19]
                20,     # [20] GetAlarm buf[0] second
                0x52,   # [21] GetAlarm buf[1] minute
                1,      # [22] GetAlarm buf[2] hour and flags: 0x40 12hours format
                0,      # [23] GetAlarm buf[3] weekday and flags
                0,      # [24] GetAlarm buf[4] hours mask1
                0,      # [25] GetAlarm buf[5] hours mask2
                0,      # [26] GetAlarm buf[6] hours mask3
                0,      # [27] GetAlarm buf[7] minute_period
                0,      # [28] GetAlarm buf[8] 0xFF to indicate EVERY_DAY or day mask
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                23,
                7,      # ALARM_EVT
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                0x05,   # [10] GetAlarmStatus buf[0] wakeup_enabled if 0x01 and 0x04 on
                0x01,   # [11] GetAlarmStatus buf[1] alarm_flag if 0x01
                0,      # [12]
                240,    # [13] status
                0,      # [14] battery charge
                194,    # [15] temperature
                52,     # [16] batVolt
                161,    # [17] batVolt
                0,      # [18]
                0,      # [19]
                20,     # [20] GetAlarm buf[0] second
                0x52,   # [21] GetAlarm buf[1] minute
                1,      # [22] GetAlarm buf[2] hour and flags: 0x40 12hours format
                0,      # [23] GetAlarm buf[3] weekday and flags
                0,      # [24] GetAlarm buf[4] hours mask1
                0,      # [25] GetAlarm buf[5] hours mask2
                0,      # [26] GetAlarm buf[6] hours mask3
                0,      # [27] GetAlarm buf[7] minute_period
                0,      # [28] GetAlarm buf[8] 0xFF to indicate EVERY_DAY or day mask
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                33,
                7,      # ALARM_EVT
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] GetAlarmStatus buf[0] wakeup_enabled if 0x01) and 0x04 on
                200,    # [11] GetAlarmStatus buf[1] alarm_flag if 0x01
                0,      # [12]
                240,    # [13] status
                0,      # [14] battery charge
                194,    # [15] temperature
                52,     # [16] batVolt
                161,    # [17] batVolt
                0,      # [18]
                0,      # [19]
                0x80,   # [20] GetAlarm buf[0] second
                0x52,   # [21] GetAlarm buf[1] minute
                1,      # [22] GetAlarm buf[2] hour and flags: 0x40 12hours format
                0,      # [23] GetAlarm buf[3] weekday and flags
                0,      # [24] GetAlarm buf[4] hours mask1
                0,      # [25] GetAlarm buf[5] hours mask2
                0,      # [26] GetAlarm buf[6] hours mask3
                0,      # [27] GetAlarm buf[7] minute_period
                0,      # [28] GetAlarm buf[8] 0xFF to indicate EVERY_DAY or day mask
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                43,
                7,      # ALARM_EVT
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] GetAlarmStatus buf[0] wakeup_enabled if 0x01) and 0x04 on
                200,    # [11] GetAlarmStatus buf[1] alarm_flag if 0x01
                0,      # [12]
                240,    # [13] status
                0,      # [14] battery charge
                194,    # [15] temperature
                52,     # [16] batVolt
                161,    # [17] batVolt
                0,      # [18]
                0,      # [19]
                0x80,   # [20] GetAlarm buf[0] second
                0x80,   # [21] GetAlarm buf[1] minute
                1,      # [22] GetAlarm buf[2] hour and flags: 0x40 12hours format
                0,      # [23] GetAlarm buf[3] weekday and flags
                0,      # [24] GetAlarm buf[4] hours mask1
                0,      # [25] GetAlarm buf[5] hours mask2
                0,      # [26] GetAlarm buf[6] hours mask3
                0x0a,   # [27] GetAlarm buf[7] minute_period
                0,      # [28] GetAlarm buf[8] 0xFF to indicate EVERY_DAY or day mask
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                53,
                7,      # ALARM_EVT
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] GetAlarmStatus buf[0] wakeup_enabled if 0x01) and 0x04 on
                200,    # [11] GetAlarmStatus buf[1] alarm_flag if 0x01
                0,      # [12]
                240,    # [13] status
                0,      # [14] battery charge
                194,    # [15] temperature
                52,     # [16] batVolt
                161,    # [17] batVolt
                0,      # [18]
                0,      # [19]
                20,     # [20] GetAlarm buf[0] second
                0x52,   # [21] GetAlarm buf[1] minute
                0x40,   # [22] GetAlarm buf[2] hour and flags: 0x40 12hours format
                0,      # [23] GetAlarm buf[3] weekday and flags
                0,      # [24] GetAlarm buf[4] hours mask1
                0,      # [25] GetAlarm buf[5] hours mask2
                0,      # [26] GetAlarm buf[6] hours mask3
                0,      # [27] GetAlarm buf[7] minute_period
                0,      # [28] GetAlarm buf[8] 0xFF to indicate EVERY_DAY or day mask
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                63,
                7,      # ALARM_EVT
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] GetAlarmStatus buf[0] wakeup_enabled if 0x01) and 0x04 on
                200,    # [11] GetAlarmStatus buf[1] alarm_flag if 0x01
                0,      # [12]
                240,    # [13] status
                0,      # [14] battery charge
                194,    # [15] temperature
                52,     # [16] batVolt
                161,    # [17] batVolt
                0,      # [18]
                0,      # [19]
                20,     # [20] GetAlarm buf[0] second
                0x52,   # [21] GetAlarm buf[1] minute
                0x80,   # [22] GetAlarm buf[2] hour and flags: 0x40 12hours format
                0,      # [23] GetAlarm buf[3] weekday and flags
                0,      # [24] GetAlarm buf[4] hours mask1
                0,      # [25] GetAlarm buf[5] hours mask2
                0,      # [26] GetAlarm buf[6] hours mask3
                0,      # [27] GetAlarm buf[7] minute_period
                0,      # [28] GetAlarm buf[8] 0xFF to indicate EVERY_DAY or day mask
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                73,
                7,      # ALARM_EVT
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] GetAlarmStatus buf[0] wakeup_enabled if 0x01) and 0x04 on
                200,    # [11] GetAlarmStatus buf[1] alarm_flag if 0x01
                0,      # [12]
                240,    # [13] status
                0,      # [14] battery charge
                194,    # [15] temperature
                52,     # [16] batVolt
                161,    # [17] batVolt
                0,      # [18]
                0,      # [19]
                20,     # [20] GetAlarm buf[0] second
                0x52,   # [21] GetAlarm buf[1] minute
                0x80,   # [22] GetAlarm buf[2] hour and flags: 0x40 12hours format
                0,      # [23] GetAlarm buf[3] weekday and flags
                0xff,   # [24] GetAlarm buf[4] hours mask1
                0xff,   # [25] GetAlarm buf[5] hours mask2
                0xff,   # [26] GetAlarm buf[6] hours mask3
                0,      # [27] GetAlarm buf[7] minute_period
                0,      # [28] GetAlarm buf[8] 0xFF to indicate EVERY_DAY or day mask
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                83,
                7,      # ALARM_EVT
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] GetAlarmStatus buf[0] wakeup_enabled if 0x01) and 0x04 on
                200,    # [11] GetAlarmStatus buf[1] alarm_flag if 0x01
                0,      # [12]
                240,    # [13] status
                0,      # [14] battery charge
                194,    # [15] temperature
                52,     # [16] batVolt
                161,    # [17] batVolt
                0,      # [18]
                0,      # [19]
                20,     # [20] GetAlarm buf[0] second
                0x52,   # [21] GetAlarm buf[1] minute
                0,      # [22] GetAlarm buf[2] hour and flags: 0x40 12hours format
                0x40,   # [23] GetAlarm buf[3] weekday and flags
                0,      # [24] GetAlarm buf[4] hours mask1
                0,      # [25] GetAlarm buf[5] hours mask2
                0,      # [26] GetAlarm buf[6] hours mask3
                0,      # [27] GetAlarm buf[7] minute_period
                0,      # [28] GetAlarm buf[8] 0xFF to indicate EVERY_DAY or day mask
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                93,
                7,      # ALARM_EVT
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] GetAlarmStatus buf[0] wakeup_enabled if 0x01) and 0x04 on
                200,    # [11] GetAlarmStatus buf[1] alarm_flag if 0x01
                0,      # [12]
                240,    # [13] status
                0,      # [14] battery charge
                194,    # [15] temperature
                52,     # [16] batVolt
                161,    # [17] batVolt
                0,      # [18]
                0,      # [19]
                20,     # [20] GetAlarm buf[0] second
                0x52,   # [21] GetAlarm buf[1] minute
                0,      # [22] GetAlarm buf[2] hour and flags: 0x40 12hours format
                0x80,   # [23] GetAlarm buf[3] weekday and flags
                0,      # [24] GetAlarm buf[4] hours mask1
                0,      # [25] GetAlarm buf[5] hours mask2
                0,      # [26] GetAlarm buf[6] hours mask3
                0,      # [27] GetAlarm buf[7] minute_period
                0x02,   # [28] GetAlarm buf[8] 0xFF to indicate EVERY_DAY or day mask
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                103,
                7,      # ALARM_EVT
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] GetAlarmStatus buf[0] wakeup_enabled if 0x01) and 0x04 on
                200,    # [11] GetAlarmStatus buf[1] alarm_flag if 0x01
                0,      # [12]
                240,    # [13] status
                0,      # [14] battery charge
                194,    # [15] temperature
                52,     # [16] batVolt
                161,    # [17] batVolt
                0,      # [18]
                0,      # [19]
                20,     # [20] GetAlarm buf[0] second
                0x52,   # [21] GetAlarm buf[1] minute
                0,      # [22] GetAlarm buf[2] hour and flags: 0x40 12hours format
                0xc0,   # [23] GetAlarm buf[3] weekday and flags
                0,      # [24] GetAlarm buf[4] hours mask1
                0,      # [25] GetAlarm buf[5] hours mask2
                0,      # [26] GetAlarm buf[6] hours mask3
                0,      # [27] GetAlarm buf[7] minute_period
                0x02,   # [28] GetAlarm buf[8] 0xFF to indicate EVERY_DAY or day mask
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                113,
                7,      # ALARM_EVT
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] GetAlarmStatus buf[0] wakeup_enabled if 0x01) and 0x04 on
                200,    # [11] GetAlarmStatus buf[1] alarm_flag if 0x01
                0,      # [12]
                240,    # [13] status
                0,      # [14] battery charge
                194,    # [15] temperature
                52,     # [16] batVolt
                161,    # [17] batVolt
                0,      # [18]
                0,      # [19]
                20,     # [20] GetAlarm buf[0] second
                0x52,   # [21] GetAlarm buf[1] minute
                0,      # [22] GetAlarm buf[2] hour and flags: 0x40 12hours format
                0xc0,   # [23] GetAlarm buf[3] weekday and flags
                0,      # [24] GetAlarm buf[4] hours mask1
                0,      # [25] GetAlarm buf[5] hours mask2
                0,      # [26] GetAlarm buf[6] hours mask3
                0,      # [27] GetAlarm buf[7] minute_period
                0xff,   # [28] GetAlarm buf[8] 0xFF to indicate EVERY_DAY or day mask
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                123,
                7,      # ALARM_EVT
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] GetAlarmStatus buf[0] wakeup_enabled if 0x01) and 0x04 on
                200,    # [11] GetAlarmStatus buf[1] alarm_flag if 0x01
                0,      # [12]
                240,    # [13] status
                0,      # [14] battery charge
                194,    # [15] temperature
                52,     # [16] batVolt
                161,    # [17] batVolt
                0,      # [18]
                0,      # [19]
                20,     # [20] GetAlarm buf[0] second
                0x52,   # [21] GetAlarm buf[1] minute
                0x80,   # [22] GetAlarm buf[2] hour and flags: 0x40 12hours format
                0,      # [23] GetAlarm buf[3] weekday and flags
                1,      # [24] GetAlarm buf[4] hours mask1
                0,      # [25] GetAlarm buf[5] hours mask2
                0,      # [26] GetAlarm buf[6] hours mask3
                0,      # [27] GetAlarm buf[7] minute_period
                0,      # [28] GetAlarm buf[8] 0xFF to indicate EVERY_DAY or day mask
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                133,
                7,      # ALARM_EVT
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] GetAlarmStatus buf[0] wakeup_enabled if 0x01) and 0x04 on
                200,    # [11] GetAlarmStatus buf[1] alarm_flag if 0x01
                0,      # [12]
                240,    # [13] status
                0,      # [14] battery charge
                194,    # [15] temperature
                52,     # [16] batVolt
                161,    # [17] batVolt
                0,      # [18]
                0,      # [19]
                20,     # [20] GetAlarm buf[0] second
                0x52,   # [21] GetAlarm buf[1] minute
                0xc0,   # [22] GetAlarm buf[2] hour and flags: 0x40 12hours format
                0,      # [23] GetAlarm buf[3] weekday and flags
                1,      # [24] GetAlarm buf[4] hours mask1
                0,      # [25] GetAlarm buf[5] hours mask2
                0,      # [26] GetAlarm buf[6] hours mask3
                0,      # [27] GetAlarm buf[7] minute_period
                0,      # [28] GetAlarm buf[8] 0xFF to indicate EVERY_DAY or day mask
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                143,
                7,      # ALARM_EVT
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] GetAlarmStatus buf[0] wakeup_enabled if 0x01) and 0x04 on
                200,    # [11] GetAlarmStatus buf[1] alarm_flag if 0x01
                0,      # [12]
                240,    # [13] status
                0,      # [14] battery charge
                194,    # [15] temperature
                52,     # [16] batVolt
                161,    # [17] batVolt
                0,      # [18]
                0,      # [19]
                20,     # [20] GetAlarm buf[0] second
                0x52,   # [21] GetAlarm buf[1] minute
                0xc0,   # [22] GetAlarm buf[2] hour and flags: 0x40 12hours format
                0,      # [23] GetAlarm buf[3] weekday and flags
                0,      # [24] GetAlarm buf[4] hours mask1
                0x10,   # [25] GetAlarm buf[5] hours mask2
                0,      # [26] GetAlarm buf[6] hours mask3
                0,      # [27] GetAlarm buf[7] minute_period
                0,      # [28] GetAlarm buf[8] 0xFF to indicate EVERY_DAY or day mask
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                153,
                7,      # ALARM_EVT
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] GetAlarmStatus buf[0] wakeup_enabled if 0x01) and 0x04 on
                200,    # [11] GetAlarmStatus buf[1] alarm_flag if 0x01
                0,      # [12]
                240,    # [13] status
                0,      # [14] battery charge
                194,    # [15] temperature
                52,     # [16] batVolt
                161,    # [17] batVolt
                0,      # [18]
                0,      # [19]
                20,     # [20] GetAlarm buf[0] second
                0x52,   # [21] GetAlarm buf[1] minute
                0xc0,   # [22] GetAlarm buf[2] hour and flags: 0x40 12hours format
                0,      # [23] GetAlarm buf[3] weekday and flags
                0x02,   # [24] GetAlarm buf[4] hours mask1
                0,      # [25] GetAlarm buf[5] hours mask2
                0,      # [26] GetAlarm buf[6] hours mask3
                0,      # [27] GetAlarm buf[7] minute_period
                0,      # [28] GetAlarm buf[8] 0xFF to indicate EVERY_DAY or day mask
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                4,
                8,      # MCU_RESET
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] powerInput5vIo
                200,    # [11] status
                9,      # [12] GPIO_5V: REGULATOR
                240,    # [13] wkupOnChargeCfg
                0,      # [14] wkupOnChargeCfg
                194,    # [15] battery charge
                52,     # [16] temperature
                161,    # [17] batVolt
                15,     # [18] batVolt
                64,     # [19] gpio5V
                20,     # [20] gpio5V
                124,    # [21] curr5Vgpio
                1,      # [22] curr5Vgpio
                0,      # [23]
                0,      # [24]
                0,      # [25]
                0,      # [26]
                0,      # [27]
                0,      # [28]
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                14,
                8,      # MCU_RESET
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] powerInput5vIo
                200,    # [11] status
                9,      # [12] GPIO_5V: REGULATOR
                240,    # [13] wkupOnChargeCfg
                0,      # [14] wkupOnChargeCfg
                194,    # [15] battery charge
                52,     # [16] temperature
                161,    # [17] batVolt
                15,     # [18] batVolt
                64,     # [19] gpio5V
                20,     # [20] gpio5V
                0x84,   # [21] curr5Vgpio
                0xfe,   # [22] curr5Vgpio
                0,      # [23]
                0,      # [24]
                0,      # [25]
                0,      # [26]
                0,      # [27]
                0,      # [28]
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                5,
                10,     # ALARM_WRITE
                64,     # [ 2] GetDateTime buf[0] second
                71,     # [ 3] GetDateTime buf[1] minute
                20,     # [ 4] GetDateTime buf[2] hour and flags: 0x40 12hours format
                4,      # [ 5] GetDateTime buf[3] weekday
                7,      # [ 6] GetDateTime buf[4] day
                18,     # [ 7] GetDateTime buf[5] month
                34,     # [ 8] GetDateTime buf[6] year
                235,    # [ 9] GetDateTime buf[7] subsecond
                1,      # [10] GetAlarmStatus buf[0] wakeup_enabled if 0x01) and 0x04 on
                200,    # [11] GetAlarmStatus buf[1] alarm_flag if 0x01
                0,      # [12]
                240,    # [13] status
                0,      # [14] battery charge
                194,    # [15] temperature
                52,     # [16] batVolt
                161,    # [17] batVolt
                0,      # [18]
                0,      # [19]
                20,     # [20] GetAlarm buf[0] second
                0x52,   # [21] GetAlarm buf[1] minute
                1,      # [22] GetAlarm buf[2] hour and flags: 0x40 12hours format
                0,      # [23] GetAlarm buf[3] weekday and flags
                0,      # [24] GetAlarm buf[4] hours mask1
                0,      # [25] GetAlarm buf[5] hours mask2
                0,      # [26] GetAlarm buf[6] hours mask3
                0,      # [27] GetAlarm buf[7] minute_period
                0,      # [28] GetAlarm buf[8] 0xFF to indicate EVERY_DAY or day mask
                0,      # [29]
                0,      # [30]
                115,    # [21]
            ],
            [
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                255,
            ],
        ]
        self.cmd_buffers_wrong = [CMD_NSUPP_RESPONSE] * 256
        self.cmd_buffers_wrong[I2C_ADDRESS_CMD] = [0x14, 0xEB]
        self.cmd_buffers = [CMD_NSUPP_RESPONSE] * 256
        self.cmd_buffers[0x40] = [0b11000011, 63]
        self.cmd_buffers[0x41] = [82, 173]
        self.cmd_buffers[0x44] = [0b1111, 255]
        self.cmd_buffers[0x45] = [1, 0, 255]
        self.cmd_buffers[0x47] = [48, 255, 48]
        self.cmd_buffers[0x49] = [180, 15, 68]
        self.cmd_buffers[0x4B] = [12, 0, 243]
        self.cmd_buffers[0x4D] = [50, 20, 217]
        self.cmd_buffers[0x4F] = [146, 251, 150]
        self.cmd_buffers[0x51] = [1, 254]
        self.cmd_buffers[0x52] = [1, 254]
        self.cmd_buffers[0x53] = [
            28,
            7,
            5,
            0,
            34,
            150,
            1,
            10,
            45,
            59,
            52,
            13,
            232,
            3,
            154,
        ]
        self.cmd_buffers[0x54] = [
            0,
            65,
            14,
            216,
            14,
            237,
            15,
            164,
            81,
            20,
            80,
            232,
            78,
            255,
            255,
            255,
            255,
            147,
        ]
        self.cmd_buffers[0x5D] = [2, 253]
        self.cmd_buffers[0x5E] = [11, 244]
        self.cmd_buffers[0x5F] = [0, 255]
        self.cmd_buffers[0x60] = [0, 255]
        self.cmd_buffers[0x61] = [0, 0, 255]
        self.cmd_buffers[0x62] = [255, 0]
        self.cmd_buffers[0x63] = [152, 103]
        self.cmd_buffers[0x64] = [0, 255]
        self.cmd_buffers[0x66] = [0, 60, 100, 167]
        self.cmd_buffers[0x67] = [0, 15, 0, 240]
        self.cmd_buffers[0x68] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 255]
        self.cmd_buffers[0x69] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 255]
        self.cmd_buffers[0x6A] = [1, 60, 60, 100, 154]
        self.cmd_buffers[0x6B] = [3, 9, 0, 0, 245]
        self.cmd_buffers[0x6E] = [0, 0, 0, 0, 1, 8, 0, 0, 17, 100, 2, 200, 73]
        self.cmd_buffers[0x6F] = [0, 0, 0, 0, 33, 4, 34, 6, 0, 0, 0, 0, 254]
        self.cmd_buffers[0x70] = [35, 0, 36, 0, 0, 0, 0, 0, 0, 0, 0, 0, 248]
        self.cmd_buffers[0x72] = [128, 53, 170, 178, 201, 155]
        self.cmd_buffers[0x75] = [117, 53, 191]
        self.cmd_buffers[0x77] = [128, 53, 170, 178, 201, 155]
        self.cmd_buffers[0x7A] = [122, 53, 176]
        self.cmd_buffers[0x7C] = [20, 235]
        self.cmd_buffers[0x7D] = [104, 151]
        self.cmd_buffers[0x7E] = [1, 254]
        self.cmd_buffers[0x7F] = [80, 175]
        self.cmd_buffers[0xB0] = [83, 25, 25, 1, 24, 18, 34, 240, 0, 117]
        self.cmd_buffers[0xB9] = [0, 0, 0, 0, 255, 255, 255, 0, 255, 255]
        self.cmd_buffers[0xC2] = [0, 0, 255]
        self.cmd_buffers[0xF0] = [240, 15, 0, 0, 0]
        self.cmd_buffers[0xF6] = [
            0,
            0,
            1,
            42,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            212,
        ]
        self.cmd_buffers[0xF8] = [9, 0, 0, 0, 0]
        self.cmd_buffers[0xFD] = [22, 0, 233]

        if SMBus.INIT_ADJUSTMENTS:
            for cmd, cmd_buf in SMBus.INIT_ADJUSTMENTS.items():
                upd_values = cmd_buf
                upd_values.append(0)
                self.cmd_buffers[cmd] = upd_values
            SMBus.INIT_ADJUSTMENTS = {}

        if SMBus.INIT_CMD_DELAYS:
            for cmd, del_cmd in SMBus.INIT_CMD_DELAYS.items():
                self.err_sim[cmd] = del_cmd
            SMBus.INIT_CMD_DELAYS = {}

    def set_power(self, io_on=False, input_on=False):
        """Set requested power states - to be used from test script."""
        _d = [0, 0]
        if io_on:
            _d[0] |= 0xC0
        if input_on:
            _d[0] |= 0x30
        self._set_buff(STATUS_CMD, _d)

    def set_charge(self, charge=50):
        """Set charge level - to be used from test script."""
        _d = [charge, 0]
        self._set_buff(CHARGE_LEVEL_CMD, _d)

    def _set_buff(self, cmd, data):
        """Set data buffer for the command - to be used from test script."""
        if data is not None:
            self.cmd_buffers[cmd] = data.copy()
            if cmd == BUTTON_EVENT_CMD:
                self.cmd_buffers[STATUS_CMD][0] |= 0b00000010
            if cmd == FAULT_EVENT_CMD:
                if data[0] != 0:
                    self.cmd_buffers[STATUS_CMD][0] |= 0b00000001
                else:
                    self.cmd_buffers[STATUS_CMD][0] &= 0b11111110

    def _get_buff(self, cmd):
        """Get data buffer for the command - to be used from test script."""
        return self.cmd_buffers[cmd].copy()

    def _get_check_sum(self, data):
        """Calculate checksum for given array."""
        _fcs = 0xFF
        for _x in data[:]:
            _fcs = _fcs ^ _x
        if self.simulate_data_curruption:
            _fcs = ~_fcs
        return _fcs

    def delay_if_needed(self, cmd):
        del_dta = self.err_sim.get(cmd)
        if del_dta is not None:
            #_LOGGER.info(f"delay_if_needed {cmd:02x} {del_dta}")
            if del_dta[0] > 0:
                time.sleep(del_dta[1])
                del_dta[0] += -1
            else:
                del self.err_sim[cmd]

    def read_i2c_block_data(self, addr, cmd, _length):
        """Read block data for command."""
        if self.signal_error_next_read_call:
            self.signal_error_next_read_call = False
            raise IOError
        self.delay_if_needed(cmd)
        if cmd == LOGGING_CMD:
            if self.logging_type == 0:  # read log buffers
                _d = self.logging_buffers[self.logging_buffer_index].copy()
                self.logging_buffer_index += 1
            if self.logging_type == 2:  # read configuration flags
                self.logging_type_response[3] = self.logging_config
                _d = self.logging_type_response.copy()
            self.logging_type = 0
        else:
            if addr == SMBus.SIM_ADDR:
                if self.temp_read_cmd == cmd:
                    _d = self.temp_read_cmd_buff
                    self.temp_read_cmd = 0
                else:
                    _d = self.cmd_buffers[cmd].copy()
            else:
                _d = self.cmd_buffers_wrong[cmd].copy()
        if self.corrupt_next_read_call:
            self.corrupt_next_read_call = False
            _d[0] = ~_d[0]
        _d[-1] = self._get_check_sum(_d[0:-1])
        if self.simulate_recoverable_chksum_issue and (_d[0]&0x80) != 0:
            _d[0] &= 0x7f
        if self.read_write_delay > 0:
            time.sleep(self.read_write_delay)
        return _d

    def write_i2c_block_data(self, addr, cmd, data):
        """Write block data for command."""
        if self.signal_error_next_write_call:
            self.signal_error_next_write_call = False
            raise IOError
        self.delay_if_needed(cmd)
        if cmd == LOGGING_CMD:
            self.logging_type = data[0]
            if self.logging_type == 0:
                self.logging_buffer_index = 0  # requested read diag log buffer
            if self.logging_type == 1:  # requested set logging flags
                self.logging_config = data[1] & 0x7F
                self.logging_type = 0
        else:
            if addr == SMBus.SIM_ADDR:
                if cmd in (BUTTON_EVENT_CMD, FAULT_EVENT_CMD):
                    for _di in range(0, len(data) - 1):
                        self.cmd_buffers[cmd][_di] &= data[_di]
                    if (
                        cmd == BUTTON_EVENT_CMD
                        and self.cmd_buffers[BUTTON_EVENT_CMD][0] == 0
                        and self.cmd_buffers[BUTTON_EVENT_CMD][1] == 0
                    ):
                        self.cmd_buffers[STATUS_CMD][0] &= 0b11111101
                    if (
                        cmd == FAULT_EVENT_CMD
                        and self.cmd_buffers[FAULT_EVENT_CMD][0] == 0
                    ):
                        self.cmd_buffers[STATUS_CMD][0] &= 0b11111110
                else:
                    self.cmd_buffers[cmd] = data
            else:
                self.cmd_buffers_wrong[cmd] = data
        if self.write_log_on:
            self.write_log[cmd] = data
        if self.read_write_delay > 0:
            time.sleep(self.read_write_delay)
