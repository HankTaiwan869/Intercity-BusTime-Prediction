import os
from pathlib import Path
from dataclasses import dataclass
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
    url = get_env("data_url")

    a = Auth(app_id, app_key)

    try:
        # Authenticate
        auth_response = requests.post(auth_url, data=a.get_auth_header())
        auth_response.raise_for_status()

        # Fetch data after authentication
        d = DataFetcher(app_id, app_key, auth_response)
        data_response = requests.get(url, headers=d.get_data_header())
        print(data_response.json())
        # Export to csv using polars
        df = pl.from_dicts(data_response.json())
        df.write_csv(data_folder / "sample.csv", include_bom=True)
        print("Data fetched successfully.")

    except requests.exceptions.HTTPError:
        print("API call failed")
    except Exception as e:
        print(f"An error occurred: {e}")
