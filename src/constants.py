from pathlib import Path
import polars as pl

# paths
ROOT_DIR = Path(__file__).parent.parent
DATA_FOLDER = ROOT_DIR / "data"
DATA_FILE = DATA_FOLDER / "bus_event_time.parquet"
ROUTES = DATA_FOLDER / "bus_routes_mar3.csv"
STOPS = DATA_FOLDER / "bus_stops_mar3.csv"
SAMPLE = DATA_FOLDER / "sample.csv"
MODELS = ROOT_DIR / "models"

ACTIVE_ROUTES = (
    pl.read_csv(ROUTES)
    .select(pl.col("SubRouteID"), pl.col("Direction"))
    .unique()
    .sort("SubRouteID")
)

DAY_CATEGORIES = ["Thu", "Fri", "Sat", "Sun", "Mon", "Tue", "Wed"]

# holidays are not used as they are not useful features
# they are kept here as a record
holidays = [...]
long_holidays = [...]
