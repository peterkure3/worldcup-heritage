import os
import json
import csv
import httpx
import pandas as pd
from pathlib import Path

API_BASE = "https://api.football-data.org/v4"
API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY")
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
FJELSTUL_DIR = RAW_DIR / "worldcup-master" / "data-csv"


def fetch_2026_matches() -> pd.DataFrame:
    headers = {"X-Auth-Token": API_KEY}
    resp = httpx.get(f"{API_BASE}/competitions/WC/matches?season=2026", headers=headers)
    resp.raise_for_status()
    data = resp.json()

    rows = []
    for m in data["matches"]:
        rows.append({
            "match_id": m["id"],
            "season": 2026,
            "utc_date": m["utcDate"],
            "status": m["status"],
            "stage": m["stage"],
            "group_name": m.get("group"),
            "matchday": m.get("matchday"),
            "home_team_id": m["homeTeam"]["id"],
            "home_team": m["homeTeam"]["name"],
            "home_team_tla": m["homeTeam"]["tla"],
            "away_team_id": m["awayTeam"]["id"],
            "away_team": m["awayTeam"]["name"],
            "away_team_tla": m["awayTeam"]["tla"],
            "home_score": m["score"]["fullTime"]["home"],
            "away_score": m["score"]["fullTime"]["away"],
            "winner": m["score"]["winner"],
        })
    return pd.DataFrame(rows)


def load_fjelstul_matches() -> pd.DataFrame:
    path = FJELSTUL_DIR / "matches.csv"
    df = pd.read_csv(path)
    df.rename(columns={
        "match_id": "fjelstul_match_id",
        "tournament_name": "tournament",
        "stage_name": "stage",
        "group_name": "group_name",
        "home_team_name": "home_team",
        "home_team_code": "home_team_tla",
        "away_team_name": "away_team",
        "away_team_code": "away_team_tla",
        "home_team_score": "home_score",
        "away_team_score": "away_score",
    }, inplace=True)

    df["home_team_id"] = pd.to_numeric(df["home_team_id"], errors="coerce").astype("Int64")
    df["away_team_id"] = pd.to_numeric(df["away_team_id"], errors="coerce").astype("Int64")
    df["winning_team"] = df["result"]
    return df


def normalize_historical(df: pd.DataFrame) -> pd.DataFrame:
    needed = {
        "tournament", "stage", "group_name", "match_date",
        "home_team", "away_team", "home_team_tla", "away_team_tla",
        "home_score", "away_score", "home_team_id", "away_team_id",
        "home_team_win", "away_team_win", "draw",
        "extra_time", "penalty_shootout", "knockout_stage",
    }
    for col in needed:
        if col not in df.columns:
            df[col] = None

    out = pd.DataFrame()
    out["match_id"] = df["fjelstul_match_id"]
    out["season"] = df["tournament"].str.extract(r"(\d{4})").astype(int)
    out["utc_date"] = df["match_date"]
    out["stage"] = df["stage"]
    out["group_name"] = df["group_name"]
    out["home_team_id"] = df["home_team_id"]
    out["home_team"] = df["home_team"]
    out["home_team_tla"] = df["home_team_tla"]
    out["away_team_id"] = df["away_team_id"]
    out["away_team"] = df["away_team"]
    out["away_team_tla"] = df["away_team_tla"]
    out["home_score"] = df["home_score"]
    out["away_score"] = df["away_score"]
    out["home_win"] = df["home_team_win"].fillna(False).astype(bool)
    out["away_win"] = df["away_team_win"].fillna(False).astype(bool)
    out["draw"] = df["draw"].fillna(False).astype(bool)
    out["extra_time"] = df["extra_time"].fillna(False).astype(bool)
    out["penalty_shootout"] = df["penalty_shootout"].fillna(False).astype(bool)
    out["knockout"] = df["knockout_stage"].fillna(False).astype(bool)
    return out


def load_teams() -> pd.DataFrame:
    path = FJELSTUL_DIR / "teams.csv"
    return pd.read_csv(path)


def load_tournaments() -> pd.DataFrame:
    path = FJELSTUL_DIR / "tournaments.csv"
    return pd.read_csv(path)


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading Fjelstul historical matches...")
    hist = load_fjelstul_matches()
    hist_norm = normalize_historical(hist)
    hist_path = RAW_DIR / "historical_matches.parquet"
    hist_norm.to_parquet(hist_path, index=False)
    print(f"  {len(hist_norm)} matches → {hist_path}")

    print("\nLoading Fjelstul teams...")
    teams = load_teams()
    teams_path = RAW_DIR / "teams.parquet"
    teams.to_parquet(teams_path, index=False)
    print(f"  {len(teams)} teams → {teams_path}")

    print("\nFetching 2026 matches from football-data.org...")
    try:
        m2026 = fetch_2026_matches()
        m2026_path = RAW_DIR / "2026_matches.parquet"
        m2026.to_parquet(m2026_path, index=False)
        print(f"  {len(m2026)} matches → {m2026_path}")

        # also save as JSON for reference
        raw = httpx.get(
            f"{API_BASE}/competitions/WC/matches?season=2026",
            headers={"X-Auth-Token": os.environ["FOOTBALL_DATA_API_KEY"]},
        ).json()
        json_path = RAW_DIR / "2026_matches_raw.json"
        json_path.write_text(json.dumps(raw, indent=2))
        print(f"  raw JSON → {json_path}")
    except Exception as e:
        print(f"  SKIP: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
