from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class PipelineConfig:
    run_id: str = field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    )

    raw_csv_folder: Path = Path("data/raw")
    stops_csv: Path = Path("data/raw/bus_stops.csv")
    artifacts_root: Path = Path("artifacts")

    train_end_date: date = date(2025, 12, 31)

    stop_distance_threshold_km: float = 4.0
    min_selected_stops_per_route: int = 2

    initial_tolerance_hours: int = 1
    max_tolerance_hours: int = 12
    tolerance_growth_threshold: float = 1.03

    exclude_zero_match_pairs: bool = True
    exclude_routes_at_max_tolerance: bool = True
    exclude_routes_with_any_invalid_pair: bool = True

    force_exclude_routes: set[str] = field(default_factory=set)
    force_remove_stops: dict[str, set[int]] = field(default_factory=dict)

    weekend_weight: float = 2.0
    optuna_trials: int = 500
    num_threads: int = 6

    model_filename: str = "lgbm_model.txt"
    target_routes_filename: str = "target_routes.json"
    target_routes_app_filename: str = "target_routes_app.json"
    target_stops_filename: str = "target_stops.json"
    stops_dict_filename: str = "stops_dict.json"
    mean_encoding_filename: str = "mean_travel_time_encoding.json"

    @property
    def run_dir(self) -> Path:
        return self.artifacts_root / self.run_id

    @property
    def processed_dir(self) -> Path:
        return self.run_dir / "processed"

    @property
    def model_dir(self) -> Path:
        return self.run_dir / "model"

    @property
    def streamlit_artifacts_dir(self) -> Path:
        return self.run_dir / "streamlit_artifacts"

    @property
    def reports_dir(self) -> Path:
        return self.run_dir / "reports"

    @property
    def logs_dir(self) -> Path:
        return self.run_dir / "logs"

    @property
    def raw_parquet_path(self) -> Path:
        return self.processed_dir / "bus_event_time.parquet"

    @property
    def clean_events_path(self) -> Path:
        return self.processed_dir / "clean_events.parquet"

    @property
    def clean_train_path(self) -> Path:
        return self.processed_dir / "clean_train.parquet"

    @property
    def clean_test_path(self) -> Path:
        return self.processed_dir / "clean_test.parquet"
