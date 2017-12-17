"""
Dump of some new exploratory routes.
TODO: Needs to be cleaned up and standardized with a way to specify arbitrary routes with fees.
E.g.:
    FNB|ZAR > LUNO|BTC > LUNO|ETH > ALT|ZAR > ALT|BTC > LUNO|ZAR
    10000 > FNB|(0.55%^650)ZAR(110) > KRAKEN|EUR(15) > KRAKEN|(0.26%)BTC(0.001) > LUNO|(0.0002)BTC(1%)
"""

from decimal import Decimal
import os

from bitrader.arbitrage_tools import (
    altcointrader_order_books, coin_exchange, ice3x_order_book,
    kraken_order_book, luno_order_book, prepare_order_book
)

CFUID = os.getenv('CFUID')
CFCLEARANCE = os.getenv('CFCLEARANCE')
USERAGENT = os.getenv('USERAGENT')


def eth_luno_xrp_kraken_arb(amount=Decimal('10000')):
    zar = Decimal(amount)

    btc_asks = prepare_order_book(luno_order_book(book_type='asks', pair='XBTZAR'), book_type='asks')
    btc = coin_exchange(btc_asks, limit=zar, order_type='buy')

    eth_asks = prepare_order_book(luno_order_book(book_type='asks', pair='ETHXBT'), book_type='asks')
    eth = coin_exchange(eth_asks, limit=btc, order_type='buy')

    eur_bids = prepare_order_book(
        kraken_order_book(book_type='bids', currency_code='EUR', coin_code='ETH'), book_type='bids')
    eur = coin_exchange(eur_bids, limit=eth, order_type='sell')

    xrp_asks = prepare_order_book(
        kraken_order_book(book_type='asks', currency_code='EUR', coin_code='XRP'), book_type='asks')
    xrp = coin_exchange(xrp_asks, limit=eur, order_type='buy')

    xrp_bids = prepare_order_book(
        altcointrader_order_books(USERAGENT, CFUID, CFCLEARANCE, 'bids', 'xrp'), book_type='bids')

    zar_out = coin_exchange(xrp_bids, limit=Decimal(xrp), order_type='sell')
    zar_out = zar_out * (1 - Decimal('0.008'))

    roi = ((zar_out - zar) / zar) * 100

    print('BTC/ETH\t', btc / eth)
    print('ZAR/ETH\t', zar / eth)
    print('ETH\t', eth)
    print('EUR/ETH\t', eur / eth)
    print('EUR\t', eur)
    print('EUR/XRP\t', eur)
    print('XRP\t', xrp)

    print('ROI\t', roi)


def btc_luno_xrp_kraken_arb(amount=Decimal('10000')):
    zar = Decimal(amount)

    btc_asks = prepare_order_book(luno_order_book(book_type='asks', pair='XBTZAR'), book_type='asks')
    btc = coin_exchange(btc_asks, limit=zar, order_type='buy')

    xrp_asks = prepare_order_book(kraken_order_book(book_type='asks', pair='XXRPXXBT'), book_type='asks')
    xrp = coin_exchange(xrp_asks, limit=btc, order_type='buy')

    xrp_bids = prepare_order_book(
        altcointrader_order_books(USERAGENT, CFUID, CFCLEARANCE, book_type='bids', coin_code='xrp'), book_type='bids')

    zar_out = coin_exchange(xrp_bids, limit=Decimal(xrp), order_type='sell')
    zar_out = zar_out * (1 - Decimal('0.008'))

    roi = ((zar_out - zar) / zar) * 100

    print('ZAR/BTC\t', zar / btc)
    print('BTC\t', btc)
    print('BTC/XRP\t', btc / xrp)
    print('XRP\t', xrp)
    print('ZAR/XRP\t', zar / xrp)
    print('ZAR\t', zar)
    print('ZAR/XRP\t', zar_out / xrp)
    print('ZAR\t', zar_out)

    print('ROI\t', roi)

    return zar, btc, xrp


def eth_alt_arb(amount=Decimal('10000'), exchange='altcointrader', verbose=False):
    zar = amount

    btc_asks = prepare_order_book(luno_order_book(book_type='asks', pair='XBTZAR'), book_type='asks')
    btc = coin_exchange(btc_asks, limit=zar, order_type='buy')

    eth_asks = prepare_order_book(luno_order_book(book_type='asks', pair='ETHXBT'), book_type='asks')
    eth = coin_exchange(eth_asks, limit=btc, order_type='buy')

    if exchange == 'ice3x':
        eth_bids = prepare_order_book(
            ice3x_order_book('bids', coin_code='ETH'), 'bids')
    elif exchange == 'altcointrader':
        eth_bids = prepare_order_book(
            altcointrader_order_books(USERAGENT, CFUID, CFCLEARANCE, book_type='bids', coin_code='eth'),
            book_type='bids')
    else:
        raise AttributeError(f'{exchange} is not a valid exchange')

    zar_out = coin_exchange(eth_bids, limit=Decimal(eth), order_type='sell')
    zar_out = zar_out * (1 - Decimal('0.008'))

    roi = ((zar_out - zar) / zar) * 100

    if verbose:
        print('BTC/ETH\t', btc / eth)
        print('ZAR/ETH\t', zar / eth)
        print('ETH\t', eth)
        print('ZAR/ETH\t', zar_out / eth)
        print('ZAR\t', zar_out)
        print('ROI\t', roi)

    return btc, eth, zar_out, roi


def eth_alt_arb_to_luno(amount=Decimal('10000'), exchange='altcointrader', verbose=False):
    zar = amount

    if exchange == 'ice3x':
        eth_asks = prepare_order_book(ice3x_order_book('asks', coin_code='ETH'), book_type='asks')
    elif exchange == 'altcointrader':
        eth_asks = prepare_order_book(
            altcointrader_order_books(
                USERAGENT, CFUID, CFCLEARANCE, book_type='asks', coin_code='ETH'), book_type='asks')
    else:
        raise AttributeError(f'{exchange} is not a valid exchange')

    eth = coin_exchange(eth_asks, limit=amount, order_type='buy')

    eth_bids = prepare_order_book(luno_order_book(book_type='bids', pair='ETHXBT'), book_type='bids')
    btc = coin_exchange(eth_bids, limit=eth, order_type='sell')

    btc_bids = prepare_order_book(luno_order_book(book_type='bids', pair='XBTZAR'), book_type='bids')
    zar_out = coin_exchange(btc_bids, limit=btc, order_type='sell')

    roi = ((zar_out - zar) / zar) * 100

    if verbose:
        print('ZAR In\t\t', 'R' + str(round(zar, 2)))
        print('ZAR/ETH Buy\t', 'R' + str(round(zar / eth, 2)))
        print('ETH\t\t', str(round(eth, 6)))
        print('ZAR/ETH Sell\t', 'R' + str(round(zar_out / eth, 2)))
        print('ZAR Out\t\t', 'R' + str(round(zar_out, 2)))
        print('ROI\t\t', str(round(roi, 2)) + '%')

    return btc, eth, zar_out, roi


def get_prepared_order_book(exchange="luno", coin_code='XBT', book_type='asks'):
    if exchange == "luno":
        if coin_code == 'XBT':
            order_book = luno_order_book(book_type=book_type, pair='XBTZAR')
        else:
            raise AttributeError(f'{coin_code} is not yet supported on Luno')
    elif exchange == "ice3x":
        order_book = ice3x_order_book(book_type=book_type, coin_code=coin_code)
    elif exchange == 'altcointrader':
        order_book = altcointrader_order_books(USERAGENT, CFUID, CFCLEARANCE, book_type=book_type, coin_code=coin_code)
    else:
        raise AttributeError(f'{exchange} is not a valid exchange')

    prepared_order_book = prepare_order_book(order_book, book_type=book_type)

    return prepared_order_book


def local_arbitrage(amount=Decimal('10000'), coin_code='ETH', verbose=False, start="ice3x", end="altcointrader"):
    """
    Works for BTC, ETH between Luno, Ice3x and Altcoin in both directions
    And LTC between Ice3x and Altcoin in both directions

    Altcointrader fees included when selling there
    """
    zar = Decimal(amount)

    if start == "luno" and coin_code == "ETH":
        _, coin, zar_out, roi = eth_alt_arb(amount=zar, exchange=end)

    elif end == "luno" and coin_code == "ETH":
        _, coin, zar_out, roi = eth_alt_arb_to_luno(amount=zar, exchange=start)

    else:
        coin_asks = get_prepared_order_book(exchange=start, coin_code=coin_code, book_type='asks')
        coin = coin_exchange(coin_asks, limit=amount, order_type='buy')

        coin_bids = get_prepared_order_book(exchange=end, coin_code=coin_code, book_type='bids')
        zar_out = coin_exchange(coin_bids, limit=Decimal(coin), order_type='sell')

        if end == "altcointrader":
            zar_out = zar_out * (1 - Decimal('0.008'))

        roi = (zar_out - zar) / zar_out * 100

    if verbose:
        print('ZAR In\t\t', 'R' + str(round(zar, 2)))
        print('ZAR/Coin Buy\t', 'R' + str(round(zar / coin, 2)))
        print('Coin\t\t', str(round(coin, 6)))
        print('ZAR/Coin Sell\t', 'R' + str(round(zar_out / coin, 2)))
        print('ZAR Out\t\t', 'R' + str(round(zar_out, 2)))
        print('ROI\t\t', str(round(roi, 2)) + '%')

    return coin, zar_out, roi
