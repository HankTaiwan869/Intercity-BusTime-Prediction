import polars as pl


def clean_df(df_dirty: pl.LazyFrame) -> pl.LazyFrame:
    """
    Standardizes bus GPS data: filters for actual departures, parses 'GPSTime', 
    and extracts 'Route' from 'SubRouteID'.

    Note:
        For max performance, filter 'SubRouteID' or 'GPSTime' **before** calling this to avoid running regex/parsing on excluded rows.

    Example:
        >>> df.filter(pl.col("SubRouteID").str.starts_with("1728")) \\
        ...   .pipe(clean_df) \\
        ...   .collect()
    """
    df_clean = (
        df_dirty.filter(pl.col("TripStartTimeType") == "實際發車時間")
        .with_columns(
            pl.col("GPSTime")
            .str.replace(r"\+08:00", "")
            .str.to_datetime(format="%Y-%m-%dT%H:%M:%S")
            .alias("Time"),
            # The last digit of SubRouteID represents same info from Direction
            # Separating them would be clearer
            pl.col("SubRouteID").str.replace(r".$", "").alias("Route"),
        )
        .select(
            pl.col("Route"),
            pl.col("PlateNumb").alias("Plate"),
            pl.col("Direction"),
            pl.col("StopNameZh_tw").alias("Stop"),
            pl.col("StopSequence").alias("StopSeq"),
            pl.col("A2EventType").alias("Event"),
            pl.col("Time"),
        )
    )

    return df_clean
