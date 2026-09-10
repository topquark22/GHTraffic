#!/usr/bin/env python3

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


PROPERTIES_FILENAME = "ghtraffic.properties"
GITHUB_API = "https://api.github.com"
REQUIRED_TABLES = {
    "repositories",
    "repository_names",
    "daily_traffic",
    "referral_traffic",
}


def windows_app_dir():
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is not set")

    if sys.platform == "cygwin":
        result = subprocess.run(
            ["cygpath", "-u", local_app_data],
            check=True,
            capture_output=True,
            text=True,
        )
        return Path(result.stdout.strip()) / "GHTraffic"

    return Path(local_app_data) / "GHTraffic"


def default_properties_path():
    if sys.platform in ("win32", "cygwin"):
        return windows_app_dir() / PROPERTIES_FILENAME

    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home).expanduser() / "ghtraffic" / PROPERTIES_FILENAME

    return Path.home() / ".config" / "ghtraffic" / PROPERTIES_FILENAME


def load_properties(path):
    if not path.exists():
        raise RuntimeError(f"properties file does not exist: {path}")

    properties = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        properties[key.strip()] = value.strip()

    return properties


def database_path():
    properties_path = default_properties_path()
    properties = load_properties(properties_path)
    value = properties.get("database.path")
    if not value:
        raise RuntimeError(
            f"database.path is not set in properties file: {properties_path}"
        )

    if sys.platform == "cygwin":
        result = subprocess.run(
            ["cygpath", "-u", value],
            check=True,
            capture_output=True,
            text=True,
        )
        return Path(result.stdout.strip())

    return Path(value).expanduser()


def github_token():
    properties_path = default_properties_path()
    properties = load_properties(properties_path)
    token = properties.get("github.token")
    if not token:
        raise RuntimeError(
            f"github.token is not set in properties file: {properties_path}"
        )

    return token


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
            "User-Agent": "GHTraffic",
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


def get_referrers(repository, token):
    owner = quote(repository["owner"]["login"], safe="")
    name = quote(repository["name"], safe="")

    return github_get(
        f"/repos/{owner}/{name}/traffic/popular/referrers",
        token,
    )


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


def update_referrers(connection, repository_id, referrers, collected_date):
    connection.execute(
        """
        DELETE FROM referral_traffic
        WHERE repository_id = ? AND collected_date = ?
        """,
        (repository_id, collected_date),
    )

    for item in referrers:
        connection.execute(
            """
            INSERT INTO referral_traffic (
                repository_id,
                collected_date,
                referrer,
                views,
                uniques
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                repository_id,
                collected_date,
                item["referrer"],
                item["count"],
                item["uniques"],
            ),
        )


def collect(connection):
    token = github_token()

    user = github_get("/user", token)
    repositories = get_repositories(token)
    print(f"Authenticated as {user['login']}; found {len(repositories)} repositories.")

    failures = 0
    for repository in repositories:
        full_name = repository["full_name"]
        collected_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        collected_date = collected_at[:10]

        try:
            traffic = get_traffic(repository, token)
            referrers = get_referrers(repository, token)

            with connection:
                update_repository(connection, repository, collected_at)
                update_traffic(
                    connection,
                    repository["id"],
                    traffic,
                    collected_at,
                )
                update_referrers(
                    connection,
                    repository["id"],
                    referrers,
                    collected_date,
                )

            print(
                f"Collected {full_name}: {len(traffic)} days, "
                f"{len(referrers)} referrers"
            )
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


def show(connection, days):
    rows = connection.execute(
        """
        SELECT
            n.repository_name,
            SUM(t.views),
            SUM(t.unique_visitors),
            SUM(t.clones),
            SUM(t.unique_cloners)
        FROM daily_traffic AS t
        JOIN repository_names AS n
            ON n.repository_id = t.repository_id
           AND n.valid_to IS NULL
        WHERE t.traffic_date >= date('now', ?)
        GROUP BY t.repository_id, n.repository_name
        HAVING SUM(t.views) > 0 OR SUM(t.clones) > 0
        ORDER BY SUM(t.views) DESC, SUM(t.clones) DESC, n.repository_name
        """,
        (f"-{days - 1} days",),
    ).fetchall()

    print(f"Traffic for the last {days} days")
    print()

    if not rows:
        print("No traffic.")
        return 0

    name_width = max(len("Repository"), *(len(row[0]) for row in rows))
    print(
        f"{'Repository':<{name_width}}  "
        f"{'Views':>7}  {'Visitors':>8}  {'Clones':>7}  {'Cloners':>7}"
    )
    print(
        f"{'-' * name_width}  "
        f"{'-' * 7}  {'-' * 8}  {'-' * 7}  {'-' * 7}"
    )

    for name, views, visitors, clones, cloners in rows:
        print(
            f"{name:<{name_width}}  "
            f"{views:>7}  {visitors:>8}  {clones:>7}  {cloners:>7}"
        )

    return 0


def show_referrers(connection):
    rows = connection.execute(
        """
        SELECT
            n.repository_name,
            r.collected_date,
            r.referrer,
            r.views,
            r.uniques
        FROM referral_traffic AS r
        JOIN repository_names AS n
            ON n.repository_id = r.repository_id
           AND n.valid_to IS NULL
        JOIN (
            SELECT repository_id, MAX(collected_date) AS collected_date
            FROM referral_traffic
            GROUP BY repository_id
        ) AS latest
            ON latest.repository_id = r.repository_id
           AND latest.collected_date = r.collected_date
        ORDER BY n.repository_name, r.views DESC, r.uniques DESC, r.referrer
        """
    ).fetchall()

    if not rows:
        print("No referrer data.")
        return 0

    repository_width = max(len("Repository"), *(len(row[0]) for row in rows))
    referrer_width = max(len("Referrer"), *(len(row[2]) for row in rows))

    print("Referrers report")
    print()
    print(
        f"{'Repository':<{repository_width}}  "
        f"{'As of':<10}  "
        f"{'Referrer':<{referrer_width}}  "
        f"{'Views':>7}  {'Uniques':>7}"
    )
    print(
        f"{'-' * repository_width}  "
        f"{'-' * 10}  "
        f"{'-' * referrer_width}  "
        f"{'-' * 7}  {'-' * 7}"
    )

    for repository, collected_date, referrer, views, uniques in rows:
        print(
            f"{repository:<{repository_width}}  "
            f"{collected_date:<10}  "
            f"{referrer:<{referrer_width}}  "
            f"{views:>7}  {uniques:>7}"
        )

    return 0


def positive_int(value):
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("days must be an integer") from error

    if number < 1:
        raise