use sqlx::postgres::{PgPool, PgPoolOptions};
use sqlx::Row;
use std::collections::HashMap;

pub async fn create_pool() -> Result<PgPool, sqlx::Error> {
    let database_url =
        std::env::var("DATABASE_URL").unwrap_or_else(|_| "postgres://postgres:changeme@localhost:5432/worldcup_heritage".into());
    let pool = PgPoolOptions::new()
        .max_connections(5)
        .connect(&database_url)
        .await?;
    tracing::info!("Connected to PostgreSQL");
    Ok(pool)
}

pub async fn seed_database(pool: &PgPool) {
    run_migrations(pool).await;
    seed_teams(pool).await;
    seed_matches_and_predictions(pool).await;
    seed_tournament_predictions(pool).await;
}

async fn run_migrations(pool: &PgPool) {
    let path = std::env::var("MIGRATIONS_PATH")
        .unwrap_or_else(|_| "../backend/migrations/init.sql".into());
    let content = match std::fs::read_to_string(&path) {
        Ok(c) => c,
        Err(e) => {
            tracing::warn!("Cannot read migration file: {}", e);
            return;
        }
    };
    for statement in content.split(';') {
        let s = statement.trim();
        if s.is_empty() {
            continue;
        }
        if let Err(e) = sqlx::query(s).execute(pool).await {
            tracing::warn!("Migration statement failed (may be OK): {}", e);
        }
    }
    tracing::info!("Migrations applied");
}

fn normalize_name(name: &str) -> &str {
    match name {
        "Bosnia-Herzegovina" => "Bosnia and Herzegovina",
        "Cape Verde Islands" => "Cape Verde",
        "Congo DR" => "Democratic Republic of the Congo",
        "Czechia" => "Czech Republic",
        n if n.starts_with("Cura") => "Curaçao",
        n => n,
    }
}

async fn seed_teams(pool: &PgPool) {
    let path = std::env::var("GROUPS_PATH")
        .unwrap_or_else(|_| "../artifacts/groups.json".into());
    let content = match std::fs::read_to_string(&path) {
        Ok(c) => c,
        Err(e) => {
            tracing::warn!("Cannot read groups.json for seeding: {}", e);
            return;
        }
    };
    let groups_data: super::models::groups::GroupsData = match serde_json::from_str(&content) {
        Ok(d) => d,
        Err(e) => {
            tracing::warn!("Cannot parse groups.json: {}", e);
            return;
        }
    };

    let count = sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM teams")
        .fetch_one(pool)
        .await
        .unwrap_or(0);

    if count > 0 {
        tracing::info!("Teams table already has {} rows, skipping seed", count);
        return;
    }

    let mut inserted = 0i64;
    for group in &groups_data.groups {
        for team in &group.standings {
            let result = sqlx::query(
                "INSERT INTO teams (id, name, short_name, crest_url) VALUES ($1, $2, $3, $4) ON CONFLICT (id) DO NOTHING",
            )
            .bind(team.team_id)
            .bind(&team.team_name)
            .bind(&team.fifa_code)
            .bind(&team.flag_svg)
            .execute(pool)
            .await;
            if let Ok(r) = result {
                inserted += r.rows_affected() as i64;
            }
        }
    }
    tracing::info!("Seeded {} teams", inserted);
}

fn load_json<T>(env_key: &str, default_path: &str) -> Option<T>
where
    T: serde::de::DeserializeOwned,
{
    let path = std::env::var(env_key).unwrap_or_else(|_| default_path.into());
    let content = match std::fs::read_to_string(&path) {
        Ok(c) => c,
        Err(e) => {
            tracing::warn!("Cannot read {}: {}", path, e);
            return None;
        }
    };
    match serde_json::from_str(&content) {
        Ok(data) => Some(data),
        Err(e) => {
            tracing::warn!("Cannot parse {}: {}", path, e);
            None
        }
    }
}

async fn build_team_map(pool: &PgPool) -> HashMap<String, i64> {
    let mut map = HashMap::new();
    match sqlx::query("SELECT id, name FROM teams").fetch_all(pool).await {
        Ok(rows) => {
            for row in &rows {
                let id: i64 = match row.try_get(0) {
                    Ok(v) => v,
                    Err(_) => continue,
                };
                let name: String = match row.try_get(1) {
                    Ok(v) => v,
                    Err(_) => continue,
                };
                map.insert(name.clone(), id);
                let norm = normalize_name(&name).to_string();
                if norm != name {
                    map.entry(norm).or_insert(id);
                }
            }
        }
        Err(e) => {
            tracing::warn!("Failed to query teams: {}", e);
        }
    }
    map
}

async fn seed_matches_and_predictions(pool: &PgPool) {
    let predictions: Vec<super::models::prediction::Prediction> = match load_json(
        "PREDICTIONS_PATH",
        "../artifacts/predictions/2026_predictions_xgboost_v1_tuned.json",
    ) {
        Some(p) => p,
        None => return,
    };

    let team_map = build_team_map(pool).await;
    tracing::info!("Team cache built with {} entries", team_map.len());
    if team_map.is_empty() {
        tracing::warn!("No teams in database, skipping match/prediction seed");
        return;
    }

    let match_count = sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM matches")
        .fetch_one(pool)
        .await
        .unwrap_or(0);

    let mut match_inserted = 0i64;
    if match_count == 0 {
        for pred in &predictions {
            let home = normalize_name(&pred.home_team);
            let away = normalize_name(&pred.away_team);
            let home_id = team_map.get(home).copied().unwrap_or(0);
            let away_id = team_map.get(away).copied().unwrap_or(0);
            if home_id == 0 || away_id == 0 {
                tracing::warn!(
                    "Unknown team: '{}' (normalized='{}', found={}) or '{}' (normalized='{}', found={})",
                    pred.home_team, home, team_map.contains_key(home),
                    pred.away_team, away, team_map.contains_key(away)
                );
                continue;
            }
            let result = sqlx::query(
                "INSERT INTO matches (id, season, utc_date, status, stage, home_team_id, away_team_id) \
                 VALUES ($1, 2026, NOW(), 'TIMED', 'GROUP_STAGE', $2, $3) ON CONFLICT (id) DO NOTHING",
            )
            .bind(pred.match_id)
            .bind(home_id)
            .bind(away_id)
            .execute(pool)
            .await;
            if let Ok(r) = result {
                match_inserted += r.rows_affected() as i64;
            }
        }
        tracing::info!("Seeded {} matches", match_inserted);
    } else {
        tracing::info!("Matches table already has {} rows", match_count);
    }

    let pred_count = sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM predictions")
        .fetch_one(pool)
        .await
        .unwrap_or(0);

    if pred_count == 0 {
        let mut pred_inserted = 0i64;
        for pred in &predictions {
            let winner = if pred.predicted_winner == "Draw" {
                "Draw".to_string()
            } else {
                normalize_name(&pred.predicted_winner).to_string()
            };
            let result = sqlx::query(
                "INSERT INTO predictions (match_id, model_name, home_win_prob, draw_prob, away_win_prob, predicted_winner, confidence, model_version) \
                 VALUES ($1, 'xgboost_v1_tuned', $2, $3, $4, $5, $6, '1.0') ON CONFLICT (match_id, model_name, model_version) DO NOTHING",
            )
            .bind(pred.match_id)
            .bind(pred.home_win_prob)
            .bind(pred.draw_prob)
            .bind(pred.away_win_prob)
            .bind(&winner)
            .bind(pred.confidence)
            .execute(pool)
            .await;
            if let Ok(r) = result {
                pred_inserted += r.rows_affected() as i64;
            }
        }
        tracing::info!("Seeded {} predictions", pred_inserted);
    } else {
        tracing::info!("Predictions table already has {} rows", pred_count);
    }
}

async fn seed_tournament_predictions(pool: &PgPool) {
    let sim: super::models::prediction::TournamentSimulation = match load_json(
        "SIMULATION_PATH",
        "../artifacts/predictions/tournament_simulation_xgboost_v1_tuned.json",
    ) {
        Some(s) => s,
        None => return,
    };

    let count = sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM tournament_predictions")
        .fetch_one(pool)
        .await
        .unwrap_or(0);

    if count > 0 {
        tracing::info!("Tournament predictions already has {} rows", count);
        return;
    }

    let team_map = build_team_map(pool).await;
    let mut inserted = 0i64;
    for (team_name, prob) in &sim.champion_probabilities {
        let norm = normalize_name(team_name);
        if let Some(&team_id) = team_map.get(norm) {
            let result = sqlx::query(
                "INSERT INTO tournament_predictions (season, team_id, champion_prob, model_version) \
                 VALUES (2026, $1, $2, '1.0') ON CONFLICT (season, team_id, model_version) DO NOTHING",
            )
            .bind(team_id)
            .bind(prob)
            .execute(pool)
            .await;
            if let Ok(r) = result {
                inserted += r.rows_affected() as i64;
            }
        } else {
            tracing::warn!("Unknown team in champion_probabilities: '{}' (normalized: '{}')", team_name, norm);
        }
    }
    tracing::info!("Seeded {} tournament predictions", inserted);
}
