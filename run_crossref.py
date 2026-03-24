#!/usr/bin/env python3
import sys, os
os.chdir('/sessions/practical-clever-hypatia/mnt/Trader')
sys.path.insert(0, 'Social_Arb')

from services.shared.cross_reference import cross_reference_all
import json

result = cross_reference_all()
print(result['brief'])
print(f"\nStats: {json.dumps(result['stats'], indent=2)}")

for cluster in result['entity_clusters'][:20]:
    if cluster['fact_count'] > 0 or len(cluster['idea_ids']) > 0:
        print(f"  {cluster['entity']}: {cluster['fact_count']} facts, {len(cluster['idea_ids'])} ideas, cross_pillar={cluster['cross_pillar']}")
