PRAGMA foreign_keys = ON;

-- Stores the websites or analysts we collect information from.
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    base_url TEXT,
    source_type TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Stores each college football game once.
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season INTEGER NOT NULL,
    week INTEGER,
    game_date TEXT,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled',
    home_score INTEGER,
    away_score INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(season, home_team, away_team, game_date)
);

-- Stores each article discovered from a registered source.
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    author TEXT,
    published_at TEXT,
    collected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    article_text TEXT,
    processed INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (source_id)
        REFERENCES sources(id)
        ON DELETE RESTRICT
);

-- Stores individual betting opinions extracted from articles.
CREATE TABLE IF NOT EXISTS bet_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    game_id INTEGER NOT NULL,

    market_type TEXT NOT NULL,

    selection TEXT NOT NULL,

    line REAL,

    odds INTEGER,

    direction TEXT,

    confidence REAL,

    reasoning TEXT,

    observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (article_id)
        REFERENCES articles(id)
        ON DELETE CASCADE,

    FOREIGN KEY (game_id)
        REFERENCES games(id)
        ON DELETE RESTRICT
);

-- Helps future searches by source.
CREATE INDEX IF NOT EXISTS idx_articles_source
ON articles(source_id);

-- Helps find all observations associated with a game.
CREATE INDEX IF NOT EXISTS idx_observations_game
ON bet_observations(game_id);

-- Helps find all observations extracted from an article.
CREATE INDEX IF NOT EXISTS idx_observations_article
ON bet_observations(article_id);
