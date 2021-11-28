import requests
from requests.exceptions import HTTPError
from datetime import datetime
import json
import dns
import logging

logging.basicConfig(format='%(asctime)s %(message)s',
    datefmt='%d-%m-%Y:%H:%M:%S',
    level=logging.INFO,
    filename='proj_logs.txt')
logger = logging.getLogger('my_app')

URL_POST = f'{dns.dns_address}/new_task/'
URL_GET = f'{dns.dns_address}/tasks/'


method = input("Digite GET ou POST: ")



# --------------------------- GET --------------------------- #
if method=='GET':
    print(URL_GET)
    try:
        response =requests.get(URL_GET)
        response.raise_for_status()
        print('Success!')
        print(response.text)

        logger.info(f"GET - response = {response.text}")
    except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')

# --------------------------- POST --------------------------- #
else:
    print(URL_POST)
    try:
        title = input("Título da tarefa: ")
        description = input("Descrição: ")
        obj={
            "title": title,
            "pub_date": (datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "description": description
        }
        print(obj)
        json_obj = json.dumps(obj)
        print(json_obj)
        response =requests.post(URL_POST, json_obj)
        response.raise_for_status()
        print('Success!')
        print(response.text)
        logger.info(f"POST - info = {response.text}")

    except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')


# Fontes:
# https://docs.python-requests.org/en/latest/user/quickstart/
# https://www.nylas.com/blog/use-python-requests-module-rest-apis/