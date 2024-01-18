import os
import configparser


class Configurate():
    def __init__(self) -> None:
        self.config = configparser.ConfigParser()
        self.config_file = "config.ini"

        self.time_update: int
        self.ip_printer: str
        self.port_printer: int
        self.logs_path: str
        self.technological_line: int
        self.tp: int
        self.test_base: int
        self.server: str
        self.data_base: str
        self.user: str
        self.api_host: str

    # ДЛЯ ИНИЦИАЛИЗАЦИИ ДАННЫХ В ХОДЕ ПРОГРАММЫ 
    def init_config(self):
        if not os.path.exists(self.config_file):
            self.write_config()
        else:
            self.get_config()  

            current_config_print = rf"""IP: {self.ip_printer}
    PORT: {self.port_printer}
    Линия: {self.technological_line}
    Технологический пост отслеживания TP {self.tp}
    Время обновления данных: {self.time_update}
    Путь сохранения логов: {self.logs_path}
    -------------Данные для подключений
    Хост для связи с Web-сервером: {self.api_host}
    Сервер: {self.server}
    База данных: {self.data_base}
    Пользователь: {self.user}
    Тестовая бд: {"Да" if self.test_base else "Нет"}
                            """
            print("Текущия конфигурация:\n", current_config_print)

            if self.config:
                init_config_answer = str(input(r"Оставить текущую конфигурацию?(Да\Нет):"))
                if init_config_answer.upper() == "ДА":
                    print("OK")
                elif init_config_answer.upper() == "НЕТ":
                    self.write_config()
                else:
                    print("Попробуй ещё раз. Ответ должен быть 'Да' или 'Нет'")
                    self.init_config()
            else:
                print("здесь запрос на новую конфигурацию")
        return self

    def write_config(self):
        config = configparser.ConfigParser()

        print("Заполните данные для конфигурации:")
        ip_printer = input("IP маркиратора: ")
        port_printer = 3550
        logs_path = input("Путь к файлу для логирования: ")
        technological_line = int(input("Номер линии: "))
        tp = int(input("Отслеживаемый технологический пост: "))
        time_update = int(input("Время обновления данных: "))
        test_base = int(input("Тестовая база (1-вкл., 0-выкл)(DESKTOP-GMTCURD): "))
        print("----Параметры подключений-----")
        print('Хост для связи с Web-сервером. Eсли программа на одном хосте с сервером, то http://localhost:8000/')
        api_host = input('Укажите хост: ')
        server = input("Сервер: ")
        data_base = input("База данных: ")
        user = input("Пользователь: ")

        config['Settings'] = {'IP_Printer': ip_printer, 'PORT_Printer': port_printer,
                            "time_update": time_update,"technological_line": technological_line, 
                            "technological_post": tp,"logs_PATH": logs_path,
                            "test_base": test_base, "server": server, "data_base": data_base,
                            "user": user, "api_host": api_host}
        print("Сохранено")

        with open(self.config_file, 'w') as configfile:
            config.write(configfile)

        self.init_config()

    
    # ДЛЯ ИНИЦИАЛИЗАЦИИ ДАННЫХ В ХОДЕ ПРОГРАММЫ 
    def get_config(self):
        self.config.read(self.config_file)      
        self.time_update = int(self.config.get('Settings', 'time_update'))

        self.ip_printer = self.config.get('Settings', 'IP_Printer')
        self.port_printer = int(self.config.get('Settings', 'port_printer'))
        self.logs_path = self.config.get('Settings', 'logs_PATH')
        self.technological_line = self.config.get('Settings', 'technological_line')
        self.tp = self.config.get('Settings', 'technological_post')
        self.test_base = int(self.config.get('Settings', "test_base"))
        self.server = self.config.get('Settings', "server")
        self.data_base = self.config.get('Settings', "data_base")
        self.user = self.config.get('Settings', "user")
        self.api_host = self.config.get('Settings', "api_host")


        return self