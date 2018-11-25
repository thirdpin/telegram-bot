#!/usr/bin/env python

import time
import enum
import minimalmodbus
import serial.tools.list_ports

from collections import namedtuple
from pykka import ThreadingActor
from functools import partial

from .common import Logger, find_device
from .exceptions import ComDeviceNotFound
from .modbus import FunctionalCodes, Register, Modbus, Action, ModbusUser

TrafficLightRegs = namedtuple(
    'TrafficLightRegs',
    ['red', 'yellow', 'green', 'red_config', 'yellow_config', 'green_config'])

REGS = TrafficLightRegs(
    red=Register(
        name="Red light",
        addr=8,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    yellow=Register(
        name="Yellow light",
        addr=9,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    green=Register(
        name="Green light",
        addr=10,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    red_config=Register(
        name="Red light config",
        addr=0,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    yellow_config=Register(
        name="Yellow light config",
        addr=1,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    green_config=Register(
        name="Green light config",
        addr=2,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
)


class TrafficLightDeviceNotFound(ComDeviceNotFound):
    pass


class TrafficLight(ModbusUser, ThreadingActor):
    class Action(enum.Enum):
        ON = 1
        OFF = 0
        SEQUENCE = 2
        TOGGLE = 3

    class State(enum.Enum):
        ON = 1
        OFF = 0

    class Color(enum.Enum):
        RED = 8
        YELLOW = 9
        GREEN = 10
        ALL = -1

    @classmethod
    def from_vid_pid(cls, vip, pid, dev_addr=2):
        Logger.for_name(__name__).info("Device search...")
        dev = find_device(vip, pid)
        return cls.start(dev.device, dev_addr)

    def __init__(self, port, dev_addr):
        ThreadingActor.__init__(self)

        self._log = Logger.for_name(__name__)
        self.states = {
            TrafficLight.Color.RED: TrafficLight.State.OFF,
            TrafficLight.Color.GREEN: TrafficLight.State.OFF,
            TrafficLight.Color.YELLOW: TrafficLight.State.OFF,
        }

        try:
            ModbusUser.__init__(
                self, minimalmodbus.Instrument(
                    str(port), dev_addr, mode='rtu'))
        except Exception as e:
            self._log.error(str(e), exc_info=True)
            raise e

        self.initialize_gpio()
        self.all(TrafficLight.State.OFF)

    def on_receive(self, msg):
        action = msg.pop('action')
        self._match_action(action, **msg)

    def _reg(self, color):
        return {
            TrafficLight.Color.RED: REGS.red,
            TrafficLight.Color.GREEN: REGS.green,
            TrafficLight.Color.YELLOW: REGS.yellow
        }[color]

    def _match_action(self, action, **kwarg):
        try:
            {
                TrafficLight.Action.OFF: partial(self.turn_off, **kwarg),
                TrafficLight.Action.ON: partial(self.turn_on, **kwarg),
                TrafficLight.Action.TOGGLE: partial(self.toggle, **kwarg),
                TrafficLight.Action.SEQUENCE: partial(self.sequence, **kwarg)
            }[action]()
        except:
            self._log.info("", exc_info=True)

    def initialize_gpio(self):
        self._write_reg(REGS.red_config, 1)
        self._write_reg(REGS.yellow_config, 1)
        self._write_reg(REGS.green_config, 1)

    def _turn(self, color, state):
        reg = self._reg(color)
        if state == TrafficLight.State.ON:
            self._write_reg(reg, 1)
        else:
            self._write_reg(reg, 0)

    def all(self, state):
        self.green(state)
        self.yellow(state)
        self.red(state)

    def green(self, state):
        self.states[TrafficLight.Color.GREEN] = state
        self._turn(TrafficLight.Color.GREEN, state)

    def yellow(self, state):
        self.states[TrafficLight.Color.YELLOW] = state
        self._turn(TrafficLight.Color.YELLOW, state)

    def red(self, state):
        self.states[TrafficLight.Color.RED] = state
        self._turn(TrafficLight.Color.RED, state)

    def turn_on(self, color):
        if color == TrafficLight.Color.ALL:
            self.all(TrafficLight.State.ON)
        else:
            self.states[color] = TrafficLight.State.ON
            self._turn(color, TrafficLight.State.ON)

    def turn_off(self, color):
        if color == TrafficLight.Color.ALL:
            self.all(TrafficLight.State.OFF)
        else:
            self.states[color] = TrafficLight.State.OFF
            self._turn(color, TrafficLight.State.OFF)

    def toggle(self, colors):
        for color in colors:
            if isinstance(color, TrafficLight.Color):
                if self.states[color] == TrafficLight.State.ON:
                    self._turn(color, TrafficLight.State.OFF)
                else:
                    self._turn(color, TrafficLight.State.ON)

    def sequence(self, sleep_time, colors):
        for color in colors:
            if isinstance(color, TrafficLight.Color):
                if self.states[color] == TrafficLight.State.ON:
                    state = TrafficLight.State.OFF
                else:
                    state = TrafficLight.State.ON
                self._turn(color, state)
                self.states[color] = state
                time.sleep(sleep_time)
