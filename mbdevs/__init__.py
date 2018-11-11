from collections import namedtuple
import minimalmodbus

ModBusDefaults = namedtuple(
    "BotDefaults",
    ["MB_BAUDRATE", "MB_PARITY", "MB_TIMEOUT"])

MB_DEFAULTS = ModBusDefaults(
    MB_BAUDRATE=115200,
    MB_PARITY='N',
    MB_TIMEOUT=3
)

minimalmodbus.BAUDRATE = MB_DEFAULTS.MB_BAUDRATE
minimalmodbus.TIMEOUT = MB_DEFAULTS.MB_TIMEOUT
minimalmodbus.PARITY = MB_DEFAULTS.MB_PARITY

def mb_init(mb_baudrate=MB_DEFAULTS.MB_BAUDRATE,
            mb_parity=MB_DEFAULTS.MB_PARITY,
            mb_timeout=MB_DEFAULTS.MB_TIMEOUT):
    minimalmodbus.BAUDRATE = mb_baudrate
    minimalmodbus.PARITY = mb_parity
    minimalmodbus.TIMEOUT = mb_timeout
