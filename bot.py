#!/usr/bin/env python
# -*- coding: utf-8 -*-

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ChatAction, ReplyKeyboardMarkup
import logging
from logging.handlers import RotatingFileHandler
import sys
from stuff.common import DoorOpener
from stuff import ivitmrs
from stuff.ivitmrs import IvitMRS, _find_device
from stuff.ivitmrs import REGS as IVIT_MRS_REGS
import json
from collections import namedtuple


class _Logger():
    def __init__(self):
        if not _Logger.is_inited:
            __formatter = logging.Formatter(
                '%(asctime)s_%(name)s_%(levelname)s: %(message)s')

            __ch = logging.StreamHandler()
            __ch.setFormatter(__formatter)
            __ch.setLevel(logging.INFO)

            __fh = RotatingFileHandler(
                "log.txt", maxBytes=1048576, backupCount=5)
            __fh.setFormatter(__formatter)
            __fh.setLevel(logging.DEBUG)

            self._logger = logging.getLogger(__name__)
            self._logger.addHandler(__fh)
            self._logger.addHandler(__ch)
            self._logger.setLevel(logging.DEBUG)

            _Logger.is_inited = True
        else:
            self._logger = logging.getLogger(__name__)

    @property
    def logger(self):
        return self._logger

    def instance():
        return _Logger()._logger

    is_inited = False


BotDefaults = namedtuple(
    "BotDefaults",
    ["MB_BAUDRATE", "MB_PARITY", "MB_TIMEOUT", "FULL_ACCESS_USER_IDS_FILE"])

_BOT_DEFAULTS = BotDefaults(
    MB_BAUDRATE=115200,
    MB_PARITY='N',
    MB_TIMEOUT=3,
    FULL_ACCESS_USER_IDS_FILE="ids.json")


class Bot(object):
    @classmethod
    def make_bot(cls,
                 full_access_ids_file=_BOT_DEFAULTS.FULL_ACCESS_USER_IDS_FILE,
                 mb_baudrate=_BOT_DEFAULTS.MB_BAUDRATE,
                 mb_parity=_BOT_DEFAULTS.MB_PARITY,
                 mb_timeout=_BOT_DEFAULTS.MB_TIMEOUT):
        return cls._BotImpl(full_access_ids_file, mb_baudrate, mb_parity,
                            mb_timeout)

    class _BotImpl(object):
        def __init__(self, full_access_ids_file, mb_baudrate, mb_parity,
                     mb_timeout):
            self._full_access_users = list()
            self._log = _Logger.instance()

            with open(full_access_ids_file) as f:
                self._full_access_users = json.load(f)["ids"]

            import minimalmodbus
            minimalmodbus.BAUDRATE = mb_baudrate
            minimalmodbus.TIMEOUT = mb_timeout
            minimalmodbus.PARITY = mb_parity

        def start(self, bot, update):
            """Send a message when the command /start is issued."""

            custom_keyboard = [["/open_door"],
                               ["/get_temperature_and_humidity"]]
            reply_markup = ReplyKeyboardMarkup(
                custom_keyboard, resize_keyboard=True)
            update.message.reply_text('Hi!', reply_markup=reply_markup)

        def get_temperature_and_humidity(self, bot, update):
            dev_handler = _find_device(0x0403, 0x6015)
            if dev_handler:
                ivt_mrs = IvitMRS(dev_handler.device)
                msg = 'Temperature: {t:0.1f}{t_units:s}. '\
                    'Humidity: {h:0.1f}{h_units:s}'.format(
                    t=ivt_mrs.temp, t_units=IVIT_MRS_REGS.temp.unit,
                    h=ivt_mrs.humidity, h_units=IVIT_MRS_REGS.humidity.unit)

                update.message.reply_text(msg)
            else:
                update.message.reply_text('Something goes wrong!')

        def open_door(self, bot, update):
            if update.message.chat.id not in self._full_access_users:
                update.message.reply_text('Sorry, but this function is not '
                                          'avaliable for you, pal.')
                self._log.warn(
                    'An attempt of restricted access, user {}'.format(
                        update.message.chat.id))
                return

            update.message.reply_text('Opening door...')
            SPIDER_ID = 1
            device = DoorOpener(SPIDER_ID)
            device.open()
            device.initialize()
            if not device.door_stuff():
                update.message.reply_text('Cannot open door')
            else:
                update.message.reply_text('Door opened')

        def error(self, bot, update, error):
            """Log Errors caused by Updates."""
            self._log.warning('Update "%s" caused error "%s"', update, error)


def main():
    """Start the bot."""

    # Make a bot instance
    bot = Bot.make_bot()

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(sys.argv[1])

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # On different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", bot.start))
    dp.add_handler(CommandHandler("open_door", bot.open_door))
    dp.add_handler(
        CommandHandler("get_temperature_and_humidity",
                       bot.get_temperature_and_humidity))

    # Log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
