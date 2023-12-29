import configparser
import datetime
import keyring
import re
import io

import pyodbc

config = configparser.ConfigParser()


previous_datetime = datetime.datetime(2020, 12, 25, 15, 24, 26, 740000)
last_pal_num = 0
source_connection = None

def connect_bd():
    global source_connection

    config.read('config.ini')
    test_base = int(config.get('Settings', "test_base"))
    server = config.get('Settings', "server")
    data_base = config.get('Settings', "data_base")
    user = config.get('Settings', "user")
    # password = keyring.get_password("KMP260", user)
    password = "7781ab60"
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


def get_update_status_and_data(first_start: bool, last_pal: bool):
    global previous_datetime
    global last_pal_num

    config.read('config.ini')
    tp = config.get('Settings', 'technological_post')
    tp_insert = f'TP {tp}'

    source_cursor = source_connection.cursor()
    if last_pal:
        # Сбрасываем время, чтобы получить последние 2 изделия
        previous_datetime = datetime.datetime(2020, 12, 25, 15, 24, 26, 740000)
        last_pal_num = 0

    if not first_start:

        with io.open('sql_queries.sql', 'r', encoding='utf-8') as file:
            sql_query = file.read()

        source_cursor.execute(sql_query, tp_insert, tp_insert, last_pal_num)

        rows = source_cursor.fetchmany(2)  # Получаем топ 2 строки
        print("Получили из бд", rows)

        count_products = 0
        if rows:
            for row in rows:
                current_datetime = row[3]
                if current_datetime > previous_datetime:
                    print("\nТекущее значение:", current_datetime, "\n-True")
                    count_products += 1
                else:
                    print("\nТекущее значение:", current_datetime, "\nПредыдущее:", previous_datetime, "\n-False")
            print("Сколько новых изделий на посту:", count_products)
            previous_datetime_row = max(rows, key=lambda x: x[3])
            previous_datetime = previous_datetime_row[3]
            last_pal_num = int(previous_datetime_row[-1])
            if count_products:
                return True, count_products, rows
            else:
                return False, None, []
        else:
            return False, None, []
    else:
        print("Первый старт. Записываем время последнего добавления изделия на пост")
        source_cursor.execute(f"""SELECT TOP 1 Timestamp, PalNo  FROM LocPalHistoryWithBarcode 
                                          WHERE locationName ='TP {tp}' 
                                          ORDER BY Timestamp DESC;""")
        data = source_cursor.fetchmany(1)[0]
        previous_datetime = data[0]
        last_pal_num = int(data[1])
        print("Дата, время последнего добавления:", previous_datetime, "Тип:", type(previous_datetime))
        return False, None, []


def convert_for_printer(row, marker_product) -> dict:
    config.read('config.ini')
    tp = config.get('Settings', 'technological_post')
    num_line = config.get('Settings', 'technological_line')

    print("Строка из бд:", row)
    result_dict = dict()
    match = re.search(r'_(.*?)_', row[2])
    num_pal = row[0]
    print(f"дата время {row[2]} from {row}")
    year = row[3].year
    month = row[3].month
    day = row[3].day
    barcode = row[1][-6:]

    result_dict[0] = [f"{'Первое' if marker_product == 1 else 'Второе'} изделие на палете. Номер пал.: {row[0]}"]
    result_dict[1] = [match.group(1)]
    result_dict[2] = [f"{year}-{month}-{day}   Л{num_line} П{num_pal}", ]

    result_dict[3] = [barcode]

    # Колличество агруметов необходимо передать в основной цикл printer.print_cycle(number_lines=\n/)

    return result_dict


def processing_server_data(rows):
    try:
        server_data = []
        max_pos_x = max(int(rows[i][-1]) for i in range(len(rows)))
        for i in range(len(rows)):
            if len(rows) > 1:
                marker_product = 1 if int(rows[i][-1]) == max_pos_x else 2  # упорядовачивание по координате x
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
        return None, None


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