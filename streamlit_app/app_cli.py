import lightgbm as lgb
import json
from datetime import datetime, timedelta
from constants import MODEL_FOLDER, PROCESSED_DATA_FOLDER
from model_helpers import raw_to_lgb_format


def get_datetime(fmt: str = "%Y-%m-%d %H:%M") -> datetime:
    while True:
        raw = input("Enter Departure Time (expected format: 2026-04-13 18:33): ")
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            print(f"Invalid format, expected {fmt}. Try again.")


def pairwise(lst: list[int]) -> list[tuple[int, int]]:
    return list(zip(lst, lst[1:]))


def predict() -> float:
    r = input("Which route would you to take: ")
    # Cast "Route" as ENUM type to ensure identical categorical variable encoding for train and test set
    with open(PROCESSED_DATA_FOLDER / "target_stops.json", "r", encoding="utf-8") as f:
        target_stops: dict[str, list[int]] = json.load(f)
    with open(PROCESSED_DATA_FOLDER / "stops_dict.json", "r", encoding="utf-8") as f:
        stops_dict: dict[str, str] = json.load(f)
    with open(PROCESSED_DATA_FOLDER / "target_routes.json", "r", encoding="utf-8") as f:
        target_routes: list[str] = json.load(f)

    if r not in target_routes:
        raise ValueError(f"Route {r} is not supported.")
    possible_stops = target_stops[r]

    print("Here are stops available for this route:")
    for s in possible_stops[:-1]:
        print(s, stops_dict[str(s)])
    depart = int(input("Please input the ID of deaprture stop: "))
    if depart not in possible_stops[:-1]:
        raise ValueError("Invalid StopID")

    depart_idx = possible_stops.index(depart)
    print(f"Here are the available destinations from {depart}:")
    for s in possible_stops[depart_idx + 1 :]:
        print(s, stops_dict[str(s)])
    arrival = int(input("Please input the ID of arrival stop: "))
    if arrival not in possible_stops[depart_idx + 1 :]:
        raise ValueError("Invalid StopID")
    current_dt = get_datetime()

    pairs = pairwise(possible_stops[depart_idx : possible_stops.index(arrival) + 1])
    r_id = target_routes.index(r)
    prediction = 0.0

    # load model last minute
    model = lgb.Booster(
        model_file=MODEL_FOLDER / "target_encoding_model/best_lgbm_model.txt"
    )
    for pair in pairs:
        my_input = raw_to_lgb_format(r, pair[0], pair[1], current_dt)
        model_input = [
            [
                r_id,
                my_input.mean_travel_time,
                my_input.minutes_past_midnight,
                my_input.day_of_week,
            ]
        ]
        step_prediction = model.predict(model_input).item()
        current_dt += timedelta(minutes=step_prediction)
        prediction += step_prediction
    print(f"Predicted Travel Time: {prediction:.2f} minutes.")
    print(
        f"Predicted Arrival Time: {current_dt.replace(second=0, microsecond=0) + timedelta(minutes=round(prediction))}"
    )

    return prediction


if __name__ == "__main__":
    predict()
