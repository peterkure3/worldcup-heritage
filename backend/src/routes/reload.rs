use actix_web::{post, web, HttpResponse, Responder};
use sqlx::PgPool;
use crate::models::match_model::Match;
use crate::models::prediction::{Prediction, TournamentSimulation};
use crate::models::groups::GroupsData;

#[post("/api/reload")]
pub async fn reload(
    matches_state: web::Data<super::matches::AppState>,
    pred_state: web::Data<super::predictions::PredictionState>,
    groups_state: web::Data<super::groups::GroupsState>,
    db_pool: web::Data<Option<PgPool>>,
) -> impl Responder {
    let mut reloaded = Vec::new();

    let matches_path = std::env::var("MATCHES_PATH")
        .unwrap_or_else(|_| "/app/artifacts/2026_matches.json".into());
    let live_matches: Option<Vec<Match>> = match std::fs::read_to_string(&matches_path) {
        Ok(content) => match serde_json::from_str::<Vec<Match>>(&content) {
            Ok(m) => {
                let mut ms = matches_state.matches.lock().unwrap();
                *ms = m.clone();
                reloaded.push("matches");
                Some(m)
            }
            Err(e) => {
                tracing::warn!("reload matches parse: {e}");
                None
            }
        },
        Err(e) => {
            tracing::warn!("reload matches read: {e}");
            None
        }
    };

    let pred_path = std::env::var("PREDICTIONS_PATH")
        .unwrap_or_else(|_| "/app/artifacts/predictions/2026_predictions_xgboost_v1_tuned.json".into());
    match std::fs::read_to_string(&pred_path) {
        Ok(content) => match serde_json::from_str::<Vec<Prediction>>(&content) {
            Ok(p) => {
                let mut ps = pred_state.predictions.lock().unwrap();
                *ps = p;
                reloaded.push("predictions");
            }
            Err(e) => tracing::warn!("reload predictions parse: {e}"),
        },
        Err(e) => tracing::warn!("reload predictions read: {e}"),
    }

    let groups_path = std::env::var("GROUPS_PATH")
        .unwrap_or_else(|_| "/app/artifacts/groups.json".into());
    match std::fs::read_to_string(&groups_path) {
        Ok(content) => match serde_json::from_str::<GroupsData>(&content) {
            Ok(g) => {
                let mut gs = groups_state.groups.lock().unwrap();
                *gs = g;
                reloaded.push("groups");
            }
            Err(e) => tracing::warn!("reload groups parse: {e}"),
        },
        Err(e) => tracing::warn!("reload groups read: {e}"),
    }

    let sim_path = std::env::var("SIMULATION_PATH")
        .unwrap_or_else(|_| "/app/artifacts/predictions/tournament_simulation_xgboost_v1_tuned.json".into());
    match std::fs::read_to_string(&sim_path) {
        Ok(content) => match serde_json::from_str::<TournamentSimulation>(&content) {
            Ok(s) => {
                let mut ss = pred_state.simulation.lock().unwrap();
                *ss = Some(s);
                reloaded.push("simulation");
            }
            Err(e) => tracing::warn!("reload simulation parse: {e}"),
        },
        Err(e) => tracing::warn!("reload simulation read: {e}"),
    }

    // Persist live match results to PostgreSQL if available
    if let Some(ref pool) = *db_pool {
        if let Some(ref matches) = live_matches {
            let updated = persist_matches(pool, matches).await;
            if updated > 0 {
                tracing::info!("Persisted {updated} match results to DB");
            }
        }
    }

    HttpResponse::Ok().json(serde_json::json!({
        "reloaded": reloaded
    }))
}

async fn persist_matches(pool: &PgPool, matches: &[Match]) -> u64 {
    let finished: Vec<&Match> = matches
        .iter()
        .filter(|m| m.status == "FINISHED" && m.home_score.is_some() && m.away_score.is_some())
        .collect();

    if finished.is_empty() {
        return 0;
    }

    // Load team name -> id map from DB
    let rows = match sqlx::query("SELECT id, name FROM teams").fetch_all(pool).await {
        Ok(r) => r,
        Err(e) => {
            tracing::warn!("persist: failed to query teams: {e}");
            return 0;
        }
    };

    let team_map: std::collections::HashMap<String, i64> = rows
        .iter()
        .filter_map(|r| {
            let id: i64 = r.get(0);
            let name: String = r.get(1);
            Some((name, id))
        })
        .collect();

    let mut count = 0u64;
    for m in &finished {
        let home_id = match team_map.get(&m.home_team) {
            Some(&id) => id,
            None => {
                tracing::warn!("persist: unknown home team '{}'", m.home_team);
                continue;
            }
        };
        let away_id = match team_map.get(&m.away_team) {
            Some(&id) => id,
            None => {
                tracing::warn!("persist: unknown away team '{}'", m.away_team);
                continue;
            }
        };

        let result = sqlx::query(
            "UPDATE matches SET home_score = $1, away_score = $2, winner = $3, status = $4, utc_date = $5::timestamptz \
             WHERE home_team_id = $6 AND away_team_id = $7 AND season = 2026",
        )
        .bind(m.home_score)
        .bind(m.away_score)
        .bind(&m.winner)
        .bind(&m.status)
        .bind(&m.utc_date)
        .bind(home_id)
        .bind(away_id)
        .execute(pool)
        .await;

        match result {
            Ok(r) => {
                if r.rows_affected() > 0 {
                    count += r.rows_affected();
                } else {
                    // Match not found by teams; try inserting by match_id
                    let insert_result = sqlx::query(
                        "INSERT INTO matches (id, season, utc_date, status, stage, group_name, matchday, \
                         home_team_id, away_team_id, home_score, away_score, winner) \
                         VALUES ($1, 2026, $2::timestamptz, $3, $4, $5, $6, $7, $8, $9, $10, $11) \
                         ON CONFLICT (id) DO UPDATE SET \
                         home_score = EXCLUDED.home_score, away_score = EXCLUDED.away_score, \
                         winner = EXCLUDED.winner, status = EXCLUDED.status",
                    )
                    .bind(m.match_id)
                    .bind(&m.utc_date)
                    .bind(&m.status)
                    .bind(&m.stage)
                    .bind(&m.group_name)
                    .bind(m.matchday)
                    .bind(home_id)
                    .bind(away_id)
                    .bind(m.home_score)
                    .bind(m.away_score)
                    .bind(&m.winner)
                    .execute(pool)
                    .await;

                    if let Ok(ir) = insert_result {
                        count += ir.rows_affected();
                    }
                }
            }
            Err(e) => tracing::warn!("persist: update error for {} vs {}: {e}", m.home_team, m.away_team),
        }
    }
    count
}
