#!/usr/bin/env python

import time
import enum
import minimalmodbus
import serial.tools.list_ports

from .common import Logger, find_device
from .exceptions import ComDeviceNotFound


class TrafficLightDeviceNotFound(ComDeviceNotFound):
    pass



class TrafficLight(object):
    class State(enum.Enum):
        ON = 1
        OFF = 0

    class Color(enum.Enum):
        RED = 8
        GREEN = 10
        YELLOW = 9

    @classmethod
    def from_vid_pid(cls, vip, pid, dev_addr=2):
        Logger.for_name(__name__).info("Device search...")
        dev = find_device(vip, pid)
        return cls(dev.device, dev_addr)

    def __init__(self, port, dev_addr):
        self.logger = Logger.for_name(__name__)
        self.states = {
            TrafficLight.Color.RED: TrafficLight.State.OFF,
            TrafficLight.Color.GREEN: TrafficLight.State.OFF,
            TrafficLight.Color.YELLOW: TrafficLight.State.OFF,
        }

        try:
            self.device = minimalmodbus.Instrument(
                str(port), dev_addr, mode='rtu')
        except Exception as e:
            log.error(str(e), exc_info=True)
            raise e

        self._dev_addr = dev_addr

        self.initialize_gpio()
        self.all(TrafficLight.State.OFF)

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
        self.device.write_bit(2, 1, functioncode=0x05)

    def _turn(self, reg_addr, state):
        if state == TrafficLight.State.ON:
            self.device.write_bit(reg_addr, 1, functioncode=0x05)
        else:
            self.device.write_bit(reg_addr, 0, functioncode=0x05)

    def all(self, state):
        self.green(state)
        self.yellow(state)
        self.red(state)

    def green(self, state):
        self.states[TrafficLight.Color.GREEN] = state
        self._turn(TrafficLight.Color.GREEN.value, state)

    def yellow(self, state):
        self.states[TrafficLight.Color.YELLOW] = state
        self._turn(TrafficLight.Color.YELLOW.value, state)

    def red(self, state):
        self.states[TrafficLight.Color.RED] = state
        self._turn(TrafficLight.Color.RED.value, state)

    def toggle(self, *argv):
        for color in argv:
            if isinstance(color, TrafficLight.Color):
                if self.states[color] == TrafficLight.State.ON:
                    self._turn(color.value, TrafficLight.State.OFF)
                else:
                    self._turn(color.value, TrafficLight.State.ON)

    def sequence(self, sleep_time, *argv):
        for color in argv:
            if isinstance(color, TrafficLight.Color):
                if self.states[color] == TrafficLight.State.ON:
                    state = TrafficLight.State.OFF
                else:
                    state = TrafficLight.State.ON
                self._turn(color.value, state)
                self.states[color] = state
                time.sleep(sleep_time)
