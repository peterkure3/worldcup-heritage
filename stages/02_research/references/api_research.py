import os
import json
import httpx
from pathlib import Path
from datetime import datetime

API_BASE = "https://api.football-data.org/v4"
API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY")
OUTPUT = Path(__file__).parent.parent / "output" / "api_research"
OUTPUT.mkdir(parents=True, exist_ok=True)

headers = {"X-Auth-Token": API_KEY}
client = httpx.Client(headers=headers, base_url=API_BASE)


def dump(name: str, data: dict | list) -> None:
    path = OUTPUT / f"{name}.json"
    path.write_text(json.dumps(data, indent=2, default=str))
    print(f"  wrote {path}")


def fetch(url: str) -> dict | list:
    resp = client.get(url)
    print(f"  GET {url} -> {resp.status_code}")
    resp.raise_for_status()
    remaining = resp.headers.get("X-Requests-Available-Minute", "?")
    print(f"    remaining requests: {remaining}")
    return resp.json()


def main():
    print("=== 1. List all competitions (look for WC) ===")
    comps = fetch("/competitions")
    for c in comps.get("competitions", []):
        if c["code"] in ("WC", "EC", "CL"):
            dump(f"competition_{c['code']}", c)

    print("\n=== 2. Fetch World Cup metadata ===")
    wc = fetch("/competitions/WC")
    dump("competition_WC_full", wc)

    print("\n=== 3. Fetch seasons for WC ===")
    available_seasons = [s["startDate"][:4] for s in wc.get("seasons", [])]
    print(f"  seasons: {available_seasons}")
    (OUTPUT / "seasons.txt").write_text("\n".join(available_seasons))

    print("\n=== 4. Fetch matches for a few historical tournaments ===")
    seasons_to_fetch = available_seasons  # all of them
    for season in available_seasons:
        print(f"\n  --- {season} ---")
        try:
            data = fetch(f"/competitions/WC/matches?season={season}")
            matches = data.get("matches", [])
            print(f"    {len(matches)} matches")
            # Lazy: each season is small enough to keep one file
            dump(f"matches_{season}", data)
        except Exception as e:
            print(f"    SKIP: {e}")

    print("\n=== 5. Schema coverage analysis ===")
    schemas = {
        "competition_keys": set(),
        "season_keys": set(),
        "match_keys": set(),
        "team_keys": set(),
        "score_keys": set(),
    }
    match_count = 0
    for f in OUTPUT.glob("matches_*.json"):
        if f.name == "matches_2026.json":
            continue  # future tournament, partial data
        data = json.loads(f.read_text())
        if "competition" in data:
            schemas["competition_keys"].update(data["competition"].keys())
        for m in data.get("matches", []):
            match_count += 1
            schemas["match_keys"].update(m.keys())
            if "homeTeam" in m:
                schemas["team_keys"].update(m["homeTeam"].keys())
            if "score" in m:
                schemas["score_keys"].update(m["score"].keys())

    print(f"\n  Total historical matches examined: {match_count}")
    print(f"  Competition keys: {sorted(schemas['competition_keys'])}")
    print(f"  Season keys:      XXX (extracted inline)")
    print(f"  Match keys:       {sorted(schemas['match_keys'])}")
    print(f"  Team keys:        {sorted(schemas['team_keys'])}")
    print(f"  Score keys:       {sorted(schemas['score_keys'])}")

    # null analysis on match fields
    print("\n=== 6. Null-field analysis (top-level match fields) ===")
    null_counts: dict[str, int] = {}
    field_count = 0
    for f in OUTPUT.glob("matches_*.json"):
        if f.name == "matches_2026.json":
            continue
        data = json.loads(f.read_text())
        for m in data.get("matches", []):
            field_count += 1
            for k in schemas["match_keys"]:
                v = m.get(k)
                if v is None or (isinstance(v, list) and len(v) == 0):
                    null_counts[k] = null_counts.get(k, 0) + 1

    if field_count:
        for k in sorted(null_counts.keys(), key=lambda x: null_counts[x], reverse=True):
            pct = null_counts[k] / field_count * 100
            if pct > 20:
                print(f"  {k}: {null_counts[k]}/{field_count} null/empty ({pct:.0f}%)")

    print("\n=== 7. Stage distribution ===")
    stage_counts = {}
    for f in OUTPUT.glob("matches_*.json"):
        if f.name == "matches_2026.json":
            continue
        data = json.loads(f.read_text())
        for m in data.get("matches", []):
            stage = m.get("stage", "UNKNOWN")
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
    for s, c in sorted(stage_counts.items()):
        print(f"  {s}: {c}")

    print(f"\nDone. All outputs in {OUTPUT}")


if __name__ == "__main__":
    main()
