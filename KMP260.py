import asyncio
import configparser
import os
import keyring

from scripts.Connections import get_update_status_and_data, processing_server_data, connect_bd
from scripts.FTP_Messenger import Printer

config_file = 'config.ini'


def init_config():
    if not os.path.exists(config_file):
        write_config()
    else:
        config = configparser.ConfigParser()
        config.read(config_file)

        time_update = int(config.get('Settings', 'time_update'))

        ip_printer = config.get('Settings', 'IP_Printer')
        port_printer = config.get('Settings', 'PORT_Printer')
        logs_path = config.get('Settings', 'logs_PATH')
        technological_line = config.get('Settings', 'technological_line')
        tp = config.get('Settings', 'technological_post')
        test_base = config.get('Settings', "test_base")
        server = config.get('Settings', "server")
        data_base = config.get('Settings', "data_base")
        user = config.get('Settings', "user")

        current_config_print = rf"""IP: {ip_printer}
 PORT: {port_printer}
 Линия: {technological_line}
 Технологический пост отслеживания TP {tp}
 Время обновления данных: {time_update}\
 Путь сохранения логов: {logs_path}
 -------------Данные для подключения к брокеру
 Сервер: {server}
 База данных: {data_base}
 Пользователь: {user}\
 Тестовая бд: {"Да" if test_base else "Нет"}
                        """

        print("Текущия конфигурация:\n", current_config_print)

        if config:
            init_config_answer = str(input(r"Оставить текущую конфигурацию?(Да\Нет):"))
            if init_config_answer.upper() == "ДА":
                print("OK")
            elif init_config_answer.upper() == "НЕТ":
                write_config()
            else:
                print("Попробуй ещё раз. Ответ должен быть 'Да' или 'Нет'")
                init_config()
        else:
            print("здесь запрос на новую конфигурацию")


def write_config():
    config = configparser.ConfigParser()

    print("Заполните данные для конфигурации:")
    ip_printer = str(input("IP маркиратора: "))
    port_printer = 3550
    logs_path = str(input("Путь к файлу для логирования: "))
    technological_line = int(input("Номер линии: "))
    tp = int(input("Отслеживаемый технологический пост: "))
    time_update = int(input("Время обновления данных: "))
    test_base = int(input("Тестовая база (1-вкл., 0-выкл)(DESKTOP-GMTCURD): "))
    print("----Параметры основной базы данных-----")
    server = str(input("Сервер: "))
    data_base = str(input("База данных: "))
    user = str(input("Пользователь: "))

    config['Settings'] = {'IP_Printer': ip_printer, 'PORT_Printer': port_printer, "logs_PATH": logs_path,
                          "technological_line": technological_line, "technological_post": tp,
                          "time_update": time_update, "test_base": test_base, "server": server, "data_base": data_base,
                          "user": user}
    print("Сохранено")

    with open(config_file, 'w') as configfile:
        config.write(configfile)

    init_config()


def product_cycle(p: Printer, server_data, reporting_info):
    for product_data in sorted(server_data, key=lambda x: x['marker_product']):
        print("-----------------------Изделие в печати: ", product_data)
        m = product_data['marker_product']
        send_info = [reporting_info[i] for i in range(len(reporting_info)) if reporting_info[i][-1] == m][0]
        send_info_list = list(send_info)
        print("Отчётные данные этого изделия:", send_info_list, type(send_info_list))
        p.init_data(product_data, send_info_list)
        command = p.print_cycle(number_lines=4)
        if int(command[-1]) == 4:
            continue
        elif int(command[-1]) == 1:
            p.init_data(server_data[0] if server_data[0]['marker_product'] == 1
                        else server_data[1],
                        send_info_list)
            command = p.print_cycle(number_lines=4)


def product_cycle_while(p: Printer, server_data, reporting_info):
    step = 1
    number_products = len(server_data)
    while step < number_products + 1:

        # product_data = server_data[0] if server_data[0]['marker_product'] == step else server_data[1]

        if server_data[0]['marker_product'] == step:
            product_data = server_data[0]
        elif len(server_data) > 1:
            product_data = server_data[1]
        else:
            return "OK"

        m = product_data['marker_product']
        send_info = [reporting_info[i] for i in range(len(reporting_info)) if reporting_info[i][-1] == m][0]
        send_info_list = list(send_info)
        p.init_data(product_data, send_info_list)
        command = p.print_cycle(number_lines=4)
        print(command)

        if command == "Next":
            step += 1
        elif int(command[-1]) == 1:
            step = 1
        elif int(command[-1]) == 2:
            step = 2
        elif int(command[-1]) == 4:
            return "LastPalCommand"
        else:
            step = 3
    return "OK"


async def async_main(printer):
    config = configparser.ConfigParser()
    config.read("config.ini")
    first_start = True  # Первый старт менять тут!!! Если 0 то программа печатает последнюю палету
    async_listener_task = None
    time_sleep = int(config.get('Settings', 'time_update'))

    while True:
        if printer.async_feedback == "Command_4":
            last_pal = True
        else:
            last_pal = False
        update_status, count_products, rows = get_update_status_and_data(first_start, last_pal)
        first_start = False
        printer.async_feedback = None

        if update_status:
            if async_listener_task is not None:
                async_listener_task.cancel()
                async_listener_task = None  # Обнуляем переменную

            print("Получаем инфо-----")
            data, info = processing_server_data(rows)
            next_status = product_cycle_while(printer, data, info)
            if next_status == "LastPalCommand":
                first_start = True
        else:
            if async_listener_task is None:
                async_listener_task = asyncio.create_task(printer.async_printer_listener())
            print("Данные асинхронного ответа:", printer.async_feedback)
            print(f"Ждём {time_sleep} сек.", "-" * 30)
            try:
                # Ждем события в течение time_sleep секунд
                await asyncio.wait_for(async_listener_task, timeout=time_sleep)
            except asyncio.TimeoutError:
                # Время ожидания истекло, переходим к следующей итерации
                pass
            # await asyncio.sleep(time_sleep)


if __name__ == "__main__":
    # init_config()
    config = configparser.ConfigParser()
    config.read("config.ini")
    # password = str(input("Пароль к бд: "))
    print("Ожидание подключения к маркировщику...")
    user = config.get('Settings', "user")
    # keyring.set_password("KMP260", user, password)

    connect_bd()

    printer_KPM = Printer()

    try:
        asyncio.run(async_main(printer_KPM))
    except KeyboardInterrupt:
        # Обработка прерываний
        pass
