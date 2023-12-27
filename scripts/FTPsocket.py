import socket
import time
import re
import os


ftp_server = "192.168.0.70"
ftp_port = 3550


def get_file_size(file_path):
    try:
        # Получаем размер файла в байтах
        size_in_bytes = os.path.getsize(file_path)
        return size_in_bytes
    except FileNotFoundError:
        print(f"Файл '{file_path}' не найден.")
        return None
    except Exception as e:
        print(f"Произошла ошибка при получении размера файла: {e}")
        return None


def stop_print():
    stop_print_command = "000B|0000|500|0|0|0000|0|0000|0D0A"
    stop_print_bytes = stop_print_command.encode('ascii')
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ftp_server, ftp_port))
            s.recv(1024)
            s.sendall(stop_print_bytes + b"\r\n")
            buffer_log = s.recv(1024)
            last_line = buffer_log.splitlines()[-1]
            if last_line.decode('ascii').startswith("0000-ok"):
                print(f"Стоп машина: {last_line}")
            s.close()
    except Exception as e:
        print(e)


def start_print():
    start_print_command = "000B|0000|100|/mnt/sdcard/MSG/1/|0|0000|0|0000|0D0A"
    start_print_bytes = start_print_command.encode('ascii')
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ftp_server, ftp_port))
            s.recv(1024)
            s.sendall(start_print_bytes + b"\r\n")
            time.sleep(0.2)
            buffer_log = s.recv(1024)
            last_line = buffer_log.splitlines()[-1]
            if last_line.decode('ascii').startswith("0000-ok"):
                print(f"Старт: {last_line}")
    except Exception as e:
        print(e)


def get_stop_status():
    get_status_command = "000B|0000|400|0|0|0000|0|0000|0D0A"
    get_status_bytes = get_status_command.encode('ascii')

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ftp_server, ftp_port))
            s.recv(1024)
            s.sendall(get_status_bytes + b"\r\n")
            buffer_log = s.recv(1024)
            last_line = buffer_log.decode('ascii').splitlines()[-1]

            match = re.search(r'\b([TF])\b', last_line)
            if match:
                status = match.group(1)
                # Если True значит стоп, если False значит печатает
                print("Стоп?", status)
                return True if status == 'F' else False
    except Exception as e:
        print(e)
        return None


class TLK:
    def __init__(self, num):
        self.num_TLK = num
        self.file_tlk_path = f"Data/{self.num_TLK}.TLK"
        file_size = get_file_size(self.file_tlk_path)
        delete_folder = f"000B|0000|900|/mnt/sdcard/MSG/{self.num_TLK}/|0|0000|0|0000|0D0A"
        print(file_size)
        send_file = f"000B|0000|300|/mnt/sdcard/MSG/{self.num_TLK}/{self.num_TLK}.TLK|{file_size}|0000|end|0000|0D0A"
        build_tlk = f"000B|0000|700|/mnt/sdcard/MSG/{self.num_TLK}/{self.num_TLK}.TLK/|{file_size}|0000|0|0000|0D0A"

        self.send_file_bytes = send_file.encode('ascii')
        self.delete_folder_bytes = delete_folder.encode('ascii')
        self.build_tlk_bytes = build_tlk.encode('ascii')

    def upload_tlk(self, s):
        try:
            s.sendall(self.delete_folder_bytes + b"\r\n")
            time.sleep(0.1)
            buffer_log = s.recv(1024).decode('ascii')
            s.sendall(self.send_file_bytes + b"\r\n")

            with open(self.file_tlk_path, "rb") as file:
                file_data = file.read()
                s.sendall(file_data + b"\r\n")
            time.sleep(5)
            # with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s2:
            #     s2.connect((ftp_server, ftp_port))
            s.recv(1024)
            s.sendall(self.build_tlk_bytes + b"\r\n")
            time.sleep(0.5)
            buffer_log = s.recv(1024)
            last_line = buffer_log.splitlines()[-1]
            print(last_line)
            if last_line.decode('ascii').startswith("0000-ok"):
                print(f"Файл скомпилирован: {last_line}")

        except Exception as e:
            print("Ошибка загрузки:", e)
