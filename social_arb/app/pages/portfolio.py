"""L5: Portfolio — Live positions, P&L tracking, and risk management."""

import streamlit as st
import plotly.graph_objects as go
from social_arb.app.db_helpers import (
    get_positions, get_reviews, get_theses, get_ohlcv, count_table, parse_json,
)


def render():
    st.title("L5 · Portfolio")
    st.caption("Live positions, P&L tracking, and risk management. The output of your conviction pipeline.")

    positions = get_positions()
    executed_reviews = get_reviews(gate="L3_conviction")
    executed = [r for r in executed_reviews if r.get("decision") == "execute"]
    theses = get_theses()

    # ── HEADER METRICS ──
    open_pos = [p for p in positions if p.get("status") == "open"]
    closed_pos = [p for p in positions if p.get("status") == "closed"]

    cols = st.columns(6)
    cols[0].metric("Open Positions", len(open_pos))
    cols[1].metric("Closed Positions", len(closed_pos))
    cols[2].metric("Executed Theses", len(executed))
    cols[3].metric("Total Theses", len(theses))

    # Capital deployed = sum of entry_price for open positions
    total_invested = sum(float(p.get("entry_price", 0) or 0) for p in open_pos)
    cols[4].metric("Capital Deployed", f"€{total_invested:,.0f}")

    # Total realized P&L from positions table
    total_pnl = sum(float(p.get("pnl", 0) or 0) for p in open_pos)
    cols[5].metric("Total P&L", f"€{total_pnl:,.0f}",
                   f"{sum(float(p.get('pnl_pct', 0) or 0) for p in open_pos) / max(len(open_pos), 1):.1f}%")

    st.divider()

    # ── ACTIVE POSITIONS ──
    if open_pos:
        st.subheader("Open Positions")

        for p in open_pos:
            entry = float(p.get("entry_price", 0) or 0)
            alloc = float(p.get("allocation_pct", 0) or 0)
            pnl = float(p.get("pnl", 0) or 0)
            pnl_pct = float(p.get("pnl_pct", 0) or 0)
            direction = p.get("direction", "long")
            conviction = p.get("conviction", "N/A")

            with st.expander(
                f"{'🟢' if pnl >= 0 else '🔴'} **{p['symbol']}** — "
                f"{'↑ Long' if direction == 'long' else '↓ Short'} · "
                f"Entry: ${entry:.2f} · Alloc: {alloc:.1f}% · "
                f"P&L: €{pnl:,.0f} ({pnl_pct:+.1f}%)"
            ):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Entry Price", f"${entry:.2f}")
                c2.metric("Allocation", f"{alloc:.1f}%")
                c3.metric("Conviction", str(conviction).upper())
                c4.metric("P&L", f"€{pnl:,.0f}", f"{pnl_pct:+.1f}%")

                # Price chart — get latest OHLCV data
                ohlcv = get_ohlcv(p["symbol"], limit=90)
                if ohlcv:
                    last_close = float(ohlcv[-1]["close"])
                    st.caption(f"Latest close: ${last_close:.2f}")

                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(
                        x=[o["timestamp"] for o in ohlcv[-60:]],
                        open=[o["open"] for o in ohlcv[-60:]],
                        high=[o["high"] for o in ohlcv[-60:]],
                        low=[o["low"] for o in ohlcv[-60:]],
                        close=[o["close"] for o in ohlcv[-60:]],
                        increasing_line_color="#22c55e", decreasing_line_color="#ef4444",
                    ))
                    # Entry price line
                    if entry > 0:
                        fig.add_hline(y=entry, line_dash="dash", line_color="#d4a017",
                                      annotation_text=f"Entry ${entry:.2f}")
                    fig.update_layout(
                        plot_bgcolor="#0b0b12", paper_bgcolor="#0b0b12",
                        font=dict(color="#888", family="monospace"),
                        height=250, margin=dict(t=10, b=30),
                        xaxis_rangeslider_visible=False,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # Kill criteria from thesis review
                review = next((r for r in executed if r.get("symbol") == p["symbol"]), None)
                if review:
                    if review.get("invalidation"):
                        st.warning(f"**Kill Trigger:** {review['invalidation']}")
                    if review.get("risk_note"):
                        st.caption(f"Risk note: {review['risk_note']}")
                    if review.get("position_size"):
                        st.caption(f"Planned size: {review['position_size']}")

    else:
        st.info(
            "No open positions yet. Execute theses through the Gate 3→4 Conviction gate "
            "and add positions here."
        )

    # ── EXECUTION PIPELINE ──
    st.divider()
    st.subheader("Execution Pipeline")
    st.caption("Theses that passed conviction — ready or recently executed.")

    if executed:
        for r in executed:
            thesis = next((t for t in theses if t["id"] == r.get("entity_id")), None)

            with st.expander(
                f"🟢 **{r['symbol']}** — Executed "
                f"(score: {r.get('total_score', 'N/A')}/{r.get('threshold', 'N/A')}) "
                f"· {r.get('created_at', '')}"
            ):
                c1, c2, c3 = st.columns(3)
                c1.metric("Conviction Score", f"{r.get('total_score', 0)}/{r.get('threshold', 0)}")
                if r.get("position_size"):
                    c2.metric("Position Size", r["position_size"])
                if thesis:
                    c3.metric("Kelly f*", thesis.get("kelly_fraction", "N/A"))

                if thesis:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Bear Case", f"{thesis.get('roi_bear', 0):.1f}%")
                    c2.metric("Base Case", f"{thesis.get('roi_base', 0):.1f}%")
                    c3.metric("Bull Case", f"+{thesis.get('roi_bull', 0):.1f}%")

                if r.get("dominant_narrative"):
                    st.markdown(f"**Conviction:** {r['dominant_narrative']}")
                if r.get("invalidation"):
                    st.warning(f"**Kill Trigger:** {r['invalidation']}")

                # Scoring breakdown
                scores = r.get("scores_json")
                if scores:
                    try:
                        scores_dict = parse_json(scores)
                        if isinstance(scores_dict, dict):
                            st.markdown("##### Scoring Breakdown")
                            for k, v in scores_dict.items():
                                bar = "█" * int(v) + "░" * (5 - int(v))
                                st.code(f"  {k:30s} [{bar}] {v}/5")
                    except (TypeError, ValueError):
                        pass
    else:
        st.info("No executed theses yet. Work through the conviction pipeline to build positions.")

    # ── CLOSED POSITIONS ──
    if closed_pos:
        st.divider()
        st.subheader("Closed Positions")

        total_realized = 0
        for p in closed_pos:
            entry = float(p.get("entry_price", 0) or 0)
            exit_price = float(p.get("exit_price", 0) or 0)
            pnl = float(p.get("pnl", 0) or 0)
            pnl_pct = float(p.get("pnl_pct", 0) or 0)
            total_realized += pnl

            st.markdown(
                f"{'🟢' if pnl >= 0 else '🔴'} **{p['symbol']}** — "
                f"Entry: ${entry:.2f} → Exit: ${exit_price:.2f} · "
                f"P&L: €{pnl:,.0f} ({pnl_pct:+.1f}%)"
            )

        st.metric("Total Realized P&L", f"€{total_realized:,.0f}")

    # ── PORTFOLIO RISK OVERVIEW ──
    st.divider()
    st.subheader("Risk Overview")

    deferred = [r for r in executed_reviews if r.get("decision") == "defer"]
    rejected = [r for r in executed_reviews if r.get("decision") == "reject"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Executed", len(executed))
    c2.metric("Deferred", len(deferred))
    c3.metric("Rejected", len(rejected))

    if executed:
        # Score distribution
        scores = [r.get("total_score", 0) for r in executed]
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=scores, nbinsx=10, marker_color="#d4a017",
            name="Conviction Scores",
        ))
        fig.update_layout(
            plot_bgcolor="#0b0b12", paper_bgcolor="#0b0b12",
            font=dict(color="#888", family="monospace"),
            xaxis_title="Conviction Score", yaxis_title="Count",
            height=250, margin=dict(t=20, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── FULL PIPELINE SUMMARY ──
    st.divider()
    st.subheader("Pipeline Summary")
    pipeline = {
        "Signals": count_table("signals"),
        "Mosaics": count_table("mosaics"),
        "Theses": count_table("theses"),
        "Reviews": count_table("reviews"),
        "Positions": count_table("positions"),
    }

    fig = go.Figure()
    fig.add_trace(go.Funnel(
        y=list(pipeline.keys()),
        x=list(pipeline.values()),
        textinfo="value+percent initial",
        marker=dict(color=["#a855f7", "#3b82f6", "#d4a017", "#22c55e", "#ef4444"]),
    ))
    fig.update_layout(
        plot_bgcolor="#0b0b12", paper_bgcolor="#0b0b12",
        font=dict(color="#888", family="monospace"),
        height=300, margin=dict(t=20, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)
