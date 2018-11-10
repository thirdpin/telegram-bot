#!/usr/bin/env python
# -*- coding: utf-8 -*-

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ChatAction, ReplyKeyboardMarkup
import logging
import sys
from stuff.common import DoorOpener
from stuff.ivitmrs import IvitMRS, _find_device
import minimalmodbus

BAUDRATE = 115200
TIMEOUT = 3
PARITY = 'N'

BAUDRATE = 115200
TIMEOUT = 3
PARITY = 'N'

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

def start(bot, update):
    """Send a message when the command /start is issued."""
    
    custom_keyboard = [["/open_door"],["/get_temperature_and_humidity"]]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)
    update.message.reply_text('Hi!', reply_markup=reply_markup)

    minimalmodbus.BAUDRATE = BAUDRATE
    minimalmodbus.TIMEOUT = TIMEOUT
    minimalmodbus.PARITY = PARITY

def get_temperature_and_humidity(bot, update):
    dev_handler = _find_device(0x0403, 0x6015)
    if dev_handler:
        ivt_mrs = IvitMRS(dev_handler.device)
        msg = 'Temperature: %s. Humidity: %s' % (float("%0.1f" % ivt_mrs.temp), 
                                                 float("%0.1f" % ivt_mrs.humidity))
        update.message.reply_text(msg)
    else:
        update.message.reply_text('Something goes wrong!')

def open_door(bot, update):
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
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    """Start the bot."""
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(sys.argv[1])

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("open_door", open_door))
    dp.add_handler(CommandHandler("get_temperature_and_humidity", get_temperature_and_humidity))

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
