import requests
import re
import json
from ..configs import Configurate

config = Configurate().get_config()
host = config.api_host

def transform_item_in_dict(item):
    pal_no = item[0]
    barcode = item[1][6:]
    raw_product_info = re.search(r'_(.*?)_', item[2]).group(1)
    timestamp = item[3]
    status_print = False
    num_prod = item[-1]

    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')

    data_to_send = {
            'PalNo': pal_no,
            'NumProd': num_prod,
            'Timestamp': timestamp_str,
            'Barcode': barcode,
            'Product': raw_product_info,
            'StatusPrint': status_print,
        }
    
    return data_to_send


def send_start_data_api(input_data):
    transformed_data = {}
    api_url = f'{host}api/local_print_history/'

    for item in input_data:
        data_to_send = transform_item_in_dict(item)

        transformed_data[f"item_{data_to_send['NumProd']}"] = data_to_send

    send_message_api(api_url, transformed_data)


def send_status_print(status, **kwargs):
    api_url = f'{host}api/printer_status'
    status_data = dict()
    status_data['status_printer']= status
    status_data['body']= kwargs
    send_message_api(api_url, status_data)


def send_update_status_product(item):
    api_url = f'{host}api/end_product'
    data_to_send = transform_item_in_dict(item)
    print("*"*19, "Отправка обновление таблица:", data_to_send)
    
    send_message_api(api_url, data_to_send)


def send_message_api(api_url, data_to_send):
    print("\n","-"*50, "end send data on server", "-"*50)
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(api_url, data=json.dumps(data_to_send), headers=headers)

        if response.status_code == 200:
            print(f"Request successful. Response code: {response.status_code}")
        else:
            print(f"Request failed. Response code: {response.status_code}")
        
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

    finally:
        print("\n","-"*50, "end send data on server", "-"*50)


