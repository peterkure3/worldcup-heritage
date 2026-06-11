mod models;
mod routes;
mod db;

use actix_web::{web, App, HttpServer};
use actix_cors::Cors;
use routes::matches::AppState;
use routes::predictions::PredictionState;
use routes::groups::GroupsState;
use tracing_actix_web::TracingLogger;

fn load_matches() -> Vec<models::match_model::Match> {
    let path = std::env::var("MATCHES_PATH")
        .unwrap_or_else(|_| "../pipeline/data/raw/2026_matches.parquet".into());
    tracing::info!("Loading matches from: {}", path);
    Vec::new()
}

fn load_predictions() -> Vec<models::prediction::Prediction> {
    let path = std::env::var("PREDICTIONS_PATH")
        .unwrap_or_else(|_| "../artifacts/predictions/2026_predictions_xgboost_v1_tuned.json".into());
    match std::fs::read_to_string(&path) {
        Ok(content) => {
            match serde_json::from_str::<Vec<models::prediction::Prediction>>(&content) {
                Ok(preds) => {
                    tracing::info!("Loaded {} predictions", preds.len());
                    preds
                }
                Err(e) => {
                    tracing::warn!("Failed to parse predictions: {}", e);
                    Vec::new()
                }
            }
        }
        Err(e) => {
            tracing::warn!("Failed to read predictions file: {}", e);
            Vec::new()
        }
    }
}

fn load_groups() -> models::groups::GroupsData {
    let path = std::env::var("GROUPS_PATH")
        .unwrap_or_else(|_| "../artifacts/groups.json".into());
    match std::fs::read_to_string(&path) {
        Ok(content) => {
            match serde_json::from_str::<models::groups::GroupsData>(&content) {
                Ok(data) => {
                    tracing::info!("Loaded {} groups", data.groups.len());
                    data
                }
                Err(e) => {
                    tracing::warn!("Failed to parse groups: {}", e);
                    models::groups::GroupsData { groups: vec![] }
                }
            }
        }
        Err(e) => {
            tracing::warn!("Failed to read groups file: {}", e);
            models::groups::GroupsData { groups: vec![] }
        }
    }
}

fn load_simulation() -> Option<models::prediction::TournamentSimulation> {
    let path = std::env::var("SIMULATION_PATH")
        .unwrap_or_else(|_| "../artifacts/predictions/tournament_simulation_xgboost_v1_tuned.json".into());
    match std::fs::read_to_string(&path) {
        Ok(content) => {
            match serde_json::from_str::<models::prediction::TournamentSimulation>(&content) {
                Ok(sim) => {
                    tracing::info!("Loaded tournament simulation");
                    Some(sim)
                }
                Err(e) => {
                    tracing::warn!("Failed to parse simulation: {}", e);
                    None
                }
            }
        }
        Err(e) => {
            tracing::warn!("Failed to read simulation file: {}", e);
            None
        }
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    tracing_subscriber::fmt::init();

    let host = dotenvy::var("HOST").unwrap_or_else(|_| "0.0.0.0".into());
    let port: u16 = dotenvy::var("PORT")
        .unwrap_or_else(|_| "7777".into())
        .parse()
        .expect("PORT must be a valid number");

    // Connect to PostgreSQL
    let db_pool = match db::create_pool().await {
        Ok(pool) => {
            db::seed_database(&pool).await;
            Some(pool)
        }
        Err(e) => {
            tracing::warn!("PostgreSQL not available: {} — running without DB", e);
            None
        }
    };

    let matches = load_matches();
    let predictions = load_predictions();
    let simulation = load_simulation();
    let groups = load_groups();

    tracing::info!(
        "Starting server at {}:{} ({} matches, {} predictions, {} groups)",
        host, port, matches.len(), predictions.len(), groups.groups.len()
    );

    let app_state = web::Data::new(AppState {
        matches: std::sync::Mutex::new(matches),
    });
    let pred_state = web::Data::new(PredictionState {
        predictions: std::sync::Mutex::new(predictions),
        simulation: std::sync::Mutex::new(simulation),
    });
    let groups_state = web::Data::new(GroupsState {
        groups: std::sync::Mutex::new(groups),
    });

    let db_pool_data = web::Data::new(db_pool);

    HttpServer::new(move || {
        let cors = Cors::permissive();
        App::new()
            .wrap(cors)
            .wrap(TracingLogger::default())
            .app_data(app_state.clone())
            .app_data(pred_state.clone())
            .app_data(groups_state.clone())
            .app_data(db_pool_data.clone())
            .service(routes::health::health)
            .service(routes::health::db_status)
            .service(routes::matches::get_matches)
            .service(routes::matches::get_match)
            .service(routes::predictions::get_predictions)
            .service(routes::predictions::get_match_prediction)
            .service(routes::predictions::get_tournament_prediction)
            .service(routes::groups::get_groups)
    })
    .bind((host.as_str(), port))?
    .run()
    .await
}
