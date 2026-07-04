import argparse
from dataclasses import replace
from datetime import date
from pathlib import Path

from pipeline.config import PipelineConfig
from pipeline.io_utils import ensure_run_dirs


def run_step(name: str, fn, config: PipelineConfig) -> None:
    print(f"\n[Pipeline] Starting: {name}", flush=True)
    fn(config)
    print(f"[Pipeline] Finished: {name}", flush=True)


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

    run_step("validate inputs", validate_inputs, config)
    run_step("ingest CSVs into Parquet", ingest_csvs, config)
    run_step("clean and split events", clean_and_split, config)
    run_step("select routes and stops", select_routes_and_stops, config)
    run_step("find ideal as-of join tolerances", find_ideal_tolerances, config)
    run_step("build travel-time training data", build_training_data, config)
    run_step("build LightGBM binary datasets", build_lightgbm_datasets, config)
    run_step("train LightGBM model", train_model, config)
    run_step("export Streamlit artifacts", export_streamlit_artifacts, config)
    run_step("validate Streamlit artifacts", validate_streamlit_artifacts, config)

    print(f"Pipeline complete: {config.run_dir}")
    print(f"Streamlit artifacts: {config.streamlit_artifacts_dir}")


if __name__ == "__main__":
    main()
