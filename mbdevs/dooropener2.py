#!/usr/bin/env python

import time
import minimalmodbus
import serial.tools.list_ports
import threading

from enum import Enum
from collections import namedtuple
from pykka import ThreadingActor
from .common import Logger, find_device
from .exceptions import CannotReadARegisterValue
from .modbus import FunctionalCodes, Register, Modbus, ModbusUser

DoorOpener2Regs = namedtuple('DoorOpener2Regs',
                            ['light', 'light_config', 'door', 'door_config', 'door_button','door_button_config'])

REGS = DoorOpener2Regs(
    light=Register(
        name="Light",
        addr=9,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    light_config=Register(
        name="Light config",
        addr=1,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    door=Register(
        name="Door",
        addr=13,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    door_config=Register(
        name="Door config",
        addr=5,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    door_button=Register(
        name="Door Button",
        addr=4100,
        func_code=FunctionalCodes.DISCRETE,
        count=1,
        value_type=bool,
        unit=''),
    door_button_config=Register(
        name="Door button config",
        addr=4,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
)


class Action(Enum):
    OPEN = 1
    CLOSE = 0
    FINALIZE_CLOSING = -1
    CHECK_BUTTON = -2


class DoorState(Enum):
    OPENED = 1,
    CLOSED = 0


class DoorOpener2(ModbusUser, ThreadingActor):
    @classmethod
    def from_vid_pid(cls, vip, pid, dev_addr=2):
        Logger.for_name(__name__).info("Device search...")
        dev = find_device(vip, pid)
        return cls.start(dev.device, dev_addr)

    def __init__(self, port, dev_addr):
        ThreadingActor.__init__(self)

        self._logger = Logger.for_name(__name__)

        try:
            self._mb = minimalmodbus.Instrument(
                str(port), dev_addr, mode='rtu')
            ModbusUser.__init__(self, self._mb)
        except Exception as e:
            self._logger.error(str(e), exc_info=True)
            raise e

        self._initialize_gpio()

        self._state = DoorState.CLOSED

    def _open_serial(self):
        if not self._mb.serial.is_open:
            self._mb.serial.open()
            self._logger.info(
                'Device {device} opened'.format(device=self._mb.serial.port))
            return True
        else:
            self._mb.serial.close()
            self._mb.serial.open()
            self._logger.info(
                'Device {device} reopened'.format(device=self._mb.serial.port))
            return True

    def _initialize_gpio(self):
        self._write_reg(REGS.door_config, 1)
        #self._write_reg(REGS.light_config, 1)
        self._write_reg(REGS.door_button_config, 0)


    def on_receive(self, msg):
        if msg["action"] == Action.OPEN:
            if self._state == DoorState.OPENED:
                return False
            else:
                self._start_opening_door_proc()
                return True
        elif msg["action"] == Action.CLOSE:
            if self._state == DoorState.OPENED:
                self._start_closing_door_proc()
        elif msg["action"] == Action.FINALIZE_CLOSING:
            if self._state == DoorState.OPENED:
                self._traffic_light_off()
                self._state = DoorState.CLOSED
                self._logger.info("Door closed...")
        elif msg["action"] == Action.CHECK_BUTTON:
            return self._read_reg(REGS.door_button)

    def _start_opening_door_proc(self):
        """Opens/closes the door and blinks traffic light."""
        self._state = DoorState.OPENED
        self._traffic_light_on()
        self._open_door()
        self._logger.info("Door opened...")
        threading.Timer(0.5, self._door_close_timer_handler,
                        [Action.CLOSE]).start()

    def _start_closing_door_proc(self):
        self._close_door()
        threading.Timer(2.5, self._door_close_timer_handler,
                        [Action.FINALIZE_CLOSING]).start()

    def _open_door(self):
        self._write_reg(REGS.door, 1)

    def _close_door(self):
        self._write_reg(REGS.door, 0)

    def _traffic_light_on(self):
        self._write_reg(REGS.light, 1)

    def _traffic_light_off(self):
        self._write_reg(REGS.light, 0)

    def _door_close_timer_handler(self, action):
        self.actor_ref.tell({"action": action})
