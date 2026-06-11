use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Match {
    pub match_id: i64,
    pub season: i32,
    pub utc_date: String,
    pub status: String,
    pub stage: String,
    pub group_name: Option<String>,
    pub matchday: Option<i32>,
    pub home_team: String,
    pub home_team_tla: String,
    pub away_team: String,
    pub away_team_tla: String,
    pub home_score: Option<i32>,
    pub away_score: Option<i32>,
    pub winner: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MatchWithPrediction {
    #[serde(flatten)]
    pub match_data: Match,
    pub prediction: Option<PredictionOutcome>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PredictionOutcome {
    pub home_win_prob: f64,
    pub draw_prob: f64,
    pub away_win_prob: f64,
    pub predicted_winner: String,
    pub confidence: f64,
}
