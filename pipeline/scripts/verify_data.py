import pandas as pd

m = pd.read_csv("data/raw/worldcup-master/data-csv/matches.csv")
print(f"Matches: {len(m)}")
print(f"Columns: {list(m.columns)}")
tours = m["tournament_name"].unique()
print(f"Tournaments: {len(tours)}")
print(f"Sample years: {sorted([t for t in tours if t.startswith('193') or t.startswith('202')])}")

cols = ["match_date", "home_team_name", "away_team_name", "home_team_score", "away_team_score", "stage_name"]
print(m[cols].head(5).to_string(index=False))
