""" Arbitrage tools

Tools for determining the

"""
import os
from decimal import Decimal

import pandas as pd
import seaborn as sns

sns.set_context(font_scale=1.1)

KRAKEN_API_KEY = os.environ.get('KRAKEN_API_KEY')
KRAKEN_PRIVATE_KEY = os.environ.get('KRAKEN_PRIVATE_KEY')
BITX_KEY = os.environ.get('BITX_KEY')
BITX_SECRET = os.environ.get('BITX_SECRET')

COIN_MAP = {
    'bitcoin': dict(
        coin_code='XBT',
        coin_name='Bitcoin',
        exchange_name='Luno'),
    'litecoin': dict(
        coin_code='LTC',
        coin_name='Litecoin',
        exchange_name='Ice3x'),
    'ethereum': dict(
        coin_code='ETH',
        coin_name='Ethereum',
        exchange_name='Ice3x')
}


def get_forex_buy_quote(currency_code: str = 'EUR', source: str = 'FNB'):
    """Get latest forex from FNB website

    """
    if source == 'FNB':
        tables = pd.read_html(
            'https://www.fnb.co.za/Controller?nav=rates.forex.list.ForexRatesList',
            index_col=1, header=0, match=currency_code)

        df = tables[0]
        exhange_rate = df.loc[currency_code, 'Bank Selling Rate']

        return Decimal("%.4f" % float(exhange_rate))


def kraken_order_book(book_type: str, currency_code: str = 'EUR', coin_code: str = 'XBT'):
    """Kraken specific orderbook retrieval

    """
    import krakenex

    kraken_api = krakenex.API(key=KRAKEN_API_KEY, secret=KRAKEN_PRIVATE_KEY, conn=krakenex.Connection())

    pair = f'X{coin_code}Z{currency_code}'
    orders = kraken_api.query_public('Depth', {'pair': pair})

    df = pd.DataFrame(
        orders['result'][pair][book_type],
        columns=['price', 'volume', 'timestamp'])

    return df


def luno_order_book(book_type: str, currency_code: str = 'ZAR'):
    """BitX specific orderbook retrieval
    """
    from bitrader import bitx

    bitx_api = bitx.BitX(BITX_KEY, BITX_SECRET)
    df = bitx_api.get_order_book_frame()

    return df[book_type]


def ice3x_order_book(book_type: str, coin_code: str = 'BTC', currency_code: str = 'ZAR'):
    """Ice3X specific orderbook retrieval
    """
    from bitrader.api_tools import Ice3xAPI
    ice = Ice3xAPI(cache=False, future=False)

    pair_map = {
        'BTC': 3,
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


def simulate(transfer_amount, eur_asks, zar_bids,
             coin_name: str = 'Bitcoin', coin_code: str = 'BTC', exchange_name: str = 'Luno',
             exchange_rate=None,
             transfer_fees: bool = True, verbose: bool = True):
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

    bitcoins = coin_exchange(eur_asks, euros - _kraken_fee, 'buy')
    _bitx_fees = bitcoins * Decimal(0.01)

    if transfer_fees:
        _bitx_withdrawel_fee = Decimal(8.5)
    else:
        _bitx_withdrawel_fee = Decimal(0)

    rands = coin_exchange(zar_bids, bitcoins - _bitx_fees, 'sell')

    btc_zar_exchange_rate = rands / (bitcoins - _bitx_fees)

    return_value = rands - _bitx_withdrawel_fee

    total_fees = (
        _swift_fee +
        _fnb_comission +
        _kraken_fee * exchange_rate +
        _bitx_fees * btc_zar_exchange_rate +
        _bitx_withdrawel_fee)

    response = [
        f'Rands out: {capital:.2f}',
        f'# forex conversion: R{_swift_fee + _fnb_comission:.2f}',
        f'Euro: {euros:.2f}',
        f'# kraken fee: R{(_kraken_fee + _kraken_deposit_fee) * exchange_rate:.2f}',
        f'{coin_name}: {bitcoins:.8f}',
        f'# {exchange_name} fee: R{(_bitx_fees * btc_zar_exchange_rate + _bitx_withdrawel_fee):.2f}',
        f'Rands in: {rands:.2f}',
        '--------------------',
        f'Profit: {return_value - capital:.2f}',
        f'ROI: {((return_value - capital) / capital) * 100:.2f}',
        '--------------------',
        f'ZAR/EUR: {exchange_rate:.2f}',
        f'EUR/{coin_code}: {(euros - _kraken_fee) / bitcoins:.2f}',
        f'{coin_code}/ZAR: {btc_zar_exchange_rate:.2f}'
    ]

    if verbose:
        print('\n'.join(response))

    return {'roi': ((return_value - capital) / capital) * 100, 'summary': '\n'.join(response)}


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
              exchange_rate=None, transfer_fees: bool = True, verbose: bool = False, books=None):
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
        eur_asks, zar_bids = get_books(coin_code=coin_code, exchange_name=exchange_name)
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
            _swift_fee = Decimal(105)
            # TODO: Factor in ebucks?
            _fnb_comission = min(max(transfer_amount * Decimal(0.0052), Decimal(140)), Decimal(650))
            # TODO: With SEPA deposit fee is 0. But check other methods?
            _kraken_deposit_fee = Decimal(0)
        else:
            _swift_fee = Decimal(0)
            _fnb_comission = Decimal(0)
            _kraken_deposit_fee = Decimal(0)

        capital = transfer_amount + _fnb_comission + _swift_fee

        euros = transfer_amount / exchange_rate - _kraken_deposit_fee
        _kraken_fee = euros * Decimal(0.0026)  # TODO: Allow to specify lower tier, e.g. over $50k = 0.0024
        # TODO: There is also now a Bitcoin send fee

        bitcoins = coin_exchange(eur_asks, euros - _kraken_fee, 'buy')
        _bitx_fees = bitcoins * Decimal(0.01)  # TODO: Allow to specify lower tier, e.g. over 10 BTC = 0.0075

        if transfer_fees:
            _bitx_withdrawel_fee = Decimal(8.5)  # TODO: Check Ice3x fees
        else:
            _bitx_withdrawel_fee = Decimal(0)

        rands = coin_exchange(zar_bids, bitcoins - _bitx_fees, 'sell')

        btc_zar_exchange_rate = rands / (bitcoins - _bitx_fees)

        return_value = rands - _bitx_withdrawel_fee

        total_fees = (
            _swift_fee +
            _fnb_comission +
            _kraken_fee * exchange_rate +
            _bitx_fees * btc_zar_exchange_rate +
            _bitx_withdrawel_fee)

        response = [
            f'Rands out: {capital:.2f}',
            f'# forex conversion: R{_swift_fee + _fnb_comission:.2f}',
            f'Euro: {euros:.2f}',
            f'# kraken fee: R{(_kraken_fee + _kraken_deposit_fee) * exchange_rate:.2f}',
            f'{coin_name}: {bitcoins:.8f}',
            f'# {exchange_name} fee: R{(_bitx_fees * btc_zar_exchange_rate + _bitx_withdrawel_fee):.2f}',
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


def optimal(max_invest: int = 1000000, coin: str = 'bitcoin', return_format: str = 'text'):
    """
    :param max_invest: 
    :param coin: bitcoin, litecoin, ethereum
    :param return_format: text or picture
    :return: 
    """

    exchange_rate = get_forex_buy_quote('EUR')

    books = get_books(
        coin_code=COIN_MAP[coin]['coin_code'],
        exchange_name=COIN_MAP[coin]['exchange_name']
    )

    results = []
    for amount in range(1000, max_invest, 1000):

        try:
            results.append(
                dict(
                    amount=amount, roi=arbitrage(
                        amount=amount,
                        exchange_rate=exchange_rate,
                        books=books,
                        **COIN_MAP[coin],
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


def reverse_arb(amount, coin_code='LTC'):
    """
    
    :param amount: 
    :param coin_code: 
    :return: 
    """
    zar_asks = prepare_order_book(ice3x_order_book('ask', coin_code=coin_code), 'asks', bitcoin_column='amount')
    eur_bids = prepare_order_book(kraken_order_book('bids', coin_code=coin_code), 'asks')

    coins = coin_exchange(zar_asks, amount, 'buy')
    euro = coin_exchange(eur_bids, coins, 'sell')

    zar_asks = prepare_order_book(luno_order_book('bids'), 'bids')

    exchange_rate = get_forex_buy_quote('EUR')
    rands = euro * exchange_rate

    return f'R{amount:.0f}, R{rands:.0f}, {(rands - amount)/amount * 100:.2f}%'

