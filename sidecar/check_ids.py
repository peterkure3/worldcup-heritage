#!/usr/bin/env python3
import json, httpx, os

# Load groups
with open("D:/Github/worldcup-heritage/artifacts/groups.json") as f:
    groups = json.load(f)

# Get team names from groups
group_teams = set()
for g in groups["groups"]:
    for s in g["standings"]:
        group_teams.add(s["team_name"])

# Get team names from API
key = os.environ.get("FOOTBALL_DATA_API_KEY")
headers = {"X-Auth-Token": key}
resp = httpx.get("https://api.football-data.org/v4/competitions/WC/matches?season=2026", headers=headers, timeout=15)
api_data = resp.json()

api_teams = set()
for m in api_data["matches"]:
    if m["homeTeam"]["name"]:
        api_teams.add(m["homeTeam"]["name"])
    if m["awayTeam"]["name"]:
        api_teams.add(m["awayTeam"]["name"])

# Find mismatches
print("Teams in groups.json but NOT in API:")
for t in sorted(group_teams - api_teams):
    print(f"  '{t}'")

print("\nTeams in API but NOT in groups.json:")
for t in sorted(api_teams - group_teams):
    print(f"  '{t}'")
