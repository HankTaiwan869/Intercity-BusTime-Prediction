import streamlit as st
import lightgbm as lgb
import pandas as pd
from datetime import time, timedelta
from pathlib import Path
from demo_app_css import get_css

# cd streamlit_demo
# uv run --with streamlit --with "pandas<3" --with lightgbm streamlit run demo_app.py

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="客運旅程時間預測",
    page_icon="⏱",
    layout="centered",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.html(get_css())

# ── Header ────────────────────────────────────────────────────────────────────
st.html("<h1>客運旅程時間預測</h1>")
st.html(
    '<p class="subtitle">1728 · 新竹轉運站 - 龍潭運動公園</p>',
)

# ── Model loading ─────────────────────────────────────────────────────────────


@st.cache_resource
def load_model() -> lgb.Booster | None:
    model_path = Path("demo_model_1728.txt")
    if not model_path.exists():
        return None
    return lgb.Booster(model_file=str(model_path))


model = load_model()

if model is None:
    st.warning("Model file not found at `demo_model_1728.txt`.")

# ── Predict helper ────────────────────────────────────────────────────────────
DAY_CATEGORIES = ["Thu", "Fri", "Sat", "Sun", "Mon", "Tue", "Wed"]


def predict(booster: lgb.Booster, target_time: time, day_of_week: str) -> float:
    minutes_from_midnight = target_time.hour * 60 + target_time.minute
    X = pd.DataFrame(
        [
            {
                "Minutes_from_midnight": minutes_from_midnight,
                "Day_of_week": day_of_week,
            }
        ]
    )
    X["Day_of_week"] = pd.Categorical(X["Day_of_week"], categories=DAY_CATEGORIES)
    return booster.predict(X).item()


# ── Inputs ────────────────────────────────────────────────────────────────────

chosen_datetime = st.datetime_input("預計乘車時間", value="now", step=600)


# Derive day-of-week abbreviation
day_abbr = chosen_datetime.strftime("%a")  # 'Mon', 'Tue' …

st.html(
    f'<p style="font-size:0.72rem;letter-spacing:0.16em;text-transform:uppercase;'
    f'color:#6b6860;margin-top:0.6rem;">'
    f'Detected day → <span style="color:#b5e36a">{day_abbr}</span></p>',
)

run = st.button("開始預測", disabled=(model is None))
st.html("</div>")

# ── Output ────────────────────────────────────────────────────────────────────
if run and model is not None:
    if chosen_datetime is None:
        st.warning("請選擇乘車時間與日期")
    else:
        result = predict(model, chosen_datetime.time(), day_abbr)

        st.html(
            f"""
            <div class="result-box">
              <div>
                <div style="display:flex;align-items:baseline;gap:0.4rem;">
                  <span class="result-value">{result:.1f}</span>
                  <span class="result-unit">分鐘</span>
                </div>
                <div class="result-label">
                  預計抵達時間 · {(chosen_datetime + timedelta(minutes=result)).replace(microsecond=0)}
                </div>
              </div>
            </div>
            """,
        )
