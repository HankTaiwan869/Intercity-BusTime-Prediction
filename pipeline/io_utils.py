import json
from pathlib import Path
from typing import Any


def ensure_run_dirs(paths: list[Path]) -> None:
    # Create the full run folder structure before any step writes artifacts.
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any, *, indent: int | None = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}")


def require_csv_folder(path: Path) -> None:
    # Fail early when the raw input folder is missing or accidentally empty.
    if not path.exists():
        raise FileNotFoundError(f"Missing raw CSV folder: {path}")
    if not any(path.glob("*.csv")):
        raise FileNotFoundError(f"No CSV files found in raw CSV folder: {path}")
