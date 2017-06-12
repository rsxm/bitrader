import json
import os
from functools import partial
from itertools import chain
from logging import getLogger
from typing import Callable

import redis as redis
import requests_cache
from requests import session
from requests_futures.sessions import FuturesSession

logger = getLogger()


# TODO: Allow cache backend to be configurable
# if True:
#     requests_cache.install_cache(os.path.join('./', 'api2'), backend='sqlite', expire_after=2592000)


def flatten_dict(response: dict):
    # http://feldboris.alwaysdata.net/blog/python-trick-how-to-flatten-dictionaries-values-composed-of-iterables.html
    return chain.from_iterable(response.values())


def get_currency_map(response):
    if response:
        d = dict()
        for s in response:
            if s:
                d.update({'%s:%s' % (s['exchange'], s['symbol']): s['currency']})
        return d


class ExternalAPIException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class BaseAPI:
    token = ''
    url_template = 'https://httpbin.org/{resource}'
    resource_templates = {
        'ip': 'ip',
        'get': 'get?{args}',
        'html': 'html',
        'delay': 'delay/{n}',
        'status': 'status/{code}',
    }
    endpoint_options = {}

    def __init__(self, cache: bool = False, future: bool = True):
        if cache:
            redis_conn = redis.StrictRedis(host='redis')
            self.session = requests_cache.core.CachedSession(
                cache_name='api_cache',
                backend='redis', expire_after=60 * 60 * 24 * 30,
                allowable_codes=(200,),
                allowable_methods=('GET',),
                old_data_on_error=False,
                connection=redis_conn,
            )
        else:
            self.session = session()
        if future:
            self.future_session = FuturesSession(max_workers=10, session=self.session)
        self.url = self.url_template.format(resource='', token=self.token)

    def get_resource(self, resource: str, processor: Callable[[dict], dict] = None,
                     data_format: str = 'raw', future: bool = False, **kwargs):
        """Method doing the actual heavy lifting

        Args:
            resource:
            processor:
            data_format: Default = raw. Options: raw, json, dataframe.
                Determines the format the data will be returned in.
            future: Default = False. Runs requests in parallel if True.
            **kwargs:

        Returns:

        """
        if resource not in self.resource_templates.keys():
            raise KeyError('%s is not a valid resource. Options are: %s' % (
                resource, self.resource_templates.keys()))
        try:
            if not getattr(self, 'token', None):
                self.token = ''
            self.url = self.url_template.format(
                token=self.token,
                resource=self.resource_templates[resource].format(**kwargs))
        except KeyError as e:
            cause = e.args[0]
            error_message = 'Resource requires extra key: %s. Valid options are: %s' % (
                cause, self.endpoint_options.get(cause, 'no options found...'))
            print(error_message)
            logger.exception(error_message)
            raise

        else:
            callback = partial(request_hook, data_format=data_format, processor=processor, **kwargs)
            hooks = dict(response=callback)
            request_session = self.future_session if future else self.session

            response = {
                'url': self.url_template.format(
                    token=self.token, resource=self.resource_templates[resource].format(**kwargs)),
                'response': request_session.get(self.url, hooks=hooks),
                'resource': resource,
                'kwargs': kwargs,
            }

            return response


def request_hook(response, data_format: bool = True, processor=None, *args, **kwargs):
    """

    Args:
        response: The response object.
        data_format: data_format: Default = raw. Options: raw, json, dataframe.
            Determines the format the data will be returned in.
        processor:
        *args:
        **kwargs:

    Returns:

    """
    logger.debug(response.url)

    if not response.ok:
        logger.error('%s %s' % (response.status_code, response.content[:20]))
        if kwargs.get('raise_on_error', True):
            raise ExternalAPIException('Got non-ok response: {}'.format(response.url))
        else:
            response.data = None

    elif data_format == 'json' or data_format == 'dataframe':
        try:
            json_response = response.json()
        except json.JSONDecodeError:
            logger.exception(response.content)
            if kwargs.get('raise_on_error', True):
                raise ExternalAPIException('Returned invalid json')
            else:
                response.data = None
        else:
            if processor:
                response.data = processor(json_response)
            else:
                response.data = json_response

        if data_format == 'dataframe':
            import pandas as pd
            response.data = pd.DataFrame(response.data)

    elif data_format == 'raw' and kwargs.get('encoding', ''):
        response.data = response.content.decode(kwargs['encoding'])
    else:
        response.data = response.content


class OpenExchangeAPI(BaseAPI):
    token = os.environ.get('OPEN_EXCHANGE_APP_ID', '')
    url_template = 'https://openexchangerates.org/api/{resource}?app_id={token}'
    resource_templates = {
        'historical': 'historical/{date}.json',
        'currencies': 'currencies.json',
        'latest': 'latest.json',
    }


class HTTPBinAPI(BaseAPI):
    pass


class Ice3xAPI(BaseAPI):
    # token = os.environ.get('OPEN_EXCHANGE_APP_ID', '')
    url_template = 'https://www.ICE3X.com/api/v1/{resource}'
    resource_templates = {
        'generic': '{api_method}/{api_action}?{api_params}',
        'stats': 'stats/marketdepthfull',
        'orderbook': 'orderbook/info?nonce={nonce}&type=bid&pair_id=6',

    }


pair_ids = [{'pair_id': '3', 'pair_name': 'btc/zar', },
     {'pair_id': '4', 'pair_name': 'btc/ngn', },
     {'pair_id': '6', 'pair_name': 'ltc/zar', },
     {'pair_id': '7', 'pair_name': 'ltc/ngn', },]
