#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
from collections import namedtuple

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ChatAction, ReplyKeyboardMarkup

import logging
from logging.handlers import RotatingFileHandler

from stuff.dooropener import DoorOpener
from stuff import ivitmrs
from stuff.ivitmrs import IvitMRS
from stuff.ivitmrs import REGS as IVIT_MRS_REGS


class _BotLogger():
    def __init__(self):
        if not _BotLogger.is_inited:
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

            _BotLogger.is_inited = True
        else:
            self._logger = logging.getLogger(__name__)

    @property
    def logger(self):
        return self._logger

    def instance():
        return _BotLogger()._logger

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
            self._log = _BotLogger.instance()
            self._ivt_mrs = IvitMRS.from_vid_pid(0x0403, 0x6015)

            try:
                with open(full_access_ids_file) as f:
                    self._full_access_users = json.load(f)["ids"]
            except FileNotFoundError as e:
                self._log.error(
                    "File \"{}\" with full access IDs is not found!".format(
                        full_access_ids_file))
                raise e

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
            try:
                msg = 'Temperature: {t:0.1f}{t_units:s}. '\
                    'Humidity: {h:0.1f}{h_units:s}.'.format(
                    t=self._ivt_mrs.temp, t_units=IVIT_MRS_REGS.temp.unit,
                    h=self._ivt_mrs.humidity, h_units=IVIT_MRS_REGS.humidity.unit)

                update.message.reply_text(msg)
            except Exception as e:
                self._log.error(
                    "Error while connection with a temp sensor!", exc_info=True)
                update.message.reply_text('Something goes wrong!')

        def open_door(self, bot, update):
            if not self._check_user_access(update.message.chat.id):
                return

            update.message.reply_text('Opening the door...')
            device = DoorOpener(spider_id=1)
            device.open()
            device.initialize()
            if not device.door_stuff():
                update.message.reply_text('Cannot open the door.')
            else:
                update.message.reply_text('The door was opened.')

        def error(self, bot, update, error):
            """Log Errors caused by Updates."""
            self._log.warning('Update "%s" caused error "%s"', update, error)

        def _check_user_access(self, user_id):
            if user_id not in self._full_access_users:
                update.message.reply_text('Sorry, but this function is not '
                                          'avaliable for you, pal.')
                self._log.warn(
                    'An attempt of a restricted access, user {}'.format(user_id))
                return False
            else:
                return True


def main():
    """Start the bot."""
    log = _BotLogger.instance()

    # Make a bot instance
    try:
        bot = Bot.make_bot()
    except Exception as e:
        log.error(
            "Can not create a bot instance:", exc_info=True)
        raise e

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
