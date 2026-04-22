"""
Social Arb — Information Arbitrage Platform
Streamlit Application Entry Point

Run: streamlit run social_arb/app/main.py
"""

import streamlit as st

st.set_page_config(
    page_title="Social Arb",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark theme override
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #111118; }
    .stApp { background-color: #0b0b12; }
    div[data-testid="stMetric"] { background: #111118; border: 1px solid #262636; padding: 12px; border-radius: 4px; }
    div[data-testid="stMetricValue"] { color: #d4a017; }
    .block-container { padding-top: 1rem; }
    h1, h2, h3 { color: #d4a017 !important; }
    .stTabs [data-baseweb="tab"] { color: #888; }
    .stTabs [aria-selected="true"] { color: #d4a017 !important; }
</style>
""", unsafe_allow_html=True)

# Initialize DB
from social_arb.app.db_helpers import ensure_db
ensure_db()

# ─── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ◆ SOCIAL ARB")
    st.caption("Information Arbitrage Platform")
    st.divider()

    page = st.radio(
        "Workflow",
        [
            "◆ Overview",
            "L1 · Signal Radar",
            "⊞ Gate 1→2 · Triage",
            "L2 · Mosaic Assembly",
            "⊞ Gate 2→3 · Validation",
            "L3 · Thesis Forge",
            "⊞ Gate 3→4 · Conviction",
            "L4 · Decisions",
            "L5 · Portfolio",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    from social_arb.app.db_helpers import count_table
    c1, c2 = st.columns(2)
    c1.metric("Signals", count_table("signals"))
    c2.metric("Mosaics", count_table("mosaics"))
    c1, c2 = st.columns(2)
    c1.metric("Theses", count_table("theses"))
    c2.metric("Reviews", count_table("reviews"))

# ─── PAGE ROUTING ──────────────────────────────────────────────────────────────
if page == "◆ Overview":
    from social_arb.app.pages.overview import render
    render()
elif page == "L1 · Signal Radar":
    from social_arb.app.pages.signal_radar import render
    render()
elif page == "⊞ Gate 1→2 · Triage":
    from social_arb.app.pages.gate_1_triage import render
    render()
elif page == "L2 · Mosaic Assembly":
    from social_arb.app.pages.mosaic_assembly import render
    render()
elif page == "⊞ Gate 2→3 · Validation":
    from social_arb.app.pages.gate_2_validation import render
    render()
elif page == "L3 · Thesis Forge":
    from social_arb.app.pages.thesis_forge import render
    render()
elif page == "⊞ Gate 3→4 · Conviction":
    from social_arb.app.pages.gate_3_conviction import render
    render()
elif page == "L4 · Decisions":
    from social_arb.app.pages.decisions import render
    render()
elif page == "L5 · Portfolio":
    from social_arb.app.pages.portfolio import render
    render()
