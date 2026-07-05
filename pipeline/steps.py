import shutil
from datetime import datetime, time, timedelta

import polars as pl

from pipeline.config import PipelineConfig
from pipeline.io_utils import read_json, require_csv_folder, require_file, write_json
from pipeline.route_app import create_target_routes_app
from src.constants import DAY_CATEGORIES
from src.helpers import (
    asof_join_by_stop_ids,
    bulk_convert_csv_to_parquet,
    calculate_distance_meter,
    clean_df,
    count_asof_matches_by_stop_ids,
)


def validate_inputs(config: PipelineConfig) -> None:
    require_csv_folder(config.raw_csv_folder)
    require_file(config.stops_csv, "stops CSV")


def ingest_csvs(config: PipelineConfig) -> None:
    rejected = bulk_convert_csv_to_parquet(
        config.raw_csv_folder,
        config.raw_parquet_path.name,
        return_error_files=True,
        output_folder=config.processed_dir,
    )
    write_json(config.reports_dir / "rejected_csv_files.json", rejected or [])


def clean_and_split(config: PipelineConfig) -> None:
    pl.scan_parquet(config.raw_parquet_path).pipe(clean_df).sink_parquet(
        config.clean_events_path
    )

    split_end = datetime.combine(config.train_end_date, time(23, 59, 59))
    split_start = split_end + timedelta(seconds=1)
    events = pl.scan_parquet(config.clean_events_path)
    events.filter(pl.col("Time") <= split_end).sink_parquet(config.clean_train_path)
    events.filter(pl.col("Time") >= split_start).sink_parquet(config.clean_test_path)


def select_routes_and_stops(config: PipelineConfig) -> None:
    train_routes = set(
        pl.scan_parquet(config.clean_train_path)
        .select("Route")
        .unique()
        .collect()
        .get_column("Route")
        .to_list()
    )
    test_routes = set(
        pl.scan_parquet(config.clean_test_path)
        .select("Route")
        .unique()
        .collect()
        .get_column("Route")
        .to_list()
    )
    target_routes = sorted(train_routes & test_routes)
    target_routes = [r for r in target_routes if r not in config.force_exclude_routes]

    stops_df = pl.read_csv(config.stops_csv)
    stops_dict = dict(
        stops_df.select(["StopID", "StopNameZh_tw"])
        .unique(subset=["StopID"])
        .cast({"StopID": pl.String})
        .iter_rows()
    )
    write_json(config.processed_dir / config.stops_dict_filename, stops_dict)

    df = pl.scan_parquet(config.clean_train_path).filter(
        pl.col("Route").is_in(target_routes)
    )
    trips = (
        df.filter(pl.col("Event").is_in(["進站", "離站"]))
        .group_by(["Route", "StopID", "Event"])
        .agg(pl.col("Time").len().alias("count"))
        .group_by(["Route", "StopID"])
        .agg(pl.col("count").max().alias("Trips_recorded"))
        .sort("Trips_recorded")
        .collect(engine="streaming")
    )

    stop_coords: dict[int, tuple[float, float]] = {}
    for row in stops_df.select(["StopID", "PositionLat", "PositionLon"]).to_dicts():
        if row["PositionLat"] is None or row["PositionLon"] is None:
            continue
        stop_coords[int(row["StopID"])] = (row["PositionLat"], row["PositionLon"])

    seq_lookup: dict[tuple[str, int], int] = {
        (row["Route"], row["StopID"]): row["StopSeq"]
        for row in (
            df.select(["Route", "StopID", "StopSeq"])
            .unique(subset=["Route", "StopID"])
            .collect(engine="streaming")
            .to_dicts()
        )
    }

    target_stops: dict[str, list[int]] = {}
    for route_key, group in trips.group_by("Route"):
        route = route_key[0]
        candidates = group.sort("Trips_recorded", descending=True)[
            "StopID"
        ].to_list()
        collected: list[int] = []
        for stop_id in candidates:
            if stop_id not in stop_coords:
                continue
            lat, lon = stop_coords[stop_id]
            too_close = False
            for existing_id in collected:
                if existing_id not in stop_coords:
                    continue
                e_lat, e_lon = stop_coords[existing_id]
                distance_km = calculate_distance_meter(lat, lon, e_lat, e_lon) / 1000
                if distance_km < config.stop_distance_threshold_km:
                    too_close = True
                    break
            if not too_close:
                collected.append(stop_id)

        removals = config.force_remove_stops.get(route, set())
        collected = [stop_id for stop_id in collected if stop_id not in removals]
        collected.sort(key=lambda sid: seq_lookup.get((route, sid), 0))
        if len(collected) >= config.min_selected_stops_per_route:
            target_stops[route] = collected

    target_routes = [route for route in target_routes if route in target_stops]
    target_stops = {
        route: stops for route, stops in target_stops.items() if route in target_routes
    }

    write_json(config.processed_dir / config.target_routes_filename, target_routes)
    write_json(config.processed_dir / config.target_stops_filename, target_stops)


def find_ideal_tolerances(config: PipelineConfig) -> None:
    target_stops: dict[str, list[int]] = read_json(
        config.processed_dir / config.target_stops_filename
    )
    collected_df = (
        pl.scan_parquet(config.clean_train_path)
        .select(["Route", "Plate", "StopID", "Event", "Time"])
        .collect(engine="streaming")
    )

    results: list[dict] = []
    invalid_routes: set[str] = set()
    for route, stop_ids in target_stops.items():
        route_df = collected_df.filter(pl.col("Route") == route)
        if route_df.is_empty():
            invalid_routes.add(route)
            continue

        for depart_id, dest_id in zip(stop_ids, stop_ids[1:]):
            tolerance_hours = config.initial_tolerance_hours
            n_rows = count_asof_matches_by_stop_ids(
                route_df, depart_id, dest_id, f"{tolerance_hours}h"
            )
            while tolerance_hours < config.max_tolerance_hours:
                new_tolerance_hours = tolerance_hours + 1
                new_nrows = count_asof_matches_by_stop_ids(
                    route_df, depart_id, dest_id, f"{new_tolerance_hours}h"
                )
                if n_rows > 0 and new_nrows / n_rows < config.tolerance_growth_threshold:
                    break
                tolerance_hours = new_tolerance_hours
                n_rows = new_nrows

            tolerance = f"{tolerance_hours}h"
            if config.exclude_zero_match_pairs and n_rows == 0:
                invalid_routes.add(route)
            if (
                config.exclude_routes_at_max_tolerance
                and tolerance_hours == config.max_tolerance_hours
            ):
                invalid_routes.add(route)
            results.append(
                {
                    "route": route,
                    "depart_id": depart_id,
                    "dest_id": dest_id,
                    "tolerance": tolerance,
                    "n_rows": n_rows,
                }
            )

    tolerances = pl.DataFrame(results)
    if invalid_routes and config.exclude_routes_with_any_invalid_pair:
        tolerances = tolerances.filter(~pl.col("route").is_in(sorted(invalid_routes)))

        target_routes: list[str] = read_json(
            config.processed_dir / config.target_routes_filename
        )
        target_routes = [route for route in target_routes if route not in invalid_routes]
        target_stops = {
            route: stops
            for route, stops in target_stops.items()
            if route not in invalid_routes
        }
        write_json(config.processed_dir / config.target_routes_filename, target_routes)
        write_json(config.processed_dir / config.target_stops_filename, target_stops)

    tolerances.write_csv(config.processed_dir / "ideal_tolerances.csv")
    write_json(config.reports_dir / "invalid_routes.json", sorted(invalid_routes))


def _create_travel_time(df: pl.DataFrame, tolerances: pl.DataFrame) -> pl.DataFrame:
    results = []
    for target in tolerances.to_dicts():
        df_target = df.filter(
            pl.col("Route") == target["route"],
            pl.col("StopID").is_in([target["depart_id"], target["dest_id"]]),
        )
        result = asof_join_by_stop_ids(
            df_target,
            target["depart_id"],
            target["dest_id"],
            target["tolerance"],
        )
        if not result.is_empty():
            results.append(result)
    return pl.concat(results) if results else pl.DataFrame()


def _format_travel_time_rows(df: pl.DataFrame) -> pl.DataFrame:
    return (
        df.select(
            pl.col("StopID").alias("DepartureStop"),
            pl.col("StopID_right").alias("ArrivalStop"),
            pl.all(),
        )
        .with_columns(
            (
                (pl.col("ArrivalTime") - pl.col("DepartureTime")).dt.total_seconds()
                / 60
            ).alias("TravelDuration_min"),
            (
                pl.col("DepartureTime").dt.hour().cast(pl.Int32) * 60
                + pl.col("DepartureTime").dt.minute().cast(pl.Int32)
            ).alias("MinutesFromMidnight"),
            pl.col("DepartureTime")
            .dt.to_string("%a")
            .cast(pl.Categorical)
            .alias("DayOfWeek"),
        )
        .select(
            [
                "Route",
                "DepartureStop",
                "ArrivalStop",
                "MinutesFromMidnight",
                "DayOfWeek",
                "TravelDuration_min",
            ]
        )
    )


def build_training_data(config: PipelineConfig) -> None:
    target_routes: list[str] = read_json(
        config.processed_dir / config.target_routes_filename
    )
    tolerances = pl.read_csv(config.processed_dir / "ideal_tolerances.csv").filter(
        pl.col("route").is_in(target_routes)
    )
    train_events = (
        pl.scan_parquet(config.clean_train_path)
        .filter(pl.col("Route").is_in(target_routes))
        .collect(engine="streaming")
    )
    test_events = (
        pl.scan_parquet(config.clean_test_path)
        .filter(pl.col("Route").is_in(target_routes))
        .collect(engine="streaming")
    )

    train_joined = _create_travel_time(train_events, tolerances)
    test_joined = _create_travel_time(test_events, tolerances)

    train = _format_travel_time_rows(train_joined)
    test = _format_travel_time_rows(test_joined)
    train.write_parquet(config.processed_dir / "train_travel_times.parquet")
    test.write_parquet(config.processed_dir / "test_travel_times.parquet")

    encoding = (
        train.group_by(["Route", "DepartureStop", "ArrivalStop"])
        .agg(pl.mean("TravelDuration_min").alias("MeanTravelTime"))
        .sort(["Route", "DepartureStop", "ArrivalStop"])
    )
    encoding.write_csv(config.processed_dir / "mean_travel_time_encoding.csv")

    encoding_json = {
        f"{row['Route']}|{row['DepartureStop']}|{row['ArrivalStop']}": row[
            "MeanTravelTime"
        ]
        for row in encoding.to_dicts()
    }
    write_json(config.processed_dir / config.mean_encoding_filename, encoding_json)

    train_features = (
        train.join(encoding, on=["Route", "DepartureStop", "ArrivalStop"], how="left")
        .select(
            [
                "Route",
                "MeanTravelTime",
                "MinutesFromMidnight",
                "DayOfWeek",
                "TravelDuration_min",
            ]
        )
        .drop_nulls(["MeanTravelTime"])
    )
    test_features = (
        test.join(encoding, on=["Route", "DepartureStop", "ArrivalStop"], how="left")
        .select(
            [
                "Route",
                "MeanTravelTime",
                "MinutesFromMidnight",
                "DayOfWeek",
                "TravelDuration_min",
            ]
        )
        .drop_nulls(["MeanTravelTime"])
    )
    train_features.write_parquet(config.processed_dir / "train_target_encoding.parquet")
    test_features.write_parquet(config.processed_dir / "test_target_encoding.parquet")


def build_lightgbm_datasets(config: PipelineConfig) -> None:
    import lightgbm as lgb

    routes: list[str] = read_json(config.processed_dir / config.target_routes_filename)
    routes_enum = pl.Enum(routes)
    days_enum = pl.Enum(DAY_CATEGORIES)

    train_raw = pl.read_parquet(config.processed_dir / "train_target_encoding.parquet")
    test_raw = pl.read_parquet(config.processed_dir / "test_target_encoding.parquet")
    weekend = ["Sat", "Sun"]
    weight = (
        train_raw.select(
            pl.when(pl.col("DayOfWeek").is_in(weekend))
            .then(config.weekend_weight)
            .otherwise(1.0)
            .alias("weight")
        )
        .to_numpy()
        .ravel()
    )

    train = train_raw.with_columns(
        pl.col("Route").cast(routes_enum).to_physical(),
        pl.col("DayOfWeek").cast(days_enum).to_physical(),
    )
    test_weekday = test_raw.filter(~pl.col("DayOfWeek").is_in(weekend)).with_columns(
        pl.col("Route").cast(routes_enum).to_physical(),
        pl.col("DayOfWeek").cast(days_enum).to_physical(),
    )
    test_weekend = test_raw.filter(pl.col("DayOfWeek").is_in(weekend)).with_columns(
        pl.col("Route").cast(routes_enum).to_physical(),
        pl.col("DayOfWeek").cast(days_enum).to_physical(),
    )

    features = [col for col in train_raw.columns if col != "TravelDuration_min"]
    train_lgb = lgb.Dataset(
        data=train.drop("TravelDuration_min").to_numpy(),
        label=train["TravelDuration_min"].to_numpy(),
        feature_name=features,
        categorical_feature=[0, 3],
        weight=weight,
        free_raw_data=False,
    )
    test_weekday_lgb = lgb.Dataset(
        data=test_weekday.drop("TravelDuration_min").to_numpy(),
        label=test_weekday["TravelDuration_min"].to_numpy(),
        feature_name=features,
        categorical_feature=[0, 3],
        reference=train_lgb,
        free_raw_data=False,
    )
    test_weekend_lgb = lgb.Dataset(
        data=test_weekend.drop("TravelDuration_min").to_numpy(),
        label=test_weekend["TravelDuration_min"].to_numpy(),
        feature_name=features,
        categorical_feature=[0, 3],
        reference=train_lgb,
        free_raw_data=False,
    )

    train_lgb.save_binary(config.model_dir / "lightgbm_train.bin")
    test_weekday_lgb.save_binary(config.model_dir / "lightgbm_test_weekday.bin")
    test_weekend_lgb.save_binary(config.model_dir / "lightgbm_test_weekend.bin")


def train_model(config: PipelineConfig) -> None:
    import lightgbm as lgb
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    train_set = lgb.Dataset(config.model_dir / "lightgbm_train.bin")
    test_set_weekday = lgb.Dataset(config.model_dir / "lightgbm_test_weekday.bin")
    test_set_weekend = lgb.Dataset(config.model_dir / "lightgbm_test_weekend.bin")

    def objective(trial: optuna.trial.Trial) -> tuple[float, float]:
        params = {
            "objective": "regression",
            "metric": "rmse",
            "verbosity": -1,
            "boosting_type": "gbdt",
            "feature_pre_filter": False,
            "learning_rate": trial.suggest_float(
                "learning_rate", 0.03, 0.5, log=True
            ),
            "num_threads": config.num_threads,
            "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 1, 2000),
            "lambda_l1": trial.suggest_float("lambda_l1", 0.0, 5.0),
            "lambda_l2": trial.suggest_float("lambda_l2", 0.0, 5.0),
            "feature_fraction": trial.suggest_float("feature_fraction", 0.7, 1.0),
            "num_leaves": trial.suggest_int("num_leaves", 255, 2047),
            "cat_smooth": trial.suggest_int("cat_smooth", 0, 20),
        }
        model = lgb.train(
            params,
            train_set,
            valid_sets=[test_set_weekday, test_set_weekend],
            valid_names=["weekday_test_set", "weekend_test_set"],
            callbacks=[lgb.log_evaluation(period=0)],
        )
        return (
            model.best_score["weekday_test_set"]["rmse"],
            model.best_score["weekend_test_set"]["rmse"],
        )

    study = optuna.create_study(directions=["minimize", "minimize"])
    study.optimize(objective, n_trials=config.optuna_trials, show_progress_bar=True)

    best_trial = min(study.best_trials, key=lambda t: sum(t.values) / len(t.values))
    params = {
        "objective": "regression",
        "metric": "rmse",
        "verbosity": -1,
        "boosting_type": "gbdt",
        "feature_pre_filter": False,
        "num_threads": config.num_threads,
        **best_trial.params,
    }
    model = lgb.train(
        params,
        train_set,
        valid_sets=[test_set_weekday, test_set_weekend],
        valid_names=["weekday_test_set", "weekend_test_set"],
        callbacks=[lgb.log_evaluation(period=0)],
    )
    model.save_model(config.model_dir / config.model_filename)

    def mean_rmse_target(trial: optuna.trial.FrozenTrial) -> float:
        return sum(trial.values) / len(trial.values)

    optuna.visualization.plot_optimization_history(
        study, target=mean_rmse_target, target_name="Mean RMSE"
    ).write_html(
        config.reports_dir / "optuna_optimization_history.html"
    )
    optuna.visualization.plot_param_importances(
        study, target=mean_rmse_target, target_name="Mean RMSE"
    ).write_html(
        config.reports_dir / "optuna_parameter_importance.html"
    )
    optuna.visualization.plot_pareto_front(study).write_html(
        config.reports_dir / "pareto_front.html"
    )


def export_streamlit_artifacts(config: PipelineConfig) -> None:
    create_target_routes_app(
        config.processed_dir / config.target_routes_filename,
        config.processed_dir / config.target_routes_app_filename,
        config.reports_dir / "unparsed_route_ids.json",
    )
    for filename in [
        config.target_routes_filename,
        config.target_routes_app_filename,
        config.target_stops_filename,
        config.stops_dict_filename,
        config.mean_encoding_filename,
    ]:
        shutil.copy2(
            config.processed_dir / filename,
            config.streamlit_artifacts_dir / filename,
        )
    shutil.copy2(
        config.model_dir / config.model_filename,
        config.streamlit_artifacts_dir / config.model_filename,
    )


def validate_streamlit_artifacts(config: PipelineConfig) -> None:
    import lightgbm as lgb

    artifact_dir = config.streamlit_artifacts_dir
    target_routes: list[str] = read_json(artifact_dir / config.target_routes_filename)
    target_stops: dict[str, list[int]] = read_json(
        artifact_dir / config.target_stops_filename
    )
    route_groups: dict[str, dict[str, str]] = read_json(
        artifact_dir / config.target_routes_app_filename
    )
    encoding: dict[str, float] = read_json(artifact_dir / config.mean_encoding_filename)
    stops_dict: dict[str, str] = read_json(artifact_dir / config.stops_dict_filename)

    route_set = set(target_routes)
    for route_key, directions in route_groups.items():
        if not directions:
            raise ValueError(f"{route_key} has no directions.")
        for label, route in directions.items():
            if label not in {"去程", "返程"}:
                raise ValueError(f"{route_key} has invalid direction label {label}.")
            if route not in route_set:
                raise ValueError(f"{route_key}/{label} points to unsupported {route}.")

    for route, stop_ids in target_stops.items():
        if route not in route_set:
            raise ValueError(f"{route} exists in target_stops but not target_routes.")
        for stop_id in stop_ids:
            if str(stop_id) not in stops_dict:
                raise ValueError(f"StopID {stop_id} for route {route} has no name.")
        for depart_id, arrival_id in zip(stop_ids, stop_ids[1:]):
            key = f"{route}|{depart_id}|{arrival_id}"
            if key not in encoding:
                raise ValueError(f"Missing mean travel time encoding for {key}.")

    model = lgb.Booster(model_file=str(artifact_dir / config.model_filename))
    sample_route = target_routes[0]
    sample_stops = target_stops[sample_route]
    sample_key = f"{sample_route}|{sample_stops[0]}|{sample_stops[1]}"
    model.predict([[0, encoding[sample_key], 8 * 60, 0]])
