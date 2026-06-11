use std::collections::HashMap;
use std::time::Duration;

use actix_web::web;
use reqwest::Client;
use serde::Deserialize;
use sqlx::{PgPool, Row};

use crate::models::match_model::Match;
use crate::models::groups::{GroupsData, TeamStanding};

const API_BASE: &str = "https://api.football-data.org/v4";
const POLL_INTERVAL: u64 = 300; // 5 minutes

static TEAM_NAME_MAP: &[(&str, &str)] = &[
    ("Bosnia-Herzegovina", "Bosnia and Herzegovina"),
    ("Cape Verde Islands", "Cape Verde"),
    ("Congo DR", "DR Congo"),
    ("Czechia", "Czech Republic"),
];

fn normalize_name(name: &str) -> &str {
    for (from, to) in TEAM_NAME_MAP {
        if *from == name {
            return to;
        }
    }
    name
}

#[derive(Deserialize, Debug)]
#[serde(rename_all = "camelCase")]
struct ApiMatch {
    id: i64,
    utc_date: String,
    status: String,
    stage: String,
    group: Option<String>,
    matchday: Option<i32>,
    home_team: ApiTeam,
    away_team: ApiTeam,
    score: ApiScore,
}

#[derive(Deserialize, Debug)]
struct ApiTeam {
    name: String,
    tla: String,
}

#[derive(Deserialize, Debug)]
#[serde(rename_all = "camelCase")]
struct ApiScore {
    full_time: ApiFullTime,
    winner: Option<String>,
}

#[derive(Deserialize, Debug)]
#[serde(rename_all = "camelCase")]
struct ApiFullTime {
    home: Option<i32>,
    away: Option<i32>,
}

#[derive(Deserialize, Debug)]
struct ApiResponse {
    matches: Vec<ApiMatch>,
}

pub fn start(
    api_key: String,
    matches_state: web::Data<super::routes::matches::AppState>,
    groups_state: web::Data<super::routes::groups::GroupsState>,
    db_pool: web::Data<Option<PgPool>>,
    artifacts_path: String,
) {
    tokio::spawn(async move {
        tracing::info!("poller started (interval={POLL_INTERVAL}s)");
        let client = Client::new();
        let url = format!("{API_BASE}/competitions/WC/matches?season=2026");
        let artifacts = std::path::PathBuf::from(&artifacts_path);

        loop {
            match poll(&client, &url, &api_key, &matches_state, &groups_state, &db_pool, &artifacts).await {
                Ok(updated) => {
                    if updated {
                        tracing::info!("poller: data updated");
                    }
                }
                Err(e) => tracing::warn!("poller: {e}"),
            }
            tokio::time::sleep(Duration::from_secs(POLL_INTERVAL)).await;
        }
    });
}

async fn poll(
    client: &Client,
    url: &str,
    api_key: &str,
    matches_state: &web::Data<super::routes::matches::AppState>,
    groups_state: &web::Data<super::routes::groups::GroupsState>,
    db_pool: &web::Data<Option<PgPool>>,
    artifacts: &std::path::Path,
) -> Result<bool, Box<dyn std::error::Error>> {
    let resp = client
        .get(url)
        .header("X-Auth-Token", api_key)
        .timeout(Duration::from_secs(15))
        .send()
        .await?;

    let body = resp.text().await?;
    let api_data: ApiResponse = match serde_json::from_str(&body) {
        Ok(d) => d,
        Err(e) => {
            tracing::error!("poller JSON parse error: {e}");
            tracing::error!("poller response body (first 500 chars): {}", &body[..body.len().min(500)]);
            return Err(e.into());
        }
    };

    let matches = normalize_matches(&api_data.matches);
    let finished_count = matches.iter().filter(|m| m.status == "FINISHED").count();

    tracing::info!(
        "poller: {} matches ({} finished)",
        matches.len(),
        finished_count
    );

    // Update in-memory matches
    {
        let mut ms = matches_state.matches.lock().unwrap();
        *ms = matches.clone();
    }

    // Save to JSON
    if let Ok(json) = serde_json::to_string_pretty(&matches) {
        let path = artifacts.join("2026_matches.json");
        if let Err(e) = std::fs::write(&path, &json) {
            tracing::warn!("poller: failed to write matches JSON: {e}");
        }
    }

    // Update group standings from finished matches
    let groups_path = artifacts.join("groups.json");
    if finished_count > 0 {
        if let Ok(content) = std::fs::read_to_string(&groups_path) {
            if let Ok(mut groups_data) = serde_json::from_str::<GroupsData>(&content) {
                update_standings(&matches, &mut groups_data);

                // Update in-memory groups
                {
                    let mut gs = groups_state.groups.lock().unwrap();
                    *gs = groups_data.clone();
                }

                // Save to JSON
                if let Ok(json) = serde_json::to_string_pretty(&groups_data) {
                    if let Err(e) = std::fs::write(&groups_path, &json) {
                        tracing::warn!("poller: failed to write groups JSON: {e}");
                    }
                }

                // Persist to DB
                if let Some(ref pool) = ***db_pool {
                    persist_matches(pool, &matches).await;
                }
            }
        }
    }

    Ok(finished_count > 0)
}

fn normalize_matches(api_matches: &[ApiMatch]) -> Vec<Match> {
    api_matches
        .iter()
        .map(|m| {
            let group = m.group.as_deref().unwrap_or("");
            let home_name = normalize_name(&m.home_team.name);
            let away_name = normalize_name(&m.away_team.name);
            let winner = m.score.winner.as_deref().and_then(|w| match w {
                "HOME_TEAM" => Some(home_name.to_string()),
                "AWAY_TEAM" => Some(away_name.to_string()),
                _ => None,
            });
            Match {
                match_id: m.id,
                season: 2026,
                utc_date: m.utc_date.clone(),
                status: m.status.clone(),
                stage: m.stage.clone(),
                group_name: Some(group.strip_prefix("GROUP_").unwrap_or(group).to_string())
                    .filter(|s| !s.is_empty()),
                matchday: m.matchday,
                home_team: home_name.to_string(),
                home_team_tla: m.home_team.tla.clone(),
                away_team: away_name.to_string(),
                away_team_tla: m.away_team.tla.clone(),
                home_score: m.score.full_time.home,
                away_score: m.score.full_time.away,
                winner,
            }
        })
        .collect()
}

fn update_standings(matches: &[Match], groups_data: &mut GroupsData) {
    let mut groups_map: HashMap<String, &mut Vec<TeamStanding>> = HashMap::new();
    for group in &mut groups_data.groups {
        for s in &mut group.standings {
            s.played = 0;
            s.won = 0;
            s.drawn = 0;
            s.lost = 0;
            s.goals_for = 0;
            s.goals_against = 0;
            s.goal_diff = 0;
            s.points = 0;
        }
        groups_map.insert(group.name.clone(), &mut group.standings);
    }

    for m in matches {
        if m.status != "FINISHED" {
            continue;
        }
        let (Some(hg), Some(ag)) = (m.home_score, m.away_score) else {
            continue;
        };
        let gname = match &m.group_name {
            Some(n) => n.as_str(),
            None => continue,
        };
        let Some(standings) = groups_map.get_mut(gname) else {
            continue;
        };

        let home_idx = standings.iter().position(|s| s.team_name == m.home_team);
        let away_idx = standings.iter().position(|s| s.team_name == m.away_team);
        let (Some(hi), Some(ai)) = (home_idx, away_idx) else {
            continue;
        };

        let hg = hg as i64;
        let ag = ag as i64;

        standings[hi].played += 1;
        standings[hi].goals_for += hg;
        standings[hi].goals_against += ag;
        standings[ai].played += 1;
        standings[ai].goals_for += ag;
        standings[ai].goals_against += hg;

        if hg > ag {
            standings[hi].won += 1;
            standings[hi].points += 3;
            standings[ai].lost += 1;
        } else if ag > hg {
            standings[ai].won += 1;
            standings[ai].points += 3;
            standings[hi].lost += 1;
        } else {
            standings[hi].drawn += 1;
            standings[hi].points += 1;
            standings[ai].drawn += 1;
            standings[ai].points += 1;
        }
    }

    for group in &mut groups_data.groups {
        for s in &mut group.standings {
            s.goal_diff = s.goals_for - s.goals_against;
        }
        group.standings.sort_by(|a, b| {
            b.points
                .cmp(&a.points)
                .then_with(|| b.goal_diff.cmp(&a.goal_diff))
                .then_with(|| b.goals_for.cmp(&a.goals_for))
        });
    }
}

async fn persist_matches(pool: &PgPool, matches: &[Match]) {
    let rows = match sqlx::query("SELECT id, name FROM teams").fetch_all(pool).await {
        Ok(r) => r,
        Err(e) => {
            tracing::warn!("poller db: failed to query teams: {e}");
            return;
        }
    };

    let team_map: HashMap<String, i64> = rows
        .iter()
        .filter_map(|r| {
            let id: i64 = r.get(0);
            let name: String = r.get(1);
            Some((name, id))
        })
        .collect();

    let finished: Vec<&Match> = matches
        .iter()
        .filter(|m| m.status == "FINISHED" && m.home_score.is_some() && m.away_score.is_some())
        .collect();

    for m in &finished {
        let (Some(home_id), Some(away_id)) = (
            team_map.get(&m.home_team).copied(),
            team_map.get(&m.away_team).copied(),
        ) else {
            tracing::warn!("poller db: unknown team '{}' or '{}'", m.home_team, m.away_team);
            continue;
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
            Ok(r) if r.rows_affected() == 0 => {
                let _ = sqlx::query(
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
            }
            Err(e) => tracing::warn!("poller db: update error for {} vs {}: {e}", m.home_team, m.away_team),
            _ => {}
        }
    }
}
