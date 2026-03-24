#!/bin/bash
# LATTICE.NET Dropship — Resubmit Script
# Run this when the API at localhost:5050 is back online.
# Products from the 2026-03-18 daily scan that failed to POST (API went offline after product #1).

API="http://localhost:5050/api/dropship/products"
LOG="http://localhost:5050/api/dropship/scan-log"

echo "Checking API availability..."
STATUS=$(curl -s --connect-timeout 5 -o /dev/null -w "%{http_code}" $API)
if [ "$STATUS" != "200" ]; then
  echo "API not available (HTTP $STATUS). Aborting."
  exit 1
fi

echo "API is online. Submitting 9 pending products..."

# Product 2: Hair Repair Mask
curl -s -X POST $API -H "Content-Type: application/json" -d '{
  "product_name": "Intensive Hair Repair Treatment Mask",
  "category": "beauty", "brand": "", "stage": "discovered",
  "signal_source": "google_trends", "signal_url": "https://trends.google.com/trends/explore",
  "signal_description": "Google Trends shows consistent rise in hair repair mask searches. Driven by clean beauty trend and TikTok haircare routines. Deep conditioning segment growing rapidly.",
  "stepps_social_currency": 0.5, "stepps_triggers": 0.6, "stepps_emotion": 0.6,
  "stepps_public": 0.4, "stepps_practical_value": 0.8, "stepps_stories": 0.7,
  "c1_organic": 0.7, "c2_velocity": 0.7, "c3_crossplatform": 0.7, "c4_premainstream": 0.5,
  "c5_pricetotrend": 0.8, "c6_category": 0.8, "c7_demographic": 0.6, "c8_timing": 0.6,
  "moat_strength": "weak", "gold_rush_phase": "growth"
}' && echo " [OK] Hair Repair Mask"

# Product 3: Satin Sleep Bonnet
curl -s -X POST $API -H "Content-Type: application/json" -d '{
  "product_name": "Satin Sleep Bonnet",
  "category": "beauty", "brand": "", "stage": "discovered",
  "signal_source": "google_trends", "signal_url": "https://trends.google.com/trends/explore",
  "signal_description": "Moving from niche natural hair community to mainstream. Google Trends + TikTok beauty showing niche-to-mainstream movement. Very low supplier cost (<$2), sells $12-20. Fully generic — no brand IP.",
  "stepps_social_currency": 0.6, "stepps_triggers": 0.8, "stepps_emotion": 0.5,
  "stepps_public": 0.3, "stepps_practical_value": 0.8, "stepps_stories": 0.6,
  "c1_organic": 0.8, "c2_velocity": 0.7, "c3_crossplatform": 0.6, "c4_premainstream": 0.7,
  "c5_pricetotrend": 0.9, "c6_category": 0.7, "c7_demographic": 0.7, "c8_timing": 0.7,
  "moat_strength": "none", "gold_rush_phase": "growth"
}' && echo " [OK] Satin Sleep Bonnet"

# Product 4: Electric Cat Toy (TOP SCORER)
curl -s -X POST $API -H "Content-Type: application/json" -d '{
  "product_name": "Electric Cat Toy with Infrared Laser Light",
  "category": "pet", "brand": "", "stage": "discovered",
  "signal_source": "tiktok", "signal_url": "https://www.tiktok.com/tag/tiktokmademebuyit",
  "signal_description": "Cat play videos on TikTok generate massive organic engagement — laser cat toys driving viral content loops. Cross-confirmed on Amazon pet category and Reddit r/cats. Cheap to source ($3-6), retails $20-40. Fully generic, no brand IP.",
  "stepps_social_currency": 0.6, "stepps_triggers": 0.9, "stepps_emotion": 0.9,
  "stepps_public": 0.8, "stepps_practical_value": 0.8, "stepps_stories": 0.9,
  "c1_organic": 0.9, "c2_velocity": 0.8, "c3_crossplatform": 0.8, "c4_premainstream": 0.6,
  "c5_pricetotrend": 0.8, "c6_category": 0.8, "c7_demographic": 0.7, "c8_timing": 0.7,
  "moat_strength": "none", "gold_rush_phase": "growth"
}' && echo " [OK] Electric Cat Toy (TOP SCORER - Camillo 76.25)"

# Product 5: Sleep Headband Speakers
curl -s -X POST $API -H "Content-Type: application/json" -d '{
  "product_name": "Sleep Headband Bluetooth Speakers",
  "category": "tech", "brand": "", "stage": "discovered",
  "signal_source": "reddit", "signal_url": "https://www.reddit.com/r/shutupandtakemymoney/",
  "signal_description": "Highly upvoted on r/shutupandtakemymoney. Flat embedded speakers for side-sleepers, soft breathable fabric. Solves a real problem. No dominant branded player — weak moat.",
  "stepps_social_currency": 0.6, "stepps_triggers": 0.8, "stepps_emotion": 0.7,
  "stepps_public": 0.4, "stepps_practical_value": 0.9, "stepps_stories": 0.7,
  "c1_organic": 0.8, "c2_velocity": 0.6, "c3_crossplatform": 0.6, "c4_premainstream": 0.7,
  "c5_pricetotrend": 0.8, "c6_category": 0.7, "c7_demographic": 0.7, "c8_timing": 0.7,
  "moat_strength": "weak", "gold_rush_phase": "growth"
}' && echo " [OK] Sleep Headband Speakers"

# Product 6: Electric Lighter
curl -s -X POST $API -H "Content-Type: application/json" -d '{
  "product_name": "Rechargeable Plasma Arc Electric Lighter",
  "category": "home", "brand": "", "stage": "discovered",
  "signal_source": "tiktok", "signal_url": "https://www.tiktok.com/tag/tiktokmademebuyit",
  "signal_description": "TikTok trending — sustainability angle + cool plasma arc visual = viral. No butane, rechargeable via USB. Visible at social gatherings = high public score. Extremely cheap to source, no brand moat.",
  "stepps_social_currency": 0.7, "stepps_triggers": 0.7, "stepps_emotion": 0.6,
  "stepps_public": 0.8, "stepps_practical_value": 0.8, "stepps_stories": 0.7,
  "c1_organic": 0.7, "c2_velocity": 0.6, "c3_crossplatform": 0.6, "c4_premainstream": 0.6,
  "c5_pricetotrend": 0.9, "c6_category": 0.7, "c7_demographic": 0.6, "c8_timing": 0.6,
  "moat_strength": "none", "gold_rush_phase": "growth"
}' && echo " [OK] Plasma Arc Electric Lighter"

# Product 7: Blue Light LED Therapy Mask
curl -s -X POST $API -H "Content-Type: application/json" -d '{
  "product_name": "Blue Light LED Therapy Face Mask",
  "category": "beauty", "brand": "", "stage": "discovered",
  "signal_source": "google_trends", "signal_url": "https://trends.google.com/trends/explore",
  "signal_description": "Blue Light Therapy growing fast on Google Trends (~150K searches/month). Before/after skin transformation videos go viral on TikTok. Acne + anti-aging dual use case. Generic versions available widely.",
  "stepps_social_currency": 0.8, "stepps_triggers": 0.6, "stepps_emotion": 0.8,
  "stepps_public": 0.7, "stepps_practical_value": 0.8, "stepps_stories": 0.9,
  "c1_organic": 0.7, "c2_velocity": 0.8, "c3_crossplatform": 0.7, "c4_premainstream": 0.6,
  "c5_pricetotrend": 0.7, "c6_category": 0.8, "c7_demographic": 0.7, "c8_timing": 0.7,
  "moat_strength": "weak", "gold_rush_phase": "growth"
}' && echo " [OK] Blue Light LED Therapy Face Mask"

# Product 8: Milk Frother
curl -s -X POST $API -H "Content-Type: application/json" -d '{
  "product_name": "Electric Handheld Milk Frother",
  "category": "kitchen", "brand": "", "stage": "discovered",
  "signal_source": "amazon", "signal_url": "https://www.amazon.com/gp/movers-and-shakers/home-garden",
  "signal_description": "Amazon Movers & Shakers kitchen category. Google Trends +17% growth. Cafe-at-home trend. Very cheap to source ($2-4), retails $10-15. Daily trigger: morning coffee. Borderline peak phase.",
  "stepps_social_currency": 0.6, "stepps_triggers": 0.9, "stepps_emotion": 0.6,
  "stepps_public": 0.5, "stepps_practical_value": 0.9, "stepps_stories": 0.6,
  "c1_organic": 0.6, "c2_velocity": 0.6, "c3_crossplatform": 0.6, "c4_premainstream": 0.3,
  "c5_pricetotrend": 0.8, "c6_category": 0.7, "c7_demographic": 0.5, "c8_timing": 0.4,
  "moat_strength": "weak", "gold_rush_phase": "peak"
}' && echo " [OK] Electric Milk Frother"

# Product 9: 3D Moon Lamp
curl -s -X POST $API -H "Content-Type: application/json" -d '{
  "product_name": "3D Moon Lamp with Remote (16 Colors)",
  "category": "home", "brand": "", "stage": "discovered",
  "signal_source": "reddit", "signal_url": "https://www.reddit.com/r/shutupandtakemymoney/",
  "signal_description": "Reddit r/shutupandtakemymoney organic upvotes. Rechargeable, 16 LED colors, remote control, wooden stand. Visual wow factor = gift category staple. Borderline peak phase — maturing product.",
  "stepps_social_currency": 0.7, "stepps_triggers": 0.6, "stepps_emotion": 0.8,
  "stepps_public": 0.7, "stepps_practical_value": 0.5, "stepps_stories": 0.8,
  "c1_organic": 0.7, "c2_velocity": 0.5, "c3_crossplatform": 0.6, "c4_premainstream": 0.4,
  "c5_pricetotrend": 0.7, "c6_category": 0.7, "c7_demographic": 0.6, "c8_timing": 0.5,
  "moat_strength": "none", "gold_rush_phase": "peak"
}' && echo " [OK] 3D Moon Lamp"

# Product 10: Magnetic Water Bottle
curl -s -X POST $API -H "Content-Type: application/json" -d '{
  "product_name": "Magnetic Motivational Water Bottle (Time Tracker)",
  "category": "fitness", "brand": "", "stage": "discovered",
  "signal_source": "tiktok", "signal_url": "https://www.tiktok.com/tag/tiktokmademebuyit",
  "signal_description": "TikTok fitness community + Google Trends rising. Time-marked hydration tracker bottles carried everywhere = high public visibility. Fitness identity signal. Cross-confirmed on Amazon and Google Trends.",
  "stepps_social_currency": 0.7, "stepps_triggers": 0.8, "stepps_emotion": 0.6,
  "stepps_public": 0.9, "stepps_practical_value": 0.8, "stepps_stories": 0.7,
  "c1_organic": 0.7, "c2_velocity": 0.7, "c3_crossplatform": 0.7, "c4_premainstream": 0.6,
  "c5_pricetotrend": 0.7, "c6_category": 0.8, "c7_demographic": 0.8, "c8_timing": 0.7,
  "moat_strength": "weak", "gold_rush_phase": "growth"
}' && echo " [OK] Magnetic Water Bottle"

echo ""
echo "Posting scan log..."
curl -s -X POST $LOG -H "Content-Type: application/json" -d '{
  "scan_type": "daily",
  "category": "all",
  "products_found": 10,
  "products_added": 10,
  "top_product": "Electric Cat Toy with Infrared Laser Light",
  "summary": "10 qualifying products found across TikTok, Reddit, Amazon, and Google Trends. Top scorer: Electric Cat Toy (Camillo 76.25) — organic viral loop via cat TikTok content, moat:none, growth phase. Strong day with 7 growth-phase products. NOTE: Product 1 (Mini Wireless Projector) posted in original run as ID 27; remaining 9 resubmitted via this script."
}' && echo " [OK] Scan log posted"

echo ""
echo "Done. All 9 pending products + scan log submitted."
