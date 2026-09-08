#!/usr/bin/env python3

import os
import sqlite3
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


DB_FILENAME = "githubtraffic.db"
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="GitHubMonitor")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


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


def connect_db():
    db_path = default_db_path()
    if not db_path.exists():
        raise RuntimeError(f"Database does not exist: {db_path}")

    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


@app.get("/", response_class=HTMLResponse)
def index():
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GitHubMonitor</title>
  <script src="/static/chart.umd.min.js"></script>
  <style>
    body {
      font-family: system-ui, sans-serif;
      margin: 2rem auto;
      max-width: 1100px;
      padding: 0 1rem;
    }
    .controls {
      display: flex;
      gap: 1rem;
      margin-bottom: 1.5rem;
    }
    label {
      display: flex;
      flex-direction: column;
      gap: 0.3rem;
    }
    select {
      min-width: 180px;
      padding: 0.4rem;
    }
    .chart-container {
      height: 420px;
      margin-bottom: 2rem;
    }
    table {
      border-collapse: collapse;
      width: 100%;
    }
    th, td {
      border-bottom: 1px solid #ddd;
      padding: 0.5rem;
      text-align: left;
    }
    th:nth-child(3), th:nth-child(4),
    td:nth-child(3), td:nth-child(4) {
      text-align: right;
    }
    .message {
      color: #666;
    }
  </style>
</head>
<body>
  <h1>GitHubMonitor</h1>

  <div class="controls">
    <label>
      Repository
      <select id="repository"></select>
    </label>
    <label>
      Period
      <select id="days">
        <option value="7">7 days</option>
        <option value="14" selected>14 days</option>
        <option value="30">30 days</option>
        <option value="90">90 days</option>
      </select>
    </label>
  </div>

  <h2>Views and clones</h2>
  <div class="chart-container">
    <canvas id="trafficChart"></canvas>
  </div>

  <h2>Referrers</h2>
  <div id="referrerMessage" class="message"></div>
  <table id="referrerTable" hidden>
    <thead>
      <tr>
        <th>As of</th>
        <th>Referrer</th>
        <th>Views</th>
        <th>Uniques</th>
      </tr>
    </thead>
    <tbody></tbody>
  </table>

  <script>
    const repositorySelect = document.getElementById('repository');
    const daysSelect = document.getElementById('days');
    const referrerTable = document.getElementById('referrerTable');
    const referrerBody = referrerTable.querySelector('tbody');
    const referrerMessage = document.getElementById('referrerMessage');
    let chart = null;

    async function loadRepositories() {
      const response = await fetch('/api/repositories');
      const repositories = await response.json();

      repositorySelect.innerHTML = '';
      for (const repository of repositories) {
        const option = document.createElement('option');
        option.value = repository.repository_id;
        option.textContent = repository.repository_name;
        repositorySelect.appendChild(option);
      }

      if (repositories.length > 0) {
        await refresh();
      }
    }

    async function loadTraffic() {
      const repositoryId = repositorySelect.value;
      const days = daysSelect.value;
      const response = await fetch(`/api/traffic?repository_id=${repositoryId}&days=${days}`);
      const traffic = await response.json();

      const labels = traffic.map(row => row.traffic_date);
      const views = traffic.map(row => row.views);
      const clones = traffic.map(row => row.clones);

      if (chart) {
        chart.destroy();
      }

      chart = new Chart(document.getElementById('trafficChart'), {
        type: 'bar',
        data: {
          labels,
          datasets: [
            { label: 'Views', data: views },
            { label: 'Clones', data: clones }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              ticks: { precision: 0 }
            }
          }
        }
      });
    }

    async function loadReferrers() {
      const repositoryId = repositorySelect.value;
      const response = await fetch(`/api/referrers?repository_id=${repositoryId}`);
      const referrers = await response.json();

      referrerBody.innerHTML = '';

      if (referrers.length === 0) {
        referrerTable.hidden = true;
        referrerMessage.textContent = 'No referrer data.';
        return;
      }

      referrerMessage.textContent = '';
      referrerTable.hidden = false;

      for (const row of referrers) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${row.collected_date}</td>
          <td>${row.referrer}</td>
          <td>${row.views}</td>
          <td>${row.uniques}</td>
        `;
        referrerBody.appendChild(tr);
      }
    }

    async function refresh() {
      await Promise.all([loadTraffic(), loadReferrers()]);
    }

    repositorySelect.addEventListener('change', refresh);
    daysSelect.addEventListener('change', loadTraffic);

    loadRepositories();
  </script>
</body>
</html>
"""


@app.get("/api/repositories")
def repositories():
    try:
        with connect_db() as connection:
            rows = connection.execute(
                """
                SELECT repository_id, repository_name
                FROM repository_names
                WHERE valid_to IS NULL
                ORDER BY repository_name
                """
            ).fetchall()

        return [dict(row) for row in rows]
    except (OSError, sqlite3.Error, RuntimeError) as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/api/traffic")
def traffic(
    repository_id: int,
    days: int = Query(default=14, ge=1),
):
    try:
        with connect_db() as connection:
            rows = connection.execute(
                """
                SELECT traffic_date, views, clones
                FROM daily_traffic
                WHERE repository_id = ?
                  AND traffic_date >= date('now', ?)
                ORDER BY traffic_date
                """,
                (repository_id, f"-{days - 1} days"),
            ).fetchall()

        return [dict(row) for row in rows]
    except (OSError, sqlite3.Error, RuntimeError) as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/api/referrers")
def referrers(repository_id: int):
    try:
        with connect_db() as connection:
            rows = connection.execute(
                """
                SELECT collected_date, referrer, views, uniques
                FROM referral_traffic
                WHERE repository_id = ?
                  AND collected_date = (
                      SELECT MAX(collected_date)
                      FROM referral_traffic
                      WHERE repository_id = ?
                  )
                ORDER BY views DESC, uniques DESC, referrer
                """,
                (repository_id, repository_id),
            ).fetchall()

        return [dict(row) for row in rows]
    except (OSError, sqlite3.Error, RuntimeError) as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
