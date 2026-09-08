PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS repositories (
    repository_id   INTEGER PRIMARY KEY,
    is_private      INTEGER NOT NULL DEFAULT 0,
    is_archived     INTEGER NOT NULL DEFAULT 0,
    is_fork         INTEGER NOT NULL DEFAULT 0,
    default_branch  TEXT,
    created_at      TEXT,
    updated_at      TEXT
);

CREATE TABLE IF NOT EXISTS repository_names (
    repository_id   INTEGER NOT NULL,
    owner_login     TEXT NOT NULL,
    repository_name TEXT NOT NULL,
    full_name       TEXT NOT NULL,
    valid_from      TEXT NOT NULL,
    valid_to        TEXT,

    PRIMARY KEY (repository_id, valid_from),

    FOREIGN KEY (repository_id)
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_repository_names_current
    ON repository_names(repository_id)
    WHERE valid_to IS NULL;

CREATE INDEX IF NOT EXISTS idx_repository_names_full_name
    ON repository_names(full_name);

CREATE TABLE IF NOT EXISTS daily_traffic (
    repository_id   INTEGER NOT NULL,
    traffic_date    TEXT NOT NULL,
    views           INTEGER NOT NULL DEFAULT 0,
    unique_visitors INTEGER NOT NULL DEFAULT 0,
    clones          INTEGER NOT NULL DEFAULT 0,
    unique_cloners  INTEGER NOT NULL DEFAULT 0,
    collected_at    TEXT NOT NULL,

    PRIMARY KEY (repository_id, traffic_date),

    FOREIGN KEY (repository_id)
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_daily_traffic_date
    ON daily_traffic(traffic_date);

CREATE TABLE IF NOT EXISTS referral_traffic (
    repository_id  INTEGER NOT NULL,
    collected_date TEXT NOT NULL,
    referrer       TEXT NOT NULL,
    views          INTEGER NOT NULL DEFAULT 0,
    uniques        INTEGER NOT NULL DEFAULT 0,

    PRIMARY KEY (repository_id, collected_date, referrer),

    FOREIGN KEY (repository_id)
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_referral_traffic_date
    ON referral_traffic(collected_date);
