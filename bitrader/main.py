import asyncio
import os
from decimal import getcontext

import telepot
import telepot.aio
from dotenv import load_dotenv
from telepot.aio.loop import MessageLoop
from telepot.namedtuple import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

from bitrader.arbitrage_tools import COIN_MAP, arbitrage

"""
Main loop for Bitcoin arbitrage.
"""

coin_type = 'bitcoin'


async def on_chat_message(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    print('Chat:', content_type, chat_type, chat_id)

    if content_type != 'text':
        return

    command = msg['text'].lower()
    amount = 0

    try:
        amount = int(command)
    except ValueError:
        pass

    # markup = ReplyKeyboardRemove()
    # await bot.sendMessage(chat_id, command, reply_markup=markup)

    if command == '/start':
        markup = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text='Bitcoin'),
             KeyboardButton(text='Litecoin')],
            [KeyboardButton(text='Ethereum')],
        ])
        # await bot.sendMessage(chat_id, 'Pick coin from options in keyboard:', reply_markup=markup)
        await bot.sendMessage(
            chat_id, 'Pick coin from options in keyboard:',
            reply_markup=markup)

    elif command in ['bitcoin', 'litecoin', 'ethereum']:
        global coin_type
        coin_type = command
        markup = ReplyKeyboardRemove()
        await bot.sendMessage(chat_id, f'How much {coin_type} do you want to simulate (in ZAR)?', reply_markup=markup)

    elif amount > 0:
        await bot.sendMessage(chat_id, f'Simulating {amount} ZAR for {coin_type}...')
        coin_data = COIN_MAP[coin_type]
        message = arbitrage(amount, **coin_data)['summary']
        # import pdb; pdb.set_trace()
        await bot.sendMessage(chat_id, message, reply_to_message_id=msg['message_id'])

    else:
        print('No idea')


getcontext().prec = 8  # Set Decimal context.
load_dotenv('.env')  # Load environment

TOKEN = os.environ.get('TELEGRAM_TOKEN')  # get token from environment

bot = telepot.aio.Bot(TOKEN)
answerer = telepot.aio.helper.Answerer(bot)
loop = asyncio.get_event_loop()

loop.create_task(MessageLoop(bot, {
    'chat': on_chat_message,
}).run_forever())

print('Listening ...')

loop.run_forever()
