#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import time

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ChatAction, ReplyKeyboardMarkup

import logging
import requests 
import html2text

from logging.handlers import RotatingFileHandler
from threading import Thread

from mbdevs.dooropener import DoorOpener, Action
from mbdevs.dooropener import Action as DoorAction
from mbdevs.dooropener2 import DoorOpener2
from mbdevs.dooropener2 import Action as DoorAction2
from mbdevs.trafflight import TrafficLight
from mbdevs.emergency import Emergency
from mbdevs import ivitmrs
from mbdevs.ivitmrs import IvitMRS
from mbdevs.ivitmrs import REGS as IVIT_MRS_REGS
from mbdevs.toilet import Toilet
from mbdevs.toiletdudka import ToiletDudka


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
            self._door2 = DoorOpener2.from_vid_pid(0x0403, 0x6015)
            self._trafflight = TrafficLight.from_vid_pid(0x0403, 0x6015)
            self._emergency = Emergency.from_vid_pid(0x0403, 0x6015)
            self._toiletdudka = ToiletDudka.from_vid_pid(0x0403, 0x6015)
            self._toilet = Toilet.from_vid_pid(0x0403, 0x6015)
            self._toilet.ask({"action":'connected'})

            self._door_manager_th = Thread(target = self._door_manager_thread)
            self._door_manager_th.start()

            self._button_check_th = Thread(target=self._button_check_thread)
            self._button_check_th.start()


            try:
                with open(full_access_ids_file) as f:
                    self._full_access_users = json.load(f)["ids"]
            except FileNotFoundError as e:
                self._log.error(
                    "File \"{}\" with full access IDs is not found!".format(
                        full_access_ids_file))
                raise e

        def _door_manager_thread(self):
            prevButtonState1 = True
            prevButtonState2 = True
            tim1 = 0
            tim2 = 0
            while True:
                buttonState2 = self._door2.ask({"action":DoorAction2.CHECK_BUTTON})
                buttonState1 = self._door.ask({"action":DoorAction.CHECK_BUTTON})
                
                if buttonState2 != prevButtonState2:
                    if buttonState2 == False:
                        if tim1 <= 2:
                            time.sleep(3)
                            self._door.tell(({"action":DoorAction.OPEN}))
                            time.sleep(3)
                            self._door.tell(({"action":DoorAction.OPEN}))
                            time.sleep(3)
                            self._door.tell(({"action":DoorAction.OPEN}))
                        tim1 = 0

                if buttonState1 != prevButtonState1:
                    if buttonState1 == False:
                        if tim2 <= 2:
                            time.sleep(3)
                            self._door2.tell(({"action":DoorAction2.OPEN}))
                            time.sleep(3)
                            self._door2.tell(({"action":DoorAction2.OPEN}))
                            time.sleep(3)
                            self._door2.tell(({"action":DoorAction2.OPEN}))
                        tim2 = 0

                prevButtonState1 = buttonState1
                prevButtonState2 = buttonState2
                time.sleep(0.05)
                tim1 = tim1 + 0.05
                tim2 = tim2 + 0.05

        def _button_check_thread(self):
            prev_msg = 'abcd'
            while True:
                msg = self._toilet.ask({"action":'is_paper_left'})
                if msg != prev_msg:
                    if msg == 'No paper left!':
                        self._toiletdudka.tell({"action":ToiletDudka.Action.SOUND_ON})
                    else:
                        self._toiletdudka.tell({"action":ToiletDudka.Action.SOUND_OFF})
                        self._trafflight.tell({
                        "action": TrafficLight.Action.OFF,
                        "color": TrafficLight.Color.ALL
                        })
                if msg == 'No paper left!':
                        self._toiletdudka.tell({"action":ToiletDudka.Action.SOUND_ON})
                        self._trafflight.tell({
                        "action":
                        TrafficLight.Action.SEQUENCE,
                        "sleep_time":
                        0.05,
                        "colors":
                        (TrafficLight.Color.GREEN, TrafficLight.Color.YELLOW,
                        TrafficLight.Color.RED,TrafficLight.Color.GREEN, TrafficLight.Color.YELLOW,
                        TrafficLight.Color.RED)
                        })
                prev_msg = msg
                time.sleep(0.5)

        def start(self, bot, update):
            """Send a message when the command /start is issued."""

            custom_keyboard = [["/open_door"],
                               ["/open_door_2"], 
                               ["/get_temperature_and_humidity"],
                               ["/is_paper_left"],
                               ["/get_toilet_score"],
                               ["/tell_a_joke"]]
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

        def is_paper_left(self, bot, update):
            try:
                msg = self._toilet.ask({"action":'is_paper_left'})
                update.message.reply_text(msg)
            except Exception as e:
                self._log.error(
                    "Error while connection with a paper button!",
                    exc_info=True)
                update.message.reply_text('Something goes wrong!')

        def get_toilet_score(self, bot, update):
            try:
                msg = self._toilet.ask({"action":'get_paper_score'})
                update.message.reply_text(msg)
            except Exception as e:
                self._log.error(
                    "Error while connection with a paper module!",
                    exc_info=True)
                update.message.reply_text('Something goes wrong!')

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
        
        def tell_a_joke(self,bot,update):
            url = 'https://bash.im/random/'
            r = requests.get(url)
            i = r.text.find('<div class="text">')
            k = r.text.find('</div>',i)
            update.message.reply_text(html2text.html2text(r.text[i:k+6]))


        def open_door_2(self, bot, update):
            self._log.info("User opening door: {}".format(
                update.message.chat.id))

            if not self._check_user_access(update):
                return

            update.message.reply_text('Opening the door...')
            try:
                not_is_opened = self._door2.ask({"action": DoorAction2.OPEN})
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
    dp.add_handler(CommandHandler("tell_a_joke", bot.tell_a_joke))
    dp.add_handler(CommandHandler("open_door_2", bot.open_door_2))
    dp.add_handler(
        CommandHandler("get_temperature_and_humidity",
                       bot.get_temperature_and_humidity))
    dp.add_handler(CommandHandler("get_toilet_score", bot.get_toilet_score))
    dp.add_handler(CommandHandler("is_paper_left", bot.is_paper_left))
    

    # Log all errors
    dp.add_error_handler(bot.error)

    #Starting special thread to check if toilet button pressed


    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
