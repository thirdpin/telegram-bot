from collections import namedtuple
import minimalmodbus

ModBusDefaults = namedtuple(
    "BotDefaults",
    ["MB_BAUDRATE", "MB_PARITY", "MB_TIMEOUT", "CLOSE_PORT_AFTER_EACH_CALL"])

MB_DEFAULTS = ModBusDefaults(
    MB_BAUDRATE=115200,
    MB_PARITY='N',
    MB_TIMEOUT=3,
    CLOSE_PORT_AFTER_EACH_CALL=True)

minimalmodbus.BAUDRATE = MB_DEFAULTS.MB_BAUDRATE
minimalmodbus.TIMEOUT = MB_DEFAULTS.MB_TIMEOUT
minimalmodbus.PARITY = MB_DEFAULTS.MB_PARITY
minimalmodbus.CLOSE_PORT_AFTER_EACH_CALL = MB_DEFAULTS.CLOSE_PORT_AFTER_EACH_CALL


def mb_init(baudrate=MB_DEFAULTS.MB_BAUDRATE,
            parity=MB_DEFAULTS.MB_PARITY,
            timeout=MB_DEFAULTS.MB_TIMEOUT,
            close_port_after_each_call=MB_DEFAULTS.CLOSE_PORT_AFTER_EACH_CALL):
    minimalmodbus.BAUDRATE = baudrate
    minimalmodbus.PARITY = parity
    minimalmodbus.TIMEOUT = timeout
    minimalmodbus.CLOSE_PORT_AFTER_EACH_CALL = close_port_after_each_call
