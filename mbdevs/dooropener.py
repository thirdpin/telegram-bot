#!/usr/bin/env python

import time
import minimalmodbus
import serial.tools.list_ports

from .common import Logger, find_device
from .exceptions import ComDeviceNotFound


class DoorOpenerDeviceNotFound(ComDeviceNotFound):
    pass


class DoorOpener(object):
    @classmethod
    def from_vid_pid(cls, vip, pid, dev_addr=1):
        Logger.for_name(__name__).info("Device search...")
        dev = find_device(vip, pid)
        return cls(dev.device, dev_addr)

    def __init__(self, port, dev_addr):
        self.logger = Logger.for_name(__name__)

        try:
            self.device = minimalmodbus.Instrument(
                str(port), dev_addr, mode='rtu')
        except Exception as e:
            log.error(str(e), exc_info=True)
            raise e

        self._dev_addr = dev_addr

        self.initialize_gpio()

    def open(self):
        if not self.device.serial.is_open:
            self.device.serial.open()
            self.logger.info('Device {device} opened'.format(
                device=self.device.serial.port))
            return True
        else:
            self.device.serial.close()
            self.device.serial.open()
            self.logger.info('Device {device} reopened'.format(
                device=self.device.serial.port))
            return True

    def initialize_gpio(self):
        self.device.write_bit(0, 1, functioncode=0x05)
        self.device.write_bit(1, 1, functioncode=0x05)

    def open_door(self):
        """Opens/closes the door and blinks traffic light."""
        self._traffic_light_on()
        self._open_door()
        time.sleep(1)
        self._close_door()
        time.sleep(3)
        self._traffic_light_off()

    def _open_door(self):
        self.logger.info("Door opened...")
        self.device.write_bit(8, 1, functioncode=0x05)

    def _close_door(self):
        self.device.write_bit(8, 0, functioncode=0x05)

    def _traffic_light_on(self):
        self.device.write_bit(9, 1, functioncode=0x05)

    def _traffic_light_off(self):
        self.device.write_bit(9, 0, functioncode=0x05)
