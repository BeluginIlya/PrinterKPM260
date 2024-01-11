import asyncio
import configparser
import os

from scripts.Connections import connect_bd
from scripts.ConnectionBroker import *
from scripts.main_loop import async_main_cycle
from scripts.Printer import Printer

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
    # logs_path = str(input("Путь к файлу для логирования: "))
    # technological_line = int(input("Номер линии: "))
    # tp = int(input("Отслеживаемый технологический пост: "))
    time_update = int(input("Время обновления данных: "))
    # test_base = int(input("Тестовая база (1-вкл., 0-выкл)(DESKTOP-GMTCURD): "))
    # print("----Параметры основной базы данных-----")
    # server = str(input("Сервер: "))
    # data_base = str(input("База данных: "))
    # user = str(input("Пользователь: "))

    config['Settings'] = {'IP_Printer': ip_printer, 'PORT_Printer': port_printer,

                          "time_update": time_update}
    # "technological_line": technological_line, "technological_post": tp,"logs_PATH": logs_path,}
    # , "test_base": test_base, "server": server, "data_base": data_base,
    # "user": user}
    print("Сохранено")

    with open(config_file, 'w') as configfile:
        config.write(configfile)

    init_config()


if __name__ == "__main__":
    # init_config()
    config = configparser.ConfigParser()
    config.read("config.ini")
    # password = str(input("Пароль к бд: "))
    print("Ожидание подключения к маркировщику...")
    user = config.get('Settings', "user")
    # keyring.set_password("KMP260", user, password)

    loop = asyncio.get_event_loop()
    connect_bd()

    while True:
        try:
            printer_KPM = Printer(loop)
            loop.run_until_complete(async_main_cycle(printer_KPM))
        except Exception as e:
            printer_KPM.send_message("Ошибка. Ожидайте подключение")
            print(e)
