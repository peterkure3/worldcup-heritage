use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TeamStanding {
    pub team_id: i64,
    pub team_name: String,
    pub flag_svg: String,
    pub flag_png: String,
    pub fifa_code: String,
    pub iso2: String,
    pub played: i64,
    pub won: i64,
    pub drawn: i64,
    pub lost: i64,
    pub goals_for: i64,
    pub goals_against: i64,
    pub goal_diff: i64,
    pub points: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GroupInfo {
    pub name: String,
    pub teams: Vec<String>,
    pub standings: Vec<TeamStanding>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GroupsData {
    pub groups: Vec<GroupInfo>,
}
