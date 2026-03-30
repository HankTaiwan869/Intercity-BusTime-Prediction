"""Deprecated: API pipeline for fetching raw intercity bus data from TDX — replaced by bulk CSV download."""

import os
from dataclasses import dataclass
from io import StringIO
import polars as pl
import requests
from dotenv import load_dotenv
from constants import DATA_FOLDER
from typing import Any
import json
from pathlib import Path


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


def process_data(
    url: str, parse_to_csv: bool, saved_file_name: Path, api_data_type: str = "json"
) -> str:
    """incoming data from API should be of json format"""
    load_dotenv("../.env")

    app_id = get_env("app_id")
    app_key = get_env("app_key")

    auth_url = get_env("auth_url")
    a = Auth(app_id, app_key)

    # Authenticate
    auth_response = requests.post(auth_url, data=a.get_auth_header())
    auth_response.raise_for_status()

    # Fetch data
    d = DataFetcher(app_id, app_key, auth_response)
    response = requests.get(url, headers=d.get_data_header())
    response.raise_for_status()

    # Decode and parse NDJSON, then save as CSV
    content = response.content.decode("utf-8-sig")  # strips BOM from first line

    # parse to csv
    if api_data_type == "csv":
        df = pl.read_csv(StringIO(content)).write_csv(
            saved_file_name.with_suffix(".csv"), include_bom=True
        )
    elif parse_to_csv:
        df = pl.read_ndjson(StringIO(content))

        # Unnest each nested columns
        struct_cols = [
            col for col, dtype in zip(df.columns, df.dtypes) if dtype == pl.Struct
        ]
        df.unnest(struct_cols, separator="_").write_csv(
            saved_file_name.with_suffix(".csv"), include_bom=True
        )
    # parse to json
    else:
        parsed_content = json.loads(content)
        with open(saved_file_name.with_suffix(".json"), "w", encoding="utf-8") as f:
            json.dump(parsed_content, f, indent=4, ensure_ascii=False)

    print("Data fetched successfully.")

    return json.dumps(parsed_content, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    # the input format should be in NDJSON or JSON
    url = "https://tdx.transportdata.tw/api/historical/v2/Historical/Bus/StopOfRoute/Date/2026-03-28/InterCity?%24format=CSV"
    api_data_type = "csv"
    parse_to_csv = True
    saved_file_name = DATA_FOLDER / "bus_routes_mar28"

    try:
        process_data(url, parse_to_csv, saved_file_name, api_data_type)
    except requests.exceptions.HTTPError as e:
        print(f"API call failed. {e}")
    except Exception as e:
        print(f"An error occurred. {e}")
