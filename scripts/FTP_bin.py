import socket
import time

from FTPsocket import get_file_size

ftp_server = "192.168.0.70"
ftp_port = 3550


def connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ftp_server, ftp_port))
    res = s.recv(1024).decode('ascii')
    print("Connect: ", res)
    return s


class TlkBin1:
    def __init__(self):
        self.s = connect()

    def del_buf(self):
        for i in range(1, 16):
            del_command = "000B|0000|1100|0|0|0000|0|0000|0D0A"
            del_command_bytes = del_command.encode('ascii')

            self.s.sendall(del_command_bytes + b"\r\n")


    def upload_bin(self, num):
        # bin_path = f"Data/{num}.bin"
        bin_path = r"/Data/1.bin"
        size = get_file_size(bin_path)
        print(size)
        del_command = f"000B|0000|1000|{num}|{size}|0000|0|0000|0D0A"
        del_command_bytes = del_command.encode('ascii')

        self.s.sendall(del_command_bytes + b"\r\n")
        print("отправляем бин:", bin_path.encode('ascii'))
        self.s.sendall(bin_path.encode('ascii'))
        # with open(bin_path, "rb") as file:
        #     file_data = file.read()
        #     self.s.sendall(file_data)
        time.sleep(2)
        res = self.s.recv(1024).decode('ascii')
        last_line = res.splitlines()[-1]
        print(last_line)
        if last_line.decode('ascii').startswith("0000-ok"):
            print("Отправили bin")
            return True

    def listen_data(self):
        try:
            buffer_data = self.s.recv(1024)
            while True:
                self.s.settimeout(30)
                data = self.s.recv(1024)
                if not data:
                    print("Соединение закрыто.")
                    break
                else:
                    buffer_data += data

                received_data = buffer_data.decode('utf-8')
                print("Получено от устройства:", received_data)
        except Exception as e:
            print(f"Произошла ошибка: {e}")

    def close_connection(self):
        self.s.close()


if __name__ == "__main__":
    bin = TlkBin1()
    bin.del_buf()
    res = bin.upload_bin(1)
    if res:
        bin.listen_data()
    bin.close_connection()