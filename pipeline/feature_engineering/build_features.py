import pandas as pd
import numpy as np
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
FEATURES_DIR = Path(__file__).resolve().parent.parent / "data" / "features"


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    hist = pd.read_parquet(RAW_DIR / "historical_matches.parquet")
    m2026 = pd.read_parquet(RAW_DIR / "2026_matches.parquet")
    return hist, m2026


def build_team_form(hist: pd.DataFrame, window: int = 5) -> dict:
    form = {}
    all_matches = pd.concat([
        hist[["utc_date", "home_team", "away_team", "home_score", "away_score", "home_win", "draw"]],
    ])
    all_matches = all_matches.sort_values("utc_date")

    teams = set(all_matches["home_team"]).union(set(all_matches["away_team"]))
    for team in teams:
        team_matches = []
        for _, row in all_matches.iterrows():
            if row["home_team"] == team:
                gf, ga = row["home_score"], row["away_score"]
                pts = 3 if row["home_win"] else (1 if row["draw"] else 0)
            elif row["away_team"] == team:
                gf, ga = row["away_score"], row["home_score"]
                pts = 3 if not row["home_win"] and not row["draw"] else (1 if row["draw"] else 0)
            else:
                continue
            team_matches.append({"date": row["utc_date"], "gf": gf, "ga": ga, "pts": pts})

        if len(team_matches) < 2:
            continue

        team_form_df = pd.DataFrame(team_matches).sort_values("date")
        team_form_df["rolling_gf"] = team_form_df["gf"].rolling(window, min_periods=1).mean()
        team_form_df["rolling_ga"] = team_form_df["ga"].rolling(window, min_periods=1).mean()
        team_form_df["rolling_pts"] = team_form_df["pts"].rolling(window, min_periods=1).mean()

        for _, r in team_form_df.iterrows():
            key = (team, str(r["date"]))
            form[key] = {
                "form_avg_gf": round(r["rolling_gf"], 2),
                "form_avg_ga": round(r["rolling_ga"], 2),
                "form_avg_pts": round(r["rolling_pts"], 2),
            }

    return form


def build_features(hist: pd.DataFrame, form: dict) -> pd.DataFrame:
    rows = []
    hist = hist.sort_values("utc_date").reset_index(drop=True)

    for _, match in hist.iterrows():
        home = match["home_team"]
        away = match["away_team"]
        date = str(match["utc_date"])

        home_form = form.get((home, date), {})
        away_form = form.get((away, date), {})

        h2h_matches = hist[
            ((hist["home_team"] == home) & (hist["away_team"] == away)) |
            ((hist["home_team"] == away) & (hist["away_team"] == home))
        ]
        h2h_matches = h2h_matches[h2h_matches["utc_date"] < match["utc_date"]]
        h2h_home_wins = 0
        h2h_away_wins = 0
        h2h_draws = 0
        if len(h2h_matches) > 0:
            for _, h2h in h2h_matches.iterrows():
                if h2h["home_team"] == home and h2h["home_win"]:
                    h2h_home_wins += 1
                elif h2h["away_team"] == home and h2h["away_win"]:
                    h2h_home_wins += 1
                elif h2h["home_team"] == away and h2h["home_win"]:
                    h2h_away_wins += 1
                elif h2h["away_team"] == away and h2h["away_win"]:
                    h2h_away_wins += 1
                else:
                    h2h_draws += 1
            h2h_total = h2h_home_wins + h2h_away_wins + h2h_draws
            h2h_home_rate = h2h_home_wins / h2h_total if h2h_total > 0 else 0.33
            h2h_away_rate = h2h_away_wins / h2h_total if h2h_total > 0 else 0.33
        else:
            h2h_home_rate = 0.33
            h2h_away_rate = 0.33

        rows.append({
            "match_id": match["match_id"],
            "season": match["season"],
            "home_team": home,
            "away_team": away,
            "home_form_gf": home_form.get("form_avg_gf", 1.5),
            "home_form_ga": home_form.get("form_avg_ga", 1.5),
            "home_form_pts": home_form.get("form_avg_pts", 1.5),
            "away_form_gf": away_form.get("form_avg_gf", 1.5),
            "away_form_ga": away_form.get("form_avg_ga", 1.5),
            "away_form_pts": away_form.get("form_avg_pts", 1.5),
            "h2h_home_win_rate": round(h2h_home_rate, 3),
            "h2h_away_win_rate": round(h2h_away_rate, 3),
            "h2h_draw_rate": round(1 - h2h_home_rate - h2h_away_rate, 3),
            "knockout": int(match["knockout"]),
            "target_home_win": int(match["home_win"]),
            "target_draw": int(match["draw"]),
            "target_away_win": int(match["away_win"]),
        })

    return pd.DataFrame(rows)


def build_2026_features(m2026: pd.DataFrame, form: dict) -> pd.DataFrame:
    rows = []
    for _, match in m2026.iterrows():
        home = match["home_team"]
        away = match["away_team"]
        home_form = form.get((home, "2026-06-11"), {})
        away_form = form.get((away, "2026-06-11"), {})

        rows.append({
            "match_id": match["match_id"],
            "season": 2026,
            "home_team": home,
            "away_team": away,
            "home_form_gf": home_form.get("form_avg_gf", 1.5),
            "home_form_ga": home_form.get("form_avg_ga", 1.5),
            "home_form_pts": home_form.get("form_avg_pts", 1.5),
            "away_form_gf": away_form.get("form_avg_gf", 1.5),
            "away_form_ga": away_form.get("form_avg_ga", 1.5),
            "away_form_pts": away_form.get("form_avg_pts", 1.5),
            "h2h_home_win_rate": 0.33,
            "h2h_away_win_rate": 0.33,
            "h2h_draw_rate": 0.33,
            "knockout": int(match["stage"] != "GROUP_STAGE"),
        })
    return pd.DataFrame(rows)


def main():
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading raw data...")
    hist, m2026 = load_data()
    print(f"  Historical: {len(hist)} matches")
    print(f"  2026: {len(m2026)} matches")

    print("\nBuilding team form features...")
    form = build_team_form(hist)
    print(f"  Form vectors: {len(form)}")

    print("\nBuilding feature matrix for historical matches...")
    features = build_features(hist, form)

    out_path = FEATURES_DIR / "training_features.parquet"
    features.to_parquet(out_path, index=False)
    print(f"  {len(features)} rows → {out_path}")
    print(f"  Target distribution:")
    print(f"    Home win: {features['target_home_win'].mean():.3f}")
    print(f"    Draw:     {features['target_draw'].mean():.3f}")
    print(f"    Away win: {features['target_away_win'].mean():.3f}")

    print("\nBuilding feature matrix for 2026 matches...")
    features_2026 = build_2026_features(m2026, form)
    out_path_2026 = FEATURES_DIR / "2026_features.parquet"
    features_2026.to_parquet(out_path_2026, index=False)
    print(f"  {len(features_2026)} rows → {out_path_2026}")

    print("\nDone.")


if __name__ == "__main__":
    main()
