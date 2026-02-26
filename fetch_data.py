import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl
import requests
from dotenv import load_dotenv


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
    auth_response: Any  # holds the requests.Response object

    def get_data_header(self) -> dict[str, str]:
        access_token = self.auth_response.json().get("access_token")
        return {"authorization": f"Bearer {access_token}", "Accept-Encoding": "gzip"}


if __name__ == "__main__":
    load_dotenv()

    data_folder = Path(get_env("data_folder"))
    app_id = get_env("app_id")
    app_key = get_env("app_key")

    auth_url = get_env("auth_url")
    url = "https://tdx.transportdata.tw/api/historical/v2/Historical/Bus/RealTimeByFrequency/InterCity?Dates=2025-01-01~2025-01-03&%24top=10&%24format=JSONL"

    a = Auth(app_id, app_key)

    try:
        # Authenticate
        auth_response = requests.post(auth_url, data=a.get_auth_header())
        auth_response.raise_for_status()

        # Fetch data
        d = DataFetcher(app_id, app_key, auth_response)
        data_response = requests.get(url, headers=d.get_data_header())
        data_response.raise_for_status()

        # Check raw bytes first
        print(repr(data_response.content))

        # Check status code
        print(data_response.status_code)

        # Check response headers
        print(data_response.headers)

        # Decode and parse
        content = data_response.content.decode(
            "utf-8-sig"
        )  # strips BOM from first line
        data = [json.loads(line) for line in content.strip().splitlines() if line]
        print(json.dumps(data, indent=4, ensure_ascii=False))

        # Export to CSV
        pl.from_dicts(data).write_csv(data_folder / "sample.csv", include_bom=True)
        print("Data fetched successfully.")

    except requests.exceptions.HTTPError as e:
        print(f"API call failed. {e}")
    except Exception as e:
        print(f"An error occurred. {e}")
