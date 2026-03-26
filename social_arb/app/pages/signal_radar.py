"""L1: Signal Radar — Browse all incoming signals with filtering."""

import streamlit as st
import pandas as pd
import plotly.express as px
from social_arb.app.db_helpers import get_signals, get_signals_grouped, count_table


def render():
    st.title("L1 · Signal Radar")
    st.caption("Raw intelligence from all collectors. Filter, explore, identify patterns.")

    # ── FILTERS ──
    col1, col2, col3 = st.columns(3)
    grouped = get_signals_grouped()
    symbols = [g["symbol"] for g in grouped]

    with col1:
        sym_filter = st.selectbox("Symbol", ["All"] + symbols)
    with col2:
        src_filter = st.selectbox("Source", ["All", "reddit", "sec_edgar", "trends", "yfinance", "coingecko"])
    with col3:
        limit = st.slider("Max signals", 50, 2000, 500, 50)

    # ── SUMMARY METRICS ──
    total = count_table("signals")
    cols = st.columns(4)
    cols[0].metric("Total Signals", total)
    if grouped:
        bullish_total = sum(g["bullish"] for g in grouped)
        neutral_total = sum(g["neutral"] for g in grouped)
        cols[1].metric("Bullish", bullish_total)
        cols[2].metric("Neutral", neutral_total)
        cols[3].metric("Symbols", len(grouped))

    # ── SIGNAL MATRIX: Social vs Institutional ──
    st.subheader("Signal Matrix — Social vs. Institutional Awareness")
    st.caption("Camillo's core insight: the gap between social buzz and institutional filing activity IS the arbitrage")

    if grouped:
        for g in grouped:
            srcs = (g.get("sources") or "").split(",")
            g["social_signals"] = g["bullish"]  # social = bullish Reddit mentions
            g["institutional_signals"] = g["neutral"]  # institutional = SEC filings
            g["source_diversity"] = g["source_count"]

        fig = px.scatter(
            grouped,
            x="institutional_signals", y="social_signals",
            size="total", color="source_count",
            text="symbol",
            color_continuous_scale=["#555", "#d4a017", "#22c55e"],
            labels={
                "institutional_signals": "Institutional (SEC filings)",
                "social_signals": "Social (Reddit bullish)",
                "source_count": "Sources",
            },
        )
        fig.update_traces(textposition="top center", textfont=dict(color="#d4a017", size=12))
        fig.update_layout(
            plot_bgcolor="#0b0b12", paper_bgcolor="#0b0b12",
            font=dict(color="#888", family="monospace"),
            height=400, margin=dict(t=20),
        )
        # Add diagonal line (parity = no divergence)
        max_val = max(max(g["institutional_signals"] for g in grouped), max(g["social_signals"] for g in grouped))
        fig.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val,
                      line=dict(dash="dash", color="#333", width=1))
        fig.add_annotation(x=max_val*0.7, y=max_val*0.5, text="← No divergence line",
                           font=dict(color="#555", size=10), showarrow=False)
        st.plotly_chart(fig, use_container_width=True)

    # ── SIGNAL TABLE ──
    st.subheader("Signal Feed")
    signals = get_signals(
        symbol=None if sym_filter == "All" else sym_filter,
        source=None if src_filter == "All" else src_filter,
        limit=limit,
    )

    if signals:
        for sig in signals:
            raw = sig.get("raw_json", {})
            title = raw.get("title", "") if isinstance(raw, dict) else ""
            direction = sig.get("direction", "neutral")
            dir_color = "🟢" if direction == "bullish" else "🔴" if direction == "bearish" else "⚪"

            with st.container():
                c1, c2, c3, c4 = st.columns([1, 3, 1, 1])
                c1.markdown(f"**{sig['symbol']}**")
                c2.markdown(f"{dir_color} {title or sig.get('signal_type', '')}")
                c3.caption(f"{sig['source']} · str:{sig.get('strength', 0):.2f}")
                c4.caption(sig.get("timestamp", "")[:16])
    else:
        st.info("No signals found. Run `social-arb collect --domain public` to collect.")
