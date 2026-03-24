#!/usr/bin/env python3
"""Crypto scan execution script - runs outside of Bash tool temp dir constraint"""
import sys
sys.path.insert(0, '/sessions/gracious-sharp-mayer/mnt/Trader/Social_Arb')

from services.shared.camillo_ideas import get_ideas, init_ideas_db, store_idea, CamilloIdea, log_scan

# Step 1: Check existing ideas
init_ideas_db()
existing = get_ideas(instrument_type='crypto', limit=50)
print(f"Existing crypto ideas: {len(existing)}")
for i in existing:
    print(f"  {i['ticker']}: {i['camillo_grade']} ({i['camillo_score']}) - {i['stage']}")

existing_tickers = {i['ticker'] for i in existing}

ideas_created = 0

# --- SIGNAL 1: Akash Network (AKT) - DePIN AI Compute ---
# Strong signal: $4.3M ARR, real enterprise AI workloads, pre-mainstream
if 'AKT' not in existing_tickers:
    idea1 = CamilloIdea(
        instrument_type='crypto',
        ticker='AKT',
        name='Akash Network',
        stage='signal',
        signal_source='web',
        signal_description='Akash Network generated $4.3M ARR with AI workloads shifting toward longer-lived, serious deployments. Enterprise demand growing in Q1 2026. DePIN sector fees hit record $2.5M in October 2025.',
        signal_date='2026-03-11',
        thesis='AI compute demand is surging and Akash is the decentralized alternative to AWS/GCP for GPU compute. Real revenue ($4.3M ARR) and growing enterprise adoption put it ahead of most DePIN tokens on utility. Still below mainstream crypto Twitter radar.',
        narrative='DePIN x AI Compute',
        c1_organic=0.72,     # Builder/enterprise signals, not CT influencer-driven
        c2_velocity=0.60,    # Steady growth, not explosive yet
        c3_crossplatform=0.65, # Web + crypto media confirming
        c4_premainstream=0.70, # Not widely covered by analysts yet
        c5_pricetotrend=0.65,  # Price lagging behind real usage metrics
        c6_category=0.55,    # Infrastructure, not consumer-facing
        c7_demographic=0.50, # Enterprise devs entering
        c8_timing=0.70,      # AI narrative building, entry window open
        confidence=0.72,
    )
    idea1_id = store_idea(idea1)
    print(f"Stored idea #{idea1_id}: {idea1.ticker} - score={idea1.camillo_score:.1f}, grade={idea1.camillo_grade}")
    ideas_created += 1
else:
    print(f"AKT already tracked, skipping")

# --- SIGNAL 2: Hivemapper (HONEY) - DePIN Mapping ---
# $32M funding, 700M km roads mapped (37% global), real utility
if 'HONEY' not in existing_tickers:
    idea2 = CamilloIdea(
        instrument_type='crypto',
        ticker='HONEY',
        name='Hivemapper',
        stage='signal',
        signal_source='web',
        signal_description='Hivemapper mapped 700M km of roads (37% of global road infrastructure) with $32M fresh funding in 2026. Network effect compounding as more dashcams join.',
        signal_date='2026-03-11',
        thesis='Hivemapper is building a real mapping dataset that competes with Google Maps via community hardware. The 37% global road coverage is a genuine product milestone that most analysts have not connected to token value. Fresh $32M funding extends runway.',
        narrative='DePIN Physical Infrastructure',
        c1_organic=0.78,     # Dashcam hobbyists and truckers - highly organic supply side
        c2_velocity=0.62,    # Consistent growth trajectory
        c3_crossplatform=0.58, # Mostly web3 media coverage
        c4_premainstream=0.75, # Under the radar of mainstream investors
        c5_pricetotrend=0.70,  # Token price hasn't reflected 37% global road coverage milestone
        c6_category=0.65,    # Consumer hardware component adds virality
        c7_demographic=0.60, # Truck drivers and fleet operators - new crypto demographic
        c8_timing=0.68,      # Post-funding window, before next media cycle
        confidence=0.68,
    )
    idea2_id = store_idea(idea2)
    print(f"Stored idea #{idea2_id}: {idea2.ticker} - score={idea2.camillo_score:.1f}, grade={idea2.camillo_grade}")
    ideas_created += 1
else:
    print(f"HONEY already tracked, skipping")

# --- SIGNAL 3: Bittensor (TAO) - AI×Crypto Marketplace ---
# 128 active subnets, $3.44B mcap but fundamentals accelerating
if 'TAO' not in existing_tickers:
    idea3 = CamilloIdea(
        instrument_type='crypto',
        ticker='TAO',
        name='Bittensor',
        stage='signal',
        signal_source='web',
        signal_description='128 active subnets running on Bittensor as of March 2026, top AI crypto by market cap at $3.44B. Pure marketplace for AI intelligence with real validator/miner activity.',
        signal_date='2026-03-11',
        thesis='Bittensor is the clearest narrative play in AI×Crypto with actual subnet activity (128 subnets). The market has repriced it partially but institutional discovery of decentralized AI marketplaces is still early. TAO is becoming the reserve token of AI compute coordination.',
        narrative='AI x Crypto Infrastructure',
        c1_organic=0.65,     # Developer-driven, some CT hype starting
        c2_velocity=0.65,    # Subnet growth accelerating
        c3_crossplatform=0.72, # GitHub, CT, institutional research all confirming
        c4_premainstream=0.55, # Getting mainstream attention but not fully priced
        c5_pricetotrend=0.60,  # Higher market cap means less upside asymmetry
        c6_category=0.55,    # Deep infra, not consumer
        c7_demographic=0.62, # ML researchers and AI labs entering
        c8_timing=0.62,      # Window narrowing as discovery increases
        confidence=0.65,
    )
    idea3_id = store_idea(idea3)
    print(f"Stored idea #{idea3_id}: {idea3.ticker} - score={idea3.camillo_score:.1f}, grade={idea3.camillo_grade}")
    ideas_created += 1
else:
    print(f"TAO already tracked, skipping")

# --- SIGNAL 4: Ondo Finance (ONDO) - RWA Tokenization ---
# BlackRock, Franklin Templeton on-chain, $11B tokenized treasuries
if 'ONDO' not in existing_tickers:
    idea4 = CamilloIdea(
        instrument_type='crypto',
        ticker='ONDO',
        name='Ondo Finance',
        stage='signal',
        signal_source='web',
        signal_description='Tokenized US Treasuries on-chain hit $11.01B as of March 6 2026 (up 22% from $8.9B in January). Broader RWA market ex-stables at $19-36B. BlackRock, Franklin Templeton, JPMorgan all on-chain. RWA narrative forming while Fear & Greed at 11.',
        signal_date='2026-03-11',
        thesis='Ondo Finance is the leading RWA protocol with institutional-grade tokenized treasuries. The disconnect between Fear & Greed at 11 and $11B in growing tokenized treasuries is a classic Camillo arbitrage — mainstream crypto traders are missing the institutional capital flowing in. 22% TVL growth in 10 weeks during a bear market is extraordinary.',
        narrative='RWA Tokenization x Institutional DeFi',
        c1_organic=0.70,     # Institutional adoption, not retail speculation
        c2_velocity=0.72,    # 22% TVL growth in 10 weeks in bear market
        c3_crossplatform=0.68, # TradFi press + crypto confirming
        c4_premainstream=0.72, # Retail CT has not discovered the $11B TVL milestone
        c5_pricetotrend=0.75,  # Token price at extreme fear while TVL hits ATH
        c6_category=0.60,    # Financial infra, TradFi crossover demographic
        c7_demographic=0.72, # TradFi asset managers - entirely new crypto demographic
        c8_timing=0.78,      # Perfect entry: fear peak + institutional TVL ATH
        confidence=0.74,
    )
    idea4_id = store_idea(idea4)
    print(f"Stored idea #{idea4_id}: {idea4.ticker} - score={idea4.camillo_score:.1f}, grade={idea4.camillo_grade}")
    ideas_created += 1
else:
    print(f"ONDO already tracked, skipping")

# Step 4: Log the scan
top_signal = 'ONDO - RWA $11B tokenized treasuries +22% in 10 weeks during fear cycle (F&G=11)'
log_scan('crypto-scan', 'crypto', searches=5, facts_found=12,
         ideas_created=ideas_created, ideas_updated=0,
         top_signal=top_signal,
         summary=f'Scanned DePIN, AI×Crypto, Solana DeFi, developer activity, RWA. Stored {ideas_created} qualifying signals. Top signal: ONDO RWA during fear cycle.')
print(f"\nScan logged. {ideas_created} ideas created.")
print(f"Top signal: {top_signal}")
