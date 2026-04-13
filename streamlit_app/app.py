"""Streamlit app for bus travel time prediction across all supported routes."""
# uv run --with streamlit --with lightgbm streamlit run app.py

import sys
from pathlib import Path

# resolve root folder issue when deployed on streamlit
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import lightgbm as lgb
import streamlit as st

from app_css import get_css
from src.constants import MODEL_FOLDER, PROCESSED_DATA_FOLDER
from src.deployment_helpers import raw_to_lgb_format

st.set_page_config(
    page_title="客運旅程時間預測",
    page_icon="⏱",
    layout="centered",
)

st.html(get_css())
st.html("<h1>客運旅程時間預測</h1>")


# ── Data & model loading ──────────────────────────────────────────────────────


@st.cache_data
def load_data() -> tuple[dict, dict, list]:
    with open(PROCESSED_DATA_FOLDER / "target_stops.json", "r", encoding="utf-8") as f:
        target_stops: dict[str, list[int]] = json.load(f)
    with open(PROCESSED_DATA_FOLDER / "stops_dict.json", "r", encoding="utf-8") as f:
        stops_dict: dict[str, str] = json.load(f)
    with open(PROCESSED_DATA_FOLDER / "target_routes.json", "r", encoding="utf-8") as f:
        target_routes: list[str] = json.load(f)
    return target_stops, stops_dict, target_routes


@st.cache_resource
def load_model() -> lgb.Booster:
    return lgb.Booster(
        model_file=str(MODEL_FOLDER / "target_encoding_model/best_lgbm_model.txt")
    )


target_stops, stops_dict, target_routes = load_data()

model: lgb.Booster | None = None
model_error: str | None = None
try:
    model = load_model()
except Exception as e:
    model_error = str(e)

if model_error:
    st.warning(f"無法載入模型：{model_error}")


# ── Helpers ───────────────────────────────────────────────────────────────────


def pairwise(lst: list[int]) -> list[tuple[int, int]]:
    return list(zip(lst, lst[1:]))


def stop_label(stop_id: int) -> str:
    return f"{stop_id} · {stops_dict.get(str(stop_id), '?')}"


# ── Route selector ────────────────────────────────────────────────────────────

route: str | None = st.selectbox(
    "路線",
    options=target_routes,
    index=None,
    placeholder="搜尋或選擇路線…",
)

possible_stops = target_stops[route] if route else []
r_id = target_routes.index(route) if route else None
depart_options = possible_stops[:-1] if route else []

# ── Departure stop ────────────────────────────────────────────────────────────

depart: int | None = st.selectbox(
    "出發站",
    options=depart_options,
    format_func=stop_label,
    index=None,
    placeholder="選擇出發站…",
    disabled=(not route),
)

depart_idx = possible_stops.index(depart) if depart else None
arrival_options = possible_stops[depart_idx + 1 :] if depart else []

# ── Arrival stop ──────────────────────────────────────────────────────────────

arrival: int | None = st.selectbox(
    "抵達站",
    options=arrival_options,
    format_func=stop_label,
    index=None,
    placeholder="選擇抵達站…",
    disabled=(not depart),
)

# ── Departure time ────────────────────────────────────────────────────────────

chosen_datetime = st.datetime_input(
    "預計乘車時間",
    value=datetime.now(ZoneInfo("Asia/Taipei")),
    step=600,
    disabled=(not arrival),
)

# ── Predict ───────────────────────────────────────────────────────────────────

run = st.button("開始預測", disabled=(not arrival or model is None))

if run and model is not None:
    arrival_idx = possible_stops.index(arrival)
    segment_stops = possible_stops[depart_idx : arrival_idx + 1]
    pairs = pairwise(segment_stops)

    current_dt = chosen_datetime.replace(tzinfo=None)
    prediction = 0.0
    segment_rows: list[dict] = []

    with st.spinner("預測中…"):
        for from_stop, to_stop in pairs:
            my_input = raw_to_lgb_format(route, from_stop, to_stop, current_dt)
            model_input = [
                [
                    r_id,
                    my_input.mean_travel_time,
                    my_input.minutes_past_midnight,
                    my_input.day_of_week,
                ]
            ]

            step_pred: float = model.predict(model_input).item()
            current_dt += timedelta(minutes=step_pred)
            prediction += step_pred
            segment_rows.append(
                {
                    "from": stop_label(from_stop),
                    "to": stop_label(to_stop),
                    "minutes": step_pred,
                }
            )

    depart_dt = chosen_datetime.replace(tzinfo=None)
    arrival_dt = depart_dt + timedelta(minutes=prediction)

    st.html(
        f"""
        <div class="result-box">
          <div>
            <div class="result-label">
              預計抵達時間
            </div>
            <div style="display:flex;align-items:baseline;gap:0.4rem;">
              <span class="result-value">{arrival_dt.strftime("%H:%M")}</span>
            </div>
            <div class="result-label">
              預計旅行時間 · {prediction:.1f} 分鐘
            </div>
          </div>
        </div>
        """
    )

    # Segment breakdown (only shown when there are multiple legs)
    if len(segment_rows) > 1:
        rows_html = "".join(
            f"<tr>"
            f"<td>{row['from']}</td>"
            f"<td>{row['to']}</td>"
            f"<td class='minutes'>{row['minutes']:.1f} 分</td>"
            f"</tr>"
            for row in segment_rows
        )
        st.html(
            f"""
            <table class="segment-table">
              <thead>
                <tr>
                  <th>出發站</th>
                  <th>抵達站</th>
                  <th>預測時間</th>
                </tr>
              </thead>
              <tbody>{rows_html}</tbody>
            </table>
            """
        )
