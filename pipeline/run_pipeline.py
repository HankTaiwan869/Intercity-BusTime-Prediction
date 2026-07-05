import argparse
import time
from dataclasses import replace
from datetime import date
from pathlib import Path

from pipeline.config import PipelineConfig
from pipeline.io_utils import ensure_run_dirs


def format_duration(seconds: float) -> str:
    minutes, remaining_seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{int(hours)}h {int(minutes)}m {remaining_seconds:.1f}s"
    if minutes:
        return f"{int(minutes)}m {remaining_seconds:.1f}s"
    return f"{remaining_seconds:.1f}s"


def run_step(
    step_number: int, total_steps: int, name: str, fn, config: PipelineConfig
) -> float:
    print(f"\n[Pipeline] Step {step_number}/{total_steps}: {name}", flush=True)
    started_at = time.perf_counter()
    fn(config)
    return time.perf_counter() - started_at


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create retrained Streamlit model artifacts from raw CSV files."
    )
    parser.add_argument("--run-id")
    parser.add_argument("--raw-csv-folder", type=Path)
    parser.add_argument("--stops-csv", type=Path)
    parser.add_argument("--artifacts-root", type=Path)
    parser.add_argument("--train-end-date", type=date.fromisoformat)
    parser.add_argument("--optuna-trials", type=int)
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> PipelineConfig:
    config = PipelineConfig()
    overrides = {
        key: value
        for key, value in {
            "run_id": args.run_id,
            "raw_csv_folder": args.raw_csv_folder,
            "stops_csv": args.stops_csv,
            "artifacts_root": args.artifacts_root,
            "train_end_date": args.train_end_date,
            "optuna_trials": args.optuna_trials,
        }.items()
        if value is not None
    }
    return replace(config, **overrides)


def main() -> None:
    pipeline_started_at = time.perf_counter()
    config = build_config(parse_args())
    from pipeline.steps import (
        build_lightgbm_datasets,
        build_training_data,
        clean_and_split,
        export_streamlit_artifacts,
        find_ideal_tolerances,
        ingest_csvs,
        select_routes_and_stops,
        train_model,
        validate_inputs,
        validate_streamlit_artifacts,
    )

    ensure_run_dirs(
        [
            config.processed_dir,
            config.model_dir,
            config.streamlit_artifacts_dir,
            config.reports_dir,
            config.logs_dir,
        ]
    )

    step_timings = []
    steps = [
        ("validate inputs", validate_inputs),
        ("ingest CSVs into Parquet", ingest_csvs),
        ("clean and split events", clean_and_split),
        ("select routes and stops", select_routes_and_stops),
        ("find ideal as-of join tolerances", find_ideal_tolerances),
        ("build travel-time training data", build_training_data),
        ("build LightGBM binary datasets", build_lightgbm_datasets),
        ("train LightGBM model", train_model),
        ("export Streamlit artifacts", export_streamlit_artifacts),
        ("validate Streamlit artifacts", validate_streamlit_artifacts),
    ]
    total_steps = len(steps)
    for step_number, (name, fn) in enumerate(steps, start=1):
        step_timings.append(
            (name, run_step(step_number, total_steps, name, fn, config))
        )

    print(f"Pipeline complete: {config.run_dir}")
    print(f"Streamlit artifacts: {config.streamlit_artifacts_dir}")
    print("\n[Pipeline] Timing summary:")
    for name, duration in step_timings:
        print(f"  {name}: {format_duration(duration)}")
    print(f"  Total: {format_duration(time.perf_counter() - pipeline_started_at)}")


if __name__ == "__main__":
    main()
