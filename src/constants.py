from pathlib import Path
from datetime import date

ROOT_DIR = Path(__file__).parent.parent
DATA_FOLDER = ROOT_DIR / "data"
DATA_FILE = DATA_FOLDER / "bus_2025.parquet"

MIN_DATE = date(2025, 2, 28)
MAX_DATE = date(2026, 2, 27)

if __name__ == "__main__":
    print(DATA_FOLDER)
