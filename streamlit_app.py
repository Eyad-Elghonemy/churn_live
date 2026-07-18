"""
Churn Ledger — a Streamlit control room for the Churn-Detection FastAPI service.

Run alongside the FastAPI backend:
    uvicorn main:app --reload          # backend, from the API project root
    streamlit run streamlit_app.py     # this dashboard

The app never loads models directly — every prediction is a real HTTP call to
your FastAPI instance, so it reflects exactly what the API returns.
"""

import time
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st

# --------------------------------------------------------------------------
# Page config
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Churn Ledger",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# Backend connection (built-in, not user-editable)
# --------------------------------------------------------------------------
API_BASE_URL = "https://eyadzz-churn-live.hf.space/"

# --------------------------------------------------------------------------
# Design tokens & theme
# --------------------------------------------------------------------------
INK = "#10161C"
PANEL = "#171F27"
PANEL_ALT = "#1D2731"
BORDER = "rgba(201,162,39,0.18)"
BRASS = "#C9A227"
BRASS_DIM = "#8A7220"
TEAL = "#3FA796"
ALERT = "#C1443C"
TEXT = "#EDEDE7"
MUTED = "#8B93A0"

PLOTLY_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=TEXT, size=13),
        colorway=[TEAL, BRASS, ALERT, "#6E8CA0", "#5B4B8A"],
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.08)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.08)"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=10, r=10, t=40, b=10),
    )
)

CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
}}

.stApp {{
    background: radial-gradient(circle at 15% 0%, #141B23 0%, {INK} 45%) fixed;
    color: {TEXT};
}}

section[data-testid="stSidebar"] {{
    background: {PANEL};
    border-right: 1px solid {BORDER};
}}

h1, h2, h3 {{
    font-family: 'Fraunces', serif;
    letter-spacing: -0.01em;
}}

.ledger-title {{
    font-family: 'Fraunces', serif;
    font-size: 2.1rem;
    font-weight: 600;
    color: {TEXT};
    margin-bottom: 0;
}}
.ledger-subtitle {{
    color: {MUTED};
    font-size: 0.95rem;
    margin-top: 0.15rem;
    letter-spacing: 0.02em;
}}
.eyebrow {{
    text-transform: uppercase;
    letter-spacing: 0.14em;
    font-size: 0.72rem;
    color: {BRASS};
    font-weight: 600;
}}
.rule {{
    border: none;
    border-top: 1px solid {BORDER};
    margin: 0.6rem 0 1.4rem 0;
}}

.kpi-card {{
    background: linear-gradient(180deg, {PANEL_ALT} 0%, {PANEL} 100%);
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 1rem 1.2rem;
    height: 100%;
}}
.kpi-label {{
    color: {MUTED};
    font-size: 0.76rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}
.kpi-value {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.9rem;
    font-weight: 600;
    color: {TEXT};
    margin-top: 0.15rem;
}}
.kpi-delta {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
    color: {TEAL};
}}

.badge {{
    display: inline-block;
    padding: 0.25rem 0.7rem;
    border-radius: 999px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.03em;
}}
.badge-low {{ background: rgba(63,167,150,0.15); color: {TEAL}; border: 1px solid rgba(63,167,150,0.4); }}
.badge-med {{ background: rgba(201,162,39,0.15); color: {BRASS}; border: 1px solid rgba(201,162,39,0.4); }}
.badge-high {{ background: rgba(193,68,60,0.15); color: {ALERT}; border: 1px solid rgba(193,68,60,0.4); }}

.ledger-row {{
    border-bottom: 1px solid {BORDER};
    padding: 0.55rem 0;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
}}

.stButton>button {{
    background: {BRASS};
    color: {INK};
    border: none;
    font-weight: 600;
    border-radius: 4px;
}}
.stButton>button:hover {{
    background: {BRASS_DIM};
    color: {TEXT};
}}

div[data-testid="stMetricValue"] {{
    font-family: 'IBM Plex Mono', monospace;
}}

/* --- Sidebar navigation menu --- */
section[data-testid="stSidebar"] div[data-testid="stButton"] button {{
    background: transparent;
    color: {MUTED};
    border: 1px solid transparent;
    border-left: 3px solid transparent;
    text-align: left;
    justify-content: flex-start;
    font-weight: 500;
    font-size: 0.95rem;
    padding: 0.6rem 0.8rem;
    border-radius: 6px;
    margin-bottom: 0.2rem;
    width: 100%;
    box-shadow: none;
}}
section[data-testid="stSidebar"] div[data-testid="stButton"] button:hover {{
    background: rgba(201,162,39,0.08);
    color: {TEXT};
    border-left-color: rgba(201,162,39,0.35);
}}
section[data-testid="stSidebar"] div[data-testid="stButton"] button:focus:not(:active) {{
    color: {TEXT};
    border-left-color: rgba(201,162,39,0.35);
}}
section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="primary"] {{
    background: linear-gradient(90deg, rgba(201,162,39,0.20), rgba(201,162,39,0.04));
    color: {BRASS} !important;
    border-left: 3px solid {BRASS};
    font-weight: 700;
}}
section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="primary"]:hover {{
    background: linear-gradient(90deg, rgba(201,162,39,0.26), rgba(201,162,39,0.08));
    color: {BRASS} !important;
}}
.nav-eyebrow-spacer {{ margin-bottom: 0.4rem; }}

/* --- KPI cards v2 (Portfolio Overview) --- */
.kpi-card-v2 {{
    background: linear-gradient(155deg, {PANEL_ALT} 0%, {PANEL} 100%);
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 1.1rem 1.3rem;
    position: relative;
    overflow: hidden;
    transition: transform .18s ease, border-color .18s ease;
    height: 100%;
}}
.kpi-card-v2:hover {{
    transform: translateY(-3px);
    border-color: rgba(201,162,39,0.45);
}}
.kpi-card-v2 .kpi-accent-bar {{
    position: absolute; top: 0; left: 0; bottom: 0; width: 4px;
}}
.kpi-card-v2 .kpi-icon {{ font-size: 1.35rem; opacity: 0.9; }}
.kpi-card-v2 .kpi-label-v2 {{
    color: {MUTED};
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-top: 0.55rem;
}}
.kpi-card-v2 .kpi-value-v2 {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.9rem;
    font-weight: 700;
    color: {TEXT};
    margin-top: 0.1rem;
}}

/* --- Leaderboard rows (Model Insights) --- */
.rank-row {{
    display: flex;
    align-items: center;
    gap: 0.9rem;
    padding: 0.5rem 0.1rem;
    border-bottom: 1px solid {BORDER};
}}
.rank-num {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.9rem;
    color: {MUTED};
    width: 1.5rem;
}}
.rank-num.gold {{ color: {BRASS}; font-weight: 700; }}
.rank-bar-track {{
    flex: 1;
    background: rgba(255,255,255,0.05);
    border-radius: 4px;
    height: 10px;
    overflow: hidden;
}}
.rank-bar-fill {{ height: 100%; border-radius: 4px; }}
.rank-label {{ min-width: 230px; font-size: 0.84rem; color: {TEXT}; }}
.rank-score {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.84rem;
    color: {MUTED};
    width: 3.4rem;
    text-align: right;
}}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Reference dataset facts (from the training notebook — Churn_Modelling.csv)
# Used for the portfolio-level dashboard since the raw dataset isn't bundled
# with the API. Swap in a live query if you wire the API to a database.
# --------------------------------------------------------------------------
DATASET_STATS = {
    "total_customers": 10000,
    "churn_rate": 0.2037,
    "geography": {"France": 5014, "Germany": 2509, "Spain": 2477},
    "gender": {"Male": 5457, "Female": 4543},
    "avg_salary_by_gender": {"Female": 100576, "Male": 99672},
    "train_size": 7990,
    "test_size": 1998,
}

FEATURE_IMPORTANCE = {
    "Age": 0.37468,
    "NumOfProducts": 0.24874,
    "Balance": 0.09514,
    "IsActiveMember": 0.06470,
    "Geography_Germany": 0.05457,
    "EstimatedSalary": 0.05183,
    "CreditScore": 0.04889,
    "Tenure": 0.02671,
    "Gender_Male": 0.02164,
    "Geography_Spain": 0.00683,
    "HasCrCard": 0.00629,
}

MODEL_LEDGER = [
    {"entry": "Logistic Regression", "note": "baseline, no balancing", "train_f1": 0.309, "test_f1": 0.375},
    {"entry": "Logistic Regression", "note": "class-weighted", "train_f1": 0.498, "test_f1": 0.499},
    {"entry": "Logistic Regression", "note": "SMOTE oversampled", "train_f1": 0.498, "test_f1": 0.508},
    {"entry": "Random Forest", "note": "class-weighted", "train_f1": 0.600, "test_f1": 0.573},
    {"entry": "Random Forest", "note": "SMOTE oversampled", "train_f1": 0.618, "test_f1": 0.590},
    {"entry": "Random Forest", "note": "tuned (GridSearchCV)", "train_f1": 0.680, "test_f1": 0.623},
    {"entry": "XGBoost", "note": "base model", "train_f1": 0.703, "test_f1": 0.595},
    {"entry": "XGBoost", "note": "tuned (RandomizedSearchCV)", "train_f1": 0.624, "test_f1": 0.609},
]

CUSTOMER_FIELDS_HELP = {
    "CreditScore": "Bureau credit score, typically 300–850.",
    "Geography": "Customer's country of residence.",
    "Gender": "Customer's gender as recorded.",
    "Age": "Customer age in years (18–100).",
    "Tenure": "Years as a customer of the bank (0–10).",
    "Balance": "Current account balance.",
    "NumOfProducts": "Number of bank products held (1–4).",
    "HasCrCard": "Whether the customer holds a credit card.",
    "IsActiveMember": "Whether the customer is an active member.",
    "EstimatedSalary": "Estimated annual salary.",
}

# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []  # list of dicts: timestamp, model, prob, pred, inputs

# --------------------------------------------------------------------------
# API helpers
# --------------------------------------------------------------------------
def api_health(base_url: str, timeout=3):
    try:
        r = requests.get(base_url.rstrip("/") + "/", timeout=timeout)
        if r.status_code == 200:
            return True, r.json().get("Message", "Connected")
        return False, f"HTTP {r.status_code}"
    except requests.exceptions.RequestException as e:
        return False, str(e)


def call_predict(base_url: str, api_key: str, model: str, payload: dict, timeout=8):
    endpoint = "/predict/forest" if model == "Random Forest" else "/predict/xgboost"
    url = base_url.rstrip("/") + endpoint
    headers = {"X-API-Key": api_key}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        if r.status_code == 200:
            return True, r.json()
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        return False, f"HTTP {r.status_code}: {detail}"
    except requests.exceptions.RequestException as e:
        return False, str(e)


def get_usage_stats(base_url: str, api_key: str, timeout=8):
    url = base_url.rstrip("/") + "/stats"
    headers = {"X-API-Key": api_key}
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code == 200:
            return True, r.json()
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        return False, f"HTTP {r.status_code}: {detail}"
    except requests.exceptions.RequestException as e:
        return False, str(e)


def risk_band(prob: float):
    if prob < 0.33:
        return "low", "badge-low", TEAL
    if prob < 0.66:
        return "medium", "badge-med", BRASS
    return "high", "badge-high", ALERT


def gauge_chart(prob: float):
    band, _, color = risk_band(prob)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=prob * 100,
            number={"suffix": "%", "font": {"size": 44, "family": "IBM Plex Mono"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": MUTED, "tickfont": {"color": MUTED}},
                "bar": {"color": color, "thickness": 0.28},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 1,
                "bordercolor": BORDER,
                "steps": [
                    {"range": [0, 33], "color": "rgba(63,167,150,0.18)"},
                    {"range": [33, 66], "color": "rgba(201,162,39,0.18)"},
                    {"range": [66, 100], "color": "rgba(193,68,60,0.18)"},
                ],
                "threshold": {"line": {"color": color, "width": 3}, "thickness": 0.9, "value": prob * 100},
            },
        )
    )
    fig.update_layout(template=PLOTLY_TEMPLATE, height=280, margin=dict(l=20, r=20, t=30, b=10))
    return fig


def kpi_card(label, value, col):
    col.markdown(
        f"""<div class="kpi-card">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def kpi_card_v2(icon, label, value, accent, col):
    col.markdown(
        f"""<div class="kpi-card-v2">
                <div class="kpi-accent-bar" style="background:{accent};"></div>
                <div class="kpi-icon">{icon}</div>
                <div class="kpi-label-v2">{label}</div>
                <div class="kpi-value-v2">{value}</div>
            </div>""",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Sidebar — connection & navigation
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div class="eyebrow">Churn Detection Service</div>'
        '<div class="ledger-title" style="font-size:1.5rem;">📖 Churn Ledger</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<hr class="rule">', unsafe_allow_html=True)

    st.markdown('<div class="eyebrow">Connection</div>', unsafe_allow_html=True)
    base_url = API_BASE_URL
    st.caption(f"API base URL: `{base_url}`")
    api_key = st.text_input("X-API-Key", type="password", value="")

    ok, msg = api_health(base_url)
    if ok:
        st.success(f"Connected — {msg}")
    else:
        st.error(f"Unreachable — {msg}")

    st.markdown('<hr class="rule">', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow nav-eyebrow-spacer">Navigate</div>', unsafe_allow_html=True)

    NAV_ITEMS = [
        ("📊", "Portfolio Overview"),
        ("🧾", "Score a Customer"),
        ("📥", "Batch Scoring"),
        ("📚", "Model Insights"),
        ("📈", "Usage Analytics"),
    ]
    if "nav_page" not in st.session_state:
        st.session_state.nav_page = NAV_ITEMS[0][1]

    for icon, label in NAV_ITEMS:
        is_active = st.session_state.nav_page == label
        if st.button(
            f"{icon}   {label}",
            key=f"nav_{label}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.nav_page = label
            st.rerun()

    page = st.session_state.nav_page

    st.markdown('<hr class="rule">', unsafe_allow_html=True)
    st.caption(f"Session predictions logged: {len(st.session_state.history)}")
    if st.session_state.history and st.button("🗑️   Clear session history", use_container_width=True):
        st.session_state.history = []
        st.rerun()

# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
st.markdown(
    '<div class="eyebrow">Bank Customer Churn</div>'
    '<div class="ledger-title">Churn Ledger</div>'
    '<div class="ledger-subtitle">A live dashboard on top of your FastAPI churn-prediction service — '
    'portfolio trends, single-customer scoring, batch scoring, and a record of the modeling work behind it.</div>'
    '<hr class="rule">',
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# PAGE: Portfolio Overview
# --------------------------------------------------------------------------
if page == "Portfolio Overview":
    st.markdown('<div class="eyebrow">Reference Portfolio — Churn_Modelling.csv</div>', unsafe_allow_html=True)
    st.caption("Figures below reflect the training dataset used to build these models.")

    c1, c2, c3, c4 = st.columns(4)
    kpi_card_v2("👥", "Total customers", f"{DATASET_STATS['total_customers']:,}", "#6E8CA0", c1)
    kpi_card_v2("📉", "Churn rate", f"{DATASET_STATS['churn_rate']*100:.2f}%", ALERT, c2)
    kpi_card_v2("🧪", "Train / test split", f"{DATASET_STATS['train_size']:,} / {DATASET_STATS['test_size']:,}", TEAL, c3)
    kpi_card_v2("🖊️", "This session's scores", f"{len(st.session_state.history)}", BRASS, c4)

    st.write("")
    left, right = st.columns([1.2, 1], gap="large")

    with left:
        st.markdown("**Where customers come from**")
        geo_items = sorted(DATASET_STATS["geography"].items(), key=lambda x: x[1])
        geo_names = [g for g, _ in geo_items]
        geo_vals = [v for _, v in geo_items]
        total = sum(geo_vals)
        colors_scale = [TEAL, "#6E8CA0", BRASS]
        fig = go.Figure(
            go.Bar(
                x=geo_vals,
                y=geo_names,
                orientation="h",
                marker=dict(color=colors_scale[: len(geo_vals)], cornerradius=8),
                text=[f"{v:,}  ·  {v/total*100:.1f}%" for v in geo_vals],
                textposition="outside",
                textfont=dict(family="IBM Plex Mono", size=13),
            )
        )
        fig.update_layout(
            template=PLOTLY_TEMPLATE, height=300,
            xaxis=dict(visible=False, range=[0, max(geo_vals) * 1.28]),
            margin=dict(l=10, r=30, t=10, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("**Retained vs. churned**")
        churned = DATASET_STATS["churn_rate"]
        fig = go.Figure(
            go.Pie(
                labels=["Retained", "Churned"],
                values=[1 - churned, churned],
                hole=0.72,
                marker_colors=[TEAL, ALERT],
                textinfo="none",
                sort=False,
            )
        )
        fig.add_annotation(
            text=f"<b>{churned*100:.1f}%</b><br><span style='font-size:11px;color:{MUTED}'>CHURN RATE</span>",
            showarrow=False, font=dict(family="IBM Plex Mono", size=22, color=TEXT),
        )
        fig.update_layout(
            template=PLOTLY_TEMPLATE, height=300, showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.write("")
    st.markdown("**Customer mix by gender**")
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Customers", "Avg. estimated salary"), horizontal_spacing=0.12)
    genders = list(DATASET_STATS["gender"].keys())
    fig.add_trace(
        go.Bar(x=genders, y=list(DATASET_STATS["gender"].values()), marker=dict(color=[TEAL, BRASS], cornerradius=8), showlegend=False),
        row=1, col=1,
    )
    fig.add_trace(
        go.Bar(
            x=genders, y=list(DATASET_STATS["avg_salary_by_gender"].values()),
            marker=dict(color=[TEAL, BRASS], cornerradius=8), showlegend=False,
        ),
        row=1, col=2,
    )
    fig.update_layout(template=PLOTLY_TEMPLATE, height=300)
    fig.update_annotations(font=dict(family="Inter", size=13, color=MUTED))
    st.plotly_chart(fig, use_container_width=True)

    if st.session_state.history:
        st.markdown('<hr class="rule">', unsafe_allow_html=True)
        st.markdown('<div class="eyebrow">This Session\'s Scoring Activity</div>', unsafe_allow_html=True)
        hist_df = pd.DataFrame(st.session_state.history)
        fig = go.Figure(
            go.Histogram(
                x=hist_df["probability"] * 100, nbinsx=20,
                marker=dict(color=BRASS, line=dict(color=INK, width=1)),
            )
        )
        avg_prob = hist_df["probability"].mean() * 100
        fig.add_vline(x=avg_prob, line=dict(color=TEAL, width=2, dash="dash"), annotation_text=f"avg {avg_prob:.0f}%", annotation_font_color=TEAL)
        fig.update_layout(
            template=PLOTLY_TEMPLATE, height=280, xaxis_title="Predicted churn probability (%)", yaxis_title="Customers scored"
        )
        st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------------------------
# PAGE: Score a Customer
# --------------------------------------------------------------------------
elif page == "Score a Customer":
    st.markdown('<div class="eyebrow">Single-Customer Prediction</div>', unsafe_allow_html=True)
    st.caption("Calls your FastAPI /predict endpoint directly — nothing here is computed locally.")

    form_col, result_col = st.columns([1, 1.1], gap="large")

    with form_col:
        model_choice = st.selectbox("Model", ["Random Forest", "XGBoost"])
        with st.form("predict_form"):
            c1, c2 = st.columns(2)
            with c1:
                credit_score = st.slider("Credit score", 300, 850, 650, help=CUSTOMER_FIELDS_HELP["CreditScore"])
                geography = st.selectbox("Geography", ["France", "Spain", "Germany"], help=CUSTOMER_FIELDS_HELP["Geography"])
                gender = st.selectbox("Gender", ["Male", "Female"], help=CUSTOMER_FIELDS_HELP["Gender"])
                age = st.slider("Age", 18, 100, 38, help=CUSTOMER_FIELDS_HELP["Age"])
                tenure = st.slider("Tenure (years)", 0, 10, 5, help=CUSTOMER_FIELDS_HELP["Tenure"])
            with c2:
                balance = st.number_input("Balance", min_value=0.0, value=75000.0, step=1000.0, help=CUSTOMER_FIELDS_HELP["Balance"])
                num_products = st.slider("Number of products", 1, 4, 1, help=CUSTOMER_FIELDS_HELP["NumOfProducts"])
                has_cr_card = st.selectbox("Has credit card", ["Yes", "No"], help=CUSTOMER_FIELDS_HELP["HasCrCard"])
                is_active = st.selectbox("Active member", ["Yes", "No"], help=CUSTOMER_FIELDS_HELP["IsActiveMember"])
                salary = st.number_input("Estimated salary", min_value=0.0, value=100000.0, step=1000.0, help=CUSTOMER_FIELDS_HELP["EstimatedSalary"])

            submitted = st.form_submit_button("Score this customer", use_container_width=True)

    if submitted:
        payload = {
            "CreditScore": int(credit_score),
            "Geography": geography,
            "Gender": gender,
            "Age": int(age),
            "Tenure": int(tenure),
            "Balance": float(balance),
            "NumOfProducts": int(num_products),
            "HasCrCard": 1 if has_cr_card == "Yes" else 0,
            "IsActiveMember": 1 if is_active == "Yes" else 0,
            "EstimatedSalary": float(salary),
        }
        with st.spinner("Calling the API..."):
            success, result = call_predict(base_url, api_key, model_choice, payload)

        with result_col:
            if not success:
                st.error(f"Prediction failed: {result}")
            else:
                prob = result["Churn_Probability"]
                pred = result["Churn_Prediction"]
                band, badge_class, _ = risk_band(prob)

                st.plotly_chart(gauge_chart(prob), use_container_width=True)
                st.markdown(
                    f'<span class="badge {badge_class}">{band.upper()} RISK</span>&nbsp;&nbsp;'
                    f'<span style="color:{MUTED};">Predicted label: '
                    f'<b style="color:{TEXT};">{"Will churn" if pred else "Will stay"}</b></span>',
                    unsafe_allow_html=True,
                )
                st.write("")
                st.markdown("**Where this customer sits on the model's top drivers**")
                top_feats = dict(sorted(FEATURE_IMPORTANCE.items(), key=lambda x: -x[1])[:5])
                fig = go.Figure(go.Bar(x=list(top_feats.values()), y=list(top_feats.keys()), orientation="h", marker_color=BRASS))
                fig.update_layout(template=PLOTLY_TEMPLATE, height=260, xaxis_title="Relative importance (Random Forest)")
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)

                st.session_state.history.append(
                    {
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "model": model_choice,
                        "probability": prob,
                        "prediction": "Churn" if pred else "Stay",
                        **payload,
                    }
                )

    if st.session_state.history:
        st.markdown('<hr class="rule">', unsafe_allow_html=True)
        st.markdown('<div class="eyebrow">Recent Scores (this session)</div>', unsafe_allow_html=True)
        recent = pd.DataFrame(st.session_state.history[::-1][:10])
        recent_display = recent[["timestamp", "model", "prediction", "probability"]].copy()
        recent_display["probability"] = recent_display["probability"].apply(lambda p: f"{p:.1%}")
        st.dataframe(recent_display, use_container_width=True, hide_index=True)

# --------------------------------------------------------------------------
# PAGE: Batch Scoring
# --------------------------------------------------------------------------
elif page == "Batch Scoring":
    st.markdown('<div class="eyebrow">Batch Scoring</div>', unsafe_allow_html=True)
    st.caption(
        "Upload a CSV with columns: "
        + ", ".join(CUSTOMER_FIELDS_HELP.keys())
        + ". Each row is sent to the API individually."
    )

    model_choice_b = st.selectbox("Model", ["Random Forest", "XGBoost"], key="batch_model")
    uploaded = st.file_uploader("Customer CSV", type=["csv"])

    if uploaded is not None:
        try:
            df = pd.read_csv(uploaded)
        except Exception as e:
            st.error(f"Could not read CSV: {e}")
            df = None

        if df is not None:
            missing = [c for c in CUSTOMER_FIELDS_HELP if c not in df.columns]
            if missing:
                st.error(f"Missing required columns: {', '.join(missing)}")
            else:
                st.dataframe(df.head(), use_container_width=True)
                if st.button(f"Score {len(df)} customers", use_container_width=True):
                    results = []
                    progress = st.progress(0.0, text="Scoring...")
                    for i, row in df.iterrows():
                        payload = {k: row[k] for k in CUSTOMER_FIELDS_HELP}
                        # Coerce numeric types the API expects
                        for k in ["CreditScore", "Age", "Tenure", "NumOfProducts", "HasCrCard", "IsActiveMember"]:
                            payload[k] = int(payload[k])
                        for k in ["Balance", "EstimatedSalary"]:
                            payload[k] = float(payload[k])

                        success, result = call_predict(base_url, api_key, model_choice_b, payload)
                        if success:
                            results.append({**payload, "Churn_Prediction": result["Churn_Prediction"], "Churn_Probability": result["Churn_Probability"]})
                        else:
                            results.append({**payload, "Churn_Prediction": None, "Churn_Probability": None, "error": result})
                        progress.progress((i + 1) / len(df), text=f"Scoring... {i+1}/{len(df)}")
                    progress.empty()

                    res_df = pd.DataFrame(results)
                    st.success(f"Scored {len(res_df)} customers.")

                    c1, c2 = st.columns(2)
                    valid = res_df.dropna(subset=["Churn_Probability"])
                    with c1:
                        st.markdown("**Risk distribution**")
                        fig = go.Figure(go.Histogram(x=valid["Churn_Probability"] * 100, nbinsx=20, marker_color=TEAL))
                        fig.update_layout(template=PLOTLY_TEMPLATE, height=300, xaxis_title="Predicted churn probability (%)")
                        st.plotly_chart(fig, use_container_width=True)
                    with c2:
                        st.markdown("**Predicted outcome split**")
                        counts = valid["Churn_Prediction"].value_counts()
                        fig = go.Figure(
                            go.Pie(
                                labels=["Will stay" if not k else "Will churn" for k in counts.index],
                                values=counts.values,
                                marker_colors=[TEAL, ALERT],
                                hole=0.55,
                            )
                        )
                        fig.update_layout(template=PLOTLY_TEMPLATE, height=300, showlegend=True)
                        st.plotly_chart(fig, use_container_width=True)

                    st.markdown("**Full results**")
                    st.dataframe(res_df, use_container_width=True, hide_index=True)
                    st.download_button(
                        "Download scored CSV",
                        res_df.to_csv(index=False).encode("utf-8"),
                        file_name="churn_scores.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

# --------------------------------------------------------------------------
# PAGE: Model Insights
# --------------------------------------------------------------------------
elif page == "Model Insights":
    st.markdown('<div class="eyebrow">Model Development Journey</div>', unsafe_allow_html=True)
    st.caption("Every configuration tried, in the order it was tested — test-set F1 climbs as imbalance handling and tuning are added.")

    ledger_df = pd.DataFrame(MODEL_LEDGER)
    ledger_df["step"] = range(1, len(ledger_df) + 1)
    ledger_df["short"] = ledger_df["entry"].str.replace("Random Forest", "RF").str.replace("Logistic Regression", "Logistic")
    best_idx = ledger_df["test_f1"].idxmax()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ledger_df["step"], y=ledger_df["train_f1"], name="Train F1",
            mode="lines+markers", line=dict(color="#6E8CA0", width=2, dash="dot"),
            marker=dict(size=6),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ledger_df["step"], y=ledger_df["test_f1"], name="Test F1",
            mode="lines+markers", line=dict(color=BRASS, width=3), marker=dict(size=8),
            fill="tozeroy", fillcolor="rgba(201,162,39,0.08)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[ledger_df.loc[best_idx, "step"]], y=[ledger_df.loc[best_idx, "test_f1"]],
            mode="markers+text", marker=dict(size=16, color=TEAL, line=dict(color=INK, width=2)),
            text=["★ best"], textposition="top center", textfont=dict(color=TEAL, size=12),
            showlegend=False,
        )
    )
    fig.update_layout(
        template=PLOTLY_TEMPLATE, height=380,
        xaxis=dict(tickmode="array", tickvals=list(ledger_df["step"]), ticktext=list(ledger_df["short"]), tickangle=-25),
        yaxis_title="F1 score", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns([1.1, 1], gap="large")

    with left:
        st.markdown('<div class="eyebrow">Leaderboard — Ranked by Test F1</div>', unsafe_allow_html=True)
        st.write("")
        ranked = ledger_df.sort_values("test_f1", ascending=False).reset_index(drop=True)
        max_f1 = ranked["test_f1"].max()
        rows_html = ""
        for i, row in ranked.iterrows():
            rank = i + 1
            pct = row["test_f1"] / max_f1 * 100
            color = BRASS if rank == 1 else (TEAL if rank <= 3 else "#6E8CA0")
            num_class = "gold" if rank == 1 else ""
            rows_html += (
                f'<div class="rank-row">'
                f'<div class="rank-num {num_class}">{rank}</div>'
                f'<div class="rank-label">{row["entry"]}<br><span style="color:{MUTED};font-size:0.75rem;">{row["note"]}</span></div>'
                f'<div class="rank-bar-track"><div class="rank-bar-fill" style="width:{pct:.0f}%;background:{color};"></div></div>'
                f'<div class="rank-score">{row["test_f1"]:.3f}</div>'
                f'</div>'
            )
        st.markdown(rows_html, unsafe_allow_html=True)

    with right:
        st.markdown('<div class="eyebrow">What Drives the Random Forest Model</div>', unsafe_allow_html=True)
        st.write("")
        feat_df = pd.DataFrame(
            {"Feature": list(FEATURE_IMPORTANCE.keys()), "Importance": list(FEATURE_IMPORTANCE.values())}
        ).sort_values("Importance", ascending=True)
        top5_cut = feat_df["Importance"].nlargest(5).min()
        colors = [BRASS if v >= top5_cut else "rgba(63,167,150,0.55)" for v in feat_df["Importance"]]
        fig = go.Figure(
            go.Bar(
                x=feat_df["Importance"], y=feat_df["Feature"], orientation="h",
                marker=dict(color=colors, cornerradius=6),
                text=[f"{v*100:.1f}%" for v in feat_df["Importance"]], textposition="outside",
                textfont=dict(family="IBM Plex Mono", size=11),
            )
        )
        fig.update_layout(template=PLOTLY_TEMPLATE, height=420, xaxis=dict(visible=False, range=[0, feat_df["Importance"].max() * 1.25]))
        st.plotly_chart(fig, use_container_width=True)

    with st.container(border=True):
        st.markdown('<div class="eyebrow">Notes</div>', unsafe_allow_html=True)
        st.markdown(
            "- Both deployed models (`forest_tuned.pkl`, `xgb-tuned.pkl`) were selected after this comparison, "
            "prioritizing test-set **F1 score** because churn is a minority class (≈20% of customers).\n"
            "- Class imbalance was addressed two ways during experimentation: **class weighting** and **SMOTE** oversampling; "
            "final Random Forest and XGBoost picks use class weighting and hyperparameter tuning.\n"
            "- `Age` and `NumOfProducts` (highlighted in brass) are by far the strongest predictors of churn in the "
            "Random Forest model — together they account for over 60% of its decision weight."
        )

# --------------------------------------------------------------------------
# PAGE: Usage Analytics
# --------------------------------------------------------------------------
elif page == "Usage Analytics":
    st.markdown('<div class="eyebrow">Who\'s Using the Models</div>', unsafe_allow_html=True)
    st.caption("Live counts pulled from the API's own request log — every successful /predict call anywhere (this dashboard or direct API calls) is counted.")

    if not api_key:
        st.warning("Enter your X-API-Key in the sidebar to load usage stats.")
    else:
        success, stats = get_usage_stats(base_url, api_key)
        if not success:
            st.error(f"Could not load usage stats: {stats}")
        else:
            forest_count = stats.get("forest", {}).get("count", 0)
            xgb_count = stats.get("xgboost", {}).get("count", 0)
            total = forest_count + xgb_count

            c1, c2, c3 = st.columns(3)
            kpi_card_v2("🌲", "Random Forest calls", f"{forest_count:,}", TEAL, c1)
            kpi_card_v2("⚡", "XGBoost calls", f"{xgb_count:,}", BRASS, c2)
            kpi_card_v2("Σ", "Total predictions served", f"{total:,}", "#6E8CA0", c3)

            st.write("")
            left, right = st.columns([1, 1.3], gap="large")

            with left:
                st.markdown("**Calls by model**")
                fig = go.Figure(
                    go.Bar(
                        x=["Random Forest", "XGBoost"], y=[forest_count, xgb_count],
                        marker=dict(color=[TEAL, BRASS], cornerradius=8),
                        text=[forest_count, xgb_count], textposition="outside",
                        textfont=dict(family="IBM Plex Mono", size=13),
                    )
                )
                fig.update_layout(template=PLOTLY_TEMPLATE, height=320, yaxis_title="Predictions served")
                st.plotly_chart(fig, use_container_width=True)

            with right:
                st.markdown("**Requests over time**")
                all_ts = []
                for model_name, color in [("forest", TEAL), ("xgboost", BRASS)]:
                    for ts in stats.get(model_name, {}).get("timestamps", []):
                        all_ts.append({"timestamp": ts, "model": model_name})
                if not all_ts:
                    st.info("No requests logged yet — once the API gets some traffic, this chart fills in.")
                else:
                    ts_df = pd.DataFrame(all_ts)
                    ts_df["timestamp"] = pd.to_datetime(ts_df["timestamp"])
                    ts_df["date"] = ts_df["timestamp"].dt.date
                    daily = ts_df.groupby(["date", "model"]).size().reset_index(name="calls")
                    fig = go.Figure()
                    for model_name, color in [("forest", TEAL), ("xgboost", BRASS)]:
                        sub = daily[daily["model"] == model_name]
                        fig.add_trace(
                            go.Bar(x=sub["date"], y=sub["calls"], name=model_name.title(), marker_color=color)
                        )
                    fig.update_layout(
                        template=PLOTLY_TEMPLATE, height=320, barmode="stack",
                        yaxis_title="Predictions", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    )
                    st.plotly_chart(fig, use_container_width=True)

            st.caption(
                "This log lives in a JSON file on the API's own filesystem — it persists while the service is "
                "running or asleep, and resets on the next deployment."
            )


# --------------------------------------------------------------------------
st.markdown('<hr class="rule">', unsafe_allow_html=True)
st.caption("Churn Ledger · a Streamlit front-end for the Churn-Detection FastAPI service · predictions are never computed locally.")
