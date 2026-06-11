# Tech Stack

## Core AI/ML Pipeline
- **Language:** Python 3.12+
- **ML/Data:** pandas, numpy, scikit-learn, xgboost, lightgbm
- **Deep Learning:** PyTorch or TensorFlow (TBD)
- **Features:** Feature-engine, optuna (hyperparameter tuning)
- **Data Sources:** FIFA rankings, historical match data, tournament stats

## Backend API (serving predictions)
- **Language:** Rust (latest stable)
- **Framework:** Actix-Web
- **API Style:** RESTful JSON API
- **Database:** PostgreSQL (match data, predictions)

## Frontend (visualization)
- **Framework:** React 18+ with TypeScript
- **Build Tool:** Vite
- **CSS/Styling:** Tailwind CSS
- **Visualization:** D3.js / Chart.js (TBD)
- **State Management:** React Query / Zustand (TBD)

## Infrastructure
- **Containerization:** Docker, Docker Compose
- **CI/CD:** GitHub Actions

## Shared
- **Data Schemas:** Defined in shared/ (OpenAPI, JSON Schema)
- **Model Artifacts:** Stored in artifacts/
