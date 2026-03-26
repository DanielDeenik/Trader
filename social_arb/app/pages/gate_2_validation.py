"""HITL Gate 2→3: Mosaic Validation — Score mosaic coherence and decide."""

import streamlit as st
from social_arb.app.db_helpers import get_mosaics, get_signals, get_reviews, save_review, parse_json


SCORING_CRITERIA = {
    "coherence_real": {
        "label": "Coherence Authenticity",
        "help": "Is the source agreement genuine or coincidental? (1=coincidental, 5=strong independent corroboration)",
    },
    "divergence_exploitable": {
        "label": "Divergence Exploitability",
        "help": "Can you actually trade this gap? (1=no clear trade, 5=clear asymmetric opportunity)",
    },
    "narrative_clarity": {
        "label": "Narrative Clarity",
        "help": "Can you explain WHY this asymmetry exists in one sentence? (1=unclear, 5=crystal clear)",
    },
    "catalyst_visibility": {
        "label": "Catalyst Visibility",
        "help": "Is there a visible catalyst that will cause repricing? (1=none visible, 5=imminent catalyst)",
    },
}

THRESHOLD = 12


def render():
    st.title("⊞ Gate 2→3 · Mosaic Validation")
    st.caption(
        "**HITL Question:** Do these assembled fragments form a coherent story the market hasn't priced in?"
    )

    mosaics = get_mosaics()
    if not mosaics:
        st.info("No mosaics to validate. Run analysis first.")
        return

    existing = get_reviews(gate="L2_validation")
    reviewed_ids = {r["entity_id"] for r in existing}

    total = len(mosaics)
    done = len(reviewed_ids)
    st.progress(done / total if total else 0, text=f"{done}/{total} mosaics reviewed")

    # Selector
    options = []
    for m in mosaics:
        prefix = "✓ " if m["id"] in reviewed_ids else ""
        options.append(f"{prefix}{m['symbol']} (#{m['id']} · coh:{m.get('coherence_score', 0):.0f} · div:{m.get('divergence_strength', 0):.0f}%)")

    selected_label = st.selectbox("Select mosaic to review", options)
    selected_id = int(selected_label.split("#")[1].split(" ")[0])
    mosaic = next(m for m in mosaics if m["id"] == selected_id)

    # ── LAYOUT ──
    data_col, decision_col = st.columns([3, 2])

    with data_col:
        st.subheader(f"{mosaic['symbol']} — Mosaic #{mosaic['id']}")

        m1, m2, m3 = st.columns(3)
        m1.metric("Coherence", f"{mosaic.get('coherence_score', 0):.1f}")
        m2.metric("Divergence", f"{mosaic.get('divergence_strength', 0):.1f}%")

        frags = parse_json(mosaic.get("fragments_json"))
        n_frags = len(frags) if isinstance(frags, list) else 0
        m3.metric("Fragments", n_frags)

        if mosaic.get("narrative"):
            st.info(f"**Machine Narrative:** {mosaic['narrative']}")

        # Fragment breakdown
        if isinstance(frags, list) and frags:
            st.markdown("##### Fragment Composition")
            bull = sum(1 for f in frags if f.get("direction") == "bullish")
            neut = sum(1 for f in frags if f.get("direction") == "neutral")
            bear = sum(1 for f in frags if f.get("direction") == "bearish")
            st.markdown(f"🟢 {bull} bullish · ⚪ {neut} neutral · 🔴 {bear} bearish")

            sources = {}
            for f in frags:
                s = f.get("source", "unknown")
                sources[s] = sources.get(s, 0) + 1
            for s, c in sorted(sources.items(), key=lambda x: -x[1]):
                st.markdown(f"  **{s}:** {c} fragments")

        # Related signals
        signals = get_signals(symbol=mosaic["symbol"], limit=10)
        if signals:
            st.markdown("##### Signal Evidence")
            for sig in signals[:8]:
                raw = sig.get("raw_json", {})
                title = raw.get("title", "") if isinstance(raw, dict) else ""
                d = sig.get("direction", "neutral")
                icon = "🟢" if d == "bullish" else "🔴" if d == "bearish" else "⚪"
                st.markdown(
                    f"{icon} **[{sig['source']}]** {title or sig.get('signal_type', '')}  \n"
                    f"<small style='color:#888'>str:{sig.get('strength', 0):.2f} · conf:{sig.get('confidence', 0):.2f} · {sig['timestamp'][:16]}</small>",
                    unsafe_allow_html=True,
                )

    with decision_col:
        st.subheader("Your Decision")

        prev = next((r for r in existing if r["entity_id"] == mosaic["id"]), None)
        if prev:
            st.success(f"Previously: **{prev['decision'].upper()}** (score: {prev.get('total_score', 'N/A')})")

        st.markdown("##### Scoring (1-5)")
        scores = {}
        for key, meta in SCORING_CRITERIA.items():
            scores[key] = st.slider(meta["label"], 1, 5, 3, help=meta["help"], key=f"g2_{mosaic['id']}_{key}")

        total_score = sum(scores.values())
        st.metric("Total Score", f"{total_score}/20", f"Threshold: {THRESHOLD}")

        st.markdown("##### Narrative")
        dominant = st.text_area("What story do these fragments tell?", key=f"g2_q1_{mosaic['id']}", height=68)
        pricing = st.text_area("Why hasn't the market priced this in yet?", key=f"g2_q2_{mosaic['id']}", height=68)
        invalidation = st.text_area("What evidence would kill this mosaic?", key=f"g2_q3_{mosaic['id']}", height=68)

        st.markdown("##### Decision")
        decision = st.radio(
            "Action", ["forge", "hold", "reject"],
            format_func=lambda x: {"forge": "⬆ FORGE THESIS →", "hold": "⏸ HOLD — Collect More", "reject": "✕ REJECT — Spurious"}[x],
            key=f"g2_dec_{mosaic['id']}", horizontal=True,
        )

        if st.button("Submit Review", type="primary", use_container_width=True, key=f"g2_sub_{mosaic['id']}"):
            save_review(
                gate="L2_validation", symbol=mosaic["symbol"],
                entity_id=mosaic["id"], entity_type="mosaic",
                scores_json=scores, total_score=total_score, threshold=THRESHOLD,
                narrative=None, dominant_narrative=dominant,
                market_pricing=pricing, invalidation=invalidation, decision=decision,
            )
            st.success(f"✓ {mosaic['symbol']} → **{decision.upper()}**")
            st.rerun()
