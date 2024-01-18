import asyncio
from colorama import Fore, Style, init

from .Printer import Printer
from datetime import timedelta
from .connections.broker import ObserverMessage
from .connections.ConnectionBroker import get_data_from_broker, processing_server_data
from .connections.server_api import send_start_data_api, send_status_print

init()

data_buffer: list[ObserverMessage] = []
last_num_pal: int = 0

# ЦИКЛ ОЖИДАНИЯ И ИСПОЛНЕНИЯ
async def async_main_cycle(printer: Printer):
    printer.status = "Start Wait"
    
    async def wait_for_data():
        count = 0
        while True:
            formatted_time = str(timedelta(seconds=count))
            print(f"\r\033[1;32mОжидание - {formatted_time}\033[0m", end='', flush=True)
            count += 1
            await asyncio.sleep(1)
    

    async def process_data_broker():
        global data_buffer
        global last_num_pal

        async for data_entry in get_data_from_broker():
            data_buffer = data_buffer[:2] if len(data_buffer)>2 else data_buffer

            print("", f"{Fore.CYAN}| TP: {data_entry.entry.location_name}{Style.RESET_ALL}")
            if data_entry: # and data_entry.entry.location_name == "TP 1":
                if last_num_pal == 0 or data_entry.entry.pal_no != last_num_pal: 
                    data_buffer.insert(0, data_entry)
                    last_num_pal = data_entry.entry.pal_no
                    for task in asyncio.all_tasks():
                        task.cancel()

    async def process_data_printer():
        print("Ждём данные от брокера")
        async for internal_command_last_pal in printer.async_printer_listener():
            if internal_command_last_pal: 
                printer.STEP = "LAST PAL"
                for task in asyncio.all_tasks():
                    task.cancel()
                

    while True:
        try:
            printer.STEP="WAIT"
            send_status_print(status="WAIT")
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
    if len(data_buffer)>0:
        current_pal = data_buffer[0].entry
        printer.STEP = "WAIT"
    else:
        print("Первый запуск! Предыдущая палета не найдена")
        printer.send_message("Первый запуск! Предыдущая палета не найдена")
        printer.STEP = "END"
    
    while printer.STEP != "END":
        data, all_item_info = processing_server_data(items=current_pal.items, 
                            timestamp=current_pal.timestamp, pal_no=current_pal.pal_no)
        # transform_data = transform_data_for_server(data)
        printer.init_data(data, all_item_info)
        printer.STEP = send_get_cycle(printer, data, all_item_info)
        last_num_pal = current_pal.pal_no

    print("-=-=-=-=-=-=-=-=-Конец функции исполнения")
            


# ЦИКЛ РАБОТЫ С ПРИНТЕРОМ И ОБРАТНАЯ СВЯЗЬ ОТ ПРИНТЕРА
def send_get_cycle(p: Printer, server_data, reporting_info):
    print("-"*50)
    print("=============================ALL_DATA:",reporting_info)
    print("=============================SERVER_DATA_CONVERT:",server_data)
    print("=============================DATA_BUFFER:",data_buffer)
    print("-"*50)


    
    number_products = len(server_data)
    printer_data_sorted = sorted(server_data, key=lambda x: x['marker_product'])
    reporting_info_sorted = sorted(reporting_info, key=lambda x: x[-1])

    send_start_data_api(printer_data_sorted) # отправка данных на сервер django

    step = 1
    while step < number_products + 1:
        product_data = printer_data_sorted[step-1] # start step = 1 
        send_info_list = list(reporting_info_sorted[step-1]) # иформационный лист для апи и бд
        send_status_print(status="PRINT", 
                          PalNo=send_info_list[0],
                          NumProd=send_info_list[4],
                          Barcode=send_info_list[1][6:]
                          )

        p.init_data(product_data, send_info_list)
        printer_command = p.print_cycle(number_lines=4)
        print(printer_command)

        if printer_command == "Next":
            step += 1
            send_status_print(status="NEXT")
        elif int(printer_command[-1]) == 1:
            step = 1
        elif int(printer_command[-1]) == 2:
            step = 2
        elif int(printer_command[-1]) == 4:
            send_status_print(status="LAST PAL")
            return "LAST PAL"
        else:
            step = 3
    return "END"