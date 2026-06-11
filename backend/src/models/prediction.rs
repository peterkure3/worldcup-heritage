use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Prediction {
    pub match_id: i64,
    pub home_team: String,
    pub away_team: String,
    pub home_win_prob: f64,
    pub draw_prob: f64,
    pub away_win_prob: f64,
    pub predicted_winner: String,
    pub confidence: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TournamentSimulation {
    pub n_simulations: u32,
    pub champion_probabilities: HashMap<String, f64>,
    pub top_champion: Option<String>,
    pub top_champion_prob: f64,
}
