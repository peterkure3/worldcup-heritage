# Architecture Principles

- **ML-First** — The prediction pipeline is the core of the project; everything else serves it
- **Separation of Concerns** — Data ingestion, feature engineering, model training, prediction serving, and visualization are distinct stages
- **Reproducibility** — All pipeline steps are deterministic; seed everything, version datasets and models
- **API-First Serving** — The frontend consumes predictions via REST API from the Rust backend
- **Modularity** — Each pipeline stage (data, features, train, predict) is independently runnable
- **Observability** — Log metrics, track experiments, monitor prediction drift
- **Maintainability** — Clean interfaces between stages, documented data schemas
