"""
Crypto Scan — 2026-03-11
Run this script to store results into the Camillo Ideas DB.
VM disk was full at scan time; execute manually to persist.
"""
import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 'Social_Arb')
from services.shared.camillo_ideas import store_idea, CamilloIdea, log_scan, init_ideas_db

init_ideas_db()

# ── Signal 1: GRASS (Wynd Network) ──────────────────────────────
# DePIN × AI data infrastructure. Price $0.34, surged 38% on revenue news.
# Top-3 DePIN by revenue (~$33M). 2.5M active devices. Solana-based.
# Revenue-driven re-rating underway while price still beaten down.
idea1 = CamilloIdea(
    instrument_type='crypto',
    ticker='GRASS',
    name='Grass (Wynd Network)',
    stage='signal',
    signal_source='web',
    signal_description='GRASS surged 38% on Mar 3 after data showed it as top-3 DePIN by revenue (~$33M). '
        '2.5M active devices contributing bandwidth for AI training data. Price at $0.34, well off highs. '
        'Real revenue + beaten-down price = classic Camillo divergence.',
    signal_date='2026-03-11',
    thesis='AI model training creates insatiable demand for structured web data. Grass monetises idle bandwidth '
        'to feed this pipeline — real revenue, not token emissions. Market still prices it as speculative DePIN '
        'while revenue fundamentals are inflecting.',
    narrative='DePIN × AI Data',
    c1_organic=0.65,       # Revenue data from DePINScan, not influencer pumps
    c2_velocity=0.70,      # 38% surge on fundamentals, growing DePIN revenue rankings
    c3_crossplatform=0.50, # CoinMarketCap, DePINScan, Messari — moderate breadth
    c4_premainstream=0.50, # Known in DePIN circles but not mainstream CT focus
    c5_pricetotrend=0.75,  # $0.34 vs growing $33M revenue — strong divergence
    c6_category=0.70,      # Consumer-facing (passive bandwidth contribution)
    c7_demographic=0.50,   # Passive income appeal, but still crypto-native users
    c8_timing=0.60,        # Just had revenue catalyst, AI narrative strengthening
    confidence=0.60,
)

# ── Signal 2: HNT (Helium) ──────────────────────────────────────
# DePIN wireless/mobile. $24M monthly revenue Jan 2026. 1.2M daily users.
# 100% subscriber revenue → HNT buybacks. Real deflationary pressure.
idea2 = CamilloIdea(
    instrument_type='crypto',
    ticker='HNT',
    name='Helium',
    stage='signal',
    signal_source='web',
    signal_description='Helium hit $24M monthly revenue in Jan 2026. Carrier offload revenue +53% QoQ in Q4 2025. '
        '1.2M daily users, 113K hotspots. 100% subscriber revenue routed to HNT buybacks since Aug 2025 — '
        'real deflationary tokenomics tied to usage. HNT surged 31% in recent DePIN rally.',
    signal_date='2026-03-11',
    thesis='Helium is the clearest DePIN revenue story — real carrier offload fees from T-Mobile partnership, '
        'not just token incentives. The 100% revenue-to-buyback model creates genuine demand pressure. '
        'Most DePIN tokens lack this direct revenue-to-token link.',
    narrative='DePIN Wireless',
    c1_organic=0.70,       # Messari quarterly reports, carrier offload data
    c2_velocity=0.60,      # 31% surge, steady coverage increase
    c3_crossplatform=0.60, # Messari, DePINScan, Solana Floor, CoinMarketCap
    c4_premainstream=0.30, # Well-known project, analysts cover it heavily
    c5_pricetotrend=0.55,  # Revenue growing but market somewhat aware
    c6_category=0.80,      # Consumer mobile service — very accessible
    c7_demographic=0.60,   # Mobile users, not just crypto natives
    c8_timing=0.50,        # Steady trajectory, no single catalyst
    confidence=0.55,
)

# ── Signal 3: RENDER ────────────────────────────────────────────
# GPU compute for AI/3D. Price $1.51, severely beaten down.
# Migrated to Solana, integrated into Octane 2026 toolsets.
# AI compute demand is structural but token hasn't repriced.
idea3 = CamilloIdea(
    instrument_type='crypto',
    ticker='RENDER',
    name='Render Network',
    stage='signal',
    signal_source='web',
    signal_description='RENDER at $1.51, dramatically below previous highs. Successfully migrated to Solana. '
        'Integrated into 2026 Octane toolsets for commercial media production. AI compute demand is '
        'structural and growing but token is in deep drawdown. Fear & Greed at 10-19.',
    signal_date='2026-03-11',
    thesis='AI compute demand is a multi-year structural trend. Render provides decentralised GPU access '
        'for 3D rendering and ML inference. Commercial integrations (Octane) prove utility. At $1.51, '
        'price-to-utility divergence is extreme if AI compute demand continues accelerating.',
    narrative='AI Compute / DePIN',
    c1_organic=0.55,       # Commercial integrations are organic, but coverage is broad
    c2_velocity=0.40,      # Price depressed, no recent surge
    c3_crossplatform=0.50, # Known across AI-crypto coverage
    c4_premainstream=0.25, # Very well-known project
    c5_pricetotrend=0.75,  # Extreme price drawdown vs growing utility
    c6_category=0.60,      # Creative/developer focused
    c7_demographic=0.40,   # Niche: 3D artists, AI developers
    c8_timing=0.55,        # Fear & Greed at historic lows, potential bottom
    confidence=0.50,
)

# ── Signal 4: ONDO (Ondo Finance) ───────────────────────────────
# RWA tokenization leader. TVL >$2.5B. Approved for tokenized stocks in 30 EEA markets.
# RWA sector delivered 185.8% avg returns in 2025. $260B on-chain heading into 2026.
idea4 = CamilloIdea(
    instrument_type='crypto',
    ticker='ONDO',
    name='Ondo Finance',
    stage='signal',
    signal_source='web',
    signal_description='Ondo TVL surpassed $2.5B in Jan 2026. Approved for tokenized US stocks/ETFs in 30 EEA '
        'markets (500M+ potential investors). RWA sector tokenized assets tripled to ~$18.6B in 2025. '
        'CLARITY Act expected to pass in 2026, deepening TradFi-crypto integration.',
    signal_date='2026-03-11',
    thesis='RWA tokenization is the bridge narrative between TradFi and crypto. Ondo leads with real TVL '
        'and regulatory approvals. CLARITY Act passage would be a major catalyst. However, already '
        'well-covered by analysts — limited information asymmetry remains.',
    narrative='RWA Tokenization',
    c1_organic=0.50,       # Institutional product, well-documented
    c2_velocity=0.50,      # Steady growth, not explosive mentions
    c3_crossplatform=0.55, # Multiple DeFi platforms, news outlets
    c4_premainstream=0.25, # Very well-known, analysts cover extensively
    c5_pricetotrend=0.40,  # $2.5B TVL likely already priced in
    c6_category=0.45,      # More institutional than consumer
    c7_demographic=0.55,   # TradFi crossover appeal
    c8_timing=0.55,        # CLARITY Act catalyst pending
    confidence=0.45,
)

# ── Store all qualifying ideas ──────────────────────────────────
ideas = [idea1, idea2, idea3, idea4]
stored = 0
for idea in ideas:
    score = idea.camillo_score
    grade = idea.camillo_grade
    print(f"  {idea.ticker}: score={score}, grade={grade}")
    if score >= 40:
        idea_id = store_idea(idea)
        print(f"    → Stored as idea #{idea_id}")
        stored += 1
    else:
        print(f"    → Skipped (below threshold)")

# ── Log the scan ────────────────────────────────────────────────
log_scan('crypto-scan', 'crypto', searches=7, facts_found=12,
         ideas_created=stored, ideas_updated=0,
         top_signal='GRASS — $33M revenue DePIN, price divergence at $0.34',
         summary='7 searches across DePIN, AI×crypto, Solana DeFi, RWA, narratives. '
                 f'4 signals scored, {stored} stored. Market in extreme fear (F&G 10-19) '
                 'with dense catalyst calendar (FOMC, BTC 20M coin, CLARITY Act).')
print("Scan logged successfully")
