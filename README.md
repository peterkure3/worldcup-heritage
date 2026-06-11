# World Cup Heritage — 2026 Predictions

End-to-end World Cup 2026 prediction pipeline: data ingestion → feature engineering → ML model training → prediction generation → Rust API backend → React frontend with official FIFA standings.

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────┐
│  Data       │ ──▶ │  Feature         │ ──▶ │  XGBoost         │ ──▶ │  Predictions  │
│  Ingestion  │     │  Engineering     │     │  Model Training  │     │  + Simulation  │
│  (Python)   │     │  (Python)        │     │  (Python/Optuna) │     │  (JSON files)  │
└─────────────┘     └──────────────────┘     └──────────────────┘     └──────┬───────┘
                                                                             │
                                                    ┌────────────────────────┘
                                                    ▼
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Frontend    │ ◀── │  nginx proxy     │ ◀── │  Rust API        │
│  React/Vite  │     │  /api → backend  │     │  Actix-Web       │
│  Recharts    │     │  port 80         │     │  port 7777       │
└──────────────┘     └──────────────────┘     └────────┬─────────┘
                                                       │
                                              ┌────────▼─────────┐
                                              │  PostgreSQL 16   │
                                              │  (optional)      │
                                              └──────────────────┘
```

## Quick Start

### Prerequisites
- Docker Desktop 29+ (with Docker Compose v5)
- Python 3.12+ (for pipeline, optional if predictions are pre-generated)

### Run the full stack

```bash
docker compose up -d
```

This starts:
- **PostgreSQL 16** on port 5432 (`worldcup:worldcup@localhost:5432/worldcup`)
- **Rust API** on port 7777
- **Frontend** (nginx) on port 80

### Verify

```bash
curl http://localhost/api/health
curl http://localhost/api/db/status
```

## Development

### Pipeline (Python)

```bash
cd pipeline
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Run full pipeline (data → features → model → predictions)
python data_ingestion/fetch_data.py
python feature_engineering/build_features.py
python training/train_model.py
python prediction/predict.py
```

### Backend (Rust)

```bash
cd backend
cargo run
# Starts on http://localhost:7777
```

Requires `DATABASE_URL` env var or `.env` file. Falls back gracefully if DB is unavailable.

### Frontend (React)

```bash
cd frontend
npm install
npm run dev
# Starts on http://localhost:5173 with /api proxied to localhost:7777
```

## Project Structure

```
├── pipeline/
│   ├── data_ingestion/       # Fetch historical matches + 2026 fixtures
│   ├── feature_engineering/  # Rolling form, H2H, Elo ratings
│   ├── training/             # XGBoost training + Optuna tuning
│   └── prediction/           # Predict 2026 + tournament simulation
├── backend/
│   ├── src/
│   │   ├── main.rs           # Server bootstrap + state
│   │   ├── db.rs             # PostgreSQL pool + seeding
│   │   ├── models/           # Data types (groups, predictions, matches)
│   │   └── routes/           # API endpoints (health, predictions, groups)
│   ├── migrations/init.sql   # Schema DDL
│   └── Dockerfile            # Multi-stage Rust build
├── frontend/
│   ├── src/
│   │   ├── api/              # API client + types
│   │   ├── components/       # GroupTable, ChampionBar, MatchCard, etc.
│   │   └── pages/            # Groups, Knockout, Predictions pages
│   ├── nginx.conf            # SPA + /api proxy config
│   └── Dockerfile            # Node build → nginx
├── artifacts/
│   ├── groups.json           # Official FIFA groups (48 teams, 12 groups)
│   └── predictions/          # ML-generated predictions + simulation
├── docker-compose.yml        # postgres + backend + frontend
└── .gitignore
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check + DB status |
| `GET /api/db/status` | Row counts for all tables |
| `GET /api/predictions` | All 72 group-stage match predictions |
| `GET /api/predictions/{id}` | Single match prediction |
| `GET /api/predictions/tournament` | Tournament simulation (champion probabilities) |
| `GET /api/groups` | Group standings with 48 teams |

## Update After a Match

After a 2026 World Cup game is played, update Elo ratings and regenerate predictions:

```bash
# 1. Update Elo ratings with the actual result
#    (manually add the result to predict.py or fetch via football-data.org)
python pipeline/feature_engineering/elo.py

# 2. Regenerate predictions for remaining matches
python pipeline/prediction/predict.py

# 3. Deploy updated files to the running Docker container
docker cp artifacts/groups.json worldcup-api:/app/artifacts/groups.json
docker cp artifacts/predictions/2026_predictions_xgboost_v1_tuned.json worldcup-api:/app/artifacts/predictions/
docker cp artifacts/predictions/tournament_simulation_xgboost_v1_tuned.json worldcup-api:/app/artifacts/predictions/
docker compose restart backend
```

The backend and frontend reload the JSON files after restart — no image rebuild needed.

> **Note**: `elo.py` currently reads historical World Cup matches (1930–2022) only. To propagate a 2026 result into Elo ratings, manually append the match to `pipeline/data/raw/historical_matches.parquet` before running the steps above, or inject it via the `football-data.org` API fetch in `fetch_data.py`.

## Data Sources

- **Match data**: [football-data.org](https://www.football-data.org/) API (historical matches 1872–present)
- **Group structure**: [worldcup26.ir](https://www.worldcup26.ir/) free API (official FIFA groupings)
- **Flags**: [flagcdn.com](https://flagcdn.com/) SVG files

## Deployment

```bash
# Build and start all services
docker compose up -d --build

# Stop and clean
docker compose down -v
```

## Known Issues

- **`rsa` crate (RUSTSEC-2023-0071)**: Transitive dependency via `sqlx-mysql`, an **unused optional feature** (we use PostgreSQL only). Not compiled, not exploitable. CI uses `cargo audit --vulnerable-path` which only scans the compiled dependency tree, so this advisory is automatically skipped.
