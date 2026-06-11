import json
from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent.parent / "artifacts"

INITIAL_ELO = 1500.0
K_FACTOR = 32
HOME_ADVANTAGE = 100


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


MEN_WC_SEASONS = {1930, 1934, 1938, 1950, 1954, 1958, 1962, 1966, 1970, 1974, 1978, 1982, 1986, 1990, 1994, 1998, 2002, 2006, 2010, 2014, 2018, 2022}


def compute_elo(hist: pd.DataFrame) -> pd.DataFrame:
    elo = {}
    records = []

    hist = hist[hist["season"].isin(MEN_WC_SEASONS)]
    matches = hist.sort_values("utc_date").reset_index(drop=True)

    for _, row in matches.iterrows():
        home = row["home_team"]
        away = row["away_team"]

        if home not in elo:
            elo[home] = INITIAL_ELO
        if away not in elo:
            elo[away] = INITIAL_ELO

        home_rating = elo[home] + HOME_ADVANTAGE
        away_rating = elo[away]

        e_home = expected_score(home_rating, away_rating)
        e_away = 1.0 - e_home

        if row["home_win"]:
            s_home, s_away = 1.0, 0.0
        elif row["away_win"]:
            s_home, s_away = 0.0, 1.0
        else:
            s_home, s_away = 0.5, 0.5

        elo[home] += K_FACTOR * (s_home - e_home)
        elo[away] += K_FACTOR * (s_away - e_away)

        records.append({
            "utc_date": row["utc_date"],
            "match_id": row["match_id"],
            "home_team": home,
            "away_team": away,
            "home_elo_before": elo[home] - K_FACTOR * (s_home - e_home),
            "away_elo_before": elo[away] - K_FACTOR * (s_away - e_away),
            "home_elo_after": elo[home],
            "away_elo_after": elo[away],
        })

    return pd.DataFrame(records)


TEAM_NAME_MAP = {
    "DR Congo": "Zaire",
    "Curaçao": "Curacao",
}


def load_groups_teams() -> list[dict]:
    path = ARTIFACTS_DIR / "groups.json"
    with open(path) as f:
        data = json.load(f)
    teams = []
    for g in data["groups"]:
        for t in g["standings"]:
            teams.append({
                "name": t["team_name"],
                "normalized": TEAM_NAME_MAP.get(t["team_name"], t["team_name"]),
            })
    return teams


def build_elo_form_values(elo_df: pd.DataFrame, target_teams: list[dict]) -> dict:
    hist_elos = {}
    for _, row in elo_df.iterrows():
        for team_col, elo_col in [("home_team", "home_elo_after"), ("away_team", "away_elo_after")]:
            hist_elos[row[team_col]] = row[elo_col]

    ratings = np.array(list(hist_elos.values()))
    lo, hi = float(ratings.min()), float(ratings.max())
    default_elo = float(np.percentile(ratings, 10))

    result = {}
    for team_info in target_teams:
        group_name = team_info["name"]
        hist_name = team_info["normalized"]
        elo_val = hist_elos.get(hist_name, default_elo)

        norm = (elo_val - lo) / (hi - lo) if hi > lo else 0.5
        norm = max(0.0, min(1.0, norm))

        result[group_name] = {
            "form_gf": round(0.5 + norm * 2.0, 2),
            "form_ga": round(2.2 - norm * 1.5, 2),
            "form_pts": round(0.3 + norm * 2.0, 2),
            "elo": round(elo_val, 1),
        }

    return result


def main():
    print("Loading historical matches...")
    hist = pd.read_parquet(RAW_DIR / "historical_matches.parquet")
    print(f"  {len(hist)} matches")

    print("\nComputing Elo ratings...")
    elo_df = compute_elo(hist)
    print(f"  {len(elo_df)} Elo updates computed")

    final_elos = {}
    for _, row in elo_df.sort_values("utc_date").iterrows():
        final_elos[row["home_team"]] = row["home_elo_after"]
        final_elos[row["away_team"]] = row["away_elo_after"]

    top10 = sorted(final_elos.items(), key=lambda x: -x[1])[:10]
    print(f"\nTop 10 teams by Elo:")
    for team, elo_val in top10:
        print(f"  {team}: {elo_val:.1f}")

    print("\nMapping Elo to form values for 2026 teams...")
    target_teams = load_groups_teams()
    print(f"  {len(target_teams)} target teams from groups.json")

    form_values = build_elo_form_values(elo_df, target_teams)
    print(f"  {len(form_values)} teams mapped")

    out_path = ARTIFACTS_DIR / "predictions" / "elo_form_values.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(form_values, indent=2, default=str))
    print(f"\nSaved -> {out_path}")

    matched = sum(1 for t in target_teams if t["name"] in form_values)
    print(f"  {matched}/{len(target_teams)} teams matched by name")

    print("\nDone.")


if __name__ == "__main__":
    main()
