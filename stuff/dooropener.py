#!/usr/bin/env python

import minimalmodbus
import serial.tools.list_ports

from .common import Logger, find_device

class DoorOpener(object):
    def __init__(self, spider_id):
        self.logger = Logger.for_name(__name__)
        self.device = self.get_device(spider_id)

    def get_device(self, spider_id):
        com = find_device(0x0403, 0x6015)

        device = minimalmodbus.Instrument(
            str(com.device), spider_id, mode='rtu')

        self.logger.info('Found device {device} '
                         'with ID {id}'.format(
                             device=str(port.device), id=spider_id))
        return device

    def open(self):
        if not self.device.serial.is_open:
            self.device.serial.open()
            self.logger.info('Device {device} opened'.format(device=self.device.serial.port))
            return True
        else:
            self.device.serial.close()
            self.device.serial.open()
            self.logger.info('Device {device} reopened'.format(device=self.device.serial.port))
            return True

    def initialize(self):
        self.device.write_bit(0,1, functioncode=0x05)
        self.device.write_bit(1,1, functioncode=0x05)

    def door_stuff(self):
        """Opens/closes the door and blinks traffic light.
        """
        try:
            self._traffic_light_on()
            self._open_door()
            time.sleep(1)
            self._close_door()
            time.sleep(3)
            self._traffic_light_off()
            return True
        except:
            return False

    def _open_door(self):
        self.device.write_bit(8,1, functioncode=0x05)

    def _close_door(self):
        self.device.write_bit(8,0, functioncode=0x05)

    def _traffic_light_on(self):
        self.device.write_bit(9,1, functioncode=0x05)

    def _traffic_light_off(self):
        self.device.write_bit(9,0, functioncode=0x05)
