import time
import logging
import minimalmodbus
import serial.tools.list_ports
from collections import namedtuple


class _Logger():
    def __init__(self):
        if not _Logger.is_inited:
            _logger_formatter = logging.Formatter(
                '%(asctime)s_%(name)s_%(levelname)s: %(message)s')

            _logger_ch = logging.StreamHandler()
            _logger_ch.setFormatter(_logger_formatter)
            _logger_ch.setLevel(logging.DEBUG)

            self._logger = logging.getLogger(__name__)
            self._logger.setLevel(logging.DEBUG)
            self._logger.addHandler(_logger_ch)

            _Logger.is_inited = True
        else:
            self._logger = logging.getLogger(__name__)

    @property
    def logger(self):
        return self._logger

    def instance():
        return _Logger()._logger

    is_inited = False


Register = namedtuple(
    'Register', ['name', 'addr', 'reg_type', 'count', 'value_type', 'unit'])

IvitMRSRegs = namedtuple('IvitMRSRegs', [
    'humidity', 'humidity_no_correction', 'humidity_no_adjustment', 'temp',
    'temp_sht', 'temp_no_correction', 'temp_no_adjustment'
])

REGS = IvitMRSRegs(
    humidity=Register("Relative humidity", 0x0016, 0x04, 2, float, '%'),
    humidity_no_correction=Register("Relative humidity (no correction)",
                                    0x0014, 0x04, 2, float, '%'),
    humidity_no_adjustment=Register("Relative humidity (no adjustment)",
                                    0x0012, 0x04, 2, float, '%'),
    temp=Register("Temperature", 0x0022, 0x04, 2, float, 'C'),
    temp_sht=Register("Temperature SHT", 0x0034, 0x04, 2, float, 'C'),
    temp_no_correction=Register("Temperature (no correction)", 0x0020, 0x04, 2,
                                float, 'C'),
    temp_no_adjustment=Register("Temperature (no adjustment)", 0x0018, 0x04, 2,
                                float, 'C'),
)


class IvitMRS(object):
    def __init__(self, port, dev_addr=247, baud=9600, parity='E', timeout=1):
        # Save an old glob MB settings
        baud_old = minimalmodbus.BAUDRATE
        timout_old = minimalmodbus.TIMEOUT
        parity_old = minimalmodbus.PARITY

        minimalmodbus.BAUDRATE = baud
        minimalmodbus.TIMEOUT = timeout
        minimalmodbus.PARITY = parity

        self._mb = minimalmodbus.Instrument(str(port), dev_addr, mode='rtu')
        self._dev_addr = dev_addr

        # Restore an old glob MB settings
        minimalmodbus.BAUDRATE = baud_old
        minimalmodbus.TIMEOUT = timout_old
        minimalmodbus.PARITY = parity_old

    def read_reg(self, reg):
        return reg.value_type(
            self._mb.read_float(reg.addr, reg.reg_type, reg.count))

    @property
    def humidity(self):
        # return float("%0.1f" % self.read_reg(REGS.humidity))
        return self.read_reg(REGS.humidity)

    @property
    def humidity_no_correction(self):
        return self.read_reg(REGS.humidity_no_correction)

    @property
    def humidity_no_adjustment(self):
        return self.read_reg(REGS.humidity_no_adjustment)

    @property
    def temp(self):
        # return float("%0.1f" % self.read_reg(REGS.temp))
        return self.read_reg(REGS.temp)

    @property
    def temp_sht(self):
        return self.read_reg(REGS.temp_sht)

    @property
    def temp_no_correction(self):
        return self.read_reg(REGS.temp_no_correction)

    @property
    def temp_no_adjustment(self):
        return self.read_reg(REGS.temp_no_adjustment)

    def poll_sesors_and_print(self):
        log = _Logger.instance()
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


def _find_device(vid, pid):
    log = _Logger.instance()
    for p in list(serial.tools.list_ports.comports()):
        if (p.vid == vid) and (p.pid == pid):
            log.info("Device found!")
            return p
    log.error("Device not found!")
    return None


if __name__ == "__main__":
    dev_handler = _find_device(0x0403, 0x6015)
    if dev_handler:
        ivt_mrs = IvitMRS(dev_handler.device)
    else:
        sys.exit(1)

    while (True):
        ivt_mrs.poll_sesors_and_print()
        time.sleep(1)
