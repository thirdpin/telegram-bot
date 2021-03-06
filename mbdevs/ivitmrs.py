import minimalmodbus
import serial.tools.list_ports
from collections import namedtuple

from .common import find_device, Logger
from .modbus import FunctionalCodes, Register, Modbus, Action, ModbusUser

IvitMRSRegs = namedtuple('IvitMRSRegs', [
    'humidity', 'humidity_no_correction', 'humidity_no_adjustment', 'temp',
    'temp_sht', 'temp_no_correction', 'temp_no_adjustment'
])

REGS = IvitMRSRegs(
    humidity=Register("Relative humidity", 0x0016, FunctionalCodes.INPUT, 2,
                      float, '%'),
    humidity_no_correction=Register("Relative humidity (no correction)",
                                    0x0014, FunctionalCodes.INPUT, 2, float,
                                    '%'),
    humidity_no_adjustment=Register("Relative humidity (no adjustment)",
                                    0x0012, FunctionalCodes.INPUT, 2, float,
                                    '%'),
    temp=Register("Temperature", 0x0022, FunctionalCodes.INPUT, 2, float, 'C'),
    temp_sht=Register("Temperature SHT", 0x0034, FunctionalCodes.INPUT, 2,
                      float, 'C'),
    temp_no_correction=Register("Temperature (no correction)", 0x0020,
                                FunctionalCodes.INPUT, 2, float, 'C'),
    temp_no_adjustment=Register("Temperature (no adjustment)", 0x0018,
                                FunctionalCodes.INPUT, 2, float, 'C'),
)

# REGS = IvitMRSRegs(
#     humidity=Register("Relative humidity", 0x0016, FunctionalCodes.INPUT, 2,
#                       ">f", '%'),
#     humidity_no_correction=Register("Relative humidity (no correction)",
#                                     0x0014, FunctionalCodes.INPUT, 2, ">f",
#                                     '%'),
#     humidity_no_adjustment=Register("Relative humidity (no adjustment)",
#                                     0x0012, FunctionalCodes.INPUT, 2, ">f",
#                                     '%'),
#     temp=Register("Temperature", 0x0022, FunctionalCodes.INPUT, 2, ">f", 'C'),
#     temp_sht=Register("Temperature SHT", 0x0034, FunctionalCodes.INPUT, 2,
#                       float, 'C'),
#     temp_no_correction=Register("Temperature (no correction)", 0x0020,
#                                 FunctionalCodes.INPUT, 2, ">f", 'C'),
#     temp_no_adjustment=Register("Temperature (no adjustment)", 0x0018,
#                                 FunctionalCodes.INPUT, 2, ">f", 'C'),
# )


class IvitMRS(ModbusUser):
    @classmethod
    def from_vid_pid(cls, vip, pid, dev_addr=247):
        Logger.for_name(__name__).info("Device search...")
        dev = find_device(vip, pid)
        return cls(dev.device, dev_addr)

    def __init__(self, port, dev_addr=247):
        log = Logger.for_name(__name__)

        try:
            self._mb = minimalmodbus.Instrument(
                str(port), dev_addr, mode='rtu')
            super().__init__(self._mb)
            # super().__init__(dev_addr, str(port), 115200)
        except Exception as e:
            log.error(str(e), exc_info=True)
            raise e

    @property
    def humidity(self):
        return self._read_reg(REGS.humidity)

    @property
    def humidity_no_correction(self):
        return self._read_reg(REGS.humidity_no_correction)

    @property
    def humidity_no_adjustment(self):
        return self._read_reg(REGS.humidity_no_adjustment)

    @property
    def temp(self):
        return self._read_reg(REGS.temp)

    @property
    def temp_sht(self):
        return self._read_reg(REGS.temp_sht)

    @property
    def temp_no_correction(self):
        return self._read_reg(REGS.temp_no_correction)

    @property
    def temp_no_adjustment(self):
        return self._read_reg(REGS.temp_no_adjustment)

    def poll_sesors_and_print(self):
        log = Logger.for_name(__name__)

        log.info(
            '%s:   %.1f%s\t' % (REGS.temp.name, self.temp, REGS.temp.unit))
        log.info('%s:   %.1f%s\t' % (REGS.temp_sht.name, self.temp_sht,
                                     REGS.temp_sht.unit))
        log.info('%s:   %.1f%s\t' %
                 (REGS.temp_no_correction.name, self.temp_no_correction,
                  REGS.temp_no_correction.unit))
        log.info('%s:   %.1f%s\t' %
                 (REGS.temp_no_adjustment.name, self.temp_no_adjustment,
                  REGS.temp_no_adjustment.unit))
        log.info('%s:   %.1f%s\t' % (REGS.humidity.name, self.humidity,
                                     REGS.humidity.unit))
        log.info('%s:   %.1f%s\t' %
                 (REGS.humidity_no_adjustment.name,
                  self.humidity_no_adjustment, REGS.humidity.unit))
        log.info('%s:   %.1f%s\t' %
                 (REGS.humidity_no_correction.name,
                  self.humidity_no_correction, REGS.humidity.unit))
        log.info('\n')


if __name__ == "__main__":
    minimalmodbus.BAUDRATE = 9600
    minimalmodbus.TIMEOUT = 1
    minimalmodbus.PARITY = 'E'

    dev_handler = find_device(0x0403, 0x6015)

    if dev_handler:
        ivt_mrs = IvitMRS(dev_handler.device)
    else:
        sys.exit(1)

    while (True):
        ivt_mrs.poll_sesors_and_print()
        time.sleep(1)
