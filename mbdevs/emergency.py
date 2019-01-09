#!/usr/bin/env python

import time
import enum
import minimalmodbus
import serial.tools.list_ports
from threading import Thread

from collections import namedtuple
from pykka import ThreadingActor
from functools import partial

from .common import Logger, find_device
from .exceptions import ComDeviceNotFound
from .modbus import FunctionalCodes, Register, Modbus, Action, ModbusUser

EmergencyRegs = namedtuple(
    'EmergencyRegs', ['button', 'sound', 'button_config', 'sound_config'])

REGS = EmergencyRegs(
    button=Register(
        name="Emergency button",
        addr=4103,
        func_code=FunctionalCodes.DISCRETE,
        count=1,
        value_type=bool,
        unit=''),
    sound=Register(
        name="Dudka",
        addr=11,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    button_config=Register(
        name="Emergency button config",
        addr=7,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    sound_config=Register(
        name="Dudka config",
        addr=3,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''))


class Emergency(ModbusUser, ThreadingActor):
    class Action(enum.Enum):
        SOUND_ON = 1
        SOUND_OFF = 0
        SUBSCRIBE_TO_BUTTON = 2
        BUTTON_STATE = 3

    class State(enum.Enum):
        ON = 1
        OFF = 0

    @classmethod
    def from_vid_pid(cls, vip, pid, dev_addr=2):
        Logger.for_name(__name__).info("Device search...")
        dev = find_device(vip, pid)
        return cls.start(dev.device, dev_addr)

    def __init__(self, port, dev_addr):
        ThreadingActor.__init__(self)

        self._log = Logger.for_name(__name__)

        try:
            ModbusUser.__init__(
                self, minimalmodbus.Instrument(
                    str(port), dev_addr, mode='rtu'))
        except Exception as e:
            self._log.error(str(e), exc_info=True)
            raise e

        self._initialize_gpio()

        self._button_state = Emergency.State.OFF

        self._button_check_th = Thread(target=self._button_check_thread)
        self._button_check_th.start()

    def on_receive(self, msg):
        action = msg.pop('action')
        self._match_action(action, **msg)

    def sound_on(self):
        self._log.info("Dudka on!")
        self._write_reg(REGS.sound, 1)

    def sound_off(self):
        self._log.info("Dudka off!")
        self._write_reg(REGS.sound, 0)

    def _button_handler(self, state):
        self._button_state = state
        if state == Emergency.State.ON:
            self._log.info("Emergency button pressed!")
            self.sound_on()
        else:
            self._log.info("Emergency button disabled")
            self.sound_off()

    def _match_action(self, action, **kwarg):
        try:
            {
                Emergency.Action.SOUND_ON:
                self.sound_on,
                Emergency.Action.SOUND_OFF:
                self.sound_off,
                Emergency.Action.BUTTON_STATE:
                lambda: self._button_handler(**kwarg)
            }[action]()
        except:
            self._log.info("", exc_info=True)

    def _initialize_gpio(self):
        self._write_reg(REGS.button_config, 0)
        self._write_reg(REGS.sound_config, 1)

    def _button_check_thread(self):
        while True:
            is_button_on = not self._read_reg(REGS.button)
            btn_state = Emergency.State.ON if is_button_on else Emergency.State.OFF
            if self._button_state != btn_state:
                self.actor_ref.tell({
                    "action": Emergency.Action.BUTTON_STATE,
                    "state": btn_state
                })
            time.sleep(0.5)
