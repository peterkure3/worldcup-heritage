#!/usr/bin/env python3
import os
import sys
import json
import time
import httpx
from pathlib import Path
from datetime import datetime, timezone

API_BASE = "https://api.football-data.org/v4"
API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY")
if not API_KEY:
    print("FOOTBALL_DATA_API_KEY is required")
    sys.exit(1)

ARTIFACTS_DIR = Path("/app/artifacts")
BACKEND_RELOAD_URL = os.environ.get(
    "BACKEND_RELOAD_URL", "http://backend:7777/api/reload"
)
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "300"))

TEAM_NAME_MAP = {
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Cape Verde Islands": "Cape Verde",
    "Congo DR": "DR Congo",
    "Czechia": "Czech Republic",
}


def fetch_matches() -> dict:
    headers = {"X-Auth-Token": API_KEY}
    resp = httpx.get(
        f"{API_BASE}/competitions/WC/matches?season=2026",
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def normalize_name(name: str) -> str:
    return TEAM_NAME_MAP.get(name, name)


def normalize_matches(api_data: dict) -> list[dict]:
    rows = []
    for m in api_data["matches"]:
        group = m.get("group", "")
        rows.append({
            "match_id": m["id"],
            "season": 2026,
            "utc_date": m["utcDate"],
            "status": m["status"],
            "stage": m["stage"],
            "group_name": group.removeprefix("GROUP_") if group else None,
            "matchday": m.get("matchday"),
            "home_team": normalize_name(m["homeTeam"]["name"]),
            "home_team_tla": m["homeTeam"]["tla"],
            "away_team": normalize_name(m["awayTeam"]["name"]),
            "away_team_tla": m["awayTeam"]["tla"],
            "home_score": m["score"]["fullTime"]["home"],
            "away_score": m["score"]["fullTime"]["away"],
            "winner": m["score"]["winner"],
        })
    return rows


def update_standings(matches: list[dict], groups_data: dict) -> dict:
    groups = {g["name"]: g for g in groups_data["groups"]}

    for group in groups.values():
        for s in group["standings"]:
            s.update(played=0, won=0, drawn=0, lost=0,
                     goals_for=0, goals_against=0, goal_diff=0, points=0)

    for m in matches:
        if m["status"] != "FINISHED":
            continue
        if m["home_score"] is None or m["away_score"] is None:
            continue

        gname = m.get("group_name")
        if not gname or gname not in groups:
            continue

        group = groups[gname]
        home = next((s for s in group["standings"] if s["team_name"] == m["home_team"]), None)
        away = next((s for s in group["standings"] if s["team_name"] == m["away_team"]), None)
        if not home or not away:
            continue

        hg, ag = m["home_score"], m["away_score"]
        home["played"] += 1
        away["played"] += 1
        home["goals_for"] += hg
        home["goals_against"] += ag
        away["goals_for"] += ag
        away["goals_against"] += hg

        if hg > ag:
            home["won"] += 1; home["points"] += 3
            away["lost"] += 1
        elif ag > hg:
            away["won"] += 1; away["points"] += 3
            home["lost"] += 1
        else:
            home["drawn"] += 1; home["points"] += 1
            away["drawn"] += 1; away["points"] += 1

    for group in groups.values():
        for s in group["standings"]:
            s["goal_diff"] = s["goals_for"] - s["goals_against"]
        group["standings"].sort(
            key=lambda s: (s["points"], s["goal_diff"], s["goals_for"]),
            reverse=True,
        )

    groups_data["groups"] = list(groups.values())
    return groups_data


def reload_backend() -> bool:
    try:
        resp = httpx.post(BACKEND_RELOAD_URL, timeout=5)
        return resp.status_code == 200
    except httpx.ConnectError:
        return False
    except Exception as e:
        print(f"  Reload error: {e}")
        return False


def main():
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] poller started (interval={POLL_INTERVAL}s)")

    while True:
        try:
            print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] fetching...")
            api_data = fetch_matches()
            matches = normalize_matches(api_data)

            raw_path = ARTIFACTS_DIR / "2026_matches_raw.json"
            raw_path.write_text(json.dumps(api_data, indent=2))

            matches_path = ARTIFACTS_DIR / "2026_matches.json"
            matches_path.write_text(json.dumps(matches, indent=2))

            finished = [m for m in matches if m["status"] == "FINISHED"]
            print(f"  {len(finished)}/{len(matches)} finished")

            if finished:
                groups_path = ARTIFACTS_DIR / "groups.json"
                if groups_path.exists():
                    groups_data = json.loads(groups_path.read_text())
                    groups_data = update_standings(matches, groups_data)
                    groups_path.write_text(json.dumps(groups_data, indent=2))
                    print(f"  standings updated")

            if reload_backend():
                print(f"  backend reloaded")
            else:
                print(f"  backend not reachable")

        except httpx.HTTPStatusError as e:
            print(f"  HTTP {e.response.status_code}")
        except Exception as e:
            print(f"  Error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
