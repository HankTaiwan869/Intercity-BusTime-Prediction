"""Deprecated: API pipeline for fetching raw intercity bus data from TDX — replaced by bulk CSV download."""

import os
from dataclasses import dataclass
from io import StringIO
import polars as pl
import requests
from dotenv import load_dotenv
from constants import DATA_FOLDER


# raise ImportError if env not found
def get_env(name: str) -> str:
    result = os.getenv(name)
    if result is None:
        raise ImportError(f"Missing mandatory environment variable: {name}")
    return result


@dataclass(frozen=True)
class Auth:
    app_id: str
    app_key: str

    def get_auth_header(self) -> dict[str, str]:
        return {
            "content-type": "application/x-www-form-urlencoded",
            "grant_type": "client_credentials",
            "client_id": self.app_id,
            "client_secret": self.app_key,
        }


@dataclass
class DataFetcher:
    app_id: str
    app_key: str
    auth_response: requests.Response

    def get_data_header(self) -> dict[str, str]:
        access_token = self.auth_response.json().get("access_token")
        return {"authorization": f"Bearer {access_token}", "Accept-Encoding": "gzip"}


if __name__ == "__main__":
    load_dotenv("../.env")

    app_id = get_env("app_id")
    app_key = get_env("app_key")

    auth_url = get_env("auth_url")
    # the input format should be in NDJSON
    url = "https://tdx.transportdata.tw/api/historical/v2/Historical/Bus/RealTimeNearStop/InterCity?Dates=2026-03-21&%24top=30&%24format=JSONL"

    a = Auth(app_id, app_key)

    try:
        # Authenticate
        auth_response = requests.post(auth_url, data=a.get_auth_header())
        auth_response.raise_for_status()

        # Fetch data
        d = DataFetcher(app_id, app_key, auth_response)
        response = requests.get(url, headers=d.get_data_header())
        response.raise_for_status()

        # Decode and parse NDJSON, then save as CSV
        content = response.content.decode("utf-8-sig")  # strips BOM from first line
        df = pl.read_ndjson(StringIO(content))

        # Unnest each nested columns
        struct_cols = [
            col for col, dtype in zip(df.columns, df.dtypes) if dtype == pl.Struct
        ]
        df.unnest(struct_cols, separator="_").write_csv(
            DATA_FOLDER / "mar_21.csv", include_bom=True
        )

        print("Data fetched successfully.")

    except requests.exceptions.HTTPError as e:
        print(f"API call failed. {e}")
    except Exception as e:
        print(f"An error occurred. {e}")
