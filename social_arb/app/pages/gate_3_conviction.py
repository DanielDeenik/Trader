"""HITL Gate 3→4: Thesis Conviction — Final scoring before execution."""

import streamlit as st
from social_arb.app.db_helpers import get_theses, get_mosaics, get_ohlcv, get_reviews, save_review


SCORING_CRITERIA = {
    "conviction_level": {
        "label": "Personal Conviction",
        "help": "Would you bet your own money on this? (1=no way, 5=high conviction)",
    },
    "risk_reward": {
        "label": "Risk/Reward Profile",
        "help": "Is the upside worth the downside? (1=terrible ratio, 5=highly asymmetric)",
    },
    "timing_confidence": {
        "label": "Timing Confidence",
        "help": "How confident are you in the repricing timeline? (1=no idea, 5=clear catalyst date)",
    },
    "position_sizing": {
        "label": "Position Sizing Comfort",
        "help": "Are you comfortable with quarter-Kelly sizing? (1=too large, 5=appropriate)",
    },
    "kill_criteria_clarity": {
        "label": "Kill Criteria Clarity",
        "help": "Can you clearly define when to exit? (1=vague, 5=precise triggers defined)",
    },
}

THRESHOLD = 15


def render():
    st.title("⊞ Gate 3→4 · Thesis Conviction")
    st.caption(
        "**HITL Question:** Would you bet real money on this thesis at the Kelly-recommended size?"
    )

    theses = get_theses()
    if not theses:
        st.info("No theses to review. Complete the analysis pipeline first.")
        return

    existing = get_reviews(gate="L3_conviction")
    reviewed_ids = {r["entity_id"] for r in existing}

    total = len(theses)
    done = len(reviewed_ids)
    st.progress(done / total if total else 0, text=f"{done}/{total} theses reviewed")

    # Selector
    options = []
    for t in theses:
        prefix = "✓ " if t["id"] in reviewed_ids else ""
        options.append(
            f"{prefix}{t['symbol']} (#{t['id']} · {t.get('lifecycle_stage', 'N/A')} · "
            f"bear:{t.get('roi_bear', 0):.1f}% / bull:+{t.get('roi_bull', 0):.1f}%)"
        )

    selected_label = st.selectbox("Select thesis", options)
    selected_id = int(selected_label.split("#")[1].split(" ")[0])
    thesis = next(t for t in theses if t["id"] == selected_id)

    # ── LAYOUT ──
    data_col, decision_col = st.columns([3, 2])

    with data_col:
        st.subheader(f"{thesis['symbol']} — Thesis #{thesis['id']}")

        # Key metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Bear Case", f"{thesis.get('roi_bear', 0):.1f}%")
        c2.metric("Base Case", f"{thesis.get('roi_base', 0):.1f}%")
        c3.metric("Bull Case", f"+{thesis.get('roi_bull', 0):.1f}%")

        c1, c2, c3 = st.columns(3)
        c1.metric("Kelly f*", thesis.get("kelly_fraction", 0))
        c2.metric("Lifecycle", thesis.get("lifecycle_stage", "N/A").upper())
        c3.metric("Domain", thesis.get("domain", ""))

        # Risk/reward visual
        bear = thesis.get("roi_bear", 0)
        bull = thesis.get("roi_bull", 0)
        base = thesis.get("roi_base", 0)

        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Waterfall(
            x=["Bear", "Base", "Bull"],
            y=[bear, base, bull],
            connector=dict(line=dict(color="#333")),
            decreasing=dict(marker=dict(color="#ef4444")),
            increasing=dict(marker=dict(color="#22c55e")),
            totals=dict(marker=dict(color="#eab308")),
            text=[f"{bear:.1f}%", f"{base:.1f}%", f"+{bull:.1f}%"],
            textposition="outside",
        ))
        fig.update_layout(
            plot_bgcolor="#0b0b12", paper_bgcolor="#0b0b12",
            font=dict(color="#888", family="monospace"),
            height=250, margin=dict(t=20, b=40),
            yaxis=dict(title="ROI %", showgrid=True, gridcolor="#1a1a26"),
        )
        st.plotly_chart(fig, use_container_width=True)

        # OHLCV context
        ohlcv = get_ohlcv(thesis["symbol"], limit=90)
        if ohlcv:
            st.markdown("##### Recent Price Action (90d)")
            fig2 = go.Figure()
            fig2.add_trace(go.Candlestick(
                x=[o["timestamp"] for o in ohlcv[-60:]],
                open=[o["open"] for o in ohlcv[-60:]],
                high=[o["high"] for o in ohlcv[-60:]],
                low=[o["low"] for o in ohlcv[-60:]],
                close=[o["close"] for o in ohlcv[-60:]],
                increasing_line_color="#22c55e", decreasing_line_color="#ef4444",
            ))
            fig2.update_layout(
                plot_bgcolor="#0b0b12", paper_bgcolor="#0b0b12",
                font=dict(color="#888", family="monospace"),
                height=250, margin=dict(t=10, b=30),
                xaxis_rangeslider_visible=False,
            )
            st.plotly_chart(fig2, use_container_width=True)

        # Mosaic context
        mosaic_data = get_mosaics(symbol=thesis["symbol"])
        if mosaic_data:
            m = mosaic_data[0]
            st.markdown(f"##### Mosaic: Coherence {m.get('coherence_score', 0):.1f} · Divergence {m.get('divergence_strength', 0):.1f}%")
            if m.get("narrative"):
                st.caption(m["narrative"])

    with decision_col:
        st.subheader("Your Decision")

        prev = next((r for r in existing if r["entity_id"] == thesis["id"]), None)
        if prev:
            st.success(f"Previously: **{prev['decision'].upper()}** (score: {prev.get('total_score', 'N/A')})")

        # ── SCORING ──
        st.markdown("##### Scoring (1-5)")
        scores = {}
        for key, meta in SCORING_CRITERIA.items():
            scores[key] = st.slider(meta["label"], 1, 5, 3, help=meta["help"], key=f"g3_{thesis['id']}_{key}")

        total_score = sum(scores.values())
        st.metric("Total Score", f"{total_score}/25", f"Threshold: {THRESHOLD}")

        # ── NARRATIVE ──
        st.markdown("##### Narrative")
        dominant = st.text_area("Why do you have conviction here?", key=f"g3_q1_{thesis['id']}", height=68)
        pricing = st.text_area("What's your expected holding period?", key=f"g3_q2_{thesis['id']}", height=68)
        invalidation = st.text_area("What's your kill trigger?", key=f"g3_q3_{thesis['id']}", height=68)

        # ── POSITION SIZING ──
        st.markdown("##### Position")
        position_size = st.text_input("Position size (e.g. €5,000)", key=f"g3_size_{thesis['id']}")
        risk_note = st.text_input("Risk note", key=f"g3_risk_{thesis['id']}")

        # ── DECISION ──
        st.markdown("##### Decision")
        decision = st.radio(
            "Action", ["execute", "defer", "reject"],
            format_func=lambda x: {"execute": "⬆ EXECUTE — Go Live", "defer": "⏸ DEFER — Not Yet", "reject": "✕ REJECT — No Edge"}[x],
            key=f"g3_dec_{thesis['id']}", horizontal=True,
        )

        if st.button("Submit Review", type="primary", use_container_width=True, key=f"g3_sub_{thesis['id']}"):
            save_review(
                gate="L3_conviction", symbol=thesis["symbol"],
                entity_id=thesis["id"], entity_type="thesis",
                scores_json=scores, total_score=total_score, threshold=THRESHOLD,
                narrative=None, dominant_narrative=dominant,
                market_pricing=pricing, invalidation=invalidation,
                decision=decision, position_size=position_size, risk_note=risk_note,
            )
            st.success(f"✓ {thesis['symbol']} → **{decision.upper()}**")
            st.rerun()
