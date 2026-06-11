export interface MatchPrediction {
  match_id: number;
  home_team: string;
  away_team: string;
  home_win_prob: number;
  draw_prob: number;
  away_win_prob: number;
  predicted_winner: string;
  confidence: number;
}

export interface TeamProbability {
  team: string;
  champion_prob: number;
  final_prob: number;
  semi_prob: number;
  quarter_prob: number;
}

export interface TournamentSimulation {
  season: number;
  champion_probabilities: TeamProbability[];
}

export interface GroupMatch {
  match_id: number;
  home_team: string;
  away_team: string;
  home_win_prob: number;
  draw_prob: number;
  away_win_prob: number;
  predicted_winner: string;
}

export interface GroupData {
  name: string;
  teams: string[];
  matches: GroupMatch[];
}

export interface HealthResponse {
  status: string;
  matches_count: number;
  predictions_count: number;
}

export interface TeamStanding {
  team_id: number;
  team_name: string;
  flag_svg: string;
  flag_png: string;
  fifa_code: string;
  iso2: string;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goals_for: number;
  goals_against: number;
  goal_diff: number;
  points: number;
}

export interface GroupInfo {
  name: string;
  teams: string[];
  standings: TeamStanding[];
}

export interface GroupsData {
  groups: GroupInfo[];
}
