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
import minimalmodbus
import json

BAUDRATE = 115200
TIMEOUT = 3
PARITY = 'N'

LIMITED_ACCESS_USER_IDS = []
LIMITED_ACCESS_USER_IDS_FILE = "ids.json"

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


def start(bot, update):
    """Send a message when the command /start is issued."""

    custom_keyboard = [["/open_door"], ["/get_temperature_and_humidity"]]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)
    update.message.reply_text('Hi!', reply_markup=reply_markup)


def get_temperature_and_humidity(bot, update):
    dev_handler = _find_device(0x0403, 0x6015)
    if dev_handler:
        ivt_mrs = IvitMRS(dev_handler.device)
        msg = 'Temperature: {t:0.1f}C. '\
              'Humidity: {h:0.1f}%'.format(
            t=ivt_mrs.temp,
            h=ivt_mrs.humidity)

        update.message.reply_text(msg)
    else:
        update.message.reply_text('Something goes wrong!')


def open_door(bot, update):
    global LIMITED_ACCESS_USER_IDS

    logger = _Logger.instance()

    if update.message.chat.id not in LIMITED_ACCESS_USER_IDS:
        update.message.reply_text('Sorry, but this function is not '
                                  'avaliable for you, pal.')
        logger.warn('An attempt of restricted access, user {}'.format(
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


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger = _Logger.instance()
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    """Start the bot."""

    minimalmodbus.BAUDRATE = BAUDRATE
    minimalmodbus.TIMEOUT = TIMEOUT
    minimalmodbus.PARITY = PARITY

    global LIMITED_ACCESS_USER_IDS
    with open(LIMITED_ACCESS_USER_IDS_FILE) as f:
        data = json.load(f)
        LIMITED_ACCESS_USER_IDS = data["ids"]

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(sys.argv[1])

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("open_door", open_door))
    dp.add_handler(
        CommandHandler("get_temperature_and_humidity",
                       get_temperature_and_humidity))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
