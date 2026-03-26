"""Overview page — pipeline status and topology visualization."""

import streamlit as st
import plotly.graph_objects as go
from social_arb.app.db_helpers import (
    count_table, get_signals_grouped, get_ohlcv_summary, get_scan_summary, get_reviews,
)


def render():
    st.title("◆ Social Arb — Overview")
    st.caption("Camillo 5-Layer Cognitive Topology · Pipeline Status")

    # ── PIPELINE METRICS ──
    cols = st.columns(6)
    cols[0].metric("L1 Signals", count_table("signals"))
    cols[1].metric("L2 Mosaics", count_table("mosaics"))
    cols[2].metric("L3 Theses", count_table("theses"))
    cols[3].metric("L4 Decisions", count_table("decisions"))
    cols[4].metric("L5 Positions", count_table("positions"))
    cols[5].metric("HITL Reviews", count_table("reviews"))

    # ── TOPOLOGY DIAGRAM ──
    st.subheader("5-Layer Topology")
    fig = go.Figure()
    layers = [
        ("L1\nSignal\nRadar", count_table("signals"), "#3b82f6"),
        ("HITL\nGate 1", len(get_reviews(gate="L1_triage")), "#eab308"),
        ("L2\nMosaic\nAssembly", count_table("mosaics"), "#a855f7"),
        ("HITL\nGate 2", len(get_reviews(gate="L2_validation")), "#eab308"),
        ("L3\nThesis\nForge", count_table("theses"), "#06b6d4"),
        ("HITL\nGate 3", len(get_reviews(gate="L3_conviction")), "#eab308"),
        ("L4\nDecisions", count_table("decisions"), "#22c55e"),
        ("L5\nPortfolio", count_table("positions"), "#d4a017"),
    ]
    for i, (label, count, color) in enumerate(layers):
        is_gate = "HITL" in label
        fig.add_trace(go.Bar(
            x=[label], y=[max(count, 1)],
            marker_color=color, marker_line_color=color,
            marker_pattern_shape="/" if is_gate else "",
            text=[str(count)], textposition="outside",
            textfont=dict(color=color, size=14),
            showlegend=False, width=0.6 if is_gate else 0.8,
        ))
    fig.update_layout(
        plot_bgcolor="#0b0b12", paper_bgcolor="#0b0b12",
        font=dict(color="#888", family="monospace"),
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=False, visible=False),
        height=280, margin=dict(t=20, b=40, l=20, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── SIGNAL DISTRIBUTION ──
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Signals by Symbol")
        grouped = get_signals_grouped()
        if grouped:
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=[g["symbol"] for g in grouped],
                y=[g["total"] for g in grouped],
                marker_color=["#d4a017" if g["bullish"] > 0 else "#555" for g in grouped],
                text=[f'{g["bullish"]}b/{g["neutral"]}n' for g in grouped],
                textposition="outside", textfont=dict(size=10, color="#888"),
            ))
            fig2.update_layout(
                plot_bgcolor="#0b0b12", paper_bgcolor="#0b0b12",
                font=dict(color="#888", family="monospace", size=10),
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=False, visible=False),
                height=220, margin=dict(t=10, b=30, l=20, r=20), showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True)

    with col2:
        st.subheader("OHLCV Archive")
        ohlcv = get_ohlcv_summary()
        if ohlcv:
            for row in ohlcv:
                st.markdown(
                    f"**{row['symbol']}** — {row['bars']} bars · "
                    f"`{row['first_bar']}` → `{row['last_bar']}` · {row['source']}"
                )
        else:
            st.info("No OHLCV data yet. Run `social-arb backfill` to populate.")

    # ── RECENT SCANS ──
    st.subheader("Recent Scans")
    scans = get_scan_summary()
    if scans:
        for s in scans:
            status_icon = "✓" if s["status"] == "completed" else "⏳" if s["status"] == "running" else "✗"
            st.markdown(
                f"{status_icon} **{s['scan_type']}** — {s['signal_count']} signals · "
                f"{s['started_at']}"
            )
    else:
        st.info("No scans yet. Run `social-arb collect` to start collecting.")
