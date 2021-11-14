import requests
from requests.exceptions import HTTPError

dns_address="bla"
URL_POST = f'http://{dns_address}/tasks'
URL_GET = f'http://{dns_address}/tasks/tarefas'


method = input("Digite GET ou POST: ")
# --------------------------- GET --------------------------- #
if method=='GET':
    try:
        response =requests.get(URL_GET)
        response.raise_for_status()
        print('Success!')
        print(response.json())
    except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')

# --------------------------- POST --------------------------- #
else:
    try:
        title = input("Título da tarefa: ")
        pub_date = input("Data - formato yyyy-mm-ddThh:mm:ssZ: ")
        description = input("Descrição: ")
        obj={
            'title':title,
            'pub_date':pub_date,
            'description':description
        }
        response =requests.post(URL_POST, obj)
        response.raise_for_status()
        print('Success!')
        print(response.json())
    except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')

