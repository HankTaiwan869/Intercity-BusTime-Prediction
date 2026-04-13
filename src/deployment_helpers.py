"""
This is a temporary file that holds all deployment related helper functions.
Due to hosting constrains, do not import bulky packages.
"""

import json
from collections import namedtuple
from datetime import datetime

from constants import PROCESSED_DATA_FOLDER

Input = namedtuple(
    "Input", ["mean_travel_time", "minutes_past_midnight", "day_of_week"]
)


def raw_to_lgb_format(route: str, depart: int, arrival: int, time: datetime) -> Input:
    # time input
    day_of_week = time.weekday()
    minutes_past_midnight = time.hour * 60 + time.minute

    # route target encoding
    with open(PROCESSED_DATA_FOLDER / "mean_travel_time_encoding.json", "r") as f:
        encoding: dict[str, float] = json.load(f)
    mean_travel_time = encoding.get(f"{route}|{depart}|{arrival}")

    return Input(mean_travel_time, minutes_past_midnight, day_of_week)
