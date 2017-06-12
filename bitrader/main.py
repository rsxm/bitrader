import os
from decimal import Decimal, getcontext
from functools import partial

import telebot
from dotenv import load_dotenv

from bitrader.arbitrage_tools import (
    bitx_order_book, kraken_order_book, prepare_order_book, simulate, ice3x_order_book)

getcontext().prec = 8
load_dotenv('.env')
telegram_bot = os.environ.get('TELEGRAM_TOKEN')

bot = telebot.TeleBot(telegram_bot)


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


# Handle '/arbilite'
@bot.message_handler(commands=['arbilite'])
def arbilite(message):
    msg = bot.reply_to(message, "How much do you want to simulate (in ZAR)?")
    bot.register_next_step_handler(msg, arbitrage_lite)


# @bot.message_handler(commands=['arbitrage'])
def arbitrage(message):
    chat_id = message.chat.id

    kraken_asks = prepare_order_book(kraken_order_book('asks'), 'asks')
    bitx_bids = prepare_order_book(bitx_order_book('bids'), 'bids')

    try:
        transfer_amount = Decimal(message.text)
    except:
        transfer_amount = 0
        bot.reply_to(message, 'Sorry, could not read reply.')

    currency_exchange_rate = Decimal(16.711)

    new = True

    try:
        if new:
            response = simulate(transfer_amount, kraken_asks, bitx_bids, transfer_fees=True)
        else:
            response = simulate(
                transfer_amount, kraken_asks, bitx_bids, exchange_rate=currency_exchange_rate, transfer_fees=False)

        bot.reply_to(message, response['summary'])
    except KeyError:
        bot.reply_to(message, "Don't be greedy, that's too much!")


# @bot.message_handler(commands=['arbitrage'])
def arbitrage_lite(message):
    chat_id = message.chat.id

    kraken_asks = prepare_order_book(kraken_order_book('asks', coin_code='LTC'), 'asks')
    icex3_bids = prepare_order_book(ice3x_order_book('bid'), 'bids', bitcoin_column='amount')

    try:
        transfer_amount = Decimal(message.text)
    except:
        transfer_amount = 0
        bot.reply_to(message, 'Sorry, could not read reply.')

    currency_exchange_rate = Decimal(16.711)

    new = True

    sim = partial(simulate, coin_code='LTC', coin_name='Litecoin', exchange_name='Ice3x')

    try:
        if new:
            response = sim(
                transfer_amount, kraken_asks, icex3_bids, transfer_fees=True)
        else:
            response = sim(
                transfer_amount, kraken_asks, icex3_bids, exchange_rate=currency_exchange_rate, transfer_fees=False)

        bot.reply_to(message, response['summary'])
    except KeyError:
        bot.reply_to(message, "Don't be greedy, that's too much!")


def main():
    print('Listening for messages...')
    bot.polling(interval=5)


if __name__ == '__main__':
    main()
