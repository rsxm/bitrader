"""Code I found here: https://github.com/CjS77/pybitx
 There is issue with code, so I copied and fixed. TODO: Create proper fix and
 pull request.
"""

import requests
import logging
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import json

__version__ = "0.1.10"

log = logging.getLogger(__name__)

# --------------------------- constants -----------------------

class BitXAPIError(ValueError):
    def __init__(self, response):
        self.url = response.url
        self.code = response.status_code
        self.message = response.text

    def __str__(self):
        return "BitX request %s failed with %d: %s" % (self.url, self.code, self.message)


class BitX:
    def __init__(self, key, secret, options={}):
        self.options = options
        self.auth = (key, secret)
        if 'hostname' in options:
            self.hostname = options['hostname']
        else:
            self.hostname = 'api.mybitx.com'
        self.port = options['port'] if 'port' in options else 443
        self.pair = options['pair'] if 'pair' in options else 'XBTZAR'
        self.ca = options['ca'] if 'ca' in options else None
        self.timeout = options['timeout'] if 'timeout' in options else 30
        self.headers = {
            'Accept': 'application/json',
            'Accept-Charset': 'utf-8',
            'User-Agent': 'py-bitx v' + __version__
        }
        self._executor = ThreadPoolExecutor(max_workers=5)

    def close(self):
        log.info('Asking MultiThreadPool to shutdown')
        self._executor.shutdown(wait=True)
        log.info('MultiThreadPool has shutdown')

    def construct_url(self, call):
        base = self.hostname
        if self.port != 443:
            base += ':%d' % (self.port,)
        return "https://%s/api/1/%s" % (base, call)

    def api_request(self, call, params, kind='auth', http_call='get'):
        """
        General API request. Generally, use the convenience functions below
        :param kind: the type of request to make. 'auth' makes an authenticated call; 'basic' is unauthenticated
        :param call: the API call to make
        :param params: a dict of query parameters
        :return: a json response, a BitXAPIError is thrown if the api returns with an error
        """
        url = self.construct_url(call)
        auth = self.auth if kind == 'auth' else None
        if http_call == 'get':
            response = requests.get(url, params, headers=self.headers, auth=auth)
        elif http_call == 'post':
            response = requests.post(url, data = params, headers=self.headers, auth=auth)
        else:
            raise ValueError('Invalid http_call parameter')
        try:
            result = response.json()
        except ValueError:
            result = {'error': 'No JSON content returned'}
        if response.status_code != 200 or 'error' in result:
            raise BitXAPIError(response)
        else:
            return result

    def get_ticker(self, kind='auth'):
        params = {'pair': self.pair}
        return self.api_request('ticker', params, kind=kind)

    def get_all_tickers(self, kind='auth'):
        return self.api_request('tickers', None, kind=kind)

    def get_order_book(self, limit=None, kind='auth'):
        params = {'pair': self.pair}
        orders = self.api_request('orderbook', params, kind=kind)
        if limit is not None:
            orders['bids'] = orders['bids'][:limit]
            orders['asks'] = orders['asks'][:limit]
        return orders

    def get_order_book_frame(self, limit=None, kind='auth'):
        q = self.get_order_book(limit, kind)
        asks = pd.DataFrame(q['asks'])
        bids = pd.DataFrame(q['bids'])
        index = pd.MultiIndex.from_product([('asks', 'bids'),('price', 'volume')])
        df = pd.DataFrame(pd.concat([asks, bids], axis=1).values, columns=index)
        return df

    def get_trades(self, limit=None, kind='auth'):
        params = {'pair': self.pair}
        trades = self.api_request('trades', params, kind=kind)
        if limit is not None:
            trades['trades'] = trades['trades'][:limit]
        return trades

    def get_trades_frame(self, limit=None, kind='auth'):
        trades = self.get_trades(limit, kind)
        df = pd.DataFrame(trades['trades'])
        df.index = pd.to_datetime(df.timestamp * 1e-3, unit='s')
        df.drop('timestamp', axis=1, inplace=True)
        return df

    def get_orders(self, state=None, kind='auth'):
        """
        Returns a list of the most recently placed orders. You can specify an optional state='PENDING' parameter to
        restrict the results to only open orders. You can also specify the market by using the optional pair parameter.
        The list is truncated after 100 items.
        :param kind: typically 'auth' if you want this to return anything useful
        :param state: String optional 'COMPLETE', 'PENDING', or None (default)
        :return:
        """
        params = {'pair': self.pair}
        if state is not None:
            params['state'] = state
        return self.api_request('listorders', params, kind=kind)

    def get_order(self, order_id):
        """
        Get an order by its ID
        :param order_id: string	The order ID
        :return: dict order details or BitXAPIError raised
        """
        return self.api_request('orders/%s' % (order_id,), None)

    def get_orders_frame(self, state=None, kind='auth'):
        q = self.get_orders(state, kind)
        tj = json.dumps(q['orders'])
        df = pd.read_json(tj, convert_dates=['creation_timestamp', 'expiration_timestamp'])
        df.index = df.creation_timestamp
        return df

    def create_limit_order(self, order_type, volume, price):
        """
        Create a new limit order
        :param order_type: 'buy' or 'sell'
        :param volume: the volume, in BTC
        :param price: the ZAR price per bitcoin
        :return: the order id
        """
        data = {
            'pair': self.pair,
            'type': 'BID' if order_type == 'buy' else 'ASK',
            'volume': str(volume),
            'price': str(price)

        }
        result = self.api_request('postorder', params=data, http_call='post')
        return result

    def stop_order(self, order_id):
        """
        Create a new limit order
        :param order_id: The order ID
        :return: a success flag
        """
        data = {
            'order_id': order_id,
        }
        return self.api_request('stoporder', params=data, http_call='post')

    def stop_all_orders(self):
        """
        Stops all pending orders, both sell and buy
        :return: dict of Boolean -- whether request succeeded or not for each order_id that was pending
        """
        pending = self.get_orders('PENDING')['orders']
        ids = [order['order_id'] for order in pending]
        result = {}
        for order_id in ids:
            status = self.stop_order(order_id)
            result[order_id] = status['success']
        return result

    def get_funding_address(self, asset):
        """
        Returns the default receive address associated with your account and the amount received via the address. You
        can specify an optional address parameter to return information for a non-default receive address. In the
        response, total_received is the total confirmed Bitcoin amount received excluding unconfirmed transactions.
        total_unconfirmed is the total sum of unconfirmed receive transactions.
        :param asset: For now, only XBT is valid
        :return: dict
        """
        return self.api_request('funding_address', {'asset': asset})

    def get_withdrawals_status(self, wid=None):
        """
        :param wid: String. Optional withdrawal id. None queries for all ids
        :return:
        """
        call = 'withdrawals'
        if wid is not None:
            call += '/%s' % (wid,)
        return self.api_request(call, None)

    def get_balance(self):
        return self.api_request('balance', None)

    def get_transactions(self, account_id, min_row=None, max_row=None):
        params = {}
        if min_row is not None:
            params['min_row'] = min_row
        if max_row is not None:
            params['max_row'] = max_row
        return self.api_request('accounts/%s/transactions' % (account_id,), params)

    def get_transactions_frame(self, account_id, min_row=None, max_row=None):
        tx = self.get_transactions(account_id, min_row, max_row)['transactions']
        df = pd.DataFrame(tx)
        df.index = pd.to_datetime(df.timestamp, unit='ms')
        df.drop('timestamp', axis=1, inplace=True)
        return df

    def get_pending_transactions(self, account_id):
        return self.api_request('accounts/%s/pending' % (account_id,), None)
