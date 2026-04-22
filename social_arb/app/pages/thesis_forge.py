"""L3: Thesis Forge — Full research page with all 4 analysis components.

Components:
1. Camillo Signal Matrix (social vs institutional)
2. Catalyst Timeline (events mapped to price)
3. Narrative Builder (structured thesis)
4. Competitive Landscape (relative positioning)
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from social_arb.app.db_helpers import (
    get_theses, get_mosaics, get_signals, get_ohlcv,
    get_signals_grouped, parse_json, count_table,
)
from social_arb.config import config


def render():
    st.title("L3 · Thesis Forge")
    st.caption("Deep research per company. All 4 analysis lenses applied to every thesis.")

    theses = get_theses()
    grouped = get_signals_grouped()
    symbols_with_data = [g["symbol"] for g in grouped]

    # Also include symbols from config that might not have theses yet
    all_symbols = list(set(symbols_with_data + [t["symbol"] for t in theses]))
    all_symbols.sort()

    if not all_symbols:
        st.info("No data yet. Collect signals and run analysis first.")
        return

    selected = st.selectbox("Company", all_symbols)

    # Get all data for this company
    thesis = next((t for t in theses if t["symbol"] == selected), None)
    mosaic_data = get_mosaics(symbol=selected)
    mosaic = mosaic_data[0] if mosaic_data else None
    signals = get_signals(symbol=selected, limit=200)
    ohlcv = get_ohlcv(symbol=selected, limit=365)
    sig_group = next((g for g in grouped if g["symbol"] == selected), None)

    # ── HEADER METRICS ──
    cols = st.columns(6)
    if ohlcv:
        latest = ohlcv[-1]
        cols[0].metric("Last Close", f"${latest['close']:.2f}")
    if sig_group:
        cols[1].metric("Signals", sig_group["total"])
        cols[2].metric("Bullish", sig_group["bullish"])
    if mosaic:
        cols[3].metric("Coherence", f"{mosaic.get('coherence_score', 0):.1f}")
        cols[4].metric("Divergence", f"{mosaic.get('divergence_strength', 0):.1f}%")
    if thesis:
        cols[5].metric("Lifecycle", thesis.get("lifecycle_stage", "N/A").upper())

    # ── TABS FOR 4 COMPONENTS ──
    tab1, tab2, tab3, tab4 = st.tabs([
        "Signal Matrix", "Catalyst Timeline", "Narrative Builder", "Competitive Landscape",
    ])

    # ════════ TAB 1: CAMILLO SIGNAL MATRIX ════════
    with tab1:
        st.subheader("Camillo Signal Matrix")
        st.caption(
            "Social velocity (Reddit buzz, trends) vs. institutional awareness (SEC filings, analyst). "
            "The GAP between these is the arbitrage opportunity."
        )

        if signals:
            # Categorize signals
            social = [s for s in signals if s["source"] in ("reddit", "trends")]
            institutional = [s for s in signals if s["source"] in ("sec_edgar", "yfinance")]

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("##### Social Signals")
                st.metric("Count", len(social))
                bull_social = sum(1 for s in social if s.get("direction") == "bullish")
                st.metric("Bullish %", f"{bull_social/len(social)*100:.0f}%" if social else "0%")
                for s in social[:5]:
                    raw = s.get("raw_json", {})
                    title = raw.get("title", "") if isinstance(raw, dict) else ""
                    st.caption(f"🟢 [{s['source']}] {title[:80]}...")

            with c2:
                st.markdown("##### Institutional Signals")
                st.metric("Count", len(institutional))
                bull_inst = sum(1 for s in institutional if s.get("direction") == "bullish")
                st.metric("Bullish %", f"{bull_inst/len(institutional)*100:.0f}%" if institutional else "0%")
                for s in institutional[:5]:
                    raw = s.get("raw_json", {})
                    title = raw.get("title", "") if isinstance(raw, dict) else ""
                    st.caption(f"⚪ [{s['source']}] {title[:80] if title else s.get('signal_type', '')}")

            # Divergence visual
            if social and institutional:
                avg_social_str = sum(s.get("strength", 0) for s in social) / len(social)
                avg_inst_str = sum(s.get("strength", 0) for s in institutional) / len(institutional)

                fig = go.Figure()
                fig.add_trace(go.Bar(x=["Social"], y=[avg_social_str], marker_color="#a855f7", name="Social"))
                fig.add_trace(go.Bar(x=["Institutional"], y=[avg_inst_str], marker_color="#3b82f6", name="Institutional"))
                fig.update_layout(
                    plot_bgcolor="#0b0b12", paper_bgcolor="#0b0b12",
                    font=dict(color="#888", family="monospace"),
                    yaxis_title="Avg Signal Strength",
                    height=250, margin=dict(t=20), showlegend=True,
                    legend=dict(font=dict(color="#888")),
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No signals for this symbol.")

    # ════════ TAB 2: CATALYST TIMELINE ════════
    with tab2:
        st.subheader("Catalyst Timeline")
        st.caption("Events mapped against price action. Annotate what you think triggers repricing.")

        if ohlcv:
            fig = make_subplots(specs=[[{"secondary_y": True}]])

            # Price line
            fig.add_trace(go.Scatter(
                x=[o["timestamp"] for o in ohlcv],
                y=[o["close"] for o in ohlcv],
                mode="lines", name="Close Price",
                line=dict(color="#d4a017", width=2),
            ), secondary_y=False)

            # Volume bars
            fig.add_trace(go.Bar(
                x=[o["timestamp"] for o in ohlcv],
                y=[o.get("volume", 0) for o in ohlcv],
                name="Volume", marker_color="rgba(212,160,23,0.15)",
            ), secondary_y=True)

            # Signal events as markers
            if signals:
                event_dates = []
                event_labels = []
                event_colors = []
                for s in signals:
                    ts = s["timestamp"][:10]
                    # Find nearest OHLCV date
                    closest = min(ohlcv, key=lambda o: abs(hash(o["timestamp"][:10]) - hash(ts)), default=None)
                    if closest:
                        raw = s.get("raw_json", {})
                        title = raw.get("title", "")[:40] if isinstance(raw, dict) else ""
                        event_dates.append(closest["timestamp"])
                        event_labels.append(f"[{s['source']}] {title}")
                        event_colors.append("#22c55e" if s["direction"] == "bullish" else "#ef4444" if s["direction"] == "bearish" else "#555")

                if event_dates:
                    closest_prices = []
                    for ed in event_dates:
                        p = next((o["close"] for o in ohlcv if o["timestamp"] == ed), None)
                        closest_prices.append(p or ohlcv[-1]["close"])

                    fig.add_trace(go.Scatter(
                        x=event_dates, y=closest_prices,
                        mode="markers", name="Signal Events",
                        marker=dict(size=10, color=event_colors, symbol="diamond", line=dict(width=1, color="#fff")),
                        text=event_labels, hoverinfo="text",
                    ), secondary_y=False)

            fig.update_layout(
                plot_bgcolor="#0b0b12", paper_bgcolor="#0b0b12",
                font=dict(color="#888", family="monospace"),
                height=400, margin=dict(t=20, b=40),
                legend=dict(font=dict(color="#888")),
            )
            fig.update_yaxes(showgrid=True, gridcolor="#1a1a26", secondary_y=False)
            fig.update_yaxes(showgrid=False, visible=False, secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)

            # Annotation input
            st.text_area(
                "Your catalyst annotation — what triggers repricing?",
                key=f"catalyst_{selected}", height=80,
                placeholder="e.g., Earnings in 2 weeks. If lawsuit liability exceeds $X, market will reprice...",
            )
        else:
            st.info(f"No OHLCV data for {selected}. Run `social-arb backfill` to populate.")

    # ════════ TAB 3: NARRATIVE BUILDER ════════
    with tab3:
        st.subheader("Narrative Builder")
        st.caption("Structured thesis writing. Not a text box — guided questions that force clarity.")

        if thesis:
            st.markdown(f"**Lifecycle Stage:** `{thesis.get('lifecycle_stage', 'N/A')}`")
            st.markdown(f"**Status:** `{thesis.get('status', 'N/A')}`")

            c1, c2, c3 = st.columns(3)
            c1.metric("Bear Case", f"{thesis.get('roi_bear', 0):.1f}%")
            c2.metric("Base Case", f"{thesis.get('roi_base', 0):.1f}%")
            c3.metric("Bull Case", f"+{thesis.get('roi_bull', 0):.1f}%")
            st.metric("Kelly Fraction (quarter-Kelly cap)", thesis.get("kelly_fraction", 0))

        st.divider()

        st.markdown("##### 1. What is the information asymmetry?")
        st.text_area(
            "Describe the gap between what you know and what the market is pricing.",
            key=f"nb_asymmetry_{selected}", height=80,
            placeholder="Social sentiment shows X but market is pricing Y because...",
        )

        st.markdown("##### 2. Why does this asymmetry exist?")
        st.text_area(
            "Why hasn't the market figured this out yet?",
            key=f"nb_why_{selected}", height=80,
            placeholder="Institutional investors are focused on Z, retail hasn't noticed...",
        )

        st.markdown("##### 3. What breaks the asymmetry?")
        st.text_area(
            "What event or data point will cause the market to reprice?",
            key=f"nb_catalyst_{selected}", height=80,
            placeholder="Earnings call on DATE, product launch, regulatory decision...",
        )

        st.markdown("##### 4. When does the market reprice?")
        st.text_area(
            "What's your time horizon? Gold Rush lifecycle stage?",
            key=f"nb_timing_{selected}", height=80,
            placeholder="2-4 weeks. Currently in Validating stage, approaching Confirmed...",
        )

        st.markdown("##### 5. What invalidates this thesis?")
        st.text_area(
            "Define your kill criteria. What would make you exit?",
            key=f"nb_kill_{selected}", height=80,
            placeholder="If divergence drops below 20%, or if insider selling increases...",
        )

    # ════════ TAB 4: COMPETITIVE LANDSCAPE ════════
    with tab4:
        st.subheader("Competitive Landscape")
        st.caption("Where does this company sit relative to peers? Compare divergence and signal strength.")

        if grouped:
            # Show all symbols in a comparison table
            fig = go.Figure()

            syms = [g["symbol"] for g in grouped]
            totals = [g["total"] for g in grouped]
            bulls = [g["bullish"] for g in grouped]
            colors = ["#d4a017" if g["symbol"] == selected else "#555" for g in grouped]

            fig.add_trace(go.Bar(x=syms, y=totals, name="Total Signals", marker_color=colors))
            fig.add_trace(go.Bar(x=syms, y=bulls, name="Bullish", marker_color=["#22c55e" if g["symbol"] == selected else "#22c55e40" for g in grouped]))

            fig.update_layout(
                barmode="overlay",
                plot_bgcolor="#0b0b12", paper_bgcolor="#0b0b12",
                font=dict(color="#888", family="monospace"),
                height=300, margin=dict(t=20),
                legend=dict(font=dict(color="#888")),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Mosaic comparison
            all_mosaics = get_mosaics()
            if all_mosaics:
                st.markdown("##### Mosaic Comparison")
                for m in all_mosaics:
                    highlight = "→ " if m["symbol"] == selected else "  "
                    bar_len = int((m.get("divergence_strength") or 0) / 2)
                    bar = "█" * bar_len + "░" * (50 - bar_len)
                    st.code(
                        f"{highlight}{m['symbol']:8s} coh:{m.get('coherence_score', 0):5.1f}  "
                        f"div:{m.get('divergence_strength', 0):5.1f}%  [{bar[:30]}]",
                        language=None,
                    )
        else:
            st.info("No comparison data available.")
