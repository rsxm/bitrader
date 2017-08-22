import datetime
import hashlib
import hmac
import requests
import os

key = os.getenv('ICE3X_KEY', '').encode('utf-8')
public = os.getenv('ICE3X_PUBLIC', '').encode('utf-8')

timestamp = int(datetime.datetime.utcnow().timestamp())

params = f'nonce={timestamp}'.encode('utf-8')

dig = hmac.new(key=key, msg=params, digestmod=hashlib.sha512)
sign = dig.hexdigest()


headers = {'Key': public, 'Sign': sign}

# url = 'https://ice3x.com/api/v1/balance/list'
# response = requests.post(url=url, headers=headers, data={'nonce': timestamp})

url = 'https://ice3x.com/api/v1/currency/list'
response = requests.get(url=url, headers=headers, data={'nonce': timestamp})

response.json()
