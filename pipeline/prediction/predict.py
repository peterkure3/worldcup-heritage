import json
import random
from collections import defaultdict
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

FEATURES_DIR = Path(__file__).resolve().parent.parent / "data" / "features"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "artifacts" / "models"
PREDICTIONS_DIR = Path(__file__).resolve().parent.parent.parent / "artifacts" / "predictions"
GROUPS_PATH = Path(__file__).resolve().parent.parent.parent / "artifacts" / "groups.json"
ELO_FORM_PATH = PREDICTIONS_DIR / "elo_form_values.json"

FEATURE_COLS = [
    "home_form_gf", "home_form_ga", "home_form_pts",
    "away_form_gf", "away_form_ga", "away_form_pts",
    "h2h_home_win_rate", "h2h_away_win_rate", "h2h_draw_rate",
    "knockout",
]

GROUP_NAMES = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]

TEAM_NAME_MAP = {
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Cape Verde Islands": "Cape Verde",
    "Congo DR": "Democratic Republic of the Congo",
    "Czechia": "Czech Republic",
}

def normalize_team(name: str) -> str:
    if name in TEAM_NAME_MAP:
        return TEAM_NAME_MAP[name]
    if "Cura" in name and ("ao" in name or "\xe7" in name):
        return "Curacao"
    return name


def load_model(name: str = "xgboost_v1_tuned.joblib"):
    path = MODELS_DIR / name
    return joblib.load(path)


def load_historical_form() -> dict:
    hist = pd.read_parquet(RAW_DIR / "historical_matches.parquet")
    window = 5
    form = {}
    all_matches = hist.sort_values("utc_date")
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
        tf = pd.DataFrame(team_matches).sort_values("date")
        tf["rolling_gf"] = tf["gf"].rolling(window, min_periods=1).mean()
        tf["rolling_ga"] = tf["ga"].rolling(window, min_periods=1).mean()
        tf["rolling_pts"] = tf["pts"].rolling(window, min_periods=1).mean()
        for _, r in tf.iterrows():
            key = (team, str(r["date"]))
            form[key] = {
                "form_avg_gf": round(r["rolling_gf"], 2),
                "form_avg_ga": round(r["rolling_ga"], 2),
                "form_avg_pts": round(r["rolling_pts"], 2),
            }
    return form


def load_groups() -> list:
    with open(GROUPS_PATH) as f:
        data = json.load(f)
    groups = []
    for g in data["groups"]:
        teams = [normalize_team(t["team_name"]) for t in g["standings"]]
        groups.append({"name": g["name"], "teams": teams})
    return groups


def generate_correct_fixtures(groups: list) -> pd.DataFrame:
    rows = []
    match_id = 537327
    for g in groups:
        t = g["teams"]
        for i in range(4):
            for j in range(i + 1, 4):
                rows.append({
                    "match_id": match_id,
                    "season": 2026,
                    "utc_date": "2026-06-11",
                    "status": "TIMED",
                    "stage": "GROUP_STAGE",
                    "group_name": g["name"],
                    "matchday": 0,
                    "home_team": t[i],
                    "away_team": t[j],
                })
                match_id += 1
    return pd.DataFrame(rows)


BASE_DRAW_RATE = 0.24


def elo_expected(elo_a: float, elo_b: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / 400.0))


def load_elo_form_values() -> dict:
    with open(ELO_FORM_PATH) as f:
        return json.load(f)


def build_2026_features(m2026: pd.DataFrame, form: dict) -> pd.DataFrame:
    elo_values = load_elo_form_values()
    rows = []
    for _, match in m2026.iterrows():
        home = match["home_team"]
        away = match["away_team"]
        home_elo = elo_values.get(home, {})
        away_elo = elo_values.get(away, {})

        e_home = elo_expected(
            home_elo.get("elo", 1500),
            away_elo.get("elo", 1500),
        )
        e_away = 1.0 - e_home
        h2h_home = round(e_home * (1.0 - BASE_DRAW_RATE), 3)
        h2h_away = round(e_away * (1.0 - BASE_DRAW_RATE), 3)

        rows.append({
            "match_id": match["match_id"],
            "season": 2026,
            "home_team": home,
            "away_team": away,
            "home_form_gf": home_elo.get("form_gf", 1.5),
            "home_form_ga": home_elo.get("form_ga", 1.5),
            "home_form_pts": home_elo.get("form_pts", 1.5),
            "away_form_gf": away_elo.get("form_gf", 1.5),
            "away_form_ga": away_elo.get("form_ga", 1.5),
            "away_form_pts": away_elo.get("form_pts", 1.5),
            "h2h_home_win_rate": h2h_home,
            "h2h_away_win_rate": h2h_away,
            "h2h_draw_rate": BASE_DRAW_RATE,
            "knockout": 0,
        })
    return pd.DataFrame(rows)


def predict_matches(model, features: pd.DataFrame) -> pd.DataFrame:
    X = features[FEATURE_COLS].values
    probs = model.predict(xgb.DMatrix(X))
    results = features[["match_id", "home_team", "away_team"]].copy()
    results["home_win_prob"] = probs[:, 0]
    results["draw_prob"] = probs[:, 1]
    results["away_win_prob"] = probs[:, 2]
    results["predicted_winner"] = np.where(
        results["home_win_prob"] > results["away_win_prob"],
        results["home_team"],
        np.where(
            results["away_win_prob"] > results["home_win_prob"],
            results["away_team"],
            "Draw",
        ),
    )
    results["confidence"] = results[["home_win_prob", "draw_prob", "away_win_prob"]].max(axis=1)
    return results


def sample_match_result(row: dict) -> str:
    p0, p1, p2 = row["home_win_prob"], row["draw_prob"], row["away_win_prob"]
    s = p0 + p1 + p2
    r = random.random() * s
    if r < p0:
        return "home"
    elif r < p0 + p2:
        return "away"
    else:
        return "home" if random.random() > 0.5 else "away"


def simulate_group_stage(predictions: list, groups: list) -> dict:
    standings = {}
    for g in groups:
        standings[g["name"]] = {t: {"pts": 0, "gd": 0, "gf": 0, "ga": 0} for t in g["teams"]}
    for pred in predictions:
        result = sample_match_result(pred)
        home = pred["home_team"]
        away = pred["away_team"]
        home_group = None
        for g in groups:
            if home in g["teams"]:
                home_group = g["name"]
                break
        if home_group is None or away not in standings[home_group]:
            continue
        if result == "home":
            standings[home_group][home]["pts"] += 3
            standings[home_group][home]["gf"] += 1
            standings[home_group][away]["ga"] += 1
            standings[home_group][home]["gd"] += 1
            standings[home_group][away]["gd"] -= 1
        elif result == "away":
            standings[home_group][away]["pts"] += 3
            standings[home_group][away]["gf"] += 1
            standings[home_group][home]["ga"] += 1
            standings[home_group][away]["gd"] += 1
            standings[home_group][home]["gd"] -= 1
        else:
            standings[home_group][home]["pts"] += 1
            standings[home_group][away]["pts"] += 1
    return standings


def rank_groups(standings: dict) -> list:
    advancing = []
    for g_name in GROUP_NAMES:
        if g_name not in standings:
            continue
        teams = sorted(
            standings[g_name].items(),
            key=lambda x: (-x[1]["pts"], -x[1]["gd"], -x[1]["gf"], x[0]),
        )
        for pos, (team, stats) in enumerate(teams):
            advancing.append({
                "team": team,
                "group": g_name,
                "position": pos + 1,
                "pts": stats["pts"],
                "gd": stats["gd"],
                "gf": stats["gf"],
            })
    return advancing


def form_strength(team: dict) -> float:
    return team["pts"] + team["gd"] * 0.5 + team["gf"] * 0.1


def simulate_knockout_match(team_a: str, team_b: str, team_form: dict) -> str:
    a_strength = team_form.get(team_a, 0)
    b_strength = team_form.get(team_b, 0)
    prob_a = 1.0 / (1.0 + 10.0 ** ((b_strength - a_strength) / 400.0))
    return team_a if random.random() < prob_a else team_b


def simulate_knockout_stage(advancing: list, team_form: dict) -> dict:
    winners = [t for t in advancing if t["position"] == 1]
    runners = [t for t in advancing if t["position"] == 2]
    third_placed = [t for t in advancing if t["position"] == 3]
    winners.sort(key=lambda x: -form_strength(x))
    runners.sort(key=lambda x: -form_strength(x))
    third_placed.sort(key=lambda x: -form_strength(x))
    bracket = winners + runners + third_placed
    n = len(bracket)
    round_teams = []
    for i in range(n // 2):
        a = bracket[i]
        b = bracket[n - 1 - i]
        round_teams.append((a["team"], b["team"]))
    current_round = round_teams
    round_names = ["LAST_32", "LAST_16", "QUARTER_FINALS", "SEMI_FINALS", "FINAL"]
    for rname in round_names:
        next_round = []
        for match_a, match_b in current_round:
            winner = simulate_knockout_match(match_a, match_b, team_form)
            next_round.append(winner)
        if len(next_round) <= 1:
            return {
                "champion": next_round[0] if next_round else None,
                "runner_up": current_round[0][0] if current_round else None,
            }
        current_round = list(zip(next_round[::2], next_round[1::2]))
    return {"champion": None, "runner_up": None}


def simulate_tournament(predictions: list, groups: list, n_simulations: int = 10000) -> dict:
    champion_counts = defaultdict(int)
    finalist_counts = defaultdict(int)
    for _ in range(n_simulations):
        standings = simulate_group_stage(predictions, groups)
        advancing = rank_groups(standings)
        third_placed = [t for t in advancing if t["position"] == 3]
        third_placed.sort(key=lambda x: (-x["pts"], -x["gd"], -x["gf"]))
        top_third = third_placed[:8]
        qualifiers = [t for t in advancing if t["position"] <= 2] + top_third
        if len(qualifiers) < 2:
            continue
        team_form = {}
        for t in qualifiers:
            team_form[t["team"]] = form_strength(t)
        result = simulate_knockout_stage(qualifiers, team_form)
        if result["champion"]:
            champion_counts[result["champion"]] += 1
        if result["runner_up"]:
            finalist_counts[result["runner_up"]] += 1
    total = max(sum(champion_counts.values()), 1)
    champ_sorted = sorted(champion_counts.items(), key=lambda x: -x[1])
    final_sorted = sorted(finalist_counts.items(), key=lambda x: -x[1])
    return {
        "n_simulations": n_simulations,
        "champion_probabilities": {t: round(c / total, 4) for t, c in champ_sorted if c > 0},
        "finalist_probabilities": {t: round(c / total, 4) for t, c in final_sorted if c > 0},
        "top_champion": champ_sorted[0][0] if champ_sorted else None,
        "top_champion_prob": round(champ_sorted[0][1] / total, 4) if champ_sorted else 0,
    }


def main():
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading model...")
    model = load_model()
    model_name = "xgboost_v1_tuned"

    print("\nLoading historical form data...")
    form = load_historical_form()
    print(f"  Form vectors: {len(form)}")

    print("\nLoading official groups...")
    groups = load_groups()
    for g in groups[:3]:
        print(f"  Group {g['name']}: {', '.join(g['teams'])}")
    print(f"  ... ({len(groups)} groups total)")

    print("\nGenerating correct group-stage fixtures...")
    fixtures = generate_correct_fixtures(groups)
    print(f"  {len(fixtures)} fixtures generated")

    print("\nBuilding feature vectors for correct fixtures...")
    features_2026 = build_2026_features(fixtures, form)
    print(f"  {len(features_2026)} feature vectors")

    print("\nPredicting match outcomes...")
    predictions = predict_matches(model, features_2026)

    pred_path = PREDICTIONS_DIR / f"2026_predictions_{model_name}.json"
    pred_dict = predictions.to_dict(orient="records")
    pred_path.write_text(json.dumps(pred_dict, indent=2, default=str))
    print(f"  Saved -> {pred_path}")
    print(f"  {len(pred_dict)} matches")

    print("\nRunning tournament simulation...")
    pred_list = predictions.to_dict(orient="records")
    sim_result = simulate_tournament(pred_list, groups, n_simulations=10000)

    print(f"  Simulations: {sim_result['n_simulations']}")
    print(f"  Top champion: {sim_result['top_champion']} ({sim_result['top_champion_prob']:.1%})")
    print(f"\n  Top 10 champions:")
    for team, prob in list(sim_result["champion_probabilities"].items())[:10]:
        print(f"    {team}: {prob:.1%}")

    sim_path = PREDICTIONS_DIR / f"tournament_simulation_{model_name}.json"
    sim_path.write_text(json.dumps(sim_result, indent=2, default=str))
    print(f"\n  Saved -> {sim_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
