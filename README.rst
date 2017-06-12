========
BITRADER
========

Bitcoin Arbitrage utilities. Jupyter notebook and Telegram bot included for free!

Quickstart
==========

1. Download code and install dependencies
-----------------------------------------

.. code-block:: bash

    git clone https://github.com/jr-minnaar/bitrader.git
    cd bitrader
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cp example.env .env


2. Configure secrets
--------------------

- Get your Telegram Bot token: https://core.telegram.org/bots#3-how-do-i-create-a-bot
- Sign up with [Kraken](https://www.kraken.com) and get your API key under Settings -> API
- Do the same for [BitX](https://www.bitx.co)

Edit the .env file and add all the relevant keys and tokens as indicated by the example .env file.

3. Run the bot
--------------

.. code-block:: bash

    python arbot.py

Then type /start in chat with your brand new Bitcoin Arbitrage bot.

4. Profit!!!
------------




