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
        self.reset_device()

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
                6,
                64,
                71,
                20,
                4,
                7,
                18,
                34,
                235,
                1,
                200,
                9,
                240,
                0,
                194,
                52,
                161,
                15,
                64,
                20,
                124,
                1,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                115,
            ],
            [
                1,
                4,
                64,
                71,
                20,
                4,
                8,
                18,
                34,
                235,
                1,
                200,
                9,
                240,
                0,
                194,
                52,
                161,
                15,
                64,
                20,
                124,
                1,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                115,
            ],
            [
                2,
                5,
                64,
                71,
                20,
                4,
                9,
                18,
                34,
                235,
                1,
                200,
                9,
                240,
                0,
                194,
                52,
                161,
                15,
                64,
                20,
                124,
                1,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                115,
            ],
            [
                3,
                7,
                64,
                71,
                20,
                4,
                10,
                18,
                34,
                235,
                1,
                200,
                9,
                240,
                0,
                194,
                52,
                161,
                15,
                64,
                20,
                124,
                1,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                115,
            ],
            [
                4,
                8,
                64,
                71,
                20,
                4,
                11,
                18,
                34,
                235,
                1,
                200,
                9,
                240,
                0,
                194,
                52,
                161,
                15,
                64,
                20,
                124,
                1,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                115,
            ],
            [
                5,
                10,
                64,
                71,
                20,
                4,
                12,
                18,
                34,
                235,
                1,
                200,
                9,
                240,
                0,
                194,
                52,
                161,
                15,
                64,
                20,
                124,
                1,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                115,
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
        self.cmd_buffers[cmd] = data
        if cmd == BUTTON_EVENT_CMD:
            self.cmd_buffers[STATUS_CMD][0] |= 0b00000010
        if cmd == FAULT_EVENT_CMD:
            if data[0] != 0:
                self.cmd_buffers[STATUS_CMD][0] |= 0b00000001
            else:
                self.cmd_buffers[STATUS_CMD][0] &= 0b11111110

    def _get_buff(self, cmd):
        """Get data buffer for the command - to be used from test script."""
        return self.cmd_buffers[cmd]

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

    def read_i2c_block_data(self, addr, cmd, length):
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
