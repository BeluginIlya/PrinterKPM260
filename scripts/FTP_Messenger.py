import asyncio
import configparser
import re
import socket
import time
import datetime

from scripts.Connections import send_printing_info, update_status_db

config = configparser.ConfigParser()



def connect():
    config.read('config.ini')
    ftp_server = config.get('Settings', 'ip_printer')
    ftp_port = int(config.get('Settings', 'port_printer'))
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ftp_server, ftp_port))
    res = s.recv(1024).decode('ascii')
    print("Connect: ", res)
    return s


def convert_to_ascii(input_string: str) -> bytes:
    print("конвертация для ", input_string)
    if input_string and any('а' <= str(char) <= 'я' or 'А' <= str(char) <= 'Я' for char in input_string):
        byte_string = input_string.encode('utf-8')
        hex_representation = byte_string.hex()
        return bytes.fromhex(hex_representation.upper())
    else:
        return input_string.encode('ascii')


def extract_num_prod(line, p):
    _, segment = extract_num_string(line)
    if segment != "G-1": # На случай если напечатали отдельную не последнюю строчку
        work_data = p.listen_data(1) # Съедаем 2 строчки
        time.sleep(5)
        return True, "G-1"
    else:
        second_line_segments = line.split('|')
        if line and len(second_line_segments) > 6 and second_line_segments[2] == '1000':
            try:
                return True, int(second_line_segments[3])
            except ValueError:
                return False, second_line_segments[3]
        else:
            return False, None


def extract_num_string(line):
    second_line_segments = line.split('|')
    if line and len(second_line_segments) > 6 and second_line_segments[2] == '1000':
        try:
            return True, int(second_line_segments[5]) - 1
        except ValueError:
            print("Исключение в функции extract_num_string. Возвращаем str")
            return False, second_line_segments[5]
    else:
        return False, None


class Printer:
    reporting_info: list
    data: dict

    def __init__(self):
        self.s = connect()
        self.async_feedback = None
        self.status = "Wait"

    def async_printer_listener(self, timeout):
        print("Ждём асинхронно информацию")
        start_time = time.time()
        while True:
            execution_time = time.time() - start_time
            if execution_time > timeout:
                return
            feedback = self.listen_data(1, timeout)
            if feedback:
                extract_status, command = extract_num_string(feedback)
                print(f"feedback: {feedback}")
                print("--------extract", extract_status, command)
                if str(feedback) == "0000-ok: null\n":
                    print("Команда, асинхронно полученная от маркиратора: 'СТОП'.")
                elif command == "Command_4":
                    print("Команда, асинхронно полученная от маркиратора: 'К предыдущей палете'. Ост. прослушивание.")
                    self.async_feedback = command
                    return
                else:
                    print(f"Команда, асинхронно полученная от маркиратора: {feedback}. Продолжаем прослушивание")
            time.sleep(5)


    def print_cycle(self, number_lines) -> str:
        send_printing_info(self.reporting_info)
        stop_status = self.get_stop_status()
        if not stop_status:
            self.stop_print()
        self.start_print()
        time.sleep(0.2)
        work_status, string_number = self.start_listen()
        while work_status and (string_number < number_lines or type(string_number) == str):
            print(string_number)
            self.send_string_message(string_number)
            if string_number == number_lines - 1:
                work_data = self.listen_data(2)  # Съедаем 2 строчки, может быть СЛАБОЕ МЕСТО
                self.end_print_cycle()
                return "Next"
            else:
                work_data = self.listen_data(2)
                lines = work_data.split('\n')
                if str(lines[1]) == "0000-ok: ":
                    work_data = self.listen_data(1)
                    work_status, string_number = extract_num_string(work_data)
                    print("Команда, полученная от маркиратора после 'СТОП': ", string_number)
                    if type(string_number) == str:
                        return string_number
                else:
                    work_status, string_number = extract_num_prod(lines[1], self)
                    if type(string_number) == str:
                        return string_number

    def init_data(self, data, reporting_info):
        self.data = data
        self.reporting_info = reporting_info

    def end_print_cycle(self):
        print("Ждём ответ о завершении работы")
        stop_info = self.listen_data(number_str=1)
        if str(stop_info) == "0000-ok: null\n":
            print("Оператор закончил печать изделия")
            update_status_db(self.reporting_info)
            return True
        else:
            return False

    def stop_print(self):
        stop_print_command = "000B|0000|500|0|0|0000|0|0000|0D0A"
        stop_print_bytes = stop_print_command.encode('ascii')
        self.s.sendall(stop_print_bytes + b"\r\n")
        time.sleep(1)
        buffer_log = self.s.recv(1024)
        last_line = buffer_log.splitlines()[-1]
        if last_line.decode('ascii').startswith("0000-ok"):
            print(f"Стоп машина: {last_line}")

    def start_print(self):
        start_print_command = "000B|0000|100|/mnt/sdcard/MSG/G-1/|0|0000|0|0000|0D0A"
        start_print_bytes = start_print_command.encode('ascii')
        self.s.sendall(start_print_bytes + b"\r\n")

    def get_stop_status(self):  # Отвечает на вопрос: стоит ли маркировщик?
        get_status_command = "000B|0000|400|0|0|0000|0|0000|0D0A"
        get_status_bytes = get_status_command.encode('ascii')
        self.s.sendall(get_status_bytes + b"\r\n")
        time.sleep(0.5)
        buffer_log = self.s.recv(1024)
        last_line = buffer_log.decode('ascii').splitlines()[-1]

        match = re.search(r'\b([TF])\b', last_line)
        if match:
            status = match.group(1)
            # Если True значит в работе, если False значит стоит
            print("Стоп?", True if status == 'F' else False)
            return True if status == 'F' else False

    def listen_data(self, number_str, timeout=None):
        try:
            buffer_data = b""
            lines_received = 0
            self.s.settimeout(timeout)

            while lines_received < number_str:
                listen_info = self.s.recv(1024)
                if not listen_info:
                    print("Соединение закрыто.")
                    break

                buffer_data += listen_info
                lines_received += buffer_data.decode('utf-8').count('\n')

            received_data = buffer_data.decode('utf-8')
            print(f"Получено от устройства ({number_str} строк): {received_data}")
            return received_data
        except Exception as e:
            print(f"{e}. Продолжаем ожидание...")
            return None

    def start_listen(self):
        received_data = self.listen_data(2)
        if received_data:
            lines = received_data.split('\n')

            is_ok = "0000-ok" in lines[0]

            second_line_segments = lines[1].split('|')
            string_number = int(second_line_segments[3]) if len(second_line_segments) > 6 and second_line_segments[
                2] == '1000' else None
            return is_ok, string_number
        else:
            print("Данные не получены")
            return None, None

    def send_message(self, message):
        start_command = f"000B|0000|600|"
        end_command = f"|0|0000|0|0000|0D0A"
        message_bytes = convert_to_ascii(message)
        start_command_bytes = start_command.encode('ascii')
        end_command_bytes = end_command.encode('ascii')
        self.s.sendall(start_command_bytes + message_bytes + end_command_bytes + b'\r\n')

    def send_string_message(self, string_number):
        start_command = f"000B|0000|600|"
        end_command = f"|0|0000|0|0000|0D0A"
        start_command_bytes = start_command.encode('ascii')
        end_command_bytes = end_command.encode('ascii')
        send_data_text = self.data[string_number]
        send_data_ascii = [start_command_bytes]

        for index in range(len(send_data_text)):
            value_ascii = convert_to_ascii(str(send_data_text[index]))
            send_data_ascii.append(value_ascii)
        print("-----------------Заполненные отправляемые данные: ", send_data_ascii)

        test = b''
        for i in range(len(send_data_ascii)):
            if i == 0:
                test += send_data_ascii[0]
            elif i == len(send_data_ascii) - 1:
                n = 12 - (len(send_data_ascii) - 1)  # запятые для элементов, которых нет, по документации)
                test += send_data_ascii[i] + b',' * n
            else:
                test += send_data_ascii[i] + b","
        command_bytes = test + end_command_bytes + b"\n\r"
        print("command_bytes:", command_bytes)
        self.s.sendall(command_bytes)

        self.s.recv(1024)
