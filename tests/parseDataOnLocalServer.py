import pyodbc

# Параметры подключения к первой базе данных (источнику)
source_connection_string = r'DRIVER={SQL Server};SERVER=192.168.15.200\sqlstandard2016;DATABASE=ebos-DSK1_W1;UID=ASUTP_viewer;PWD=7781ab60'

# Параметры подключения ко второй базе данных (назначению)
destination_connection_string = r'DRIVER={SQL Server};SERVER=DESKTOP-GMTCURD;DATABASE=Test;Trusted_Connection=yes'

def transfer_data():
    try:
        # Подключение к базе данных источнику
        source_connection = pyodbc.connect(source_connection_string)
        source_cursor = source_connection.cursor()

        destination_connection = pyodbc.connect(destination_connection_string)
        destination_cursor = destination_connection.cursor()

        source_cursor.execute('SELECT TOP 20 * FROM LocPalHistoryWithBarcode')
        rows = source_cursor.fetchall()
        print(rows)
        
        source_connection.close()

        # Вставка данных в таблицу в базе данных назначению
        for row in rows:
            destination_cursor.execute('INSERT INTO LocPalHistoryWithBarcode VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                                       row.LocationName, row.PalNo, row.Timestamp, row.Barcode, row.Product,
                                       row.ProductionThickness, row.MaxLength, row.MaxWidth)

        # Подтверждение изменений и закрытие соединений
        destination_connection.commit()
        destination_connection.close()

        print('Перенос данных успешно выполнен.')
    except Exception as e:
        print('Произошла ошибка:', e)

if __name__ == "__main__":
    transfer_data()
