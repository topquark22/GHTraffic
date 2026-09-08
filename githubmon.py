#!/usr/bin/env python3

import argparse
import os
import sqlite3
import sys
from pathlib import Path


DB_FILENAME = "githubtraffic.db"
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


def collect(connection):
    del connection
    print("Collection is not implemented yet.")


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
                collect(connection)
    except (OSError, sqlite3.Error, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
