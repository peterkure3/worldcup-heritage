use actix_web::{get, web, HttpResponse, Responder};
use std::sync::Mutex;
use crate::models::prediction::{Prediction, TournamentSimulation};

pub struct PredictionState {
    pub predictions: Mutex<Vec<Prediction>>,
    pub simulation: Mutex<Option<TournamentSimulation>>,
}

#[get("/api/predictions")]
pub async fn get_predictions(state: web::Data<PredictionState>) -> impl Responder {
    let predictions = state.predictions.lock().unwrap();
    HttpResponse::Ok().json(predictions.clone())
}

#[get("/api/matches/{id}/prediction")]
pub async fn get_match_prediction(
    state: web::Data<PredictionState>,
    path: web::Path<i64>,
) -> impl Responder {
    let id = path.into_inner();
    let predictions = state.predictions.lock().unwrap();
    match predictions.iter().find(|p| p.match_id == id) {
        Some(p) => HttpResponse::Ok().json(p),
        None => HttpResponse::NotFound().json(serde_json::json!({"error": "prediction not found"})),
    }
}

#[get("/api/predictions/tournament")]
pub async fn get_tournament_prediction(
    state: web::Data<PredictionState>,
) -> impl Responder {
    let sim = state.simulation.lock().unwrap();
    match sim.as_ref() {
        Some(s) => HttpResponse::Ok().json(s),
        None => HttpResponse::NotFound().json(serde_json::json!({"error": "tournament simulation not available"})),
    }
}
