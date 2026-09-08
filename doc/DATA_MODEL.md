# GitHubMonitor Data Model

## Overview

GitHubMonitor uses the stable numeric GitHub repository ID as the canonical identifier for a repository. Repository names are treated as mutable historical attributes because a repository may be renamed without changing its GitHub ID.

Traffic records therefore reference `repository_id`, never a repository name.

## SQLite DDL

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE repositories (
    repository_id   INTEGER PRIMARY KEY,
    is_private      INTEGER NOT NULL DEFAULT 0 CHECK (is_private IN (0, 1)),
    is_archived     INTEGER NOT NULL DEFAULT 0 CHECK (is_archived IN (0, 1)),
    is_fork         INTEGER NOT NULL DEFAULT 0 CHECK (is_fork IN (0, 1)),
    default_branch  TEXT,
    first_seen_at   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL
);

CREATE TABLE repository_names (
    repository_id   INTEGER NOT NULL,
    owner_name      TEXT NOT NULL,
    repository_name TEXT NOT NULL,
    full_name       TEXT NOT NULL,
    valid_from      TEXT NOT NULL,
    valid_to        TEXT,

    PRIMARY KEY (repository_id, valid_from),

    FOREIGN KEY (repository_id)
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,

    CHECK (full_name = owner_name || '/' || repository_name),
    CHECK (valid_to IS NULL OR valid_to > valid_from)
);

CREATE UNIQUE INDEX idx_repository_names_current
    ON repository_names(repository_id)
    WHERE valid_to IS NULL;

CREATE INDEX idx_repository_names_full_name
    ON repository_names(full_name);

CREATE TABLE daily_traffic (
    repository_id   INTEGER NOT NULL,
    traffic_date    TEXT NOT NULL,
    views           INTEGER NOT NULL DEFAULT 0 CHECK (views >= 0),
    unique_visitors INTEGER NOT NULL DEFAULT 0 CHECK (unique_visitors >= 0),
    clones          INTEGER NOT NULL DEFAULT 0 CHECK (clones >= 0),
    unique_cloners  INTEGER NOT NULL DEFAULT 0 CHECK (unique_cloners >= 0),
    collected_at    TEXT NOT NULL,

    PRIMARY KEY (repository_id, traffic_date),

    FOREIGN KEY (repository_id)
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE
);

CREATE INDEX idx_daily_traffic_date
    ON daily_traffic(traffic_date);
```

## Table semantics

### `repositories`

`repository_id` is the numeric ID assigned by GitHub. No separate local surrogate key is used.

The table stores repository attributes that are not part of the repository name history:

- whether the repository is private
- whether it is archived
- whether it is a fork
- the default branch
- the first time GitHubMonitor observed the repository
- the most recent time GitHubMonitor observed the repository

Although forked repositories are retained in the model if discovered, they are excluded from traffic collection.

### `repository_names`

This table records repository naming history.

A repository may have only one row whose `valid_to` is `NULL`; that row represents the current name. When a rename or ownership change is detected, GitHubMonitor closes the current row by setting `valid_to` and inserts a new row with the same `repository_id`.

`full_name` is retained explicitly for convenient querying, while the check constraint ensures that it remains consistent with `owner_name` and `repository_name`.

### `daily_traffic`

This table stores one row per repository per GitHub traffic date.

The composite primary key `(repository_id, traffic_date)` makes collection idempotent and supports upserting the full traffic window returned by GitHub on every collection run.

`collected_at` records when the row was most recently refreshed from GitHub.

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
    n.owner_name,
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

## Daily report query

```sql
SELECT
    n.full_name,
    t.views,
    t.unique_visitors,
    t.clones,
    t.unique_cloners
FROM daily_traffic AS t
JOIN repository_names AS n
    ON n.repository_id = t.repository_id
   AND n.valid_to IS NULL
WHERE t.traffic_date = ?
ORDER BY t.views DESC, t.clones DESC, n.full_name;
```

## Notes

Dates and timestamps are stored as ISO 8601 text. SQLite does not provide a dedicated date/time storage class, and ISO 8601 text preserves chronological ordering while remaining compatible with SQLite date functions.

Multi-day sums of `unique_visitors` or `unique_cloners` are not true multi-day unique counts, because GitHub does not expose identities that would allow the same visitor or cloner to be deduplicated across multiple days.
