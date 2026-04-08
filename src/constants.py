from pathlib import Path
from datetime import date
import polars as pl

# paths
ROOT_DIR = Path(__file__).parent.parent
DATA_FOLDER = ROOT_DIR / "data"
RAW_DATA_FOLDER = DATA_FOLDER / "raw"
PROCESSED_DATA_FOLDER = DATA_FOLDER / "processed"
DATA_FILE = RAW_DATA_FOLDER / "bus_event_time_train.parquet"
DATA_TEST_FILE = RAW_DATA_FOLDER / "bus_event_time_test.parquet"
ROUTES = RAW_DATA_FOLDER / "bus_routes_mar28.csv"
STOPS = RAW_DATA_FOLDER / "bus_stops_mar3.csv"
SAMPLE = RAW_DATA_FOLDER / "bus_GPS_sample.csv"
DEMO_FOLDER = ROOT_DIR / "streamlit_demo"
MODEL_FOLDER = ROOT_DIR / "model"


DAY_CATEGORIES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# holidays are not used as they are not useful features
holidays = [
    # 2025
    # New Year's Day
    date(2025, 1, 1),
    # Lunar New Year
    date(2025, 1, 25),
    date(2025, 1, 26),
    date(2025, 1, 27),
    date(2025, 1, 28),
    date(2025, 1, 29),
    date(2025, 1, 30),
    date(2025, 1, 31),
    date(2025, 2, 1),
    date(2025, 2, 2),
    # 228 Peace Memorial Day
    date(2025, 2, 28),
    date(2025, 3, 1),
    date(2025, 3, 2),
    # Children's Day & Tomb Sweeping Day
    date(2025, 4, 3),
    date(2025, 4, 4),
    date(2025, 4, 5),
    date(2025, 4, 6),
    # Labor Day
    date(2025, 5, 1),
    # Dragon Boat Festival
    date(2025, 5, 30),
    date(2025, 5, 31),
    date(2025, 6, 1),
    # Teacher's Day
    date(2025, 9, 27),
    date(2025, 9, 28),
    date(2025, 9, 29),
    # Mid-Autumn Festival
    date(2025, 10, 4),
    date(2025, 10, 5),
    date(2025, 10, 6),
    # National Day
    date(2025, 10, 10),
    date(2025, 10, 11),
    date(2025, 10, 12),
    # Taiwan Retrocession Day
    date(2025, 10, 24),
    date(2025, 10, 25),
    date(2025, 10, 26),
    # Constitution Day
    date(2025, 12, 25),
    # 2026
    # New Year's Day
    date(2026, 1, 1),
    # Lunar New Year
    date(2026, 2, 14),
    date(2026, 2, 15),
    date(2026, 2, 16),
    date(2026, 2, 17),
    date(2026, 2, 18),
    date(2026, 2, 19),
    date(2026, 2, 20),
    date(2026, 2, 21),
    date(2026, 2, 22),
    # 228 Peace Memorial Day
    date(2026, 2, 27),
    date(2026, 2, 28),
    date(2026, 3, 1),
    # Children's Day & Tomb Sweeping Day
    date(2026, 4, 3),
    date(2026, 4, 4),
    date(2026, 4, 5),
    date(2026, 4, 6),
    # Labor Day
    date(2026, 5, 1),
    date(2026, 5, 2),
    date(2026, 5, 3),
    # Dragon Boat Festival
    date(2026, 6, 19),
    date(2026, 6, 20),
    date(2026, 6, 21),
    # Mid-Autumn Festival & Teacher's Day
    date(2026, 9, 25),
    date(2026, 9, 26),
    date(2026, 9, 27),
    date(2026, 9, 28),
    # National Day
    date(2026, 10, 9),
    date(2026, 10, 10),
    date(2026, 10, 11),
    # Taiwan Retrocession Day
    date(2026, 10, 24),
    date(2026, 10, 25),
    date(2026, 10, 26),
    # Constitution Day
    date(2026, 12, 25),
    date(2026, 12, 26),
    date(2026, 12, 27),
]

long_holidays = [
    # 2025
    # Lunar New Year (9 days)
    date(2025, 1, 25),
    date(2025, 1, 26),
    date(2025, 1, 27),
    date(2025, 1, 28),
    date(2025, 1, 29),
    date(2025, 1, 30),
    date(2025, 1, 31),
    date(2025, 2, 1),
    date(2025, 2, 2),
    # 228 Peace Memorial Day (3 days)
    date(2025, 2, 28),
    date(2025, 3, 1),
    date(2025, 3, 2),
    # Children's Day & Tomb Sweeping Day (4 days)
    date(2025, 4, 3),
    date(2025, 4, 4),
    date(2025, 4, 5),
    date(2025, 4, 6),
    # Dragon Boat Festival (3 days)
    date(2025, 5, 30),
    date(2025, 5, 31),
    date(2025, 6, 1),
    # Teacher's Day (3 days)
    date(2025, 9, 27),
    date(2025, 9, 28),
    date(2025, 9, 29),
    # Mid-Autumn Festival (3 days)
    date(2025, 10, 4),
    date(2025, 10, 5),
    date(2025, 10, 6),
    # National Day (3 days)
    date(2025, 10, 10),
    date(2025, 10, 11),
    date(2025, 10, 12),
    # Taiwan Retrocession Day (3 days)
    date(2025, 10, 24),
    date(2025, 10, 25),
    date(2025, 10, 26),
    # 2026
    # Lunar New Year (9 days)
    date(2026, 2, 14),
    date(2026, 2, 15),
    date(2026, 2, 16),
    date(2026, 2, 17),
    date(2026, 2, 18),
    date(2026, 2, 19),
    date(2026, 2, 20),
    date(2026, 2, 21),
    date(2026, 2, 22),
    # 228 Peace Memorial Day (3 days)
    date(2026, 2, 27),
    date(2026, 2, 28),
    date(2026, 3, 1),
    # Children's Day & Tomb Sweeping Day (4 days)
    date(2026, 4, 3),
    date(2026, 4, 4),
    date(2026, 4, 5),
    date(2026, 4, 6),
    # Labor Day (3 days)
    date(2026, 5, 1),
    date(2026, 5, 2),
    date(2026, 5, 3),
    # Dragon Boat Festival (3 days)
    date(2026, 6, 19),
    date(2026, 6, 20),
    date(2026, 6, 21),
    # Mid-Autumn Festival & Teacher's Day (4 days)
    date(2026, 9, 25),
    date(2026, 9, 26),
    date(2026, 9, 27),
    date(2026, 9, 28),
    # National Day (3 days)
    date(2026, 10, 9),
    date(2026, 10, 10),
    date(2026, 10, 11),
    # Taiwan Retrocession Day (3 days)
    date(2026, 10, 24),
    date(2026, 10, 25),
    date(2026, 10, 26),
    # Constitution Day (3 days)
    date(2026, 12, 25),
    date(2026, 12, 26),
    date(2026, 12, 27),
]
