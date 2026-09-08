#!/usr/bin/env python3

import json
import os
import sqlite3
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


DB_FILENAME = "githubtraffic.db"
STATIC_DIR = Path(__file__).resolve().parent / "static"
HOST = "127.0.0.1"
PORT = 8501


def default_db_path():
    override = os.environ.get("GITHUBMONITOR_DB")
    if override:
        return Path(override).expanduser()

    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise RuntimeError("LOCALAPPDATA is not set")

        return Path(local_app_data) / "GitHubMonitor" / DB_FILENAME

    if sys.platform == "cygwin":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise RuntimeError("LOCALAPPDATA is not set")

        result = subprocess.run(
            ["cygpath", "-u", local_app_data],
            check=True,
            capture_output=True,
            text=True,
        )
        return Path(result.stdout.strip()) / "GitHubMonitor" / DB_FILENAME

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


def get_repositories(days):
    with connect_db() as connection:
        rows = connection.execute(
            """
            SELECT n.repository_id, n.owner_login, n.repository_name
            FROM repository_names AS n
            LEFT JOIN daily_traffic AS t
                ON t.repository_id = n.repository_id
               AND t.traffic_date >= date('now', ?)
            WHERE n.valid_to IS NULL
            GROUP BY n.repository_id, n.owner_login, n.repository_name
            ORDER BY COALESCE(SUM(t.views), 0) DESC, n.repository_name
            """,
            (f"-{days - 1} days",),
        ).fetchall()

    return [dict(row) for row in rows]


def get_traffic(repository_id, days):
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


def get_referrers(repository_id):
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


INDEX_HTML = """<!doctype html>
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

  <h1 id="pageTitle">GitHub Traffic</h1>

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
    const pageTitle = document.getElementById('pageTitle');
    const repositorySelect = document.getElementById('repository');
    const daysSelect = document.getElementById('days');
    const referrerTable = document.getElementById('referrerTable');
    const referrerBody = referrerTable.querySelector('tbody');
    const referrerMessage = document.getElementById('referrerMessage');
    let chart = null;

    async function loadRepositories(preserveSelection = false) {
      const selectedRepository = preserveSelection ? repositorySelect.value : null;
      const days = daysSelect.value;
      const response = await fetch(`/api/repositories?days=${days}`);
      const repositories = await response.json();

      repositorySelect.innerHTML = '';
      for (const repository of repositories) {
        const option = document.createElement('option');
        option.value = repository.repository_id;
        option.textContent = repository.repository_name;
        repositorySelect.appendChild(option);
      }

      if (repositories.length > 0) {
        pageTitle.textContent = `GitHub Traffic — ${repositories[0].owner_login}`;
      }

      if (selectedRepository && repositories.some(
          repository => String(repository.repository_id) === selectedRepository)) {
        repositorySelect.value = selectedRepository;
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
    daysSelect.addEventListener('change', () => loadRepositories(true));

    loadRepositories();
  </script>
</body>
</html>
"""


class RequestHandler(BaseHTTPRequestHandler):
    def send_bytes(self, data, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, value, status=200):
        data = json.dumps(value).encode("utf-8")
        self.send_bytes(data, "application/json; charset=utf-8", status)

    def send_error_json(self, message, status=500):
        self.send_json({"error": message}, status)

    def do_GET(self):
        parsed = urlparse(self.path)

        try:
            if parsed.path == "/":
                self.send_bytes(
                    INDEX_HTML.encode("utf-8"),
                    "text/html; charset=utf-8",
                )
                return

            if parsed.path == "/static/chart.umd.min.js":
                chart_path = STATIC_DIR / "chart.umd.min.js"
                data = chart_path.read_bytes()
                self.send_bytes(data, "text/javascript; charset=utf-8")
                return

            query = parse_qs(parsed.query)

            if parsed.path == "/api/repositories":
                days = int(query.get("days", ["14"])[0])
                if days < 1:
                    raise ValueError("days must be at least 1")

                self.send_json(get_repositories(days))
                return

            if parsed.path == "/api/traffic":
                repository_id = int(query["repository_id"][0])
                days = int(query.get("days", ["14"])[0])
                if days < 1:
                    raise ValueError("days must be at least 1")

                self.send_json(get_traffic(repository_id, days))
                return

            if parsed.path == "/api/referrers":
                repository_id = int(query["repository_id"][0])
                self.send_json(get_referrers(repository_id))
                return

            self.send_error_json("Not found", 404)
        except (KeyError, ValueError):
            self.send_error_json("Invalid request", 400)
        except (OSError, sqlite3.Error, RuntimeError) as error:
            self.send_error_json(str(error), 500)

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")


def main():
    server = ThreadingHTTPServer((HOST, PORT), RequestHandler)
    print(f"GitHubMonitor UI: http://{HOST}:{PORT}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
