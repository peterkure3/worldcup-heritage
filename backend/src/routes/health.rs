use actix_web::{get, web, HttpResponse, Responder};
use sqlx::PgPool;

#[get("/api/health")]
pub async fn health(db_pool: web::Data<Option<PgPool>>) -> impl Responder {
    let db_connected = match db_pool.as_ref() {
        Some(pool) => sqlx::query_scalar::<_, i32>("SELECT 1")
            .fetch_one(pool)
            .await
            .is_ok(),
        None => false,
    };

    HttpResponse::Ok().json(serde_json::json!({
        "status": "ok",
        "service": "worldcup-heritage-api",
        "version": "0.1.0",
        "database": db_connected
    }))
}

#[get("/api/db/status")]
pub async fn db_status(db_pool: web::Data<Option<PgPool>>) -> impl Responder {
    match db_pool.as_ref() {
        Some(pool) => {
            match sqlx::query_as::<_, (i64, i64, i64, i64)>(
                "SELECT (SELECT COUNT(*) FROM teams), (SELECT COUNT(*) FROM matches), (SELECT COUNT(*) FROM predictions), (SELECT COUNT(*) FROM tournament_predictions)"
            )
            .fetch_one(pool)
            .await
            {
                Ok((teams, matches, predictions, tournament)) => {
                    HttpResponse::Ok().json(serde_json::json!({
                        "connected": true,
                        "teams": teams,
                        "matches": matches,
                        "predictions": predictions,
                        "tournament_predictions": tournament,
                    }))
                }
                Err(e) => {
                    HttpResponse::Ok().json(serde_json::json!({
                        "connected": false,
                        "error": e.to_string()
                    }))
                }
            }
        }
        None => {
            HttpResponse::Ok().json(serde_json::json!({
                "connected": false,
                "error": "No database pool configured"
            }))
        }
    }
}
