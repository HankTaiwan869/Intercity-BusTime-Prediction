def get_css() -> str:
    return """
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
        """


if __name__ == "__main__":
    print(get_css())
