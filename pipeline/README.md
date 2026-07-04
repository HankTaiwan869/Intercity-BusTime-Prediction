# Retraining Pipeline

This pipeline rebuilds the model and Streamlit support files from raw TDX CSV files.
It writes a versioned artifact folder and does **not** overwrite `streamlit_app/`.

## Required Inputs

By default, the pipeline expects:

```text
data/raw/*.csv
data/raw/bus_stops.csv
```

The raw event CSV files must follow the existing schema used by `src.helpers.bulk_convert_csv_to_parquet`.

Obtain the csv files through https://tdx.transportdata.tw/.
Request items 公路客運定點歷史資料(A2) and 公路客運站牌歷史資料.
## Run

```bash
uv run python -m pipeline.run_pipeline \
  --run-id 2027-01-retrain \
  --train-end-date 2026-12-31
```

Optional path overrides:

```bash
uv run python -m pipeline.run_pipeline \
  --run-id 2027-01-retrain \
  --raw-csv-folder data/raw \
  --stops-csv data/raw/bus_stops.csv \
  --artifacts-root artifacts \
  --train-end-date 2026-12-31 \
  --optuna-trials 500
```

## Output

The final deployable files are written to:

```text
artifacts/<run-id>/streamlit_artifacts/
```

Expected files:

```text
lgbm_model.txt
target_routes.json
target_routes_app.json
target_stops.json
stops_dict.json
mean_travel_time_encoding.json
```

Intermediate data, model binaries, and reports are stored under the same run folder:

```text
artifacts/<run-id>/processed/
artifacts/<run-id>/model/
artifacts/<run-id>/reports/
```

## Notes

- `target_routes_app.json` is generated from `target_routes.json` using the fixed route ID rule: first four digits are the route number, the fifth character is main/sub-route, and the final digit is direction.
- Routes with invalid stop-pair joins are excluded from the final artifacts.
- Promotion into `streamlit_app/` is intentionally separate and not handled by this command.
