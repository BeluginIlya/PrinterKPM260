import re
import ast
import asyncio
import configparser

from .broker import *


config = configparser.ConfigParser()


async def get_data_from_broker():
    MQ_SERVER="spa.dsk1.ru"
    MQ_PORT=5672
    MQ_USER="admin"
    MQ_PASSWORD="38northernSTUDYdown63"
    MQ_VHOST="joan-v4"

    mq = MessageQueue(MQ_VHOST, MQ_USER, MQ_PASSWORD, MQ_SERVER, MQ_PORT)

    async with mq.connect() as connection:
        async with connection.channel() as channel:
            async with Broker(channel) as broker:
                repo = DBObserverRepository(broker)
                async for entry in repo.get_db_entry_feed():
                    yield entry


def processing_server_data(items: list[Item], timestamp, pal_no): # упорядовачивание данных, объект посредник конвертации данных
    server_data = []
    print(f"\nitems в processing_server_data {items}\n")
    all_info_item: list[set] = []
    for index in range(len(items)): # НУЖНО СОРТИРОВАТЬ ПО ПОЗИЦИИ X
        item = items[index]
        all_info_item.append((pal_no, item.barcode, item.product,
                                 timestamp, index))
        
        convert_data = convert_for_printer(item, index, pal_no, timestamp)
    

        server_data.append(convert_data)


    
    print("Конвертированные данные:", server_data)
    print("Отчётная информация: ", all_info_item)
    return server_data, all_info_item


def convert_for_printer(row: Item, marker_product, pal_no, timestamp) -> dict: # Функция отвечает за формирования переменных для маркиратора
    config.read('config.ini')
    tp = config.get('Settings', 'technological_post')
    num_line = config.get('Settings', 'technological_line')

    result_dict = dict()
    product = re.search(r'_(.*?)_', row.product).group(1)
    year = timestamp.year
    month = timestamp.month
    day = timestamp.day

    result_dict[0] = [f"{'Первое' if marker_product == 1 else 'Второе'} изделие на палете. Номер пал.: {pal_no}."]
    result_dict[1] = [product]
    result_dict[2] = [f"{year}-{month}-{day}   Л{num_line} П{pal_no}", ]

    result_dict[3] = [str(row.barcode[-6:])]
    result_dict["marker_product"] = marker_product
    # Колличество агруметов необходимо передать в основной цикл printer.print_cycle(number_lines=\n/)

    return result_dict





