import asyncio
import configparser
from .Printer import Printer
from datetime import timedelta
from .broker import ObserverMessage
from .ConnectionBroker import get_data_from_broker, processing_server_data


data_buffer: list[ObserverMessage] = []
last_num_pal: int = 0

# ЦИКЛ ОЖИДАНИЯ И ИСПОЛНЕНИЯ
async def async_main_cycle(printer: Printer):
    config = configparser.ConfigParser()
    config.read("config.ini")
    first_start = False  # Первый старт менять тут!!! Если 0 то программа печатает последнюю палету
    printer.status = "Start Wait"
    time_sleep = int(config.get('Settings', 'time_update'))

    async def wait_for_data():
        count = 0
        while True:
            formatted_time = str(timedelta(seconds=count))
            print(f"\rОжидание - {formatted_time}", end='', flush=True)
            count += 1
            await asyncio.sleep(1)

    async def process_data_broker():
        global data_buffer
        global last_num_pal

        async for data_entry in get_data_from_broker():
            data_buffer = data_buffer[:2] if len(data_buffer)>2 else data_buffer

            print("\nPOST = ", data_entry.entry.location_name)
            if data_entry and data_entry.entry.location_name == "TP 1":
                if last_num_pal == 0 or data_entry.entry.pal_no != last_num_pal: 
                    data_buffer.insert(0, data_entry)
                    last_num_pal = data_entry.entry.pal_no
                    for task in asyncio.all_tasks():
                        task.cancel()

    async def process_data_printer():
        print("Ждём данные от брокера")
        async for internal_command_last_pal in printer.async_printer_listener():
            print(internal_command_last_pal)
            if internal_command_last_pal: 
                printer.STEP = "LAST PAL"
                for task in asyncio.all_tasks():
                    task.cancel()

    # Создаем задачи и запускаем их параллельно
    while True:
        try:
            printer.STEP="WAIT"
            printer.send_message("Ожидание новой палеты...")  
            printer.listen_data(1) # Съедаем фидбэк
            tasks = [asyncio.create_task(process_data_broker()), asyncio.create_task(process_data_printer()), asyncio.create_task(wait_for_data())]
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            print("Все таски ожидания данных завершены-> Исполнение основного цикла:\n")
            await start_print(printer)


# ФУНКЦИЯ ИСПОЛНЕНИЯ
async def start_print(printer: Printer):
    global data_buffer
    global last_num_pal
    current_pal = data_buffer[0].entry

    
    while printer.STEP != "END":
        if printer.STEP == "LAST PAL":
            if data_buffer:
                print("функционал для печати последней палеты")
                current_pal = data_buffer[0].entry
                printer.STEP = "WAIT"
            else:
                print("Первый запуск! Предыдущая палета не найдена")
                printer.send_message("Первый запуск! Предыдущая палета не найдена")
                printer.STEP != "END"
        elif printer.STEP == "WAIT":
            data, all_item_info = processing_server_data(items=current_pal.items, 
                                timestamp=current_pal.timestamp, pal_no=current_pal.pal_no)
            printer.init_data(data, all_item_info)
            printer.STEP = send_get_cycle(printer, data, all_item_info)
            last_num_pal = current_pal.pal_no
            


# ЦИКЛ РАБОТЫ С ПРИНТЕРОМ И ОБРАТНАЯ СВЯЗЬ ОТ ПРИНТЕРА
def send_get_cycle(p: Printer, server_data, reporting_info):
    print("-"*50)
    print("=============================ALL_DATA:",reporting_info)
    print("=============================SERVER_DATA_CONVERT:",server_data)
    print("=============================DATA_BUFFER:",data_buffer)
    print("-"*50)


    step = 1
    number_products = len(server_data)
    while step < number_products + 1:

        # product_data = server_data[0] if server_data[0]['marker_product'] == step else server_data[1]

        if server_data[0]['marker_product'] == step:
            product_data = server_data[0]
        elif len(server_data) > 1:
            product_data = server_data[1]
        else:
            return "END"

        num = product_data['marker_product']
        send_info = [reporting_info[i] for i in range(len(reporting_info)) if reporting_info[i][-1] == num][0]
        send_info_list = list(send_info)
        p.init_data(product_data, send_info_list)
        printer_command = p.print_cycle(number_lines=4)
        print(printer_command)

        if printer_command == "Next":
            step += 1
        elif int(printer_command[-1]) == 1:
            step = 1
        elif int(printer_command[-1]) == 2:
            step = 2
        elif int(printer_command[-1]) == 4:
            return "LAST PAL"
        else:
            step = 3
    return "END"