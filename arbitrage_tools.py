""" Arbitrage tools

Tools for determining the

"""
import pandas as pd
import os
from decimal import Decimal

KRAKEN_API_KEY = os.environ.get('KRAKEN_API_KEY')
KRAKEN_PRIVATE_KEY = os.environ.get('KRAKEN_PRIVATE_KEY')
BITX_KEY = os.environ.get('BITX_KEY')
BITX_SECRET = os.environ.get('BITX_SECRET')


def get_forex_buy_quote(currency_code: str = 'EUR', source: str ='FNB'):
    """Get latest forex from FNB website

    """
    if source == 'FNB':
        tables = pd.read_html(
            'https://www.fnb.co.za/Controller?nav=rates.forex.list.ForexRatesList',
            index_col=1, header=0, match=currency_code)

        df = tables[0]
        exhange_rate = df.loc[currency_code, 'Bank Selling Rate']

        return Decimal("%.4f" % float(exhange_rate))


def kraken_order_book(book_type: str, currency_code: str = 'EUR'):
    """Kraken specific orderbook retrieval

    """
    import krakenex

    kraken_api = krakenex.API(key=KRAKEN_API_KEY, secret=KRAKEN_PRIVATE_KEY, conn=krakenex.Connection())

    pair = 'XXBTZ' + currency_code
    orders = kraken_api.query_public('Depth', {'pair': pair})

    df = pd.DataFrame(
        orders['result'][pair][book_type],
        columns=['price', 'volume', 'timestamp'])

    return df


def bitx_order_book(book_type: str, currency_code: str = 'ZAR'):
    """BitX specific orderbook retrieval
    """
    import bitx

    bitx_api = bitx.BitX(BITX_KEY, BITX_SECRET)
    df = bitx_api.get_order_book_frame()

    return df[book_type]


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


def bitcoin_exchange(df, limit, order_type: str, bitcoin_column: str = 'volume', currency_column: str = 'value'):
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


def simulate(transfer_amount, asks, bids, exchange_rate=None, transfer_fees: bool = True, verbose: bool = True):
    """ Calculate the arbitrage oppertunity

    """

    if not exchange_rate:
        exchange_rate = get_forex_buy_quote('EUR')

    if transfer_fees:
        _swift_fee = Decimal(105)
        _fnb_comission = min(max(transfer_amount * Decimal(0.0052), Decimal(140)), Decimal(650))
        _kraken_deposit_fee = Decimal(15)
    else:
        _swift_fee = Decimal(0)
        _fnb_comission = Decimal(0)
        _kraken_deposit_fee = Decimal(0)

    capital = transfer_amount + _fnb_comission + _swift_fee

    euros = transfer_amount / exchange_rate - _kraken_deposit_fee
    _kraken_fee = euros * Decimal(0.0026)

    bitcoins = bitcoin_exchange(asks, euros - _kraken_fee, 'buy')
    _bitx_fees = bitcoins * Decimal(0.01)

    if transfer_fees:
        _bitx_withdrawel_fee = Decimal(8.5)
    else:
        _bitx_withdrawel_fee = Decimal(0)

    rands = bitcoin_exchange(bids, bitcoins - _bitx_fees, 'sell')

    btc_zar_exchange_rate = rands / (bitcoins - _bitx_fees)

    return_value = rands - _bitx_withdrawel_fee

    total_fees = (
        _swift_fee +
        _fnb_comission +
        _kraken_fee * exchange_rate +
        _bitx_fees * btc_zar_exchange_rate +
        _bitx_withdrawel_fee)

    response = []

    response.append('Rands out: %.2f' % capital)
    response.append('# forex conversion: R%.2f' % float(_swift_fee + _fnb_comission))
    response.append('Euro: %.2f' % euros)
    response.append('# kraken fee: R%.2f' % float((_kraken_fee + _kraken_deposit_fee) * exchange_rate ))
    response.append('Bitcoins: %.8f' % bitcoins)
    response.append('# bitx fee: R%.2f' % (_bitx_fees*btc_zar_exchange_rate + _bitx_withdrawel_fee))
    response.append('Rands in: %.2f' % rands)
    response.append('--------------------')
    response.append('Profit: %.2f' % (return_value - capital))
    response.append('ROI: %.2f' % (((return_value - capital)/capital)*100))
    response.append('--------------------')
    response.append('ZAR/EUR: %.2f' % exchange_rate)
    response.append('EUR/BTC: %.2f' % ((euros - _kraken_fee)/bitcoins))
    response.append('BTC/ZAR: %.2f' % btc_zar_exchange_rate)

    if verbose:
        print('\n'.join(response))

    return {'roi': ((return_value - capital)/capital)*100, 'summary': '\n'.join(response) }
