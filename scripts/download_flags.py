import json
import urllib.request
import os

with open('D:\\Github\\worldcup-heritage\\tmp_teams.json', encoding='utf-8') as f:
    teams_data = json.load(f)
teams = teams_data['teams']

flags_dir = 'D:\\Github\\worldcup-heritage\\frontend\\public\\flags'
os.makedirs(flags_dir, exist_ok=True)

for t in teams:
    name = t['name_en']
    iso2 = t.get('iso2', '').lower()
    if not iso2:
        print(f"SKIP {name}: no iso2")
        continue
    url = f"https://flagcdn.com/{iso2}.svg"
    path = os.path.join(flags_dir, f"{iso2}.svg")
    if os.path.exists(path):
        print(f"EXISTS {name} ({iso2})")
        continue
    try:
        urllib.request.urlretrieve(url, path)
        print(f"OK {name} ({iso2})")
    except Exception as e:
        print(f"FAIL {name} ({iso2}): {e}")

print(f"\nDone. Flags in {flags_dir}")
