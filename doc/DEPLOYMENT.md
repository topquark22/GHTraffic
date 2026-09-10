# GHTraffic Deployment

This document describes manual deployment of GHTraffic on Windows after the initial setup and GitHub authentication steps have been completed.

For the normal installation path, run:

```cmd
python install.py
```

The installer performs these steps automatically. This document is retained for users who want the details or need a custom deployment.

See [SETUP.md](SETUP.md) for installation and database setup, and [GITHUB_SETUP.md](GITHUB_SETUP.md) for GitHub token configuration.

## Application directory

GHTraffic uses the following per-user application directory on Windows:

```text
%LOCALAPPDATA%\GHTraffic\
```

The deployed installation should contain:

```text
%LOCALAPPDATA%\GHTraffic\
    ghtraffic.py
    ghtraffic_ui.py
    ghtraffic.db
    static\
        chart.umd.min.js
        favicon.ico
```

The `static` directory is required by the user interface because it contains the bundled Chart.js library and favicon.

Copy the current scripts and static files from the source tree into the application directory. For example, from a Windows command prompt in the source directory:

```cmd
copy ghtraffic.py "%LOCALAPPDATA%\GHTraffic\ghtraffic.py"
copy ghtraffic_ui.py "%LOCALAPPDATA%\GHTraffic\ghtraffic_ui.py"
xcopy /E /I /Y static "%LOCALAPPDATA%\GHTraffic\static"
```

The database should already exist in `%LOCALAPPDATA%\GHTraffic` after the database installation step.

## Test the collector

Run the deployed collector manually before enabling scheduled execution:

```cmd
python "%LOCALAPPDATA%\GHTraffic\ghtraffic.py" collect
```

Verify that the command completes successfully and updates:

```text
%LOCALAPPDATA%\GHTraffic\ghtraffic.db
```

The collector requires `GITHUB_TOKEN` to be available in its environment. See [GITHUB_SETUP.md](GITHUB_SETUP.md).

## Schedule the collector

Create a Windows Task Scheduler task named:

```text
GHTraffic Collector
```

The default configuration runs only while the user is logged on. This avoids the Windows password prompt associated with unattended task execution.

**General**

- Run only when the user is logged on.
- Do not select **Run with highest privileges**.

**Triggers**

- One time.
- Choose a start time a few minutes in the future.
- After triggered, repeat every 1 hour indefinitely.
- Enabled.

The `install.py` installer calculates the initial start time automatically, so this manual step is required only when creating the task by hand.

**Actions**

Start the native Windows Python interpreter with the deployed collector. For example:

```text
%LOCALAPPDATA%\Python\bin\python.exe %LOCALAPPDATA%\GHTraffic\ghtraffic.py collect
```

Use the actual full path to `python.exe` on the machine.

Start in:

```text
%LOCALAPPDATA%\GHTraffic\
```

**Settings**

- Allow task to be run on demand.
- Run task as soon as possible after a scheduled start is missed.
- If the task is already running, do not start a new instance.

After creating the task, use **Run** in Task Scheduler and verify that the database is updated successfully.

### Collection while logged out

The default logged-on-only configuration is sufficient for most desktop installations because every successful collection refreshes the recent daily traffic window returned by GitHub. Short periods when the computer is off or the user is logged out are therefore normally recovered by the next collection.

If no collection succeeds for longer than GitHub's traffic-retention window, older daily views and clones that GitHub no longer returns cannot be reconstructed. Users who need uninterrupted historical collection can change the collector task to:

```text
Run whether user is logged on or not
```

Windows normally asks for the user's password when this task mode is configured. GHTraffic does not request, handle, or store that Windows password itself.

The UI does not need to run while the user is logged out.

## Test the user interface

The user interface uses only the Python standard library and the bundled copy of Chart.js. No additional Python packages are required.

Run the deployed UI manually with:

```cmd
python "%LOCALAPPDATA%\GHTraffic\ghtraffic_ui.py"
```

Then open:

```text
http://127.0.0.1:8501
```

Verify that the GitHub account name, repository list, traffic chart, referrer data, and favicon appear.

If the page loads but the traffic chart is missing, verify that this file exists:

```text
%LOCALAPPDATA%\GHTraffic\static\chart.umd.min.js
```

If the favicon is missing, verify that this file exists:

```text
%LOCALAPPDATA%\GHTraffic\static\favicon.ico
```

### Traffic history availability

The **Period** selector limits the chart to the requested number of days, but GHTraffic displays only traffic records that actually exist in the local database.

GitHub's traffic API supplies only a short window of recent daily traffic data. GHTraffic preserves those records on each collection so that a longer history accumulates over time. Consequently, a new installation may have only about 14 days of history even when **30 days** or **90 days** is selected. As scheduled collection continues, those longer views will gradually extend to the full requested period.

GHTraffic does not synthesize zero-valued records for dates before collection began or for other dates for which no record exists. A missing record means that traffic is unknown; it must not be interpreted as zero views or zero clones.

GitHub traffic dates are UTC, and the graph labels its date axis accordingly.

## Run the user interface continuously

Create a second Task Scheduler task for the UI:

```text
GHTraffic UI
```

Configure the task as follows:

- Run it under the user's account.
- Select **Run only when user is logged on**.
- Use **At log on** as the trigger.
- Set the action to run the native Windows `python.exe`.
- Pass `%LOCALAPPDATA%\GHTraffic\ghtraffic_ui.py` as the script argument. If Task Scheduler does not expand the environment variable, use the full path instead.
- Set **Start in** to `%LOCALAPPDATA%\GHTraffic`, or its full expanded path.
- Disable **Stop the task if it runs longer than**.
- Set **If the task is already running** to **Do not start a new instance**.

After creating the task, use **Run** in Task Scheduler and confirm that the UI remains available at:

```text
http://localhost:8501
```

The UI listens only on `127.0.0.1:8501`, so it is available only from the local computer and is not exposed to other computers on the network.

## Updating an existing deployment

The simplest update procedure is to run the current installer again:

```cmd
python install.py
```

The installer replaces the application and static files, preserves the existing database and credential configuration, updates the scheduled tasks, and restarts the UI.

For a manual update, copy the updated scripts and static files into `%LOCALAPPDATA%\GHTraffic` again:

```cmd
copy /Y ghtraffic.py "%LOCALAPPDATA%\GHTraffic\ghtraffic.py"
copy /Y ghtraffic_ui.py "%LOCALAPPDATA%\GHTraffic\ghtraffic_ui.py"
xcopy /E /I /Y static "%LOCALAPPDATA%\GHTraffic\static"
```

Restart the `GHTraffic UI` task after updating `ghtraffic_ui.py` or files under `static`.
