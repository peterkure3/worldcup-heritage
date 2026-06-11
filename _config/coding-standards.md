# Coding Standards

- **Python (pipeline):** Type-annotate all public functions, use pathlib, follow PEP 8
- **Rust (backend):** rustfmt, Clippy lints, prefer Result over panics
- **TypeScript (frontend):** strict mode, Prettier formatting
- **Notebooks:** Never commit raw notebooks; extract to .py scripts
- **Data:** Never commit raw data to git; use DVC or track via scripts/download.py
- **Models:** Version artifacts in artifacts/ with metadata
- **Tests:** Unit tests for feature engineering and model evaluation
