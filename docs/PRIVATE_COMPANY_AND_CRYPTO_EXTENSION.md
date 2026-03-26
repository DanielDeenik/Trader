# Social Arb — Private Company & Crypto Extension
## First-Principles Architecture for Mosaic Theory Beyond Public Markets

*Author: Dan Deenik | Date: 2026-03-26 | Status: Architecture Proposal*

---

## First Principles Decomposition

Before designing anything, decompose the problem to its atoms:

**What is mosaic theory?** Assembling fragments of individually non-material, publicly available information into a composite picture that reveals something the market hasn't priced in.

**What changes when you go from public → private companies?**
1. No ticker — no OHLCV, no SEC filings, no real-time price discovery
2. Information is sparser — fragments are rarer and harder to find
3. Valuation is opaque — no market cap, no P/E, only funding rounds and revenue estimates
4. The "market" to diverge from is VC consensus, not Wall Street consensus

**What changes when you add crypto?**
1. Price data exists (like public markets) but on different infrastructure (DEX/CEX)
2. On-chain data IS the signal — wallet movements, TVL, protocol revenue are all public
3. Social signal is amplified — crypto communities are louder than any other asset class
4. Regulatory risk is a first-order variable, not background noise

**The invariant across all three domains:**
```
Information Arbitrage = f(signal_growth) - f(market_consensus_growth)
```
The topology engine doesn't change. The 5 layers don't change. What changes is: where you find fragments, how you measure consensus, and how you size positions.

---

## Domain Architecture

### Current State (What We Just Built)

```
PUBLIC MARKETS
├── Collectors: yfinance, Reddit, Google Trends, SEC EDGAR
├── Signals → DB (data_class='public')
├── Pipeline: coherence + divergence → mosaics → theses
├── HITL: approve/reject/defer
└── Engines: Kelly, IRR, sentiment divergence, cross-domain amplifier
```

### Extended Architecture (Three Domains)

```
┌─────────────────────────────────────────────────────────────────┐
│                    SOCIAL ARB — MOSAIC ENGINE                    │
├─────────────────┬─────────────────────┬─────────────────────────┤
│  PUBLIC MARKETS  │  PRIVATE COMPANIES  │        CRYPTO           │
│  data_class:     │  data_class:        │  data_class:            │
│  'public'        │  'private'          │  'public'               │
├─────────────────┼─────────────────────┼─────────────────────────┤
│ L1 COLLECTORS   │ L1 COLLECTORS       │ L1 COLLECTORS           │
│ ─────────────── │ ──────────────────  │ ────────────────────    │
│ • yfinance      │ • Crunchbase/       │ • CoinGecko API         │
│ • Reddit        │   PitchBook proxy   │ • DeFi Llama (TVL)      │
│ • Google Trends │ • LinkedIn job API  │ • Dune Analytics         │
│ • SEC EDGAR     │ • GitHub activity   │ • Reddit (r/crypto,     │
│                 │ • Patent filings    │   r/defi, r/ethereum)   │
│                 │ • SimilarWeb proxy  │ • On-chain (Etherscan)  │
│                 │ • Glassdoor/levels  │ • Governance proposals  │
│                 │ • Google Trends     │ • Google Trends         │
├─────────────────┼─────────────────────┼─────────────────────────┤
│ L2 DIVERGENCE   │ L2 DIVERGENCE       │ L2 DIVERGENCE           │
│ ─────────────── │ ──────────────────  │ ────────────────────    │
│ Social chatter  │ Hiring velocity     │ On-chain activity       │
│ vs. price       │ vs. VC consensus    │ vs. token price         │
│ action          │ valuation           │                         │
├─────────────────┼─────────────────────┼─────────────────────────┤
│ L3 THESIS       │ L3 THESIS           │ L3 THESIS               │
│ ─────────────── │ ──────────────────  │ ────────────────────    │
│ Kelly sizing    │ IRR/MOIC sim        │ Kelly sizing (modified  │
│ Public exit     │ Private exit:       │ for volatility)         │
│                 │ IPO/M&A/Secondary   │ DeFi yield modeling     │
├─────────────────┼─────────────────────┼─────────────────────────┤
│ L4 LIFECYCLE    │ L4 LIFECYCLE        │ L4 LIFECYCLE            │
│ ─────────────── │ ──────────────────  │ ────────────────────    │
│ Gold Rush:      │ Funding stage:      │ Protocol maturity:      │
│ Emerging →      │ Seed → Series A →   │ Launch → Growth →       │
│ Saturated       │ Growth → Pre-IPO    │ Maturity → Fork risk    │
├─────────────────┼─────────────────────┼─────────────────────────┤
│ L5 POSITION     │ L5 POSITION         │ L5 POSITION             │
│ ─────────────── │ ──────────────────  │ ────────────────────    │
│ Kelly fraction  │ Angel check size    │ Kelly fraction with     │
│ with stop-loss  │ (€1K-€50K range)    │ higher safety factor    │
│                 │ via AngelList/SPV   │ (2x vol adjustment)     │
└─────────────────┴─────────────────────┴─────────────────────────┘
                            │
                    ┌───────┴───────┐
                    │  HITL GATES   │
                    │  (unchanged)  │
                    │  Manual →     │
                    │  Supervised → │
                    │  Autonomous   │
                    └───────────────┘
```

---

## New Collectors: Private Companies

### 1. GitHub Activity Collector (`github_collector.py`)

**Why:** Engineering velocity is the hardest-to-fake signal for a private company. You can't hire 200 engineers and have them do nothing — GitHub commits, repo creation, and open-source activity are real proxy signals for "Build" capability.

**Data source:** GitHub REST API (free, 5000 req/hour with token)

**Signals produced:**
- Commit velocity (monthly trend)
- New repo creation rate
- Open issue/PR activity
- Star velocity on public repos
- Language distribution shifts (signals pivot)

**Divergence formula for private companies:**
```
Private Divergence = (GitHub Activity Growth %) − (VC Valuation Growth %)
```
If a company's engineering output is accelerating but their last funding round was 18 months ago at a flat valuation → the market is underpricing their build capability.

### 2. Job Posting Collector (`jobs_collector.py`)

**Why:** Thomas's email nails this — "anchor clients" are revealed by who companies hire for. A private company hiring "cleared" engineers with TS/SCI clearances is a signal they have government contracts. Hiring 30 account executives in Frankfurt signals European enterprise expansion.

**Data sources:** LinkedIn Jobs API (or scraped), Glassdoor, Levels.fyi

**Signals produced:**
- Hiring velocity by department (engineering vs. sales vs. compliance)
- Geographic expansion signals (new office locations)
- Security clearance requirements (→ defense/gov contracts)
- Salary bands (→ funding health)
- "Build vs. Sell" ratio: `engineering_posts / sales_posts`

**The Naval Score:**
```
Build Score = engineering_hires + patent_filings + github_commits
Sell Score  = sales_hires + marketing_spend + PR_mentions
Balance     = Build Score / (Build Score + Sell Score)

Balance > 0.6 → Building mode (bullish for long-term)
Balance < 0.4 → Selling mode (could be desperate or scaling)
Balance ≈ 0.5 → Healthy equilibrium
```

### 3. Web Traffic Proxy Collector (`traffic_collector.py`)

**Why:** SimilarWeb data reveals product-market fit before any revenue announcement. If a private company's developer docs are getting 10x more traffic than their marketing site, they're building something developers want.

**Data sources:** SimilarWeb API (paid), or proxy via Google Trends + Alexa rank

**Signals produced:**
- Total visit trend (monthly)
- Traffic source breakdown (direct vs. referral vs. search)
- Referral domain analysis (→ anchor client discovery)
- Subdomain traffic: `/docs`, `/api`, `/login` vs. `/pricing`, `/careers`
- Geographic traffic distribution

### 4. Patent & IP Collector (`patent_collector.py`)

**Why:** Patent filings are public but nobody reads them systematically. A private AI company filing 15 patents in "autonomous vehicle perception" when they claim to be building "enterprise data tools" is a massive mosaic fragment.

**Data source:** USPTO API (free), Google Patents

**Signals:**
- Filing velocity
- Technology category shifts
- Inventor network (who's filing → who did they hire from?)
- Citation velocity (other companies citing their patents)

---

## New Collectors: Crypto

### 1. CoinGecko Collector (`coingecko_collector.py`)

**Why:** Price + volume + market cap for all tokens. Free API, no key needed.

**Signals:**
- OHLCV equivalent for tokens
- Market cap ranking changes
- Volume spikes (divergence from social chatter)
- Exchange listing events

### 2. DeFi Llama Collector (`defillama_collector.py`)

**Why:** Total Value Locked (TVL) is the fundamental metric for DeFi protocols. It's the equivalent of AUM for traditional finance — but completely public and real-time.

**Data source:** DeFi Llama API (free, no key)

**Signals:**
- TVL trend per protocol
- TVL vs. token market cap ratio (undervalued if TVL >> market cap)
- Chain TVL migration patterns
- Protocol revenue (fees collected)

**Divergence formula for crypto:**
```
Crypto Divergence = (TVL Growth % + On-chain Activity Growth %) − (Token Price Growth %)
```
If Aave's TVL is growing 40% while AAVE token is flat → market is underpricing the protocol's fundamental usage.

### 3. On-Chain Collector (`onchain_collector.py`)

**Why:** Blockchain data is the ultimate mosaic source — every transaction is public. Whale wallet movements, smart contract interactions, and governance votes are all signals.

**Data sources:** Etherscan API (free tier), Dune Analytics API

**Signals:**
- Active address growth
- Whale wallet accumulation/distribution
- Smart contract deployment velocity
- Gas usage by protocol (demand proxy)
- Governance proposal activity (engagement proxy)

---

## New Scoring Systems

### The Anchor Client Score (Thomas's Framework)

For private companies, the most valuable signal is: **who are their real customers, especially long-term government/enterprise clients?**

```
Anchor Client Score = weighted sum of:
  0.3 × cleared_hiring_signals        (security clearance job posts)
  0.2 × government_referral_traffic   (SimilarWeb .gov/.mil referrals)
  0.2 × contract_award_mentions       (GovCon Wire, Federal Compass)
  0.2 × enterprise_integration_search (Google Trends: "Company + API")
  0.1 × regulatory_certification      (FedRAMP, SOC 2, ISO 27001)
```

### The Build vs. Sell Score (Naval's Framework)

```python
def naval_score(company_signals):
    build = (
        github_commit_velocity * 0.3 +
        engineering_hire_rate * 0.3 +
        patent_filing_rate * 0.2 +
        developer_doc_traffic * 0.2
    )
    sell = (
        sales_hire_rate * 0.3 +
        marketing_traffic * 0.3 +
        pr_mention_volume * 0.2 +
        paid_ad_presence * 0.2
    )
    ratio = build / (build + sell) if (build + sell) > 0 else 0.5
    return {
        "build_score": build,
        "sell_score": sell,
        "balance_ratio": ratio,
        "assessment": "building" if ratio > 0.6 else "selling" if ratio < 0.4 else "balanced"
    }
```

### The Convergence Score (Cross-Domain Amplification)

From your INTEGRATION_FRAMEWORK.md — when AI, Cloud/Payments, and Sustainability signals converge on the same company:

```
Convergence Score = base_coherence × domain_multiplier

Where domain_multiplier:
  1 domain  → 1.0x (no amplification)
  2 domains → 1.5x (emerging convergence)
  3 domains → 2.5x (full convergence — highest alpha)
```

Companies in the convergence zone (Persefoni, Databricks, Stripe) get amplified scores because the information arbitrage is structurally larger — analysts cover them in vertical silos.

---

## Database Schema Extensions

The current 12-table schema supports this natively. Key additions:

```sql
-- New instrument types (already supported in CHECK constraint)
-- type IN ('stock','private','etf','crypto')

-- New signal_types for private company collectors:
-- 'github_activity', 'job_posting', 'web_traffic', 'patent_filing'

-- New signal_types for crypto collectors:
-- 'token_ohlcv', 'tvl_metric', 'onchain_activity', 'governance_vote'

-- New domain values in mosaics/theses:
-- 'public_markets', 'private_markets', 'crypto', 'convergence_zone'
```

No schema migration needed — the existing `signal_type TEXT` and `domain TEXT` columns are freeform.

---

## Implementation Priority (First Principles)

**Principle: Start with the highest signal-to-noise ratio collectors.**

### Phase 1: GitHub + CoinGecko (Week 1)
- Highest quality free data
- GitHub: direct proxy for engineering velocity of private companies
- CoinGecko: OHLCV equivalent for crypto, free API
- Both follow the existing BaseCollector pattern exactly

### Phase 2: DeFi Llama + Job Posting Proxy (Week 2)
- TVL is the fundamental metric for DeFi
- Job postings reveal anchor clients and build/sell balance
- LinkedIn scraping may need proxy; start with Google Jobs API

### Phase 3: On-Chain + Web Traffic + Patents (Week 3-4)
- Deeper mosaic fragments
- Etherscan for on-chain signals
- SimilarWeb is paid — start with Google Trends as proxy
- USPTO for patent filings

### Phase 4: Scoring Engines (Week 4)
- Naval Build vs. Sell score
- Anchor Client score
- Convergence score (AI × Cloud × Sustainability)
- Modify pipeline.py to compute domain-specific scores

---

## The Daily Batch Workflow (From Gemini Conversation → Implemented)

Your Gemini conversation identified the right architecture: **daily batch with morning HITL review.** This is exactly what we built:

```
CURRENT WORKFLOW (already working):
  python -m social_arb.cli collect    # Batch pull signals
  python -m social_arb.cli analyze    # Compute mosaics + theses
  python -m social_arb.cli review     # HITL morning review
  python -m social_arb.cli status     # Portfolio overview

EXTENDED WORKFLOW (same commands, more collectors):
  python -m social_arb.cli collect --sources yfinance,reddit,sec_edgar,github,coingecko,defillama
  python -m social_arb.cli analyze --domains public,private,crypto
  python -m social_arb.cli review     # Now shows private + crypto theses too
  python -m social_arb.cli status     # Shows all three domains
```

The CLI architecture scales naturally. Adding a new domain = adding collectors + registering them in cli.py.

---

## Key Insight: What Gemini Missed

The Gemini conversation proposed three separate architectures (Morning Briefing, Anchor Client Network, Naval Matrix). But with first-principles thinking, these aren't alternatives — **they're all layers of the same topology:**

- Morning Briefing → L1 (Signal Radar) + L2 (Mosaic Assembly)
- Anchor Client Network → L2 (Mosaic Assembly) + L3 (Thesis Forge)
- Naval Matrix → L3 (Thesis Forge) + L4 (Lifecycle Monitor)

Your 5-layer topology already unifies them. The Gemini conversation was reinventing what Camillo's architecture already solves — you just need more collectors feeding into Layer 1, and domain-specific scoring in Layer 2-3.

---

## Crypto-Specific Considerations

### Position Sizing Adjustment
Crypto volatility is 3-5x equity volatility. The Kelly Criterion needs a safety factor adjustment:

```python
# Public markets: safety_factor = 0.25 (quarter Kelly)
# Crypto: safety_factor = 0.10 (tenth Kelly)
# Private: kelly not applicable — use fixed allocation % of angel budget
```

### Lifecycle Model for Crypto
```
Gold Rush (Public Markets):     Emerging → Validating → Confirmed → Saturated
Protocol Lifecycle (Crypto):    Launch → Adoption → Maturity → Fork/Compete
Funding Lifecycle (Private):    Seed → Series A → Growth → Pre-IPO/M&A
```

All three map to the same 4-stage topology (L4). The stages have different names and different signal sources, but the decision logic is identical: enter early, exit before saturation.

---

## Summary: What to Build Next

| Priority | Collector | Domain | Data Source | Cost | Signal Quality |
|----------|-----------|--------|-------------|------|----------------|
| 1 | `github_collector.py` | Private | GitHub API | Free | HIGH |
| 2 | `coingecko_collector.py` | Crypto | CoinGecko API | Free | HIGH |
| 3 | `defillama_collector.py` | Crypto | DeFi Llama API | Free | HIGH |
| 4 | `onchain_collector.py` | Crypto | Etherscan API | Free tier | MEDIUM |
| 5 | `jobs_collector.py` | Private | Google Jobs/proxy | Free | MEDIUM |
| 6 | `patent_collector.py` | Private | USPTO API | Free | MEDIUM |
| 7 | `traffic_collector.py` | Private | SimilarWeb | Paid | HIGH |

All follow the existing `BaseCollector` pattern. Zero architecture changes needed.
