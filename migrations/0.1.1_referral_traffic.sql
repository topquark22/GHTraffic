PRAGMA foreign_keys = ON;

CREATE TABLE referral_traffic (
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

CREATE INDEX idx_referral_traffic_date
    ON referral_traffic(collected_date);
