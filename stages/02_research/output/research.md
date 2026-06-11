# Research Findings — World Cup Prediction

## 1. Data Source Evaluation

### football-data.org API (v4)
**Plan:** Free tier
**Rate limit:** 10 req/min
**Base URL:** `https://api.football-data.org/v4`

| Resource | Access | Data Obtained |
|----------|--------|---------------|
| `GET /competitions/WC` | ✅ Full | Competition metadata, 23 seasons (1930–2026), winners per edition |
| `GET /competitions/WC/matches?season=2026` | ✅ Full | 104 matches: groups, teams, schedule, venues, referees |
| `GET /competitions/WC/matches?season=YYYY` | ❌ 403 (past) | Historical match data requires paid tier (€29/mo+) |
| `GET /competitions/WC/teams?season=2026` | Not tested | Likely works for current season |
| `GET /teams/{id}` | Not tested | Team details (current season) |

**Verdict:** Use only for **2026 fixture list** and live updates during the tournament.

### J. Fjelstul World Cup Database (recommended for training)
- **Source:** https://github.com/jfjelstul/worldcup
- **License:** Open (CC0 / MIT)
- **Coverage:** All 22 men's tournaments (1930–2022), all 8 women's tournaments (1991–2019)
- **Formats:** CSV, JSON, SQLite, R package
- **Size:** 27 datasets, 1.58M+ data points
- **Key tables:** matches, goals, tournaments, teams, players, managers, referees, groups, squads

**Verdict:** Primary source for historical training data. Download once, cache locally.

## 2. 2026 World Cup — Key Facts

| Property | Value |
|----------|-------|
| **Format** | 48 teams (expanded from 32) |
| **Groups** | 12 groups (A–L), 4 teams each |
| **Group stage matches** | 6 per group × 12 = 72 |
| **Knockout format** | Top 2 per group + 8 best 3rd-placed → LAST_32 |
| **Total matches** | 104 |
| **Hosts** | USA, Canada, Mexico |
| **Dates** | June 11 – July 19, 2026 |

### Stages in API
```
GROUP_STAGE → LAST_32 → LAST_16 → QUARTER_FINALS → SEMI_FINALS → THIRD_PLACE → FINAL
```

### Participating Teams (49 confirmed, 1 TBD via playoff)
Argentina, Australia, Austria, Belgium, Bosnia & Herzegovina, Brazil, Canada, Cape Verde, Colombia, Croatia, Czech Republic, Denmark, DR Congo, Ecuador, Egypt, England, France, Germany, Ghana, Haiti, Iran, Iraq, Ivory Coast, Japan, Jordan, Mexico, Morocco, Netherlands, New Zealand, Norway, Panama, Paraguay, Portugal, Qatar, Saudi Arabia, Scotland, Senegal, South Africa, South Korea, Spain, Sweden, Switzerland, Tunisia, Turkey, United States, Uruguay, Uzbekistan (48+1 playoff)

## 3. API Data Schema

### Match Object (2026 fixtures)
```json
{
  "area":       {"id": int, "name": str, "code": str},
  "competition": {"id": int, "name": str, "code": "WC"},
  "season":     {"id": int, "startDate": str, "endDate": str, "currentMatchday": int, "winner": null},
  "id":         int,
  "utcDate":    "2026-06-11T19:00:00Z",
  "status":     "TIMED" | "SCHEDULED" | "FINISHED" | ...,
  "matchday":   int,
  "stage":      "GROUP_STAGE" | "LAST_32" | "LAST_16" | "QUARTER_FINALS" | "SEMI_FINALS" | "THIRD_PLACE" | "FINAL",
  "group":      "GROUP_A" ... "GROUP_L",
  "homeTeam":   {"id": int, "name": str, "shortName": str, "tla": str, "crest": url},
  "awayTeam":   {"id": int, "name": str, "shortName": str, "tla": str, "crest": url},
  "score":      {"winner": null|"HOME_TEAM"|"AWAY_TEAM", "duration": "REGULAR",
                  "fullTime": {"home": int|null, "away": int|null},
                  "halfTime": {"home": int|null, "away": int|null}},
  "odds":       {"msg": "Activate Odds-Package..."},
  "referees":   [{"id": int, "name": str, "type": "REFEREE", "nationality": str}]
}
```

## 4. Feature Engineering Strategy

Using the Fjelstul database, we can derive per-match features:

### Team-level features (rolling, computed from historical matches)
- **Form:** Goals scored/conceded in last 5 WC matches
- **Win rate:** Rolling win/draw/loss ratio in WC
- **Goal difference:** Average GD in last N matches
- **Knockout experience:** Number of KO matches played by each team historically
- **Historical H2H:** Head-to-head record between the two teams

### Tournament-level features
- **Group stage performance:** Points, GD, goals in current group stage
- **Stage:** Round of tournament (group vs knockout)
- **Host advantage:** Whether team is host or confederation host

### External features (to add later)
- FIFA World Ranking (Elo rating proxy)
- Player-level metrics (squad value, caps, average age)
- Qualifying campaign stats

## 5. Recommendation

| Concern | Recommendation |
|---------|---------------|
| **Training data** | Download jfjelstul/worldcup CSV dataset, cache in `pipeline/data/raw/` |
| **2026 fixtures** | football-data.org API — fetch on startup, cache |
| **Live scores** | football-data.org API during tournament (10 req/min enough) |
| **Model target** | Match outcome: HOME_WIN / DRAW / AWAY_WIN |
| **Evaluation** | Time-series CV (train on 1930–2014, evaluate on 2018+2022) |
| **Min viable data** | 1998–2022 (8 tournaments, 64 matches each, reliable data) |

## 6. Raw Data Collected

All outputs in `stages/02_research/output/api_research/`:
- `competition_WC.json` — World Cup metadata
- `competition_WC_full.json` — Full competition data (all seasons + winners)
- `competition_EC.json` — European Championship (reference)
- `competition_CL.json` — Champions League (reference)
- `matches_2026.json` — All 104 fixtures for 2026 (6,212 lines)
