"""
This is a temporary file that holds all deployment related helper functions.
Due to hosting constrains, do not import bulky packages.
"""

import json
from pathlib import Path


def get_mean_travel_time(route: str, depart: int, arrival: int) -> float | None:
    FILE_LOCATION = Path(__file__).parent
    # route target encoding
    with open(FILE_LOCATION / "mean_travel_time_encoding.json", "r") as f:
        encoding: dict[str, float] = json.load(f)
    mean_travel_time = encoding.get(f"{route}|{depart}|{arrival}")

    return mean_travel_time
