"""L4: Decisions — Execution log of all HITL gate outcomes."""

import streamlit as st
import json
from social_arb.app.db_helpers import get_reviews, count_table


def render():
    st.title("L4 · Decisions")
    st.caption("Complete audit trail of every HITL gate decision. Your investment journal.")

    # ── METRICS ──
    all_reviews = get_reviews()
    if not all_reviews:
        st.info("No decisions yet. Work through the HITL gates (Gate 1→2, 2→3, 3→4) to build your decision trail.")
        return

    cols = st.columns(5)
    gates = {"L1_triage": 0, "L2_validation": 0, "L3_conviction": 0}
    decisions = {"promote": 0, "watch": 0, "discard": 0, "forge": 0, "hold": 0, "reject": 0, "execute": 0, "defer": 0}
    for r in all_reviews:
        g = r.get("gate", "")
        if g in gates:
            gates[g] += 1
        d = r.get("decision", "")
        if d in decisions:
            decisions[d] += 1

    cols[0].metric("Total Reviews", len(all_reviews))
    cols[1].metric("Gate 1 (Triage)", gates.get("L1_triage", 0))
    cols[2].metric("Gate 2 (Validation)", gates.get("L2_validation", 0))
    cols[3].metric("Gate 3 (Conviction)", gates.get("L3_conviction", 0))
    cols[4].metric("Executions", decisions.get("execute", 0))

    # ── FILTER ──
    gate_filter = st.selectbox("Filter by gate", ["All", "L1_triage", "L2_validation", "L3_conviction"])
    filtered = all_reviews if gate_filter == "All" else [r for r in all_reviews if r["gate"] == gate_filter]

    # ── DECISION LOG ──
    st.subheader(f"Decision Log ({len(filtered)} entries)")

    for r in filtered:
        decision = r.get("decision", "")
        icon = {
            "promote": "⬆", "forge": "⬆", "execute": "🟢",
            "watch": "👁", "hold": "⏸", "defer": "⏸",
            "discard": "✕", "reject": "✕",
        }.get(decision, "•")

        color = {
            "promote": "green", "forge": "green", "execute": "green",
            "watch": "orange", "hold": "orange", "defer": "orange",
            "discard": "red", "reject": "red",
        }.get(decision, "gray")

        with st.expander(
            f"{icon} **{r['symbol']}** — {r['gate']} → {decision.upper()} "
            f"(score: {r.get('total_score', 'N/A')}/{r.get('threshold', 'N/A')}) "
            f"· {r.get('created_at', '')}"
        ):
            c1, c2, c3 = st.columns(3)
            c1.metric("Score", f"{r.get('total_score', 0)}/{r.get('threshold', 0)}")
            c2.metric("Gate", r["gate"])
            c3.metric("Decision", decision.upper())

            # Scores breakdown
            scores = r.get("scores_json")
            if scores:
                try:
                    scores_dict = json.loads(scores) if isinstance(scores, str) else scores
                    if isinstance(scores_dict, dict):
                        st.markdown("##### Scoring Breakdown")
                        for k, v in scores_dict.items():
                            bar = "█" * v + "░" * (5 - v)
                            st.code(f"  {k:30s} [{bar}] {v}/5")
                except (json.JSONDecodeError, TypeError):
                    pass

            # Narrative
            if r.get("dominant_narrative"):
                st.markdown(f"**Dominant narrative:** {r['dominant_narrative']}")
            if r.get("market_pricing"):
                st.markdown(f"**Market pricing:** {r['market_pricing']}")
            if r.get("invalidation"):
                st.markdown(f"**Invalidation criteria:** {r['invalidation']}")
            if r.get("position_size"):
                st.markdown(f"**Position size:** {r['position_size']}")
            if r.get("risk_note"):
                st.markdown(f"**Risk note:** {r['risk_note']}")

    # ── SUMMARY TABLE ──
    st.divider()
    st.subheader("Decision Summary by Symbol")
    symbol_decisions = {}
    for r in all_reviews:
        sym = r["symbol"]
        if sym not in symbol_decisions:
            symbol_decisions[sym] = {"L1": "-", "L2": "-", "L3": "-"}
        gate_short = {"L1_triage": "L1", "L2_validation": "L2", "L3_conviction": "L3"}.get(r["gate"], "")
        if gate_short:
            symbol_decisions[sym][gate_short] = r["decision"]

    if symbol_decisions:
        import pandas as pd
        df = pd.DataFrame([
            {"Symbol": sym, "L1 Triage": v["L1"], "L2 Validation": v["L2"], "L3 Conviction": v["L3"]}
            for sym, v in symbol_decisions.items()
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
