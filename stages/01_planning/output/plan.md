# Planning — World Cup Winner Prediction

## 1. Project Goal

Build an ML system that predicts World Cup match outcomes (win/loss/draw) for every game in a tournament, culminating in a predicted champion. The system ingests historical data, engineers features, trains a model, and serves predictions via an API.

## 2. Data Sources

### Primary: football-data.org API

| Endpoint | Data | Coverage |
|----------|------|----------|
| `GET /competitions/WC` | World Cup competition metadata | All editions |
| `GET /competitions/WC/matches?season=YYYY` | All matches for a given year | 1930–2026 |
| `GET /competitions/WC/teams?season=YYYY` | Participating teams per edition | Historical |
| `GET /teams/{id}` | Team details + squad | Current only (Tier limit) |
| `GET /competitions/{id}/standings` | Group standings | Knockout stage data |

**API Limits:** Free plan = 10 req/min. We'll cache aggressively and batch historical fetches.

### Supplementary (future consideration)
- FIFA World Ranking historical data
- Player-level stats (age, caps, goals)
- Elo ratings

## 3. Pipeline Stages

```
data_ingestion/    → fetch raw match data from API, cache locally
feature_engineering/ → transform raw data into training features
model_training/    → train classifiers, tune hyperparameters
prediction/        → predict match outcomes + simulate tournament
api/               → serve predictions via Rust backend
```

### Stage 1: Data Ingestion
- Fetch all historical World Cup matches (1930–2022)
- Normalise match records (home/away, score, stage, group)
- Store as parquet files in `pipeline/data/raw/`
- Fetch team metadata

### Stage 2: Feature Engineering
Per-match features:
- **Team form:** Goals scored/conceded in last N matches
- **Historical H2H:** Head-to-head record
- **Tournament context:** Group stage vs knockout, match number
- **Qualifying performance:** How the team qualified
- **Team strength:** Rolling Elo or ranking proxy
- **Continental effects:** Confederation, host continent advantage

### Stage 3: Model Training
- **Target:** Match outcome (H / D / A)
- **Models to evaluate:**
  - XGBoost / LightGBM (primary)
  - Logistic Regression (baseline)
  - Ensemble approaches
- **Evaluation:** Cross-validation by tournament year (time-series split)
- **Hyperparameter tuning:** Optuna
- **Metrics:** Log-loss, accuracy, Brier score

### Stage 4: Tournament Simulation
- For a given World Cup fixture list, predict each match
- Simulate group stage → round of 16 → QF → SF → Final
- Output probability distributions for champion
- Confidence intervals for each prediction

### Stage 5: Serving
- API endpoint: `GET /predictions/match?home=...&away=...`
- API endpoint: `GET /predictions/tournament?year=YYYY`
- Frontend displays bracket with predicted winners + probabilities

## 4. System Architecture

```
┌──────────────┐    ┌─────────────────┐    ┌────────────────┐
│  Pipeline     │───▶│  PostgreSQL     │───▶│  Rust API      │
│  (Python ML)  │    │  (matches,      │    │  (Actix-Web)   │
│               │    │   features,     │    │                │
│               │    │   predictions)  │    │                │
└──────────────┘    └─────────────────┘    └───────┬────────┘
                                                   │
                                                   ▼
                                          ┌────────────────┐
                                          │  React Frontend │
                                          │  (Vite + TS)    │
                                          │  (Bracket view) │
                                          └────────────────┘
```

**Data flow:**
1. Python pipeline fetches data from football-data.org
2. Transforms and trains model
3. Stores predictions in PostgreSQL
4. Rust API serves predictions
5. React frontend renders bracket

## 5. Deliverables

| # | Artifact | Location |
|---|----------|----------|
| 1 | Raw match dataset (parquet) | `pipeline/data/raw/` |
| 2 | Feature-engineered dataset | `pipeline/data/features/` |
| 3 | Trained model artifacts | `artifacts/models/` |
| 4 | Prediction outputs (JSON) | `artifacts/predictions/` |
| 5 | REST API endpoints | `backend/` |
| 6 | Frontend bracket visualization | `frontend/` |

## 6. Constraints & Risks

- **Free API tier:** Only 10 req/min. Must cache aggressively.
- **Historical squad data:** Free tier may not have historic squads. Feature scope may need adjustment.
- **Time-series leakage:** Must never train on future matches. Use temporal cross-validation.
- **Class imbalance:** Draws are rarer than home/away wins. Use stratified sampling or custom loss.

## 7. Next Steps

1. `02_research/` — Prototype API data fetch, validate schema coverage
2. `03_architecture/` — Define database schema, API contract, module interfaces
3. `04_implementation/` — Build pipeline stages incrementally
4. `05_testing/` — Validate model performance, backtest on past tournaments
5. `06_review/` — Review predictions, document methodology
6. `07_deployment/` — Deploy API, finalize frontend
