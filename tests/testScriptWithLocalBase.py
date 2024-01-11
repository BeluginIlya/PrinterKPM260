import random
import time
from datetime import datetime

import pyodbc

# Строка подключения к базе данных
destination_connection_string = r'DRIVER={SQL Server};SERVER=rz-pc-astp-2200;DATABASE=Test;Trusted_Connection=yes'


def insert_data(numbers_of_data):
    try:
        # Подключение к базе данных
        destination_connection = pyodbc.connect(destination_connection_string)
        destination_cursor = destination_connection.cursor()
        data_to_insert = []
        pal_no = random.randint(1, 150)
        timestamp1 = datetime.now()
        barcode1 = random.randint(10 ** 11, 10 ** 12 - 1)
        time.sleep(0.5)
        timestamp2 = datetime.now()
        barcode2 = random.randint(10 ** 11, 10 ** 12 - 1)
        print(timestamp1, timestamp2)


        # for i in range(numbers_of_data):
        for i in range(numbers_of_data):
            if i % 2 == 0:
                timestamp = timestamp1
                barcode = barcode1
            else:
                timestamp = timestamp2
                barcode = barcode2
            
            posx = random.randint(100, 999)
            data_to_insert.append(
                ('TP 1', 11, timestamp, barcode, '1_3НСг-СН-390.305.36-2-5_17.05.2023 15.29.58.uni', 360,
                 3045, 3895, posx)
            )

        # Вставка данных в таблицу
        for data in data_to_insert:
            destination_cursor.execute('''
                INSERT INTO [dbo].[LocPalHistoryWithBarcode]
                ([LocationName], [PalNo], [Timestamp], [Barcode], [Product], [ProductionThickness], [MaxLength], [MaxWidth], [PosX])
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', data)

        destination_connection.commit()
        destination_connection.close()
        print(f"Добавленные данные: {data_to_insert}")

        print('Вставка данных успешно выполнена.')
    except Exception as e:
        print('Произошла ошибка:', e)


if __name__ == "__main__":
    numbers_of_data = int(input("Колличество новых значений в бд: "))
    insert_data(numbers_of_data)
