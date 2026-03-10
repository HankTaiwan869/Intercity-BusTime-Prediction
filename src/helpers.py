import polars as pl
from datetime import time, date


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
            # The last digit of `SubRouteID` represents same info from `Direction`
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


def create_time_features(
    df: pl.DataFrame,
    morning_rush_interval: list[time] = [time(7, 30, 0), time(9, 30, 0)],
    evening_rush_interval: list[time] = [time(16, 30, 0), time(20, 0, 0)],
) -> pl.DataFrame:
    if "Plate" not in df.columns:
        raise ValueError("Expected a cleaned df. Try pipe in clean_df() first.")

    return df.with_columns(
        pl.when(pl.col("Time").dt.time().is_between(*morning_rush_interval))
        .then(pl.lit("morning_rush"))
        .when(pl.col("Time").dt.time().is_between(*evening_rush_interval))
        .then(pl.lit("evening_rush"))
        .otherwise(pl.lit("not_rush"))
        .cast(pl.Categorical)
        .alias("is_rush_hour"),
        pl.col("Time").dt.to_string("%a").cast(pl.Categorical).alias("day_of_week"),
    )


def create_travel_time_column(
    df: pl.DataFrame,
    depart_stop: str,
    dest_stop: str,
    direction: str,
    join_tolerance: str = "2h",
) -> pl.DataFrame:
    if "Plate" not in df.columns:
        raise ValueError("Expected a cleaned df. Try pipe in clean_df() first.")

    depart_df = (
        df.filter(
            pl.col("Event") == "離站",
            pl.col("Stop") == depart_stop,
            pl.col("Direction") == direction,
        )
        .with_columns(pl.col("Time").alias("DepartureTime"))
        .sort("Time")
    )
    dest_df = (
        df.filter(
            pl.col("Event") == "進站",
            pl.col("Stop") == dest_stop,
            pl.col("Direction") == direction,
        )
        .with_columns(pl.col("Time").alias("ArrivalTime"))
        .sort("Time")
    )
    result_df = (
        depart_df.join_asof(
            dest_df,
            on="Time",
            by="Plate",
            strategy="forward",
            tolerance=join_tolerance,
            check_sortedness=False,
        )
        .drop_nulls()
        .with_columns(
            (
                (pl.col("ArrivalTime") - pl.col("DepartureTime")).dt.total_seconds()
                / 60
            ).alias("Duration_min")
        )
    )
    return result_df
