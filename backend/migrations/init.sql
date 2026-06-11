CREATE TABLE IF NOT EXISTS teams (
    id          BIGINT PRIMARY KEY,
    name        TEXT NOT NULL,
    short_name  TEXT,
    tla         TEXT,
    crest_url   TEXT,
    confederation TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS matches (
    id              BIGINT PRIMARY KEY,
    season          INTEGER NOT NULL,
    utc_date        TIMESTAMP NOT NULL,
    status          TEXT NOT NULL DEFAULT 'TIMED',
    stage           TEXT NOT NULL,
    group_name      TEXT,
    matchday        INTEGER,
    home_team_id    BIGINT REFERENCES teams(id),
    away_team_id    BIGINT REFERENCES teams(id),
    home_score      INTEGER,
    away_score      INTEGER,
    winner          TEXT,
    venue           TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_matches_season ON matches(season);
CREATE INDEX IF NOT EXISTS idx_matches_stage ON matches(stage);

CREATE TABLE IF NOT EXISTS predictions (
    id              SERIAL PRIMARY KEY,
    match_id        BIGINT REFERENCES matches(id),
    model_name      TEXT NOT NULL,
    home_win_prob   REAL NOT NULL,
    draw_prob       REAL NOT NULL,
    away_win_prob   REAL NOT NULL,
    predicted_winner TEXT,
    confidence      REAL,
    model_version   TEXT,
    created_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(match_id, model_name, model_version)
);

CREATE TABLE IF NOT EXISTS tournament_predictions (
    id              SERIAL PRIMARY KEY,
    season          INTEGER NOT NULL,
    team_id         BIGINT REFERENCES teams(id),
    champion_prob   REAL NOT NULL DEFAULT 0,
    final_prob      REAL NOT NULL DEFAULT 0,
    semi_prob       REAL NOT NULL DEFAULT 0,
    quarter_prob    REAL NOT NULL DEFAULT 0,
    round_32_prob   REAL,
    group_advance_prob REAL,
    model_version   TEXT,
    created_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(season, team_id, model_version)
);
