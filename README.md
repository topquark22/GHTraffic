# GitHubMonitor

GitHubMonitor collects GitHub repository traffic statistics and stores them in a local SQLite database so that historical data is retained beyond GitHub's short traffic-retention window.

The current version monitors all non-fork repositories owned by the authenticated GitHub user.

## Commands

Collect the latest repository traffic data:

```bash
python githubmon.py collect
```

Show traffic for the last 14 days:

```bash
python githubmon.py show
```

Show traffic for a specific number of days:

```bash
python githubmon.py show 30
```

Use an alternate database file for testing:

```bash
python githubmon.py --db ./githubtraffic.db collect
python githubmon.py --db ./githubtraffic.db show
```

## Database

On Windows, the default database location is:

```text
%LOCALAPPDATA%\GitHubMonitor\githubtraffic.db
```

The database path may be overridden with the `GITHUBMONITOR_DB` environment variable or the `--db` command-line option.

## Authentication

GitHubMonitor reads its GitHub access token from:

```text
GITHUB_TOKEN
```

See [doc/GITHUB_SETUP.md](doc/GITHUB_SETUP.md) for token setup.

## Setup and design

- [Windows setup](doc/SETUP.md)
- [GitHub authentication setup](doc/GITHUB_SETUP.md)
- [Requirements](doc/REQUIREMENTS.md)
- [Data model](doc/DATA_MODEL.md)

## Scheduling

On Windows, GitHubMonitor is intended to run once per day using Windows Task Scheduler under the user's account, including when the user is not logged in.
