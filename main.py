import requests
from dotenv import load_dotenv
import os
import polars as pl
from pathlib import Path

load_dotenv()
app_id = os.getenv("app_id")
app_key = os.getenv("app_key")

DATA_FOLDER = Path("raw_data")

AUTH_URL = (
    "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
)
DATA_URL = "https://tdx.transportdata.tw/api/historical/v2/Historical/Bus/RealTimeByFrequency/InterCity?Dates=2021-06-01~2021-06-30&%24top=30&%24format=JSONL"


class Auth:
    def __init__(self, app_id, app_key):
        self.app_id = app_id
        self.app_key = app_key

    def get_auth_header(self):
        content_type = "application/x-www-form-urlencoded"
        grant_type = "client_credentials"

        return {
            "content-type": content_type,
            "grant_type": grant_type,
            "client_id": self.app_id,
            "client_secret": self.app_key,
        }


class data:
    def __init__(self, app_id, app_key, auth_response):
        self.app_id = app_id
        self.app_key = app_key
        self.auth_response = auth_response

    def get_data_header(self):
        auth_JSON = self.auth_response.json()
        access_token = auth_JSON.get("access_token")

        return {"authorization": "Bearer " + access_token, "Accept-Encoding": "gzip"}


if __name__ == "__main__":
    a = Auth(app_id, app_key)

    try:
        # Authenticate
        auth_response = requests.post(AUTH_URL, data=a.get_auth_header())
        auth_response.raise_for_status()

        # Fetch data after authentication
        d = data(app_id, app_key, auth_response)
        data_response = requests.get(DATA_URL, headers=d.get_data_header())
        print(data_response.json())
        # Export to csv using polars
        df = pl.from_dicts(data_response.json())
        df.write_csv(DATA_FOLDER / "sample.csv", include_bom=True)
        print("Data downloaded successfully!")

    except requests.exceptions.HTTPError:
        print("API call failed")
    except Exception as e:
        print(f"An error occurred: {e}")
