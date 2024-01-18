import asyncio

from scripts.connections.server_api import send_status_print
from scripts.connections.ConnectionsMS import connect_bd
from scripts.connections.ConnectionBroker import *
from scripts.main_loop import async_main_cycle
from scripts.configs import Configurate
from scripts.Printer import Printer



if __name__ == "__main__":
    config = Configurate().init_config()
    print("Ожидание подключения к маркиратору...")
    user = config.user
    # keyring.set_password("KMP260", user, password)

    loop = asyncio.get_event_loop()
    connect_bd(config)

    while True:
        try:
            printer_KPM = Printer(loop)
            loop.run_until_complete(async_main_cycle(printer_KPM))
        except Exception as e:
            print(e)
            send_status_print(status="NOT CONNECT")