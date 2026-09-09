# GitHubMonitor Deployment

This document describes deployment of GitHubMonitor on Windows after the initial setup and GitHub authentication steps have been completed.

See [SETUP.md](SETUP.md) for installation and database setup, and [GITHUB_SETUP.md](GITHUB_SETUP.md) for GitHub token configuration.

## Application directory

GitHubMonitor uses the following per-user application directory on Windows:

```text
%LOCALAPPDATA%\GitHubMonitor\
```

The deployed installation should contain:

```text
%LOCALAPPDATA%\GitHubMonitor\
    githubmon.py
    githubmon_ui.py
    githubtraffic.db
    static\
        chart.umd.min.js
```

The `static` directory is required by the user interface because it contains the bundled Chart.js library used to draw the traffic graph.

Copy the current scripts and static files from the source tree into the application directory. For example, from a Windows command prompt in the source directory:

```cmd
copy githubmon.py "%LOCALAPPDATA%\GitHubMonitor\githubmon.py"
copy githubmon_ui.py "%LOCALAPPDATA%\GitHubMonitor\githubmon_ui.py"
xcopy /E /I /Y static "%LOCALAPPDATA%\GitHubMonitor\static"
```

The database should already exist in `%LOCALAPPDATA%\GitHubMonitor` after the database installation step.

## Test the collector

Run the deployed collector manually before enabling scheduled execution:

```cmd
python "%LOCALAPPDATA%\GitHubMonitor\githubmon.py" collect
```

Verify that the command completes successfully and updates:

```text
%LOCALAPPDATA%\GitHubMonitor\githubtraffic.db
```

The collector requires `GITHUB_TOKEN` to be available in its environment. See [GITHUB_SETUP.md](GITHUB_SETUP.md).

## Schedule the collector

Create a Windows Task Scheduler task named, for example:

```text
GitHubMonitor Collector
```

Configure it to run once per day under the user's account, including when the user is logged out.

Recommended settings:

- Select **Run whether user is logged on or not**.
- Use a daily trigger at the desired collection time.
- Set the action to run the native Windows `python.exe`.
- Pass `%LOCALAPPDATA%\GitHubMonitor\githubmon.py collect` as the arguments. If Task Scheduler does not expand the environment variable, use the full expanded path instead.
- Set **Start in** to `%LOCALAPPDATA%\GitHubMonitor`, or its full expanded path.
- Set **If the task is already running** to **Do not start a new instance**.

After creating the task, use **Run** in Task Scheduler and verify that the database is updated successfully.

## Test the user interface

The user interface uses only the Python standard library and the bundled copy of Chart.js. No additional Python packages are required.

Run the deployed UI manually with:

```cmd
python "%LOCALAPPDATA%\GitHubMonitor\githubmon_ui.py"
```

Then open:

```text
http://127.0.0.1:8501
```

Verify that the GitHub account name, repository list, traffic chart, and referrer data appear.

If the page loads but the traffic chart is missing, verify that this file exists:

```text
%LOCALAPPDATA%\GitHubMonitor\static\chart.umd.min.js
```

### Traffic history availability

The **Period** selector limits the chart to the requested number of days, but GitHubMonitor displays only traffic records that actually exist in the local database.

GitHub's traffic API supplies only a short window of recent daily traffic data. GitHubMonitor preserves those records on each collection so that a longer history accumulates over time. Consequently, a new installation may have only about 14 days of history even when **30 days** or **90 days** is selected. As scheduled collection continues, those longer views will gradually extend to the full requested period.

GitHubMonitor does not synthesize zero-valued records for dates before collection began or for other dates for which no record exists. A missing record means that traffic is unknown; it must not be interpreted as zero views or zero clones.

## Run the user interface continuously

Create a second Task Scheduler task for the UI, separate from the daily collector task. A name such as the following is suitable:

```text
GitHubMonitor UI
```

Configure the task as follows:

- Run it under the user's account.
- Select **Run whether user is logged on or not**.
- Use **At startup** as the trigger.
- Set the action to run the native Windows `python.exe`.
- Pass `%LOCALAPPDATA%\GitHubMonitor\githubmon_ui.py` as the script argument. If Task Scheduler does not expand the environment variable, use the full path instead.
- Set **Start in** to `%LOCALAPPDATA%\GitHubMonitor`, or its full expanded path.
- Disable **Stop the task if it runs longer than**.
- Set **If the task is already running** to **Do not start a new instance**.

After creating the task, use **Run** in Task Scheduler and confirm that the UI remains available at:

```text
http://localhost:8501
```

The UI listens only on `127.0.0.1:8501`, so it is available only from the local computer and is not exposed to other computers on the network.

## Updating an existing deployment

After pulling a newer version of GitHubMonitor, copy the updated scripts and static files into `%LOCALAPPDATA%\GitHubMonitor` again:

```cmd
copy /Y githubmon.py "%LOCALAPPDATA%\GitHubMonitor\githubmon.py"
copy /Y githubmon_ui.py "%LOCALAPPDATA%\GitHubMonitor\githubmon_ui.py"
xcopy /E /I /Y static "%LOCALAPPDATA%\GitHubMonitor\static"
```

Restart the `GitHubMonitor UI` task after updating `githubmon_ui.py` or files under `static`.
