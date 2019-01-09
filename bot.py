#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import time

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ChatAction, ReplyKeyboardMarkup

import logging
from logging.handlers import RotatingFileHandler

from mbdevs.dooropener import DoorOpener, Action
from mbdevs.dooropener import Action as DoorAction
from mbdevs.trafflight import TrafficLight
from mbdevs.emergency import Emergency
from mbdevs import ivitmrs
from mbdevs.ivitmrs import IvitMRS
from mbdevs.ivitmrs import REGS as IVIT_MRS_REGS


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


FULL_ACCESS_USER_IDS_FILE = "ids.json"


class Bot(object):
    @classmethod
    def make_bot(
            cls,
            full_access_ids_file=FULL_ACCESS_USER_IDS_FILE,
    ):
        log = _BotLogger.instance()
        return cls._BotImpl(full_access_ids_file)

    class _BotImpl(object):
        def __init__(self, full_access_ids_file):
            self._full_access_users = list()
            self._log = _BotLogger.instance()
            self._ivt_mrs = IvitMRS.from_vid_pid(0x0403, 0x6015)
            self._door = DoorOpener.from_vid_pid(0x0403, 0x6015)
            self._trafflight = TrafficLight.from_vid_pid(0x0403, 0x6015)
            self._emergency = Emergency.from_vid_pid(0x0403, 0x6015)

            try:
                with open(full_access_ids_file) as f:
                    self._full_access_users = json.load(f)["ids"]
            except FileNotFoundError as e:
                self._log.error(
                    "File \"{}\" with full access IDs is not found!".format(
                        full_access_ids_file))
                raise e

        def start(self, bot, update):
            """Send a message when the command /start is issued."""

            custom_keyboard = [["/open_door"],
                               ["/get_temperature_and_humidity"]]
            reply_markup = ReplyKeyboardMarkup(
                custom_keyboard, resize_keyboard=True)
            update.message.reply_text('Hi!', reply_markup=reply_markup)

        def _traffic_light(self):
            '''Just for lulz aka test'''

            self._trafflight.tell({
                "action":
                TrafficLight.Action.SEQUENCE,
                "sleep_time":
                0.1,
                "colors":
                (TrafficLight.Color.GREEN, TrafficLight.Color.YELLOW,
                 TrafficLight.Color.RED, TrafficLight.Color.GREEN,
                 TrafficLight.Color.YELLOW, TrafficLight.Color.YELLOW,
                 TrafficLight.Color.GREEN, TrafficLight.Color.RED,
                 TrafficLight.Color.YELLOW, TrafficLight.Color.GREEN)
            })

            self._trafflight.tell({
                "action": TrafficLight.Action.OFF,
                "color": TrafficLight.Color.ALL
            })

        def get_temperature_and_humidity(self, bot, update):
            try:
                msg = 'Temperature: {t:0.1f}{t_units:s}. '\
                    'Humidity: {h:0.1f}{h_units:s}.'.format(
                    t=self._ivt_mrs.temp, t_units=IVIT_MRS_REGS.temp.unit,
                    h=self._ivt_mrs.humidity, h_units=IVIT_MRS_REGS.humidity.unit)

                update.message.reply_text(msg)
            except Exception as e:
                self._log.error(
                    "Error while connection with a temp sensor!",
                    exc_info=True)
                update.message.reply_text('Something goes wrong!')

            self._traffic_light()

        def open_door(self, bot, update):
            self._log.info("User opening door: {}".format(
                update.message.chat.id))

            if not self._check_user_access(update):
                return

            update.message.reply_text('Opening the door...')
            try:
                not_is_opened = self._door.ask({"action": DoorAction.OPEN})
                if not_is_opened:
                    update.message.reply_text('The door was opened.')
                    self._trafflight.tell({
                        "action":
                        TrafficLight.Action.SEQUENCE,
                        "sleep_time":
                        0.5,
                        "colors":
                        (TrafficLight.Color.GREEN, TrafficLight.Color.GREEN,
                        TrafficLight.Color.GREEN, TrafficLight.Color.GREEN,
                        TrafficLight.Color.GREEN, TrafficLight.Color.GREEN)
                    })
                else:
                    update.message.reply_text('The door is already opened.')
            except Exception as e:
                self._log.error(
                    "Error while connection with a door opener!",
                    exc_info=True)
                update.message.reply_text('Cannot open the door.')

        def error(self, bot, update, error):
            """Log Errors caused by Updates."""
            self._log.warning('Update "%s" caused error "%s"', update, error)

        def _check_user_access(self, update):
            if update.message.chat.id not in self._full_access_users:
                update.message.reply_text('Sorry, but this function is not '
                                          'avaliable for you, pal.')
                self._log.warn(
                    'An attempt of a restricted access, user {}'.format(
                        update.message.chat.id))
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
        log.error("Can not create a bot instance:", exc_info=True)
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
    dp.add_error_handler(bot.error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
