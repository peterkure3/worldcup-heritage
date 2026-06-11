use actix_web::{post, web, HttpResponse, Responder};
use crate::models::match_model::Match;
use crate::models::prediction::{Prediction, TournamentSimulation};
use crate::models::groups::GroupsData;

#[post("/api/reload")]
pub async fn reload(
    matches_state: web::Data<super::matches::AppState>,
    pred_state: web::Data<super::predictions::PredictionState>,
    groups_state: web::Data<super::groups::GroupsState>,
) -> impl Responder {
    let mut reloaded = Vec::new();

    let matches_path = std::env::var("MATCHES_PATH")
        .unwrap_or_else(|_| "/app/artifacts/2026_matches.json".into());
    match std::fs::read_to_string(&matches_path) {
        Ok(content) => {
            match serde_json::from_str::<Vec<Match>>(&content) {
                Ok(m) => {
                    let mut ms = matches_state.matches.lock().unwrap();
                    *ms = m;
                    reloaded.push("matches");
                }
                Err(e) => tracing::warn!("reload matches parse: {e}"),
            }
        }
        Err(e) => tracing::warn!("reload matches read: {e}"),
    }

    let pred_path = std::env::var("PREDICTIONS_PATH")
        .unwrap_or_else(|_| "/app/artifacts/predictions/2026_predictions_xgboost_v1_tuned.json".into());
    match std::fs::read_to_string(&pred_path) {
        Ok(content) => {
            match serde_json::from_str::<Vec<Prediction>>(&content) {
                Ok(p) => {
                    let mut ps = pred_state.predictions.lock().unwrap();
                    *ps = p;
                    reloaded.push("predictions");
                }
                Err(e) => tracing::warn!("reload predictions parse: {e}"),
            }
        }
        Err(e) => tracing::warn!("reload predictions read: {e}"),
    }

    let groups_path = std::env::var("GROUPS_PATH")
        .unwrap_or_else(|_| "/app/artifacts/groups.json".into());
    match std::fs::read_to_string(&groups_path) {
        Ok(content) => {
            match serde_json::from_str::<GroupsData>(&content) {
                Ok(g) => {
                    let mut gs = groups_state.groups.lock().unwrap();
                    *gs = g;
                    reloaded.push("groups");
                }
                Err(e) => tracing::warn!("reload groups parse: {e}"),
            }
        }
        Err(e) => tracing::warn!("reload groups read: {e}"),
    }

    let sim_path = std::env::var("SIMULATION_PATH")
        .unwrap_or_else(|_| "/app/artifacts/predictions/tournament_simulation_xgboost_v1_tuned.json".into());
    match std::fs::read_to_string(&sim_path) {
        Ok(content) => {
            match serde_json::from_str::<TournamentSimulation>(&content) {
                Ok(s) => {
                    let mut ss = pred_state.simulation.lock().unwrap();
                    *ss = Some(s);
                    reloaded.push("simulation");
                }
                Err(e) => tracing::warn!("reload simulation parse: {e}"),
            }
        }
        Err(e) => tracing::warn!("reload simulation read: {e}"),
    }

    HttpResponse::Ok().json(serde_json::json!({
        "reloaded": reloaded
    }))
}
