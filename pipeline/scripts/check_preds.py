import json
from pathlib import Path

p = Path("../artifacts/predictions/2026_predictions_xgboost_v1_tuned.json")
data = json.loads(p.read_text())
print(f"{len(data)} predictions")
for x in data[:5]:
    print(f"  {x['home_team']} vs {x['away_team']}: H={x['home_win_prob']:.2f} D={x['draw_prob']:.2f} A={x['away_win_prob']:.2f} -> {x['predicted_winner']}")
