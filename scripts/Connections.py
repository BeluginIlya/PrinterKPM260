import configparser
import datetime
import keyring
import re

import pyodbc

config = configparser.ConfigParser()


previous_datetime = datetime.datetime(2020, 12, 25, 15, 24, 26, 740000)
source_connection = None

def connect_bd():
    global source_connection

    config.read('config.ini')
    test_base = int(config.get('Settings', "test_base"))
    server = config.get('Settings', "server")
    data_base = config.get('Settings', "data_base")
    user = config.get('Settings', "user")
    password = keyring.get_password("KMP260", user)
    if test_base:
        source_connection_string = r'DRIVER={SQL Server};SERVER=DESKTOP-GMTCURD;DATABASE=Test;Trusted_Connection=yes'
    else:
        source_connection_string = (
            r'DRIVER={SQL Server};'
            rf'SERVER={server};'
            rf'DATABASE={data_base};'
            rf'UID={user};'
            rf'PWD={password};'
        )
    source_connection = pyodbc.connect(source_connection_string)


def get_update_status(first_start: bool, last_pal: bool):
    config.read('config.ini')
    tp = config.get('Settings', 'technological_post')
    global previous_datetime

    source_cursor = source_connection.cursor()
    if last_pal:
        # Сбрасываем время, чтобы получить последние 2 изделия
        previous_datetime = datetime.datetime(2020, 12, 25, 15, 24, 26, 740000)

    if not first_start:
        source_cursor.execute(f"""SELECT TOP 2 Timestamp, PalNo FROM LocPalHistoryWithBarcode 
                                  WHERE locationName ='TP {tp}'  AND PalNo = (SELECT TOP 1 PalNo  
                                  FROM LocPalHistoryWithBarcode ORDER BY Timestamp DESC)
                                  ORDER BY Timestamp DESC""")

        rows = source_cursor.fetchmany(2)  # Получаем топ 2 строки
        print("Получили из бд", rows)

        count_products = 0
        for row in rows:
            current_datetime = row[0]
            if current_datetime > previous_datetime:
                print("\nТекущее значение:", current_datetime, "\n-True")
                count_products += 1
            else:
                print("\nТекущее значение:", current_datetime, "\nПредыдущее:", previous_datetime, "\n-False")
        print("Сколько новых изделий на посту:", count_products)
        previous_datetime_row = max(rows, key=lambda x: x[0])
        previous_datetime = previous_datetime_row[0]
        if count_products:
            return True, count_products
        else:
            return False, None
    else:
        print("Первый старт. Записываем время последнего добавления изделия на пост")
        source_cursor.execute(f"""SELECT TOP 1 Timestamp FROM LocPalHistoryWithBarcode 
                                          WHERE locationName ='TP {tp}' 
                                          ORDER BY Timestamp DESC;""")
        previous_datetime = source_cursor.fetchmany(1)[0][0]
        print("Дата, время последнего добавления:", previous_datetime, "Тип:", type(previous_datetime))
        return False, None


def convert_for_printer(row, marker_product) -> dict:
    config.read('config.ini')
    tp = config.get('Settings', 'technological_post')
    num_line = config.get('Settings', 'technological_line')

    print("Строка из бд:", row)
    result_dict = dict()
    match = re.search(r'_(.*?)_', row[2])

    result_dict[0] = [f"{'Первое' if marker_product == 1 else 'Второе'} изделие на палете. Номер палеты: {row[0]}"]
    result_dict[1] = [match.group(1)]
    result_dict[2] = [0, "0000000000", num_line, tp]
    barcode = row[1][-6:]
    print(0, barcode, "barcode: ")
    result_dict[3] = [0, barcode, "P00000", ]

    # Колличество агруметов необходимо передать в основной цикл printer.print_cycle(number_lines=\n/)

    return result_dict


def get_data_from_server(count_products):
    config.read('config.ini')
    tp = config.get('Settings', 'technological_post')
    try:
        source_cursor = source_connection.cursor()
        source_cursor.execute(f"""
            SELECT TOP {count_products} PalNo,Barcode, Product, Timestamp, PosX 
            FROM LocPalHistoryWithBarcode 
            WHERE locationName = ?
            ORDER BY Timestamp DESC;
        """, f'TP {tp}')
        rows = source_cursor.fetchall()

        server_data = []
        max_pos_x = max(int(rows[i][-1]) for i in range(len(rows)))
        for i in range(len(rows)):
            if len(rows) > 1:
                marker_product = 2 if int(rows[i][-1]) == max_pos_x else 1  # упорядовачивание по координате x
            else:
                marker_product = 1
            convert_data = convert_for_printer(rows[i], marker_product)
            convert_data["marker_product"] = marker_product

            rows[i][-1] = marker_product
            server_data.append(convert_data)

        print("Конвертированные данные:", server_data)
        print("Отчётная информация: ", rows)
        return server_data, rows

    except Exception as e:
        print('Произошла ошибка:', e)
        return None


def send_printing_info(reporting_info: list):
    source_cursor = source_connection.cursor()
    timestamp = reporting_info[3]
    barcode = reporting_info[1]
    source_cursor.execute("""
MERGE INTO [dbo].[LocalPrintHistory] AS target
USING (SELECT ?, ?, ?, ?, ?, ?) AS source ([PalNo], [NumProd], [Timestamp], [Barcode], [Product], [StatusPrint])
ON target.[Timestamp] = source.[Timestamp] AND target.[Barcode] = source.[Barcode]
WHEN NOT MATCHED THEN
    INSERT ([PalNo], [NumProd], [Timestamp], [Barcode], [Product], [StatusPrint])
    VALUES (source.[PalNo], source.[NumProd], source.[Timestamp], source.[Barcode], source.[Product], source.[StatusPrint]);
            """, reporting_info[0],
                          reporting_info[-1],
                          timestamp,
                          barcode,
                          reporting_info[2],
                          0,
                          )

    source_cursor.commit()


def update_status_db(reporting_info):
    source_cursor = source_connection.cursor()
    source_cursor.execute("""
    UPDATE [dbo].[LocalPrintHistory]
    SET [StatusPrint] = 1
    WHERE [Barcode] = ? AND [Timestamp] = CONVERT(DATETIME,?, 21)
                """, reporting_info[1],
                          reporting_info[3],
                          )

    source_cursor.commit()