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

ToiletRegs = namedtuple(
    'ToiletRegs',['button_end','button_like','button_dislike','lamp_button','lamp_green','lamp_red','lamp_connection','button_like_config','button_dislike_config','button_end_config','lamp_config_green','lamp_config_red','lamp_config_connection','lamp_config_button'])

REGS = ToiletRegs(
    button_end=Register(
        name="button_end",
        addr=4103,
        func_code=FunctionalCodes.DISCRETE,
        count=1,
        value_type=bool,
        unit=''),
    button_like=Register(
        name="button_like",
        addr=4097,
        func_code=FunctionalCodes.DISCRETE,
        count=1,
        value_type=bool,
        unit=''),
    button_dislike=Register(
        name="button_dislike",
        addr=4098,
        func_code=FunctionalCodes.DISCRETE,
        count=1,
        value_type=bool,
        unit=''),
    lamp_button=Register(
        name="lamp_button",
        addr=9,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    lamp_green=Register(
        name="lamp_green",
        addr=13,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    lamp_red=Register(
        name="lamp_red",
        addr=12,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    lamp_connection=Register(
        name="lamp_connection",
        addr=14,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    button_end_config=Register(
        name="button_end_config",
        addr=7,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    button_dislike_config=Register(
        name="button_dislike_config",
        addr=2,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    button_like_config=Register(
        name="button_like_config",
        addr=1,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    lamp_config_button=Register(
        name="lamp_config_button",
        addr=1,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    lamp_config_green=Register(
        name="lamp_config_green",
        addr=5,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    lamp_config_red=Register(
        name="lamp_config_red",
        addr=4,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''),
    lamp_config_connection=Register(
        name="lamp_config_connection",
        addr=6,
        func_code=FunctionalCodes.COIL,
        count=1,
        value_type=bool,
        unit=''))


class Toilet(ModbusUser, ThreadingActor):
    class Action(enum.Enum):
        lamp_ON = 1
        lamp_OFF = 0
        SUBSCRIBE_TO_BUTTON = 2
        BUTTON_STATE = 3

    class State(enum.Enum):
        ON = 1
        OFF = 0

    class PaperState(enum.Enum):
        LEFT = 1
        ABSCENT = 0
    
    paperState = PaperState.LEFT
    paperScore = 0
    paperLikes = 0
    paperDislikes = 0
    paperMsg = 'Device is not ready'

    @classmethod
    def from_vid_pid(cls, vip, pid, dev_addr=5):
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

        self._button_state = Toilet.State.OFF

        self._button_check_th = Thread(target=self._button_check_thread)
        self._button_check_th.start()

    def on_receive(self, msg):
        action = msg.pop('action')
        if action == 'get_paper_score':
            return 'likes: %d dislikes: %d score: %d' % (self.paperLikes, self.paperDislikes, self.paperScore)
        if action == 'is_paper_left':
            return self.paperMsg 
        if action == 'connected':
            self._write_reg(REGS.lamp_connection, 1)

    def lamp_on(self):
        self._log.info("Lamp on!")
        self._write_reg(REGS.lamp_button, 1)

    def lamp_off(self):
        self._log.info("Lamp off!")
        self._write_reg(REGS.lamp_button, 0)

    def _button_handler(self, state):
        self._button_state = state
        if state == Toilet.State.ON:
            self._log.info("Toilet button pressed!")
            self.lamp_on()
        else:
            self._log.info("Toilet button disabled")
            self.lamp_off()


    def _match_action(self, action, **kwarg):
        try:
            {
                Toilet.Action.lamp_ON:
                self.lamp_on,
                Toilet.Action.lamp_OFF:
                self.lamp_off,
                Toilet.Action.BUTTON_STATE:
                lambda: self._button_handler(**kwarg)
            }[action]()
        except:
            self._log.info("", exc_info=True)

    def _initialize_gpio(self):
        self._write_reg(REGS.button_end_config, 0)
        self._write_reg(REGS.button_like_config, 0)
        self._write_reg(REGS.button_dislike_config, 0)
        self._write_reg(REGS.lamp_config_button, 1)
        self._write_reg(REGS.lamp_config_green, 1)
        self._write_reg(REGS.lamp_config_red, 1)
        self._write_reg(REGS.lamp_config_connection, 1)

    def _button_check_thread(self):
        prev_button_end = 0
        prev_button_like = 0
        prev_button_dislike = 0
        lamp_button_state = 0
        while True:
            button_end = self._read_reg(REGS.button_end)
            button_like = self._read_reg(REGS.button_like)
            button_dislike = self._read_reg(REGS.button_dislike)


            if button_end != prev_button_end:
                if button_end == True:
                    if lamp_button_state == 0:
                        self._write_reg(REGS.lamp_button,1)
                        self.paperState = self.PaperState.ABSCENT
                        self.paperMsg = 'No paper left!'
                        lamp_button_state = 1
                    else:
                        self._write_reg(REGS.lamp_button,0)
                        self.paperState = self.PaperState.LEFT
                        self.paperMsg = 'Paper is ok!'
                        lamp_button_state = 0

                
                    
            if button_like != prev_button_like:
                if button_like == True:
                    self._write_reg(REGS.lamp_green,1)
                    self.paperLikes = self.paperLikes + 1
                    self.paperScore = self.paperScore + 1 
                else:
                    self._write_reg(REGS.lamp_green,0)

            if button_dislike != prev_button_dislike:
                if button_dislike == True:
                    self._write_reg(REGS.lamp_red,1)
                    self.paperDislikes = self.paperDislikes + 1
                    self.paperScore = self.paperScore - 1 
                else:
                    self._write_reg(REGS.lamp_red,0)

            prev_button_dislike = button_dislike
            prev_button_end = button_end
            prev_button_like = button_like
                
            time.sleep(0.05)
