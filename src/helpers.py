"""Reusable EDA, feature engineering, dataframe cleaning functions"""

from datetime import date, datetime, time, timedelta
from pathlib import Path
import pandas as pd
import polars as pl
import numpy as np


def clean_df(df_dirty: pl.LazyFrame) -> pl.LazyFrame:
    """
    Standardizes bus GPS data: filters for actual departures, parses 'GPSTime' then sort 'Time'.

    Note:
        For max performance, filter 'GPSTime' **before** calling this to avoid running regex/parsing on excluded rows.

    Example:
        >>> df.filter(pl.col("GPSTime").str.starts_with("2026")) \\
        ...   .pipe(clean_df) \\
        ...   .collect()
    """
    df_clean = (
        df_dirty.filter(pl.col("TripStartTimeType") == "實際發車時間")
        .with_columns(
            pl.col("GPSTime")
            .str.replace(r"\+08:00", "")
            .str.to_datetime(format="%Y-%m-%dT%H:%M:%S")
            .alias("Time")
        )
        .with_columns(
            pl.col("Time").dt.to_string("%a").cast(pl.Categorical).alias("Day_of_week"),
        )
        .select(
            pl.col("SubRouteID").alias("Route"),
            pl.col("PlateNumb").alias("Plate"),
            pl.col("Direction"),
            pl.col("StopNameZh_tw").alias("Stop"),
            pl.col("StopID"),
            pl.col("StopSequence").alias("StopSeq"),
            pl.col("A2EventType").alias("Event"),
            pl.col("Time"),
            pl.col("Day_of_week"),
        )
        .sort("Time")
    )

    return df_clean


# This function is now deprecated as the features are not useful
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


# things to improve in this function:
# use pl.LazyFrame
# automatically decide join_tolerance (by calculating travel time of the whole journey and multiply by some factor)
# not sure if the `Event` setting is robust to different routes
# DON'T worry about join by `Direction` as that's taken of by `SubRouteID`
def create_travel_time_column(
    df: pl.DataFrame,
    depart_stop: str,
    dest_stop: str,
    direction: str,
    join_tolerance: str = "2h",
) -> pl.DataFrame:
    if "Plate" not in df.columns:
        raise ValueError("Expected a cleaned df. Try df.pipe(clean_df) first.")

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


def ml_data_preprocess(df: pl.DataFrame, separating_date: date) -> list[pd.DataFrame]:
    if "Plate" not in df.columns:
        raise ValueError("Expected a cleaned df. Try df.pipe(clean_df) first.")
    if "Duration_min" not in df.columns:
        raise ValueError(
            "Expected `Duration_min` column. Try create_travel_time_column first."
        )

    min_datetime = df.select(pl.col("Time").min()).item()
    max_datetime = df.select(pl.col("Time").max()).item()

    df_train = (
        df.filter(
            # pl.col("Duration_min").is_between(20, 120), TODO: think about faulty data filtering
            pl.col("Time").is_between(
                min_datetime,
                datetime(
                    separating_date.year,
                    separating_date.month,
                    separating_date.day,
                    23,
                    59,
                    59,
                ),
            ),
        )
        .with_columns(
            (
                pl.col("Time").dt.hour().cast(pl.Int32) * 60
                + pl.col("Time").dt.minute().cast(pl.Int32)
            ).alias("Minutes_from_midnight")
        )
        .select(
            [
                "Minutes_from_midnight",
                "Day_of_week",
                "Duration_min",
            ]
        )
    )
    df_test = (
        df.filter(
            # pl.col("Duration_min").is_between(20, 120), TODO
            pl.col("Time").is_between(
                separating_date + timedelta(days=1), max_datetime
            ),
        )
        .with_columns(
            (
                pl.col("Time").dt.hour().cast(pl.Int32) * 60
                + pl.col("Time").dt.minute().cast(pl.Int32)
            ).alias("Minutes_from_midnight")
        )
        .select(
            [
                "Minutes_from_midnight",
                "Day_of_week",
                "Duration_min",
            ]
        )
    )
    X_train = df_train.drop("Duration_min").to_pandas()
    y_train = df_train.select("Duration_min").to_pandas()
    X_test = df_test.drop("Duration_min").to_pandas()
    y_test = df_test.select("Duration_min").to_pandas()

    return [X_train, X_test, y_train, y_test]


def calculate_distance_meter(
    lat_1: float, lon_1: float, lat_2: float, lon_2: float
) -> float:
    """calculate the real distance in meters between two sets of Earth coordinates"""
    R = 6_371_000  # Earth's radius in meters

    phi_1, phi_2, delta_phi, delta_lambda = np.radians(
        [lat_1, lat_2, lat_2 - lat_1, lon_2 - lon_1]
    )

    a = (
        np.sin(delta_phi / 2) ** 2
        + np.cos(phi_1) * np.cos(phi_2) * np.sin(delta_lambda / 2) ** 2
    )
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return float(R * c)


def bulk_convert_csv_to_parquet(
    data_folder: Path, parquet_name: str, return_error_files: bool
) -> list[str] | None:
    files = [f.name for f in data_folder.glob("*.csv")]
    schema = {
        "PlateNumb": pl.String,
        "OperatorID": pl.Int32,
        "OperatorNo": pl.Int32,
        "RouteUID": pl.String,
        "RouteID": pl.Int32,
        "RouteNameZh_tw": pl.String,
        "RouteNameEn": pl.String,
        "SubRouteUID": pl.String,
        "SubRouteID": pl.String,
        "SubRouteNameZh_tw": pl.String,
        "SubRouteNameEn": pl.String,
        "Direction": pl.Categorical,
        "StopUID": pl.String,
        "StopID": pl.Int32,
        "StopNameZh_tw": pl.String,
        "StopNameEn": pl.String,
        "StopSequence": pl.Int32,
        "MessageType": pl.Categorical,
        "DutyStatus": pl.Categorical,
        "BusStatus": pl.Categorical,
        "A2EventType": pl.Categorical,
        "GPSTime": pl.String,
        "TripStartTimeType": pl.Categorical,
        "TripStartTime": pl.String,
        "TransTime": pl.String,
        "SrcRecTime": pl.String,
        "SrcTransTime": pl.String,
        "SrcUpdateTime": pl.String,
        "UpdateTime": pl.String,
    }

    error_files = []
    for file in files:
        try:
            pl.scan_csv(
                data_folder / file,
                schema=schema,
            ).null_count().collect()
        except Exception:
            error_files.append(file)

    correct_files = [data_folder / file for file in files if file not in error_files]
    # Ensure .parquet suffix
    saved_path = data_folder / Path(parquet_name).with_suffix(".parquet")

    pl.scan_csv(
        correct_files,
        schema=schema,
    ).sink_parquet(saved_path)
    if return_error_files:
        return error_files
