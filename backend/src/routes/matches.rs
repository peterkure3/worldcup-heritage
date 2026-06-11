use actix_web::{get, web, HttpResponse, Responder};
use crate::models::match_model::Match;

pub struct AppState {
    pub matches: std::sync::Mutex<Vec<Match>>,
}

#[get("/api/matches")]
pub async fn get_matches(data: web::Data<AppState>) -> impl Responder {
    let matches = data.matches.lock().unwrap();
    HttpResponse::Ok().json(matches.clone())
}

#[get("/api/matches/{id}")]
pub async fn get_match(data: web::Data<AppState>, path: web::Path<i64>) -> impl Responder {
    let id = path.into_inner();
    let matches = data.matches.lock().unwrap();
    match matches.iter().find(|m| m.match_id == id) {
        Some(m) => HttpResponse::Ok().json(m),
        None => HttpResponse::NotFound().json(serde_json::json!({"error": "match not found"})),
    }
}
