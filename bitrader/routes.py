"""
Dump of some new exploratory routes.
TODO: Needs to be cleaned up and standardized with a way to specify arbitrary routes with fees.
E.g.:
    FNB|ZAR > LUNO|BTC > LUNO|ETH > ALT|ZAR > ALT|BTC > LUNO|ZAR
    10000 > FNB|(0.55%^650)ZAR(110) > KRAKEN|EUR(15) > KRAKEN|(0.26%)BTC(0.001) > LUNO|(0.0002)BTC(1%)
"""

from decimal import Decimal

import pandas as pd

from bitrader.arbitrage_tools import (
    CFUID, altcointrader_order_books, coin_exchange, ice3x_order_book,
    kraken_order_book, luno_order_book, prepare_order_book
)


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
        order_book=pd.DataFrame(altcointrader_order_books(CFUID)['xrp']['bids']), book_type='bids')

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
        order_book=pd.DataFrame(altcointrader_order_books(CFUID)['xrp']['bids']), book_type='bids')

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


def eth_alt_arb(amount=Decimal('10000'), exchange='altcointrader'):
    zar = amount

    btc_asks = prepare_order_book(luno_order_book(book_type='asks', pair='XBTZAR'), book_type='asks')
    btc = coin_exchange(btc_asks, limit=zar, order_type='buy')

    eth_asks = prepare_order_book(luno_order_book(book_type='asks', pair='ETHXBT'), book_type='asks')
    eth = coin_exchange(eth_asks, limit=btc, order_type='buy')

    if exchange == 'ice3x':
        eth_bids = prepare_order_book(
            ice3x_order_book('bid', coin_code='ETH'), 'bids', bitcoin_column='amount')
    elif exchange == 'altcointrader':
        eth_bids = prepare_order_book(
            order_book=pd.DataFrame(altcointrader_order_books(CFUID)['eth']['bids']), book_type='bids')
    else:
        raise AttributeError(f'{exchange} is not a valid exchange')

    zar_out = coin_exchange(eth_bids, limit=Decimal(eth), order_type='sell')
    zar_out = zar_out * (1 - Decimal('0.008'))

    roi = ((zar_out - zar) / zar) * 100

    print('BTC/ETH\t', btc / eth)
    print('ZAR/ETH\t', zar / eth)
    print('ETH\t', eth)
    print('ZAR/ETH\t', zar_out / eth)
    print('ZAR\t', zar_out)
    print('ROI\t', roi)

    return btc, eth, zar_out, roi


def ice3x_ltc_altcointrader_ltc(amount: Decimal):
    zar = Decimal(amount)
    ltc_asks = prepare_order_book(
        ice3x_order_book('ask', coin_code='LTC'), 'asks', bitcoin_column='amount')
    ltc = coin_exchange(ltc_asks, limit=zar, order_type='buy')
    ltc_bids = prepare_order_book(
        order_book=pd.DataFrame(altcointrader_order_books(CFUID)['ltc']['bids']), book_type='bids')
    zar_out = coin_exchange(ltc_bids, limit=Decimal(ltc), order_type='sell')
    roi = (zar_out - zar) / zar_out * 100

    print('ZAR\t', zar)
    print('ZAR/LTC\t', zar / ltc)
    print('LTC\t', ltc)
    print('ZAR/LTC\t', zar_out / ltc)
    print('ZAR\t', zar_out)
    print('ROI\t', roi)

    return zar, ltc, zar_out, roi


def altcointrader_ltc_ice3x_ltc(amount: Decimal):
    zar = Decimal(amount)

    ltc_asks = prepare_order_book(
        order_book=pd.DataFrame(altcointrader_order_books(CFUID)['ltc']['asks']), book_type='asks')
    ltc = coin_exchange(ltc_asks, limit=zar, order_type='buy')

    ltc_bids = prepare_order_book(
        ice3x_order_book('bid', coin_code='LTC'), 'bids', bitcoin_column='amount')

    zar_out = coin_exchange(ltc_bids, limit=Decimal(ltc), order_type='sell')
    roi = (zar_out - zar) / zar_out * 100

    print('ZAR\t', zar)
    print('ZAR/LTC\t', zar / ltc)
    print('LTC\t', ltc)
    print('ZAR/LTC\t', zar_out / ltc)
    print('ZAR\t', zar_out)
    print('ROI\t', roi)

    return zar, ltc, zar_out, roi
