from collections import namedtuple
from enum import Enum
from .common import Logger
import pykka
import minimalmodbus

FunctionCode = namedtuple('FunctionCodes', ['read', 'write'])


class FunctionalCodes(Enum):
    COIL = FunctionCode(1, 5)
    DISCRETE = FunctionCode(2, None)
    INPUT = FunctionCode(4, None)
    HOLDING = FunctionCode(3, 6)


Register = namedtuple(
    'MbRegister', ['name', 'addr', 'func_code', 'count', 'value_type', 'unit'])


class Action(Enum):
    READ = 0
    WRITE = 1

class Modbus(pykka.ThreadingActor):
    __instance = None

    @classmethod
    def modbus(cls):
        if not cls.__instance:
            cls.__instance = cls.start()

        return cls.__instance

    def __init__(self):
        super().__init__()
        self._log = Logger.for_name(__name__)
        self._mb = None

    def on_receive(self, msg):
        self._mb = msg["mb"]
        if self._mb:
            reg = msg["reg"]
            if msg["action"] == Action.READ:
                return self._read(msg["reg"])
            elif msg["action"] == Action.WRITE:
                return self._write(msg["reg"], msg["value"])

    def _read(self, reg):
        try:
            if reg.func_code == FunctionalCodes.COIL:
                return bool(
                    self._mb.read_bit(reg.addr, reg.func_code.value.read))
            elif reg.value_type is float:
                return reg.value_type(
                    self._mb.read_float(reg.addr, reg.func_code.value.read))
            elif reg.value_type is str:
                return reg.value_type(
                    self._mb.read_string(reg.addr, reg.count,
                                         reg.func_code.value.read))
            else:
                return reg.value_type(
                    self._mb.read_register(reg.addr, reg.count,
                                           reg.func_code.value.read))
        except Exception as e:
            self._log.error(
                "Cannot read a \"{}\" register!".format(reg.name),
                exc_info=True)
            return None

    def _write(self, reg, val):
        try:
            if reg.func_code == FunctionalCodes.COIL:
                self._mb.write_bit(reg.addr, val, reg.func_code.value.write)
            elif reg.value_type is float:
                self._mb.write_float(reg.addr, reg.value_type(val),
                                     reg.func_code.value.write)
            elif reg.value_type is str:
                self._mb.write_string(reg.addr, reg.value_type(val))
            else:
                return self._mb.write_registers(reg.addr, val)
        except Exception as e:
            self._log.error(
                "Cannot write to a \"{}\" register!".format(reg.name),
                exc_info=True)

        return None

class ModbusUser:
    def __init__(self, mb_instrument):
        self._mb = mb_instrument
        self._mb_actor = Modbus.modbus()
    
    def _read_reg(self, reg):
        ans = self._mb_actor.ask({
            "mb": self._mb,
            "action": Action.READ,
            "reg": reg
        })

        if not ans:
            raise CannotReadARegisterValue(reg)

        return ans

    def _write_reg(self, reg, val):
        ans = self._mb_actor.ask({
            "mb": self._mb,
            "action": Action.WRITE,
            "reg": reg,
            "value": val
        })

        return ans
