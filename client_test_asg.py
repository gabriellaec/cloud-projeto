import requests
from requests.exceptions import HTTPError
from datetime import datetime
import json
import dns
import time

URL_POST = f'{dns.dns_address}/new_task/'
URL_GET = f'{dns.dns_address}/tasks/'



method='GET'
while(1):

    print(URL_GET)
    try:
        response =requests.get(URL_GET)
        response.raise_for_status()
        print('Success!')
        print(response.text)
    except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')

    time.sleep(.1)
