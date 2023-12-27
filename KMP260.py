import configparser
import os
import time

from scripts.Connections import get_update_status, get_data_from_server
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

        current_config_print = rf"""IP: {ip_printer}
 PORT: {port_printer}
 Линия: {technological_line}
 Технологический пост отслеживания TP {tp}\
 Время обновления данных: {time_update}
 -------------Данные для подключения к брокеру
 Путь сохранения логов: {logs_path}
                        """

        print("Текущия конфигурация:\n", current_config_print)

        if config:
            init_config_answer = str(input(r"Оставить текущую конфигурацию?(Да\Нет):"))
            if init_config_answer.upper() == "ДА":
                print("Ok")
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

    config['Settings'] = {'IP_Printer': ip_printer, 'PORT_Printer': port_printer, "logs_PATH": logs_path,
                          "technological_line": technological_line, "technological_post": tp,
                          "time_update": time_update}

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
        product_data = server_data[0] if server_data[0]['marker_product'] == step else server_data[1]
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

if __name__ == "__main__":
    # init_config()

    printer = Printer()
    last_pal = False
    try:
        while True:
            update_status, count_products = get_update_status(last_pal)
            last_pal = False
            if update_status:
                data, info = get_data_from_server(count_products)
                next_status = product_cycle_while(printer, data, info)
                if next_status == "LastPalCommand":
                    last_pal = True

            time.sleep(5)

    except KeyboardInterrupt:
        # Обработка прерываний
        pass
