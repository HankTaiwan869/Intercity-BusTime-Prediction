import streamlit as st
import lightgbm as lgb
import pandas as pd
from datetime import time, date, datetime, timedelta
from pathlib import Path
from constants import DAY_CATEGORIES, MODELS

# uv run --with streamlit --with "pandas<3" --with lightgbm streamlit run demo_app.py

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="客運旅程時間預測",
    page_icon="⏱",
    layout="centered",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.html(
    """
    <style>
    /* 1. Import a standard, clean font like Inter */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        /* 2. Change global font to Inter/Sans-Serif */
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background-color: #0e0e11;
        color: #e8e4dc;
    }

    .block-container { max-width: 640px; padding-top: 3rem; }

    h1 {
        font-family: 'Inter', sans-serif;
        font-size: 2.2rem; /* Slightly smaller for a standard look */
        font-weight: 700;
        letter-spacing: -0.01em; /* Tighter, more standard tracking */
        color: #52330B;
        line-height: 1.2;
        margin-bottom: 0;
    }

    .subtitle {
        font-size: 0.85rem;
        letter-spacing: 0.02em; /* Reduced spacing */
        text-transform: none; /* Removed uppercase for a more natural feel */
        color: #88857e;
        margin-top: 0.4rem;
        margin-bottom: 0.8rem;
    }

    /* Result banner */
    .result-box {
        background: #1a1f14;
        border: 1px solid #3d5c20;
        border-radius: 12px;
        padding: 1.8rem 2rem;
        margin-top: 1.5rem;
        display: flex;
        align-items: baseline;
        gap: 0.5rem;
    }
    .result-value {
        font-family: 'Inter', sans-serif;
        font-size: 3.2rem;
        font-weight: 800;
        color: #b5e36a;
        line-height: 1;
    }
    .result-unit {
        font-size: 1.1rem;
        font-weight: 500;
        color: #6b8042;
        letter-spacing: normal;
    }
    .result-label {
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: #4e5c35;
        margin-top: 0.4rem;
    }

    /* Streamlit input tweaks */
    .stNumberInput input, .stDateInput input {
        background: #0e0e11 !important;
        border: 1px solid #2a2a33 !important;
        color: #e8e4dc !important;
        border-radius: 6px !important;
        font-family: 'Inter', sans-serif !important;
    }
    div[data-testid="stNumberInput"] label,
    div[data-testid="stDateInput"] label {
        font-size: 0.8rem !important;
        font-weight: 500;
        letter-spacing: normal !important;
        text-transform: none !important;
        color: #a19f99 !important;
    }

    .stButton > button {
        width: 100%;
        background: #b5e36a;
        color: #0e0e11;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 0.95rem;
        letter-spacing: normal;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-top: 0.5rem;
        transition: background 0.15s ease;
    }
    .stButton > button:hover { background: #c9f07c; }

    hr { border-color: #2a2a33; }

    #MainMenu, footer, header { visibility: hidden; }
    </style>
    """,
)

# ── Header ────────────────────────────────────────────────────────────────────
st.html("<h1>客運旅程時間預測</h1>")
st.html(
    '<p class="subtitle">1728 · 新竹轉運站 - 龍潭運動公園</p>',
)

# ── Model loading ─────────────────────────────────────────────────────────────


@st.cache_resource
def load_model() -> lgb.Booster | None:
    model_path = MODELS / "model_1728.txt"
    if not model_path.exists():
        return None
    return lgb.Booster(model_file=str(model_path))


model = load_model()

if model is None:
    st.warning(
        "Model file not found at `models/model_1728.txt`. "
        "Place the file there and reload."
    )

# ── Predict helper ────────────────────────────────────────────────────────────


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

# st.html(
#     '<p class="subtitle">預計乘車時間</p>',
# )

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
