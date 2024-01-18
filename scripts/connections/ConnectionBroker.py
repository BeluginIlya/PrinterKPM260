import re

from .broker import *
from scripts.configs import Configurate

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
    printer_data = []
    print(f"\nitems в processing_printer_data {items}\n")
    all_info_item: list[set] = []
    sort_items_by_posx = sorted(items, key=lambda x: x.pos_x, reverse=True) # СОРТИРОВКА ПО ПОЗИЦИИ X
    for index in range(len(sort_items_by_posx)): 
        item = items[index]

        marker_product = index+1
        all_info_item.append((pal_no, item.barcode, item.product,
                                 timestamp, marker_product)) 
        
        convert_data = convert_for_printer(item, marker_product, pal_no, timestamp) # ПОКА ЧТО МАРКЕР ПРОДУКА ПО ИНДЕКСУ 1, 2. ПОТОМ ОТПРАВЛЯЕМ POSX И СОРТИРОВКА 
    

        printer_data.append(convert_data)


    
    print("Конвертированные данные:", printer_data)
    print("Отчётная информация: ", all_info_item)
    return printer_data, all_info_item


def convert_for_printer(row: Item, marker_product, pal_no, timestamp) -> dict: # Функция отвечает за формирования переменных для маркиратора
    config = Configurate().get_config()
    tp = config.tp
    num_line = config.technological_line

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





