#!/usr/bin/env python3

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DB_FILENAME = "githubtraffic.db"
GITHUB_API = "https://api.github.com"
REQUIRED_TABLES = {
    "repositories",
    "repository_names",
    "daily_traffic",
}


def default_db_path():
    override = os.environ.get("GITHUBMONITOR_DB")
    if override:
        return Path(override).expanduser()

    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise RuntimeError("LOCALAPPDATA is not set")

        return Path(local_app_data) / "GitHubMonitor" / DB_FILENAME

    data_home = os.environ.get("XDG_DATA_HOME")
    if data_home:
        return Path(data_home).expanduser() / "githubmonitor" / DB_FILENAME

    return Path.home() / ".local" / "share" / "githubmonitor" / DB_FILENAME


def connect_db(db_path):
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def verify_schema(connection):
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    tables = {row[0] for row in rows}

    missing = REQUIRED_TABLES - tables
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise RuntimeError(f"database schema is incomplete; missing: {missing_list}")


def github_get(path, token):
    request = Request(
        f"{GITHUB_API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "GitHubMonitor",
        },
    )

    try:
        with urlopen(request) as response:
            return json.load(response)
    except HTTPError as error:
        try:
            body = json.loads(error.read().decode("utf-8"))
            message = body.get("message", error.reason)
        except (UnicodeDecodeError, json.JSONDecodeError):
            message = error.reason

        raise RuntimeError(
            f"GitHub API request failed ({error.code}): {message}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"GitHub API request failed: {error.reason}") from error


def get_repositories(token):
    repositories = []
    page = 1

    while True:
        batch = github_get(
            f"/user/repos?affiliation=owner&per_page=100&page={page}",
            token,
        )
        repositories.extend(repo for repo in batch if not repo["fork"])

        if len(batch) < 100:
            break

        page += 1

    return repositories


def update_repository(connection, repository, collected_at):
    repository_id = repository["id"]
    owner_login = repository["owner"]["login"]
    repository_name = repository["name"]
    full_name = repository["full_name"]

    connection.execute(
        """
        INSERT INTO repositories (
            repository_id,
            is_private,
            is_archived,
            is_fork,
            default_branch,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(repository_id)
        DO UPDATE SET
            is_private     = excluded.is_private,
            is_archived    = excluded.is_archived,
            is_fork        = excluded.is_fork,
            default_branch = excluded.default_branch,
            created_at     = excluded.created_at,
            updated_at     = excluded.updated_at
        """,
        (
            repository_id,
            int(repository["private"]),
            int(repository["archived"]),
            int(repository["fork"]),
            repository.get("default_branch"),
            repository.get("created_at"),
            repository.get("updated_at"),
        ),
    )

    current_name = connection.execute(
        """
        SELECT owner_login, repository_name, full_name
        FROM repository_names
        WHERE repository_id = ? AND valid_to IS NULL
        """,
        (repository_id,),
    ).fetchone()

    new_name = (owner_login, repository_name, full_name)
    if current_name == new_name:
        return

    if current_name is not None:
        connection.execute(
            """
            UPDATE repository_names
            SET valid_to = ?
            WHERE repository_id = ? AND valid_to IS NULL
            """,
            (collected_at, repository_id),
        )

    connection.execute(
        """
        INSERT INTO repository_names (
            repository_id,
            owner_login,
            repository_name,
            full_name,
            valid_from,
            valid_to
        )
        VALUES (?, ?, ?, ?, ?, NULL)
        """,
        (
            repository_id,
            owner_login,
            repository_name,
            full_name,
            collected_at,
        ),
    )


def get_traffic(repository, token):
    owner = quote(repository["owner"]["login"], safe="")
    name = quote(repository["name"], safe="")

    views = github_get(
        f"/repos/{owner}/{name}/traffic/views?per=day",
        token,
    )["views"]
    clones = github_get(
        f"/repos/{owner}/{name}/traffic/clones?per=day",
        token,
    )["clones"]

    traffic = {}

    for item in views:
        traffic_date = item["timestamp"][:10]
        traffic[traffic_date] = {
            "views": item["count"],
            "unique_visitors": item["uniques"],
            "clones": 0,
            "unique_cloners": 0,
        }

    for item in clones:
        traffic_date = item["timestamp"][:10]
        values = traffic.setdefault(
            traffic_date,
            {
                "views": 0,
                "unique_visitors": 0,
                "clones": 0,
                "unique_cloners": 0,
            },
        )
        values["clones"] = item["count"]
        values["unique_cloners"] = item["uniques"]

    return traffic


def update_traffic(connection, repository_id, traffic, collected_at):
    for traffic_date, values in traffic.items():
        connection.execute(
            """
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
                collected_at    = excluded.collected_at
            """,
            (
                repository_id,
                traffic_date,
                values["views"],
                values["unique_visitors"],
                values["clones"],
                values["unique_cloners"],
                collected_at,
            ),
        )


def collect(connection):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set")

    user = github_get("/user", token)
    repositories = get_repositories(token)
    print(f"Authenticated as {user['login']}; found {len(repositories)} repositories.")

    failures = 0
    for repository in repositories:
        full_name = repository["full_name"]
        collected_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        try:
            traffic = get_traffic(repository, token)

            with connection:
                update_repository(connection, repository, collected_at)
                update_traffic(
                    connection,
                    repository["id"],
                    traffic,
                    collected_at,
                )

            print(f"Collected {full_name}: {len(traffic)} days")
        except (sqlite3.Error, RuntimeError) as error:
            failures += 1
            print(f"Error collecting {full_name}: {error}", file=sys.stderr)

    if failures:
        print(
            f"Collection completed with {failures} failure(s).",
            file=sys.stderr,
        )
        return 1

    print("Collection completed successfully.")
    return 0


def parse_args():
    parser = argparse.ArgumentParser(
        description="Collect and report GitHub repository traffic."
    )
    parser.add_argument(
        "--db",
        type=Path,
        help="path to githubtraffic.db",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("collect", help="collect repository traffic from GitHub")

    return parser.parse_args()


def main():
    args = parse_args()
    db_path = args.db.expanduser() if args.db else default_db_path()

    if not db_path.exists():
        print(f"Error: database does not exist: {db_path}", file=sys.stderr)
        return 1

    try:
        with connect_db(db_path) as connection:
            verify_schema(connection)

            if args.command == "collect":
                return collect(connection)
    except (OSError, sqlite3.Error, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
