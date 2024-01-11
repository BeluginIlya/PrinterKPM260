with tt as (select top 4 * from [dbo].[LocPalHistoryWithBarcode] where [LocationName] = 'TP 1' order by [Timestamp] desc), t as (SELECT top 4
        [LocationName],
        [PalNo],
        [Timestamp],
        [Barcode],
        [Product],
        [ProductionThickness],
        [MaxLength],
        [MaxWidth],
        [PosX],
        ROW_NUMBER() OVER (PARTITION BY [Barcode] ORDER BY [Timestamp] DESC) AS RowNum
    FROM tt
    WHERE [LocationName] = ?  AND [PalNo] = (
        SELECT TOP (1) [PalNo]
        FROM [dbo].[LocPalHistoryWithBarcode]
        WHERE [LocationName] = ?
        ORDER BY [Timestamp] DESC
    ) AND [PalNo] <> ?
	order by [Timestamp] desc)


SELECT top 2
    [PalNo],
    [Barcode],
    [Product],
    [Timestamp],
    [PosX]
FROM t
WHERE RowNum = 1;