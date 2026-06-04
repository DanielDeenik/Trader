# Social Arb Agent Topology

## Cognitive Layer Flow (Camillo Architecture)

```
L0: Collection
    ↓ SIGNALS_COLLECTED
L1: Signal Scoring & Clustering
    ↓ MOSAICS_ASSEMBLED
L2: Signal Assembly → Mosaic Formation
    ↓ (decision: build_thesis)
L3: Thesis Generation (Strategist Agent)
    ↓ THESES_FORGED → HITL_REQUIRED
L4: Human Review Gate (Gatekeeper Agent)
    ↓ DECISIONS_MADE
L5: Position Execution (Executor Agent)
    ↓ POSITIONS_UPDATED
```

## Agent Responsibilities

### strategist.py (L2→L3)
**Layer:** Cognitive thesis generation with divergence + conviction scoring

**Triggers:** 
- `MOSAICS_ASSEMBLED` - primary entry point
- `DECISIONS_MADE` - feedback loop for thesis refinement

**Behavior:**
1. Query mosaics with `action='build_thesis'` lacking theses
2. Verify theses exist in DB (created by pipeline.py)
3. Score by conviction: `kelly_fraction × coherence_score`
4. Publish `THESES_FORGED` with ranked thesis list
5. Publish `HITL_REQUIRED` for pending reviews

**Config:**
- `min_coherence` (default 0.5) - minimum mosaic coherence
- `min_kelly` (default 0.02) - minimum kelly fraction

---

### gatekeeper.py (L3→L4)
**Layer:** Human-In-The-Loop decision gate management

**Triggers:**
- `THESES_FORGED` - populate review queue
- `HITL_REQUIRED` - priority review flagging

**Behavior:**
1. Query pending reviews from reviews table
2. Rank by lifecycle_stage urgency (emerging > validating > confirmed > saturated)
3. Auto-promote if `trust_level='autonomous'` AND `total_score >= threshold`
4. Periodic tick (30s default): poll for completed reviews
5. Convert completed reviews to DECISIONS_MADE events

**Config:**
- `auto_promote_threshold` (default 15.0) - score threshold for autonomous approval
- `review_poll_interval` (default 30) - seconds between review polling

**Auto-promotion Logic:**
- High-conviction theses with autonomous trust history can bypass manual review
- Maintains audit trail of all decisions (human + auto)

---

### executor.py (L4→L5)
**Layer:** Position lifecycle management and execution

**Triggers:**
- `DECISIONS_MADE` with decision='execute'/'promote'/'auto_approve'

**Behavior:**
1. On decision: create position record if not duplicate
2. Use thesis data: allocation_pct, conviction, entry_price
3. Periodic tick (120s): monitor open positions
4. Exit conditions:
   - Thesis invalidated → close position
   - Lifecycle regression (confirmed → saturated) → close position
5. Calculate PnL and publish POSITIONS_UPDATED

**Config:**
- `max_positions` (default 10) - concurrent open position limit
- `max_allocation_pct` (default 5.0) - max per-position allocation

**Exit Signals:**
- Thesis status changes to 'invalidated'
- Thesis lifecycle_stage regresses to 'saturated'
- Total allocation exceeds 100% across portfolio

---

## Event Bus Contract

All agents extend `BaseAgent` and implement:

```python
def subscriptions(self) -> List[EventType]:
    """Which events this agent reacts to."""
    
async def handle_event(self, event: Event):
    """React to subscribed events."""
    
async def tick(self):
    """Optional: periodic checks for polling-based logic."""
```

## Database Tables Used

| Agent | Tables | Operations |
|-------|--------|-----------|
| **Strategist** | mosaics, theses | SELECT (query_mosaics_to_forge), UPDATE (thesis status) |
| **Gatekeeper** | reviews, decisions, theses | SELECT (query_pending_reviews), INSERT (mark_review_processed) |
| **Executor** | positions, theses, ohlcv, audit_trail | SELECT (open positions, thesis, price), INSERT (create position), UPDATE (close position) |

## Feedback Loops

**Strategist ← Gatekeeper:**
- DECISIONS_MADE triggers strategist to refine thesis status
- Closed loop: rejected theses inform future mosaic evaluation

**Gatekeeper ← Executor:**
- POSITIONS_UPDATED can trigger review of allocation limits
- Closed loop: position performance informs future decision thresholds

---

## Testing Notes

- All agents use sqlite3 with absolute db_path
- No LLM calls — pure orchestration
- Async event-driven: tick-based polling for external state changes
- Metrics tracked: actions_taken, actions_failed, events_received, events_published
