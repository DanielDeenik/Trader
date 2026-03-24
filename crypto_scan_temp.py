import sys, os
os.environ['TMPDIR'] = '/sessions/wonderful-loving-ritchie/mnt/Trader'
sys.path.insert(0, '/sessions/wonderful-loving-ritchie/mnt/Trader/Social_Arb')
from services.shared.camillo_ideas import get_ideas, init_ideas_db
init_ideas_db()
existing = get_ideas(instrument_type='crypto', limit=50)
print(f'Existing crypto ideas: {len(existing)}')
for i in existing:
    print(f'  {i["ticker"]}: {i["camillo_grade"]} ({i["camillo_score"]}) - {i["stage"]}')
