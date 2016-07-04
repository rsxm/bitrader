import telebot
import pandas as pd
import os
from decimal import Decimal, getcontext
from dotenv import load_dotenv, find_dotenv
from arbitrage_tools import *


getcontext().prec = 8
load_dotenv('.env')
telegram_bot = os.environ.get('TELEGRAM_TOKEN')

try:
    bot = telebot.TeleBot(telgram_bot)
except:
    print('Sorry, bad or missing bot key')


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, """Howdy, how are you doing?
I'm arbot and I simulate Bitcoin arbitrage plays.
Type /arbitrage to run a simulation""")


# Handle '/start' and '/help'
@bot.message_handler(commands=['arbitrage'])
def send_welcome(message):
    msg = bot.reply_to(message, "How much do you want to simulate (in ZAR)?")
    bot.register_next_step_handler(msg, arbitrage)


# @bot.message_handler(commands=['arbitrage'])
def arbitrage(message):
    chat_id = message.chat.id

    kraken_asks = prepare_order_book(kraken_order_book('asks'), 'asks')
    bitx_bids = prepare_order_book(bitx_order_book('bids'), 'bids')

    try:
        TRANSFER_AMOUNT = Decimal(message.text)
    except:
        bot.reply_to(message, 'oooops')

    # TRANSFER_AMOUNT = Decimal(50000)

    CURRENCY_EXCHANGE_RATE = Decimal(16.711)
    BITCOIN_EXCHANGE_RATE = Decimal(16.711)

    new = True

    try:
        if new:
            response = simulate(TRANSFER_AMOUNT,  kraken_asks, bitx_bids,
                            transfer_fees=True)
        else:
            response = simulate(TRANSFER_AMOUNT,  kraken_asks, bitx_bids,
                            exchange_rate=CURRENCY_EXCHANGE_RATE, transfer_fees=False)

        bot.reply_to(message, response['summary'])
    except KeyError:
        bot.reply_to(message, "Don't be greedy, thats to much!")

# @bot.message_handler(func=lambda message: True)
# def echo_all(message):
#     bot.reply_to(message, message.text)


bot.polling(interval=5)
