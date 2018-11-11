import time
import logging
import serial.tools.list_ports

from collections import namedtuple
from .exceptions import ComDeviceNotFound

LoggerDefaults = namedtuple("LoggerDefaults", ["str_format", "logger_level"])
LOGGER_DEFAULTS = LoggerDefaults(
    str_format='%(asctime)s_%(name)s_%(levelname)s: %(message)s',
    logger_level=logging.DEBUG)


class _Logger():
    def __init__(self, name):
        if not _Logger.is_inited:
            _logger_formatter = logging.Formatter(LOGGER_DEFAULTS.str_format)

            _logger_ch = logging.StreamHandler()
            _logger_ch.setFormatter(_logger_formatter)
            _logger_ch.setLevel(LOGGER_DEFAULTS.logger_level)

            self._logger = logging.getLogger(name)
            self._logger.setLevel(logging.DEBUG)
            self._logger.addHandler(_logger_ch)

            _Logger.is_inited = True
        else:
            self._logger = logging.getLogger(name)

    @property
    def logger(self):
        return self._logger

    def instance():
        return _Logger()._logger

    is_inited = False


class Logger():
    @staticmethod
    def for_name(name):
        return _Logger(name).logger


def find_device(vid, pid):
    log = Logger.for_name(__name__)

    for p in list(serial.tools.list_ports.comports()):
        if (p.vid == vid) and (p.pid == pid):
            log.info("Device found!")
            return p
    log.error("Device not found!")
    raise ComDeviceNotFound(
        "Not found any devices with VID:PID = {vid}:{pid}".format(**locals()))