#!/usr/bin/env python3

import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import streamlit as st


DB_FILENAME = "githubtraffic.db"


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
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


def get_repositories(connection):
    return connection.execute(
        """
        SELECT n.repository_id, n.repository_name
        FROM repository_names AS n
        WHERE n.valid_to IS NULL
        ORDER BY n.repository_name
        """
    ).fetchall()


def get_traffic(connection, repository_id, days):
    return pd.read_sql_query(
        """
        SELECT
            traffic_date AS Date,
            views AS Views,
            clones AS Clones
        FROM daily_traffic
        WHERE repository_id = ?
          AND traffic_date >= date('now', ?)
        ORDER BY traffic_date
        """,
        connection,
        params=(repository_id, f"-{days - 1} days"),
        parse_dates=["Date"],
    )


def get_referrers(connection, repository_id):
    return pd.read_sql_query(
        """
        SELECT
            collected_date AS "As of",
            referrer AS Referrer,
            views AS Views,
            uniques AS Uniques
        FROM referral_traffic
        WHERE repository_id = ?
          AND collected_date = (
              SELECT MAX(collected_date)
              FROM referral_traffic
              WHERE repository_id = ?
          )
        ORDER BY views DESC, uniques DESC, referrer
        """,
        connection,
        params=(repository_id, repository_id),
    )


def main():
    st.set_page_config(page_title="GitHubMonitor", layout="wide")
    st.title("GitHubMonitor")

    db_path = default_db_path()
    if not db_path.exists():
        st.error(f"Database does not exist: {db_path}")
        return

    try:
        with connect_db(db_path) as connection:
            repositories = get_repositories(connection)

            if not repositories:
                st.info("No repositories found in the database.")
                return

            repository_names = [name for _, name in repositories]
            repository_by_name = {name: repository_id for repository_id, name in repositories}

            col1, col2 = st.columns([3, 1])
            with col1:
                selected_repository = st.selectbox("Repository", repository_names)
            with col2:
                days = st.selectbox("Period", [7, 14, 30, 90], index=1)

            repository_id = repository_by_name[selected_repository]
            traffic = get_traffic(connection, repository_id, days)

            st.subheader("Views and clones")
            if traffic.empty:
                st.info("No traffic data for this period.")
            else:
                chart_data = traffic.set_index("Date")[["Views", "Clones"]]
                st.bar_chart(chart_data)

            st.subheader("Referrers")
            referrers = get_referrers(connection, repository_id)
            if referrers.empty:
                st.info("No referrer data.")
            else:
                st.dataframe(referrers, hide_index=True, use_container_width=True)
    except (OSError, sqlite3.Error, RuntimeError) as error:
        st.error(str(error))


if __name__ == "__main__":
    main()
