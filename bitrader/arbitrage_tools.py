""" Arbitrage tools

Tools for determining the

"""
import itertools
import os
import time
from decimal import Decimal
from http.client import HTTPException
from socket import timeout

import krakenex
import pandas as pd
import requests
from bs4 import BeautifulSoup

from bitrader import bitx
from bitrader.api_tools import Ice3xAPI

# Removed as it complicates the bot on server deploys (?)
# import seaborn as sns
# sns.set_context(font_scale=1.1)

KRAKEN_API_KEY = os.environ.get('KRAKEN_API_KEY')
KRAKEN_PRIVATE_KEY = os.environ.get('KRAKEN_PRIVATE_KEY')

BITX_KEY = os.environ.get('BITX_KEY')
BITX_SECRET = os.environ.get('BITX_SECRET')

ICE3X_KEY = os.getenv('ICE3X_KEY')  # .encode('utf-8')
ICE3X_PUBLIC = os.getenv('ICE3X_PUBLIC')  # .encode('utf-8')

CFUID = os.getenv('CFUID')

COIN_MAP = {
    'ice3x': {
        'bitcoin': dict(
            coin_code='XBT',
            coin_name='Bitcoin',
            exchange_name='Ice3x'),
        'litecoin': dict(
            coin_code='LTC',
            coin_name='Litecoin',
            exchange_name='Ice3x'),
        'ethereum': dict(
            coin_code='ETH',
            coin_name='Ethereum',
            exchange_name='Ice3x')
    },
    'luno': {
        'bitcoin': dict(
            coin_code='XBT',
            coin_name='Bitcoin',
            exchange_name='Luno'),
    },
    'kraken': {
        'bitcoin': dict(
            coin_code='XBT',
            coin_name='Bitcoin',
            exchange_name='Kraken'),
        'litecoin': dict(
            coin_code='LTC',
            coin_name='Litecoin',
            exchange_name='Kraken'),
        'ethereum': dict(
            coin_code='ETH',
            coin_name='Ethereum',
            exchange_name='Kraken'),
    },
}


def retry(delays=(5, 5, 5, 10, 5, 5, 5, 10), exception=Exception, report=lambda *args: None):
    def wrapper(function):
        def wrapped(*args, **kwargs):
            problems = []
            for delay in itertools.chain(delays, [None]):
                try:
                    return function(*args, **kwargs)
                except exception as problem:
                    problems.append(problem)
                    if delay is None:
                        report("retryable failed definitely:", problems)
                        raise
                    else:
                        report("retryable failed:", problem,
                               "-- delaying for %ds" % delay)
                        time.sleep(delay)

        return wrapped

    return wrapper


def get_forex_buy_quote(currency_code: str = 'EUR', source: str = 'FNB', order_type: str = 'buy'):
    """Get latest forex from FNB website

    """
    if source == 'FNB':
        tables = pd.read_html(
            'https://www.fnb.co.za/Controller?nav=rates.forex.list.ForexRatesList',
            index_col=1, header=0, match=currency_code)

        df = tables[0]

        types = {
            'buy': 'Bank Selling Rate',
            'sell': 'Bank Buying Rate',
        }

        exhange_rate = df.loc[currency_code, types[order_type]]

        return Decimal("%.4f" % float(exhange_rate))


@retry(exception=(HTTPException, timeout, ValueError), report=print)
def kraken_order_book(book_type: str, currency_code: str = 'EUR', coin_code: str = 'XBT', pair: str = None):
    """Kraken specific orderbook retrieval

    """
    import krakenex

    kraken_api = krakenex.API(key=KRAKEN_API_KEY, secret=KRAKEN_PRIVATE_KEY, conn=krakenex.Connection())

    if not pair:
        pair = f'X{coin_code}Z{currency_code}'
    orders = kraken_api.query_public('Depth', {'pair': pair})

    df = pd.DataFrame(
        orders['result'][pair][book_type],
        columns=['price', 'volume', 'timestamp'])

    return df


def luno_order_book(book_type: str, pair: str = 'XBTZAR'):
    """

    Args:
        book_type: 'asks' or 'bids'
        pair: Default = 'XBTZAR'.

    Returns: Dataframe with order book.

    """
    bitx_api = bitx.BitX(BITX_KEY, BITX_SECRET, options={'pair': pair})
    df = bitx_api.get_order_book_frame()

    return df[book_type]


def ice3x_order_book(book_type: str, coin_code: str = 'BTC', currency_code: str = 'ZAR'):
    """Ice3X specific orderbook retrieval
    """
    ice = Ice3xAPI(cache=False, future=False)

    pair_map = {
        'XBT': 3,
        'LTC': 6,
        'ETH': 11,
    }
    pair_id = pair_map[coin_code]

    r = ice.get_resource(
        'generic',
        api_method='orderbook',
        api_action='info',
        api_params=f'type={book_type}&pair_id={pair_id}',
        data_format='raw')

    bids = pd.DataFrame(r['response'].json()['response']['entities'])

    return bids


def prepare_order_book(order_book, book_type: str, bitcoin_column: str = 'volume', currency_column: str = 'price'):
    """Function for getting order book in standard form

    :param: book_type bids or asks
        asks is what I'll have to pay if I want to buy
        bids is what I'll get if I want to sell

    """

    options = {
        'ascending': {
            'bids': False,
            'asks': True, }}

    df = order_book.copy()
    df = df.astype(float)

    df = df.sort_values(by=currency_column, ascending=options['ascending'][book_type]).reset_index(drop=True)

    df['value'] = df[currency_column] * df[bitcoin_column]
    df['cumulative_volume'] = df[bitcoin_column].cumsum()
    df['cumulative_value'] = df.value.cumsum()

    return df


def coin_exchange(df, limit, order_type: str, bitcoin_column: str = 'volume', currency_column: str = 'value'):
    """Convert specified amount of bitcoin to currency or currency to bitcoin

    :param: order_type buy or sell
        buy exchanges currency for bitcoin
        sell exchanges bitcoins for currency

    """

    options = {
        'buy': {'from': currency_column, 'to': bitcoin_column},
        'sell': {'from': bitcoin_column, 'to': currency_column}
    }

    filtered = df.loc[df['cumulative_%s' % options[order_type]['from']] < float(limit), :]
    rows = filtered.shape[0]

    over = Decimal(df.loc[rows, 'cumulative_%s' % options[order_type]['from']]) - limit

    price = Decimal(df.loc[rows, 'price'])

    if order_type == 'buy':
        over_convert = over / price
    else:
        over_convert = over * price

    result = Decimal(df.loc[rows, 'cumulative_%s' % options[order_type]['to']]) - over_convert
    return result


def get_books(coin_code: str = 'XBT', exchange_name: str = 'Luno'):
    """

    :param coin_code: BTC, LTC, or ETH
    :param exchange_name: Luno or Ice3x
    :return:
    """
    eur_asks = prepare_order_book(kraken_order_book('asks', coin_code=coin_code), 'asks')

    if exchange_name.lower() == 'luno':
        zar_bids = prepare_order_book(luno_order_book('bids'), 'bids')
    elif exchange_name.lower() == 'ice3x':
        zar_bids = prepare_order_book(ice3x_order_book('bid', coin_code=coin_code), 'bids', bitcoin_column='amount')
    else:
        raise KeyError(f'{exchange_name} is not a valid exchange_name')

    return eur_asks, zar_bids


def arbitrage(amount, coin_code='XBT', coin_name='bitcoin', exchange_name='Luno',
              exchange_rate=None, transfer_fees: bool = True, verbose: bool = False, books=None,
              trade_fees: bool = True):
    """

    :param amount: The amount in ZAR (TODO: also allow reverse
    :param coin_code: Default = XBT. LTC and ETH also supported.
    :param coin_name: Default = Bitcoin. Litecoin and Ethereum also supported
    :param exchange_name: Luno or Ice3x.
    :param exchange_rate: The ZAR / EURO Exchange rate.
    :param transfer_fees: Whether to include FOREX fees or not. E.g. when you want to simulate money alrady in Europe.
    :param verbose: Default = False. Whether to print the summary to command line
    :param books:
    :return: Dict with ROIC and summary of arbitrage

    TODO:
        Make coin_code, coin_name, exchange_name a NamedTuple or something.
        Even better, make Exchange, Bank, Coin classes and build in stuff like exchange rates.
    """

    if not books:
        try:
            eur_asks, zar_bids = get_books(coin_code=coin_code, exchange_name=exchange_name)
        except KeyError:
            return 'Error processing order books. Check if the exchanges are working and that there are open orders.'
    else:
        eur_asks, zar_bids = books

    try:
        transfer_amount = Decimal(amount)
    except (ValueError, AttributeError):
        return 'Sorry, could not read reply.'

    try:
        if not exchange_rate:
            exchange_rate = get_forex_buy_quote('EUR')

        if transfer_fees:
            _swift_fee = Decimal(110)
            _fnb_comission = min(max(transfer_amount * Decimal(0.0055), Decimal(140)), Decimal(650))
            _kraken_deposit_fee = Decimal(15)  # Fees: https://www.kraken.com/en-us/help/faq
        else:
            _swift_fee = Decimal(0)
            _fnb_comission = Decimal(0)
            _kraken_deposit_fee = Decimal(0)

        capital = transfer_amount + _fnb_comission + _swift_fee

        euros = transfer_amount / exchange_rate - _kraken_deposit_fee
        _kraken_fee = euros * Decimal(0.0026)  # TODO: Allow to specify lower tier, e.g. over $50k = 0.0024

        _kraken_withdrawal_fee = Decimal(0.001)
        _luno_deposit_fee = Decimal(0.0002)

        bitcoins = coin_exchange(eur_asks, euros - _kraken_fee, 'buy') - _kraken_withdrawal_fee - _luno_deposit_fee

        if trade_fees:
            _luno_fees = bitcoins * Decimal(0.01)  # TODO: Allow to specify lower tier, e.g. over 10 BTC = 0.0075
        else:
            _luno_fees = Decimal(0)

        if transfer_fees:
            _luno_withdrawel_fee = Decimal(8.5)  # TODO: Check Ice3x fees
        else:
            _luno_withdrawel_fee = Decimal(0)

        rands = coin_exchange(zar_bids, bitcoins - _luno_fees, 'sell')

        btc_zar_exchange_rate = rands / (bitcoins - _luno_fees)

        return_value = rands - _luno_withdrawel_fee

        total_fees = (
                _swift_fee +
                _fnb_comission +
                _kraken_fee * exchange_rate +
                _kraken_deposit_fee * exchange_rate +
                _kraken_withdrawal_fee * btc_zar_exchange_rate +
                _luno_deposit_fee * btc_zar_exchange_rate +
                _luno_fees * btc_zar_exchange_rate +
                _luno_withdrawel_fee)

        response = [
            f'Rands out: {capital:.2f}',
            f'# forex conversion: R{_swift_fee + _fnb_comission:.2f}',
            f'Euro: {euros:.2f}',
            f'# kraken deposit and withdraw fee: R{(_kraken_deposit_fee * exchange_rate) + (_kraken_withdrawal_fee * btc_zar_exchange_rate):.2f}',
            f'# kraken trade fee: R{(_kraken_fee * exchange_rate):.2f}',
            f'{coin_name}: {bitcoins:.8f}',
            f'# {exchange_name} deposit and withdraw fee: R{_luno_withdrawel_fee + (_luno_deposit_fee * btc_zar_exchange_rate):.2f}',
            f'# {exchange_name} trade fee: R{(_luno_fees * btc_zar_exchange_rate):.2f}',
            f'Rands in: {rands:.2f}',
            '--------------------',
            f'Profit: {return_value - capital:.2f}',
            f'ROI: {((return_value - capital) / capital) * 100:.2f}',
            '--------------------',
            f'ZAR/EUR: {exchange_rate:.2f}',
            f'EUR/{coin_code}: {(euros - _kraken_fee) / bitcoins:.2f}',
            f'{coin_code}/ZAR: {btc_zar_exchange_rate:.2f}',
            '--------------------',
            f'Total fees: R{total_fees:.2f}',
        ]

        if verbose:
            print('\n'.join(response))

        return {'roi': ((return_value - capital) / capital) * 100, 'summary': '\n'.join(response)}

    except KeyError:
        return "Don't be greedy, that's too much!"


def optimal(max_invest: int = 1000000, coin: str = 'bitcoin', exchange='luno', return_format: str = 'text',
            exchange_rate: Decimal = None):
    """

    Args:
        max_invest:
        coin: bitcoin, litecoin, ethereum
        exchange: luno, ice3x or kraken
        return_format: text or picture
        exchange_rate:
    """

    if not exchange_rate:
        exchange_rate = get_forex_buy_quote('EUR')

    books = get_books(
        coin_code=COIN_MAP[exchange][coin]['coin_code'],
        exchange_name=COIN_MAP[exchange][coin]['exchange_name']
    )

    results = []
    for amount in range(20000, max_invest, 5000):

        try:
            results.append(
                dict(
                    amount=amount, roi=arbitrage(
                        amount=amount,
                        exchange_rate=exchange_rate,
                        books=books,
                        transfer_fees=True,
                        **COIN_MAP[exchange][coin],
                    )['roi']))
        except Exception as e:
            print(e)
            break

    df = pd.DataFrame(results)
    df.amount = df.amount.astype(float)
    df = df.set_index('amount')
    df.roi = df.roi.astype(float)

    max_roi = df.max()

    try:
        near_optimal = df.loc[df.roi > max_roi * (1 - 0.001)].reset_index()
        invest_amount = near_optimal.iloc[0].amount
        invest_roi = near_optimal.iloc[0].roi
    except:
        return df

    if return_format == 'text':
        return f'Ideal invest amount: {invest_amount} with ROI of {invest_roi:.2f}'
    elif return_format == 'values':
        return invest_amount, near_optimal
    elif return_format == 'raw':
        return df
    elif return_format == 'png':
        raise NotImplementedError('Not yet implemented')
    else:
        raise KeyError(f'Invalid return_format selection {return_format}')


def reverse_arb(amount, coin='litecoin', exchange_buy='ice3x', exchange_sell='kraken'):
    """

    :param amount:
    :param coin:
    :return:
    """
    if coin in ['litecoin', 'ethereum']:
        zar_asks = prepare_order_book(
            ice3x_order_book(
                'ask', coin_code=COIN_MAP[exchange_buy][coin]['coin_code']), 'asks', bitcoin_column='amount')
    else:
        zar_asks = prepare_order_book(luno_order_book('asks'), 'asks')

    eur_bids = prepare_order_book(
        kraken_order_book('bids', coin_code=COIN_MAP[exchange_sell][coin]['coin_code']), 'asks')

    coins = coin_exchange(zar_asks, amount, 'buy')
    euro = coin_exchange(eur_bids, coins, 'sell')

    zar_asks = prepare_order_book(luno_order_book('bids'), 'bids')

    exchange_rate = get_forex_buy_quote('EUR')
    rands = euro * exchange_rate

    return f'R{amount:.0f}, R{rands:.0f}, {(rands - amount)/amount * 100:.2f}%'


@retry(exception=(HTTPException, timeout, ValueError), report=print)
def get_balance(asset: str = None):
    kraken_api = krakenex.API(key=KRAKEN_API_KEY, secret=KRAKEN_PRIVATE_KEY, conn=krakenex.Connection())
    balance = kraken_api.query_private('Balance')

    if asset is not None:
        amount = balance['result']['X' + asset]
        print('{asset} balance: {amount}'.format(asset=asset, amount=amount))
        return amount
    else:
        return balance


@retry(exception=(HTTPException, timeout, ValueError), report=print)
def withdraw(asset: str = 'XBT', wallet_key: str = 'Luno', amount=None):
    kraken_api = krakenex.API(key=KRAKEN_API_KEY, secret=KRAKEN_PRIVATE_KEY, conn=krakenex.Connection())

    if amount is None:
        amount = get_balance(asset=asset)
        amount = round(float(amount), 8)
    if round(float(amount), 2) > 0:
        result = kraken_api.query_private('Withdraw', {'asset': asset, 'key': wallet_key, 'amount': amount})
        print('Success!!', result)
        return result
    else:
        print('All funds have been withdrawn from f{wallet_key}')


@retry(exception=(HTTPException, timeout, ValueError), report=print)
def get_coins(amount=None):
    if not amount:
        # Use full balance
        kraken_api = krakenex.API(key=KRAKEN_API_KEY, secret=KRAKEN_PRIVATE_KEY, conn=krakenex.Connection())
        amount = kraken_api.query_private('Balance')['result']['ZEUR']
        print(amount)

    eur_asks = prepare_order_book(
        kraken_order_book('asks', coin_code='XBT'), 'asks')

    coins = coin_exchange(eur_asks, Decimal(amount), 'buy')
    coins = str(round(coins, 6))
    return coins


@retry(exception=(HTTPException, timeout, ValueError), report=print)
def buy_coins(euro=None, coins=None):
    if coins is None:
        coins = get_coins(amount=euro)

    kraken_api = krakenex.API(key=KRAKEN_API_KEY, secret=KRAKEN_PRIVATE_KEY, conn=krakenex.Connection())
    result = kraken_api.query_private(
        'AddOrder', {'pair': 'XXBTZEUR', 'type': 'buy', 'ordertype': 'market', 'volume': coins})

    return result


def truncate(f, n):
    """Truncates/pads a float f to n decimal places without rounding"""
    s = '{}'.format(f)
    if 'e' in s or 'E' in s:
        return '{0:.{1}f}'.format(f, n)
    i, p, d = s.partition('.')
    return '.'.join([i, (d + '0' * n)[:n]])


def altcointrader_order_books(cfduid: str):
    """To use this function you need to manually get the cfduid  by copying the cookie value from your browser.

    """
    s = requests.Session()
    s.headers.update({
        'User-Agent':
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
    })
    s.cookies.update({
        '__cfduid': cfduid,
    })

    assets = [
        ('xbt', '/'),
        #     ('bch', '/bcc'),
        #     ('btg', '/btg'),
        ('ltc', '/ltc'),
        #     ('nmc', '/nmc'),
        ('xrp', '/xrp'),
        ('eth', '/eth'),
        #     ('dash', '/dash'),
        #     ('zec', '/zec'),
    ]

    base_url = 'https://www.altcointrader.co.za'
    order_book = {}

    for code, path in assets:
        r = s.get(base_url + path)
        soup = BeautifulSoup(r.text, "html.parser")
        asks = []
        bids = []
        for row in soup.select('tr.orderUdSell'):
            asks.append({
                'volume': row.select_one('.orderUdSAm').text,
                'price': row.select_one('.orderUdSPr').text
            })

        for row in soup.select('tr.orderUdBuy'):
            bids.append({
                'volume': row.select_one('.orderUdBAm').text,
                'price': row.select_one('.orderUdBPr').text
            })

        order_book.update({code: {
            'timestamp': int(time.time() * 1000),
            'asks': asks,
            'bids': bids,
        }})
    return order_book
