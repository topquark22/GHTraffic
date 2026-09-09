# GHTraffic Data Model

## Overview

GHTraffic uses the stable numeric GitHub repository ID as the canonical identifier for a repository. Repository names are treated as mutable historical attributes because a repository may be renamed without changing its GitHub ID.

Traffic records therefore reference `repository_id`, never a repository name.

The authoritative schema is defined in `ddl.sql`.

## SQLite DDL

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE repositories (
    repository_id   INTEGER PRIMARY KEY,
    is_private      INTEGER NOT NULL DEFAULT 0,
    is_archived     INTEGER NOT NULL DEFAULT 0,
    is_fork         INTEGER NOT NULL DEFAULT 0,
    default_branch  TEXT,
    created_at      TEXT,
    updated_at      TEXT
);

CREATE TABLE repository_names (
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

CREATE UNIQUE INDEX idx_repository_names_current
    ON repository_names(repository_id)
    WHERE valid_to IS NULL;

CREATE INDEX idx_repository_names_full_name
    ON repository_names(full_name);

CREATE TABLE daily_traffic (
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

CREATE INDEX idx_daily_traffic_date
    ON daily_traffic(traffic_date);

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
```

## Table semantics

### `repositories`

`repository_id` is the numeric ID assigned by GitHub. No separate local surrogate key is used.

The table stores repository attributes that are not part of the repository name history:

- whether the repository is private
- whether it is archived
- whether it is a fork
- the default branch
- GitHub's repository creation timestamp (`created_at`)
- GitHub's repository update timestamp (`updated_at`)

Forked repositories are excluded from collection before they are inserted by the collector.

### `repository_names`

This table records repository naming history.

A repository may have only one row whose `valid_to` is `NULL`; that row represents the current name. When a rename or ownership change is detected, GHTraffic closes the current row by setting `valid_to` and inserts a new row with the same `repository_id`.

`owner_login`, `repository_name`, and `full_name` are retained so reports can use the current repository name while historical identity remains tied to the stable GitHub ID.

### `daily_traffic`

This table stores one row per repository per GitHub traffic date.

The composite primary key `(repository_id, traffic_date)` makes collection idempotent and supports upserting the full traffic window returned by GitHub on every collection run.

`collected_at` records when the row was most recently refreshed from GitHub.

### `referral_traffic`

This table stores snapshots of GitHub's top referrers for each repository.

GitHub returns referrer data as a rolling 14-day aggregate rather than as daily observations. Each collection therefore stores the current snapshot using `collected_date`.

The composite primary key `(repository_id, collected_date, referrer)` allows one row per referrer in each daily snapshot.

`views` is the number of visits attributed to the referrer during GitHub's trailing 14-day window, and `uniques` is GitHub's unique count for that referrer over the same window.

The table is created with `CREATE TABLE IF NOT EXISTS`, so the schema extension can be applied directly to an existing database without a separate migration path.

## Example upsert

```sql
INSERT INTO daily_traffic (
    repository_id,
    traffic_date,
    views,
    unique_visitors,
    clones,
    unique_cloners,
    collected_at
)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(repository_id, traffic_date)
DO UPDATE SET
    views           = excluded.views,
    unique_visitors = excluded.unique_visitors,
    clones          = excluded.clones,
    unique_cloners  = excluded.unique_cloners,
    collected_at    = excluded.collected_at;
```

## Current-name query

```sql
SELECT
    r.repository_id,
    n.owner_login,
    n.repository_name,
    n.full_name,
    r.is_private,
    r.is_archived,
    r.is_fork,
    r.default_branch
FROM repositories AS r
JOIN repository_names AS n
    ON n.repository_id = r.repository_id
WHERE n.valid_to IS NULL;
```

## Reporting

The `show [days]` command aggregates `daily_traffic` over the requested date window and joins to the current row in `repository_names`.

By default, `show` reports the most recent 14 days. Repositories with no views and no clones during the selected period are omitted.

Multi-day sums of `unique_visitors` or `unique_cloners` are not true multi-day unique counts, because GitHub does not expose identities that would allow the same visitor or cloner to be deduplicated across multiple days.

Referral data is inherently a rolling 14-day snapshot and should be presented as such rather than aggregated as though it represented independent daily counts.

## Notes

Dates and timestamps are stored as ISO 8601 text. SQLite does not provide a dedicated date/time storage class, and ISO 8601 text preserves chronological ordering while remaining compatible with SQLite date functions.
