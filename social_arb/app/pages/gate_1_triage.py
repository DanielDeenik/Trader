"""HITL Gate 1→2: Signal Triage — Score and decide per symbol cluster."""

import json
import streamlit as st
from social_arb.app.db_helpers import (
    get_signals, get_signals_grouped, get_reviews, save_review,
)


SCORING_CRITERIA = {
    "signal_quality": {
        "label": "Signal Quality",
        "help": "Are these real signals or noise? (1=boilerplate, 5=high-conviction)",
    },
    "source_diversity": {
        "label": "Source Diversity",
        "help": "How many independent sources agree? (1=single source, 5=multi-source corroboration)",
    },
    "divergence_magnitude": {
        "label": "Divergence Magnitude",
        "help": "How wide is the gap between social sentiment and market pricing? (1=none, 5=extreme)",
    },
    "timeliness": {
        "label": "Timeliness",
        "help": "How fresh are these signals? (1=stale/weeks old, 5=breaking/today)",
    },
}

THRESHOLD = 12


def render():
    st.title("⊞ Gate 1→2 · Signal Triage")
    st.caption(
        "**HITL Question:** Is this symbol's signal cluster worth assembling into a mosaic?"
    )

    # Show existing reviews
    existing = get_reviews(gate="L1_triage")
    reviewed_symbols = {r["symbol"] for r in existing}

    grouped = get_signals_grouped()
    if not grouped:
        st.info("No signals to triage. Collect signals first.")
        return

    # Progress
    total = len(grouped)
    done = len(reviewed_symbols)
    st.progress(done / total if total else 0, text=f"{done}/{total} symbols reviewed")

    # Symbol selector
    symbols = [g["symbol"] for g in grouped]
    pending = [s for s in symbols if s not in reviewed_symbols]
    all_options = pending + [f"✓ {s}" for s in symbols if s in reviewed_symbols]

    selected = st.selectbox("Select symbol to review", all_options)
    if selected.startswith("✓ "):
        selected = selected[2:]

    # Get data for selected symbol
    g = next((x for x in grouped if x["symbol"] == selected), None)
    if not g:
        return

    signals = get_signals(symbol=selected, limit=50)

    # ── LAYOUT: Data | Decision ──
    data_col, decision_col = st.columns([3, 2])

    with data_col:
        st.subheader(f"{selected} — Signal Cluster")

        # Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total", g["total"])
        m2.metric("Bullish", g["bullish"])
        m3.metric("Neutral", g["neutral"])
        m4.metric("Sources", g["source_count"])

        # Signal feed
        st.markdown("##### Signal Fragments")
        for sig in signals[:15]:
            raw = sig.get("raw_json", {})
            title = raw.get("title", "") if isinstance(raw, dict) else ""
            direction = sig.get("direction", "neutral")
            icon = "🟢" if direction == "bullish" else "🔴" if direction == "bearish" else "⚪"
            votes = raw.get("upvotes", "") if isinstance(raw, dict) else ""
            sub = raw.get("subreddit", "") if isinstance(raw, dict) else ""

            with st.container():
                st.markdown(
                    f"{icon} **[{sig['source']}]** {title or sig.get('signal_type', '')}  \n"
                    f"<small style='color:#888'>{sig['timestamp'][:16]} · "
                    f"str:{sig.get('strength', 0):.2f} · conf:{sig.get('confidence', 0):.2f}"
                    f"{f' · ↑{votes}' if votes else ''}"
                    f"{f' · r/{sub}' if sub else ''}</small>",
                    unsafe_allow_html=True,
                )

    with decision_col:
        st.subheader("Your Decision")

        # Check if already reviewed
        prev = next((r for r in existing if r["symbol"] == selected), None)
        if prev:
            st.success(f"Previously reviewed: **{prev['decision'].upper()}** (score: {prev.get('total_score', 'N/A')})")
            st.caption("Submitting again will create a new review.")

        # ── SCORING ──
        st.markdown("##### Scoring (1-5)")
        scores = {}
        for key, meta in SCORING_CRITERIA.items():
            scores[key] = st.slider(
                meta["label"], 1, 5, 3, help=meta["help"], key=f"score_{selected}_{key}",
            )

        total_score = sum(scores.values())
        score_color = "🟢" if total_score >= THRESHOLD else "🟡" if total_score >= 8 else "🔴"
        st.metric("Total Score", f"{total_score}/20", f"Threshold: {THRESHOLD}")
        st.caption(f"{score_color} {'Passes threshold' if total_score >= THRESHOLD else 'Below threshold'}")

        # ── NARRATIVE QUESTIONS ──
        st.markdown("##### Narrative")
        dominant = st.text_area(
            "What's the dominant narrative in these signals?",
            key=f"q1_{selected}", height=68,
        )
        pricing = st.text_area(
            "Is the market already pricing this in? Evidence?",
            key=f"q2_{selected}", height=68,
        )
        invalidation = st.text_area(
            "What would change your mind?",
            key=f"q3_{selected}", height=68,
        )

        # ── DECISION ──
        st.markdown("##### Decision")
        decision = st.radio(
            "Action",
            ["promote", "watch", "discard"],
            format_func=lambda x: {"promote": "⬆ PROMOTE → Mosaic", "watch": "👁 WATCH — Monitor", "discard": "✕ DISCARD — Noise"}[x],
            key=f"dec_{selected}",
            horizontal=True,
        )

        if st.button("Submit Review", type="primary", use_container_width=True, key=f"submit_{selected}"):
            save_review(
                gate="L1_triage",
                symbol=selected,
                entity_id=0,
                entity_type="signal_cluster",
                scores_json=scores,
                total_score=total_score,
                threshold=THRESHOLD,
                narrative=None,
                dominant_narrative=dominant,
                market_pricing=pricing,
                invalidation=invalidation,
                decision=decision,
            )
            st.success(f"✓ {selected} → **{decision.upper()}** (score: {total_score}/20)")
            st.rerun()

    # ── REVIEW SUMMARY ──
    if existing:
        st.divider()
        st.subheader("Review Summary")
        promote = [r for r in existing if r["decision"] == "promote"]
        watch = [r for r in existing if r["decision"] == "watch"]
        discard = [r for r in existing if r["decision"] == "discard"]

        c1, c2, c3 = st.columns(3)
        c1.metric("Promoted", len(promote))
        c2.metric("Watching", len(watch))
        c3.metric("Discarded", len(discard))

        for r in existing:
            icon = "⬆" if r["decision"] == "promote" else "👁" if r["decision"] == "watch" else "✕"
            st.markdown(f"{icon} **{r['symbol']}** — score: {r.get('total_score', 'N/A')}/20 — {r['decision']}")
