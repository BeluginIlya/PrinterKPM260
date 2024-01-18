import datetime

import pyodbc
from scripts.configs import Configurate

previous_datetime = datetime.datetime(2020, 12, 25, 15, 24, 26, 740000)
last_pal_num = 0
source_connection = None


def connect_bd(config: Configurate):
    global source_connection

    test_base = config.test_base
    server = config.server
    data_base = config.data_base
    user = config.user
    # password = keyring.get_password("KMP260", user)
    password = "7781ab60"
    if test_base:
        source_connection_string = r'DRIVER={SQL Server};SERVER=rz-pc-astp-2200;DATABASE=Test;Trusted_Connection=yes'
    else:
        source_connection_string = (
            r'DRIVER={SQL Server};'
            rf'SERVER={server};'
            rf'DATABASE={data_base};'
            rf'UID={user};'
            rf'PWD={password};'
        )
        print("Подключение:", source_connection_string)
    print("Включена ли тестовая база?:", test_base)
        
    source_connection = pyodbc.connect(source_connection_string)

    return(source_connection)


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
    # haven't feedback about added data or error
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
    
    print("Ответ при обновлении: ", source_cursor.fetchall)

    source_cursor.commit()