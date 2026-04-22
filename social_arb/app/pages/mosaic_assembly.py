"""L2: Mosaic Assembly — View assembled mosaic cards with fragment analysis."""

import streamlit as st
import plotly.graph_objects as go
from social_arb.app.db_helpers import get_mosaics, get_signals, parse_json


def render():
    st.title("L2 · Mosaic Assembly")
    st.caption("Machine-assembled fragment cards. Coherence = source agreement. Divergence = sentiment vs. price gap.")

    mosaics = get_mosaics()
    if not mosaics:
        st.info("No mosaics yet. Run `social-arb analyze` after collecting signals.")
        return

    # ── MOSAIC OVERVIEW ──
    st.subheader("Mosaic Cards")
    cols = st.columns(4)
    cols[0].metric("Total Mosaics", len(mosaics))
    avg_coh = sum(m.get("coherence_score", 0) or 0 for m in mosaics) / len(mosaics)
    avg_div = sum(m.get("divergence_strength", 0) or 0 for m in mosaics) / len(mosaics)
    cols[1].metric("Avg Coherence", f"{avg_coh:.1f}")
    cols[2].metric("Avg Divergence", f"{avg_div:.1f}%")
    high_div = [m for m in mosaics if (m.get("divergence_strength") or 0) >= 50]
    cols[3].metric("High Divergence", len(high_div))

    # ── SCATTER: Coherence vs Divergence ──
    st.subheader("Coherence vs. Divergence Matrix")
    fig = go.Figure()
    for m in mosaics:
        frags = parse_json(m.get("fragments_json"))
        n_frags = len(frags) if isinstance(frags, list) else 0
        fig.add_trace(go.Scatter(
            x=[m.get("divergence_strength", 0)],
            y=[m.get("coherence_score", 0)],
            mode="markers+text",
            marker=dict(
                size=max(n_frags * 3, 12),
                color="#d4a017" if (m.get("divergence_strength") or 0) >= 50 else "#555",
                line=dict(width=1, color="#d4a017"),
            ),
            text=[m["symbol"]], textposition="top center",
            textfont=dict(color="#d4a017", size=12),
            name=m["symbol"], showlegend=False,
        ))

    fig.add_vrect(x0=50, x1=100, fillcolor="#d4a017", opacity=0.03, line_width=0)
    fig.add_annotation(x=75, y=85, text="HIGH DIVERGENCE\nZONE", font=dict(color="#9a7510", size=10), showarrow=False)

    fig.update_layout(
        plot_bgcolor="#0b0b12", paper_bgcolor="#0b0b12",
        font=dict(color="#888", family="monospace"),
        xaxis=dict(title="Divergence Strength (%)", showgrid=True, gridcolor="#1a1a26"),
        yaxis=dict(title="Coherence Score", showgrid=True, gridcolor="#1a1a26"),
        height=380, margin=dict(t=20, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── MOSAIC CARDS ──
    st.subheader("Individual Mosaic Cards")
    for m in mosaics:
        frags = parse_json(m.get("fragments_json"))
        n_frags = len(frags) if isinstance(frags, list) else 0

        with st.expander(
            f"**{m['symbol']}** — Coherence: {m.get('coherence_score', 0)} · "
            f"Divergence: {m.get('divergence_strength', 0)}% · {n_frags} fragments",
            expanded=(m.get("divergence_strength") or 0) >= 50,
        ):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Coherence", f"{m.get('coherence_score', 0):.1f}")
            c2.metric("Divergence", f"{m.get('divergence_strength', 0):.1f}%")
            c3.metric("Domain", m.get("domain", ""))
            c4.metric("Fragments", n_frags)

            if m.get("narrative"):
                st.markdown(f"**Narrative:** {m['narrative']}")

            if isinstance(frags, list) and frags:
                st.markdown("##### Fragment Breakdown")
                # Count by source and direction
                src_counts = {}
                for f in frags:
                    src = f.get("source", "unknown")
                    d = f.get("direction", "neutral")
                    key = f"{src}/{d}"
                    src_counts[key] = src_counts.get(key, 0) + 1

                for key, count in sorted(src_counts.items(), key=lambda x: -x[1]):
                    src, d = key.split("/")
                    icon = "🟢" if d == "bullish" else "🔴" if d == "bearish" else "⚪"
                    st.markdown(f"{icon} **{src}** · {d} × {count}")

            # Show related signals
            signals = get_signals(symbol=m["symbol"], limit=5)
            if signals:
                st.markdown("##### Latest Signals")
                for sig in signals[:3]:
                    raw = sig.get("raw_json", {})
                    title = raw.get("title", "") if isinstance(raw, dict) else ""
                    st.caption(f"[{sig['source']}] {title or sig.get('signal_type', '')} — {sig['timestamp'][:16]}")
