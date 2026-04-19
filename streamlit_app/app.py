"""Streamlit app for bus travel time prediction across all supported routes."""

import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

import lightgbm as lgb
import streamlit as st

from app_css import get_css
from deployment_helpers import raw_to_lgb_format

ROOT = Path(__file__).parent

st.set_page_config(
    page_title="公路客運旅程時間預測",
    page_icon="⏱",
    layout="centered",
)

st.html(get_css())
st.html("<h1>公路客運旅程時間預測</h1>")


# ── Data & model loading ──────────────────────────────────────────────────────


@st.cache_data
def load_data() -> tuple[dict, dict, list, dict]:
    with open(ROOT / "target_stops.json", "r", encoding="utf-8") as f:
        target_stops: dict[str, list[int]] = json.load(f)
    with open(ROOT / "stops_dict.json", "r", encoding="utf-8") as f:
        stops_dict: dict[str, str] = json.load(f)
    with open(ROOT / "target_routes.json", "r", encoding="utf-8") as f:
        target_routes: list[str] = json.load(f)
    with open(ROOT / "target_routes_app.json", "r", encoding="utf-8") as f:
        route_groups: dict[str, dict[str, str]] = json.load(f)
    return target_stops, stops_dict, target_routes, route_groups


@st.cache_resource
def load_model() -> lgb.Booster:
    return lgb.Booster(model_file=str(ROOT / "lgbm_model.txt"))


target_stops, stops_dict, target_routes, route_groups = load_data()

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
    return stops_dict.get(str(stop_id), "?")


# ── Route groups loaded from JSON ─────────────────────────────────────────────

base_routes = sorted(route_groups.keys())


# ── Route selector ────────────────────────────────────────────────────────────

selected_base_route: str | None = st.selectbox(
    "路線(結尾0代表主路線)",
    options=base_routes,
    index=None,
    placeholder="搜尋或選擇路線…",
)

# ── Direction selector ────────────────────────────────────────────────────────

direction_options = (
    route_groups.get(selected_base_route, {}) if selected_base_route else {}
)

selected_direction: str | None = st.selectbox(
    "方向",
    options=list(direction_options.keys()),
    index=None,
    placeholder="選擇方向…",
    disabled=(not selected_base_route),
)

# Get the actual full route ID based on user selection
route: str | None = (
    direction_options.get(selected_direction) if selected_direction else None
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
        <div style="display: flex; flex-direction: column; gap: 20px">
            
            <div>
            <div class="result-label">預計抵達時間</div>
            <div style="display:flex; align-items:baseline; gap:0.4rem;">
                <span class="result-value">{arrival_dt.strftime("%H:%M")}</span>
            </div>
            </div>

            <div>
            <div class="result-label">預計旅行時間</div>
            <div style="display:flex; align-items:baseline; gap:0.4rem;">
                <span class="result-value">{prediction:.0f}</span>
                <span class="result-label">分鐘</span>
            </div>
            </div>

        </div>
        </div>
        """
    )

    # Segment breakdown (only shown when there are multiple legs)
    if len(segment_rows) > 1:
        # Use an expander to make the breakdown a toggle option
        with st.expander("查看各站間詳細預估時間"):
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

# ── Disclaimer ────────────────────────────────────────────────────────────────

st.html(
    """
    <div style="margin-top: 3rem; padding: 1rem; text-align: center; color: #666; font-size: 0.9rem;">
      本網站預測結果僅供參考<br>
      由於模型訓練資料不足緣故<br>
      部分路線並未納入本系統<br>
      預測亦不適用於特殊連假或極端氣候
    </div>
    """
)
