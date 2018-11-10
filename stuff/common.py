#!/usr/bin/env python

import minimalmodbus
import serial.tools.list_ports
import time
import logging


BAUDRATE = 115200
TIMEOUT = 3
PARITY = 'N'

class Logger():
    def __init__(self):
        # Enable logging
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.INFO)

        self.logger = logging.getLogger(__name__)

    def get_logger(self):
        return self.logger


class Device(object):
    def __init__(self, spider_id):
        self.logger = Logger().get_logger()
        self.device = self.get_device(spider_id)

    def get_device(self, spider_id):
        minimalmodbus.BAUDRATE = BAUDRATE
        minimalmodbus.TIMEOUT = TIMEOUT
        minimalmodbus.PARITY = PARITY
        for port in list(serial.tools.list_ports.comports()):
            if (port.vid == 0x0403) and (port.pid == 0x6015):
                device = minimalmodbus.Instrument(str(port.device),
                                                  spider_id,
                                                  mode='rtu')
                self.logger.info('Found device {device} '
                                 'with ID {id}'.format(device=str(port.device),
                                                       id=spider_id))
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
        self.device.write_bit(2,1, functioncode=0x05)
        self.device.write_bit(3,1, functioncode=0x05)
        self.device.write_bit(4,1, functioncode=0x05)
        self.device.write_bit(5,1, functioncode=0x05)
        self.device.write_bit(6,1, functioncode=0x05)
        self.device.write_bit(7,1, functioncode=0x05)

    def blink(self):
        self.device.write_bit(8,1, functioncode=0x05)
        self.device.write_bit(9,1, functioncode=0x05)
        self.device.write_bit(10,1, functioncode=0x05)
        self.device.write_bit(11,1, functioncode=0x05)
        self.device.write_bit(12,1, functioncode=0x05)
        self.device.write_bit(13,1, functioncode=0x05)
        self.device.write_bit(14,1, functioncode=0x05)
        self.device.write_bit(15,1, functioncode=0x05)
        time.sleep(1)
        self.device.write_bit(8,0, functioncode=0x05)
        self.device.write_bit(9,0, functioncode=0x05)
        self.device.write_bit(10,0, functioncode=0x05)
        self.device.write_bit(11,0, functioncode=0x05)
        self.device.write_bit(12,0, functioncode=0x05)
        self.device.write_bit(13,0, functioncode=0x05)
        self.device.write_bit(14,0, functioncode=0x05)
        self.device.write_bit(15,0, functioncode=0x05)