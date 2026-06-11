#!/usr/bin/env python3
import json, sys
sys.path.insert(0, "D:/Github/worldcup-heritage/sidecar")
import importlib.util
spec = importlib.util.spec_from_file_location("poller", "D:/Github/worldcup-heritage/sidecar/poller.py")
poller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(poller)

# Test name normalization
tests = [
    ("Czechia", "Czech Republic"),
    ("Bosnia-Herzegovina", "Bosnia and Herzegovina"),
    ("Cape Verde Islands", "Cape Verde"),
    ("Congo DR", "DR Congo"),
    ("Mexico", "Mexico"),
    ("Brazil", "Brazil"),
]
for inp, expected in tests:
    result = poller.normalize_name(inp)
    status = "OK" if result == expected else "FAIL"
    print(f"  {status}: '{inp}' -> '{result}' (expected '{expected}')")

# Now test the full flow with the API
import os, httpx
key = os.environ.get("FOOTBALL_DATA_API_KEY")
if key:
    headers = {"X-Auth-Token": key}
    resp = httpx.get("https://api.football-data.org/v4/competitions/WC/matches?season=2026", headers=headers, timeout=15)
    api_data = resp.json()
    matches = poller.normalize_matches(api_data)
    print(f"\nNormalized matches: {len(matches)}")
    for m in matches[:5]:
        print(f"  ID {m['match_id']}: {m['home_team']} vs {m['away_team']} [{m['status']}] score=({m['home_score']},{m['away_score']})")

    # Test standings update
    with open("D:/Github/worldcup-heritage/artifacts/groups.json") as f:
        groups_data = json.load(f)
    updated = poller.update_standings(matches, groups_data)
    grp_a = next(g for g in updated["groups"] if g["name"] == "A")
    print(f"\nGroup A after update:")
    for s in grp_a["standings"]:
        print(f"  {s['team_name']}: P={s['played']} W={s['won']} D={s['drawn']} L={s['lost']} GF={s['goals_for']} GA={s['goals_against']} Pts={s['points']}")
