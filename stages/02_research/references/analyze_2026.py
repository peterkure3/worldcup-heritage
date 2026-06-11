import json
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "output/api_research/matches_2026.json"
d = json.loads(p.read_text())

teams = set()
for m in d["matches"]:
    teams.add(m["homeTeam"]["name"])
    teams.add(m["awayTeam"]["name"])

stages = set(m.get("stage") for m in d["matches"])
groups = set(m.get("group") for m in d["matches"])

print(f"2026 World Cup Matches: {d['resultSet']['count']}")
print(f"Teams: {len(teams)}")
print(f"Stages: {sorted(stages)}")
print(f"Groups: {sorted(g for g in groups if g)}")

# Show first match as schema reference
print("\n--- Match schema keys ---")
print(list(d["matches"][0].keys()))
print("\n--- Score keys ---")
print(list(d["matches"][0]["score"].keys()))
print("\n--- HomeTeam keys ---")
print(list(d["matches"][0]["homeTeam"].keys()))
