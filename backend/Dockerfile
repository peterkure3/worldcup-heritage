FROM rust:slim-bookworm AS builder
WORKDIR /app

RUN apt-get update && apt-get install -y pkg-config libssl-dev && rm -rf /var/lib/apt/lists/*

COPY backend/Cargo.toml backend/Cargo.lock ./
COPY backend/src/ src/
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app

COPY --from=builder /app/target/release/worldcup-heritage-api /app/

COPY artifacts/groups.json /app/artifacts/groups.json
COPY artifacts/predictions/2026_predictions_xgboost_v1_tuned.json /app/artifacts/predictions/2026_predictions_xgboost_v1_tuned.json
COPY artifacts/predictions/tournament_simulation_xgboost_v1_tuned.json /app/artifacts/predictions/tournament_simulation_xgboost_v1_tuned.json
COPY backend/migrations/init.sql /app/backend/migrations/init.sql

ENV MATCHES_PATH=/app/artifacts/2026_matches.json
ENV GROUPS_PATH=/app/artifacts/groups.json
ENV PREDICTIONS_PATH=/app/artifacts/predictions/2026_predictions_xgboost_v1_tuned.json
ENV SIMULATION_PATH=/app/artifacts/predictions/tournament_simulation_xgboost_v1_tuned.json
ENV MIGRATIONS_PATH=/app/backend/migrations/init.sql
ENV DATABASE_URL=postgres://worldcup:worldcup@postgres:5432/worldcup
ENV HOST=0.0.0.0
ENV PORT=7777

EXPOSE 7777
CMD ["/app/worldcup-heritage-api"]
