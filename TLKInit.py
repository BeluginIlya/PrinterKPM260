from scripts.FTPsocket import *

# НЕ ЗАБУДЬ ПРО IP

if __name__ == "__main__":

    status_stop = get_stop_status()

    if not status_stop:
        stop_print()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ftp_server, ftp_port))
        buffer_log = s.recv(1024).decode('ascii')
        for num in range(1, 5):
            TLK(num).upload_tlk(s)
        print("---OK---")
