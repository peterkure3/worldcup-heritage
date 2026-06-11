import pandas as pd
m = pd.read_parquet("data/raw/2026_matches.parquet")
ko = m[m["stage"] != "GROUP_STAGE"]
print(f"Knockout with known teams: {len(ko.dropna(subset=['home_team', 'away_team']))}")
print(f"Knockout with TBD teams: {len(ko) - len(ko.dropna(subset=['home_team', 'away_team']))}")
print()
for _, r in ko.iterrows():
    ht = r["home_team"] if pd.notna(r["home_team"]) else "TBD"
    at = r["away_team"] if pd.notna(r["away_team"]) else "TBD"
    print(f"  {r['stage']:20s} {ht:25s} vs {at}")
