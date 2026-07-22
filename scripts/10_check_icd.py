import json
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

d = json.load(open('databases/icd10_vn/icd10_database.json', 'r', encoding='utf-8'))
codes = list(d['codes'].values())[:5]
for c in codes:
    print(f"{c['code']}: vi={c.get('name_vi','')[:40]} en={c.get('name_en','')[:40]}")

# Check search_text
print("\n--- search_text samples ---")
for c in codes:
    print(f"  {c['code']}: {c.get('search_text','')[:80]}")
