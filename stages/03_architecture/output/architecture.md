# Architecture — World Cup Prediction System

## 1. System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     DATA INGESTION LAYER                          │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │ football-data.org│  │ jfjelstul/worldcup│  │ FIFA Rankings   │ │
│  │ API (2026 only) │  │ CSV (hist. data) │  │ (future)        │ │
│  └────────┬────────┘  └────────┬─────────┘  └────────┬────────┘ │
│           │                    │                      │          │
│           ▼                    ▼                      ▼          │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                  pipeline/data/raw/                          │ │
│  │  (parquet/CSV cache, read-only after fetch)                  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    FEATURE ENGINEERING LAYER                      │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  pipeline/feature_engineering/                                │ │
│  │  • build_match_features() → per-match feature vectors        │ │
│  │  • build_team_form() → rolling form metrics                  │ │
│  │  • build_h2h_features() → head-to-head records               │ │
│  │  • build_tournament_context() → stage, host, group info      │ │
│  │  Output: pipeline/data/features/training_features.parquet    │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                     MODEL TRAINING LAYER                          │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  pipeline/model_training/                                    │ │
│  │  • train_test_split() → time-series CV folds                │ │
│  │  • train_xgboost() → primary model                           │ │
│  │  • train_lightgbm() → secondary model                        │ │
│  │  • train_baseline() → logistic regression                    │ │
│  │  • tune_hyperparameters() → Optuna search                    │ │
│  │  • evaluate() → log-loss, accuracy, Brier score              │ │
│  │  Output: artifacts/models/{model_name}.joblib                │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    PREDICTION / SERVING LAYER                     │
│  ┌────────────────────┐   ┌────────────────────────────────────┐ │
│  │ pipeline/prediction/│   │ backend/ (Rust Actix-Web API)      │ │
│  │ • predict_match()   │   │                                    │ │
│  │ • simulate_tourney()│   │ GET /api/health                    │ │
│  │ • export_predictions│   │ GET /api/matches                   │ │
│  │   → artifacts/      │   │ GET /api/matches/{id}/prediction   │ │
│  └─────────┬──────────┘   │ GET /api/tournament/prediction      │ │
│            │              └──────────────────┬─────────────────┘ │
│            ▼                                 ▼                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    PostgreSQL Database                        │ │
│  │  • matches (fixtures + results)                              │ │
│  │  • teams                                                     │ │
│  │  • predictions (stored for API serving)                      │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    FRONTEND LAYER                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  frontend/ (React + Vite + TypeScript)                       │ │
│  │  • Bracket view → knockout bracket with predictions          │ │
│  │  • Group tables → standings with predicted outcomes          │ │
│  │  • Team detail → team stats and upcoming matches             │ │
│  │  • Champion probability → distribution visualization          │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## 2. Database Schema

### Table: `teams`
```sql
CREATE TABLE teams (
    id          INTEGER PRIMARY KEY,          -- football-data.org team ID
    name        TEXT NOT NULL,
    short_name  TEXT,
    tla         TEXT,                          -- 3-letter code (e.g. "BRA")
    crest_url   TEXT,
    confederation TEXT,                        -- UEFA, CONMEBOL, etc.
    fifa_ranking INTEGER,
    created_at  TIMESTAMP DEFAULT NOW()
);
```

### Table: `matches`
```sql
CREATE TABLE matches (
    id              INTEGER PRIMARY KEY,       -- football-data.org match ID
    season          INTEGER NOT NULL,           -- 2026
    utc_date        TIMESTAMP NOT NULL,
    status          TEXT NOT NULL DEFAULT 'TIMED',  -- TIMED | FINISHED | ...
    stage           TEXT NOT NULL,              -- GROUP_STAGE | LAST_32 | ...
    group_name      TEXT,                       -- GROUP_A ... GROUP_L
    matchday        INTEGER,
    home_team_id    INTEGER REFERENCES teams(id),
    away_team_id    INTEGER REFERENCES teams(id),
    home_score      INTEGER,                    -- null before match
    away_score      INTEGER,                    -- null before match
    winner          TEXT,                       -- HOME_TEAM | AWAY_TEAM | DRAW | null
    venue           TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_matches_season ON matches(season);
CREATE INDEX idx_matches_stage ON matches(stage);
CREATE INDEX idx_matches_team ON matches(home_team_id);
CREATE INDEX idx_matches_team2 ON matches(away_team_id);
```

### Table: `predictions`
```sql
CREATE TABLE predictions (
    id              SERIAL PRIMARY KEY,
    match_id        INTEGER REFERENCES matches(id),
    model_name      TEXT NOT NULL,              -- xgboost | lightgbm | ensemble
    home_win_prob   REAL NOT NULL,              -- 0.0 – 1.0
    draw_prob       REAL NOT NULL,              -- 0.0 – 1.0
    away_win_prob   REAL NOT NULL,              -- 0.0 – 1.0
    predicted_winner TEXT,                      -- HOME_TEAM | AWAY_TEAM | DRAW
    confidence      REAL,                       -- max probability
    model_version   TEXT,
    created_at      TIMESTAMP DEFAULT NOW(),

    UNIQUE(match_id, model_name, model_version)
);

CREATE INDEX idx_predictions_match ON predictions(match_id);
```

### Table: `tournament_predictions`
```sql
CREATE TABLE tournament_predictions (
    id              SERIAL PRIMARY KEY,
    season          INTEGER NOT NULL,
    team_id         INTEGER REFERENCES teams(id),
    champion_prob   REAL NOT NULL,              -- probability of winning it all
    final_prob      REAL NOT NULL,              -- probability of reaching final
    semi_prob       REAL NOT NULL,              -- probability of reaching SF
    quarter_prob    REAL NOT NULL,              -- probability of reaching QF
    round_16_prob   REAL,                       -- probability of reaching R16
    group_advance_prob REAL,                    -- probability of advancing from group
    model_version   TEXT,
    created_at      TIMESTAMP DEFAULT NOW(),

    UNIQUE(season, team_id, model_version)
);
```

## 3. Pipeline Module Interfaces

### Module: `pipeline/data_ingestion/`

```
fetch_from_football_data() -> pd.DataFrame  # 2026 matches
load_fjelstul_csv() -> pd.DataFrame          # historical matches
merge_and_normalize() -> pd.DataFrame        # unified match format
save_raw(df, path) -> None
```

### Module: `pipeline/feature_engineering/`

```
Input:  pd.DataFrame with columns [match_id, season, match_date, home_team, away_team,
        home_score, away_score, stage, group, knockout, neutral]
Output: pd.DataFrame with columns [match_id, *feature_cols, target]

Features:
  - form_home_last_5: avg goals scored/conceded in last 5 WC matches
  - form_away_last_5: same for away team
  - h2h_win_rate: historical head-to-head win rate
  - stage_is_knockout: binary
  - group_stage_points: points earned so far in group
  - goal_diff_rolling: rolling goal difference
  - days_since_last_match: rest advantage
  - host_advantage: home confederation or host nation
  - elo_proxy: inferred from historical results
```

### Module: `pipeline/model_training/`

```
prepare_data(features_df) -> X_train, X_test, y_train, y_test
train_xgboost(X_train, y_train) -> model
train_lightgbm(X_train, y_train) -> model
tune_optuna(X_train, y_train) -> best_params
evaluate(model, X_test, y_test) -> dict  # metrics
save_model(model, name) -> None
```

### Module: `pipeline/prediction/`

```
predict_match(model, home_team, away_team, context) -> dict  # probs
simulate_tournament(model, fixtures_df, n_simulations=10000) -> pd.DataFrame
export_results(predictions_df) -> None
```

## 4. API Contract (Rust Backend)

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/matches` | List all 2026 matches with predictions |
| GET | `/api/matches/{id}` | Single match detail |
| GET | `/api/matches/{id}/prediction` | Prediction for one match |
| GET | `/api/teams` | List all teams |
| GET | `/api/teams/{id}` | Team detail with stats |
| GET | `/api/tournament/prediction` | Full tournament prediction (bracket + champion probs) |
| GET | `/api/tournament/groups` | Group standings with predicted outcomes |
| POST | `/api/predictions/refresh` | Trigger re-prediction (admin) |

### Response Shape

```json
GET /api/matches/{id}/prediction
{
  "match_id": 537327,
  "home_team": "Mexico",
  "away_team": "South Africa",
  "prediction": {
    "home_win_prob": 0.62,
    "draw_prob": 0.21,
    "away_win_prob": 0.17,
    "predicted_winner": "HOME_TEAM",
    "confidence": 0.62,
    "model": "xgboost_v1"
  }
}
```

```json
GET /api/tournament/prediction
{
  "season": 2026,
  "generated_at": "2026-06-11T00:00:00Z",
  "champion": {
    "team": "Brazil",
    "probability": 0.14
  },
  "top_5": [
    {"team": "Brazil", "probability": 0.14},
    {"team": "France", "probability": 0.12},
    {"team": "Argentina", "probability": 0.10},
    {"team": "England", "probability": 0.08},
    {"team": "Germany", "probability": 0.07}
  ],
  "bracket": {
    "round_of_32": [...],
    "round_of_16": [...],
    "quarter_finals": [...],
    "semi_finals": [...],
    "third_place": {...},
    "final": {...}
  }
}
```

## 5. Project Structure

```
worldcup-heritage/
├── backend/
│   ├── src/
│   │   ├── main.rs           — server entry, routes
│   │   ├── routes/
│   │   │   ├── mod.rs
│   │   │   ├── health.rs
│   │   │   ├── matches.rs    — match endpoints
│   │   │   ├── teams.rs
│   │   │   └── predictions.rs
│   │   ├── models/
│   │   │   ├── mod.rs
│   │   │   ├── match.rs
│   │   │   ├── team.rs
│   │   │   └── prediction.rs
│   │   ├── db.rs             — DB connection pool
│   │   └── errors.rs         — error types
│   └── Cargo.toml
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api/              — API client
│   │   ├── components/
│   │   │   ├── Bracket.tsx    — knockout bracket
│   │   │   ├── GroupTable.tsx — group standings
│   │   │   ├── MatchCard.tsx — single match view
│   │   │   └── ChampionBar.tsx — probability chart
│   │   └── hooks/            — data fetching hooks
│   └── ...
│
├── pipeline/
│   ├── data_ingestion/
│   │   └── fetch_data.py
│   ├── feature_engineering/
│   │   └── build_features.py
│   ├── model_training/
│   │   └── train.py
│   ├── prediction/
│   │   └── predict.py
│   ├── data/
│   │   ├── raw/              — cached raw data (gitignored)
│   │   └── features/         — engineered features (gitignored)
│   ├── scripts/              — utility scripts
│   └── .venv/
│
├── artifacts/
│   ├── models/               — trained model files (gitignored)
│   └── predictions/          — prediction exports (gitignored)
│
├── shared/                   — API schemas, shared types
├── _config/                  — workspace configuration
├── stages/                   — ICM stage outputs
└── docker-compose.yml        — PostgreSQL + API
```

## 6. Data Flow for a Prediction Run

```
1. DATA INGESTION
   football-data.org API ────→ raw/2026_matches.parquet
   fjelstul CSVs ───────────→ raw/historical_matches.parquet

2. FEATURE ENGINEERING
   raw/*.parquet ───────────→ features/training_features.parquet
                              features/2026_features.parquet

3. TRAINING
   features/training_features.parquet ───→ models/xgboost_v1.joblib

4. PREDICTION
   models/xgboost_v1.joblib + features/2026_features.parquet
       ───→ predictions/2026_predictions.json
       ───→ predictions/tournament_simulation.json

5. SERVE
   predictions/*.json ───→ PostgreSQL ───→ Rust API ───→ React frontend
```

## 7. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Model format | XGBoost + LightGBM | Best for tabular data; handles non-linearity, missing values |
| Training target | 3-class (H/D/A) | Simpler than score prediction; sufficient for winner prediction |
| Tournament sim | Monte Carlo (10k iterations) | Accounts for chain of upsets |
| Feature store | Parquet files | Simple, fast, no infra needed |
| Serving DB | PostgreSQL | Reliable, good with Rust (sqlx), supports JSON |
| API framework | Actix-Web | Fast, mature Rust web framework |
| Frontend framework | React + Vite + Tailwind | Fast dev cycle, good visualization ecosystem |
| Time-series split | 1998–2010 train, 2014 valid, 2018+2022 test | Modern era has reliable data |
