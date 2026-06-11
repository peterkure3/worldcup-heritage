use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Team {
    pub id: i64,
    pub name: String,
    pub short_name: Option<String>,
    pub tla: Option<String>,
    pub crest_url: Option<String>,
}
