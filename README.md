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

Show the latest referrer data:

```bash
python githubmon.py referrers
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

## User interface

GitHubMonitor includes a local web user interface in `githubmon_ui.py`. The UI uses only the Python standard library and the bundled copy of Chart.js, so no additional Python packages are required.

The UI displays repository traffic from the SQLite database. Repositories are ordered by decreasing views during the selected reporting period, which defaults to 14 days. The selected repository shows daily views and clones together with the most recently collected referrer data.

Run the UI directly from the source tree with:

```bash
python3 githubmon_ui.py
```

Then open:

```text
http://127.0.0.1:8501
```

### Windows installation

The deployed UI should use the same application directory and database as the scheduled collector:

```text
%LOCALAPPDATA%\GitHubMonitor\
    githubmon_ui.py
    githubtraffic.db
    static\
        chart.umd.min.js
```

Copy `githubmon_ui.py` and the complete `static` directory from the source tree into `%LOCALAPPDATA%\GitHubMonitor`. The `static` directory is required because it contains the bundled Chart.js library used to draw the traffic graph.

For example, from a Windows command prompt in the source directory:

```cmd
copy githubmon_ui.py "%LOCALAPPDATA%\GitHubMonitor\githubmon_ui.py"
xcopy /E /I /Y static "%LOCALAPPDATA%\GitHubMonitor\static"
```

The database should already exist in this directory if the collector has been installed and run.

Test the deployed UI using the native Windows Python installation:

```cmd
python "%LOCALAPPDATA%\GitHubMonitor\githubmon_ui.py"
```

Open `http://127.0.0.1:8501` and verify that the repository list, traffic chart, and referrer data appear.

### Running the UI continuously on Windows

The UI can be kept running with Windows Task Scheduler. Create a separate task for the UI rather than modifying the daily collection task.

Configure the task as follows:

- Run it under the user's account.
- Select **Run whether user is logged on or not**.
- Use **At startup** as the trigger.
- Set the action to run the native Windows `python.exe`.
- Pass `%LOCALAPPDATA%\GitHubMonitor\githubmon_ui.py` as the script argument. If Task Scheduler does not expand the environment variable in the argument field, use the full path instead.
- Set **Start in** to `%LOCALAPPDATA%\GitHubMonitor`, or its full expanded path.
- Disable **Stop the task if it runs longer than**.
- Set **If the task is already running** to **Do not start a new instance**.

The UI listens only on `127.0.0.1:8501`, so it is available from the local computer at:

```text
http://localhost:8501
```

It is not exposed to other computers on the network.

## Setup and design

- [Windows setup](doc/SETUP.md)
- [GitHub authentication setup](doc/GITHUB_SETUP.md)
- [Requirements](doc/REQUIREMENTS.md)
- [Data model](doc/DATA_MODEL.md)

## Scheduling

On Windows, the GitHubMonitor collector is intended to run once per day using Windows Task Scheduler under the user's account, including when the user is not logged in. The user interface runs continuously as a separate scheduled task.
