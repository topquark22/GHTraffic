# GHTraffic Setup

This document describes the Windows setup for GHTraffic.

For the normal installation path, run:

```cmd
python install.py
```

When no GitHub token is already configured, the installer prompts for it securely and stores it in `%LOCALAPPDATA%\GHTraffic\ghtraffic.properties`. See [GITHUB_SETUP.md](GITHUB_SETUP.md) for token creation and credential details.

The installer performs the application deployment, database initialization, hourly Task Scheduler configuration, initial collection when credentials are available, and UI startup. The remaining sections document the underlying Windows setup in more detail.

## 1. Python

GHTraffic runs using native Windows Python 3. Python's standard library includes the `sqlite3` module, so no separate Python SQLite package is required.

Verify Python and SQLite support from Command Prompt or PowerShell:

```cmd
python -c "import sys, sqlite3; print(sys.executable); print(sqlite3.sqlite_version)"
```

For scheduled execution, use the full path to the real Python interpreter rather than the WindowsApps Python alias. The interpreter path can be found with:

```cmd
where python
```

For the current development machine, the native interpreter is:

```text
%LOCALAPPDATA%\Python\bin\python.exe
```

If `install.py` is launched from Cygwin, it still performs a native Windows installation and locates a native Windows `python.exe` for Task Scheduler.

## 2. SQLite

GHTraffic uses Python's built-in `sqlite3` module to access the database. The standalone SQLite command-line program is optional and is useful for inspecting and querying the database manually.

No Cygwin SQLite package is required.

## 3. Database location

The database file is named:

```text
ghtraffic.db
```

On Windows, its default location is:

```text
%LOCALAPPDATA%\GHTraffic\ghtraffic.db
```

Create the directory if it does not already exist:

```cmd
mkdir "%LOCALAPPDATA%\GHTraffic"
```

The application determines this location at runtime from the `LOCALAPPDATA` environment variable rather than hard-coding a user profile path.

An explicit database path may be supplied through the environment variable:

```text
GHTRAFFIC_DB
```

When set, `GHTRAFFIC_DB` overrides the platform default.

The `--db` command-line option overrides both the environment variable and the platform default. This is useful for local testing:

```cmd
python ghtraffic.py --db ghtraffic.db show
```

The live database should not be stored in or committed to the GHTraffic source repository.

## 4. Initialize the database manually

The main `install.py` installer initializes the database automatically when it does not already exist and preserves an existing database during upgrades.

For database-only initialization from Command Prompt, run:

```cmd
install_db.bat
```

The Windows database installer uses Python's built-in `sqlite3` module, so neither Cygwin nor the standalone SQLite command-line program is required.

To initialize an alternate database for testing:

```cmd
install_db.bat -d .\ghtraffic.db
```

`GHTRAFFIC_DB` is honored when `-d` is not supplied. Otherwise the installer creates the database at the standard Windows location.

## 5. Credentials

The collector reads the GitHub access token from:

```text
%LOCALAPPDATA%\GHTraffic\ghtraffic.properties
```

using the property:

```text
github.token=github_pat_...
```

No credential environment variable is required. The same properties file is used for interactive and scheduled collection.

## 6. Windows scheduled task

The normal installation configures a Task Scheduler task named:

```text
GHTraffic Collector
```

The collector runs once per hour while the user is logged on. This is the default because it does not require the user's Windows password.

The installer computes a valid first start time automatically, a few minutes in the future, and runs one initial collection immediately when `github.token` is configured. The user therefore does not have to choose a future start date or time manually.

The task runs under the Windows user account that owns the GHTraffic data and credentials, uses the native Windows Python interpreter, and is configured not to start overlapping collector instances.

Short interruptions do not normally create gaps because each collection refreshes the recent daily traffic window returned by GitHub. If no collection succeeds for longer than GitHub's retention window, older daily traffic that GitHub no longer returns cannot be reconstructed.

For users who require collection while logged out, see [DEPLOYMENT.md](DEPLOYMENT.md). That optional configuration may require Windows credentials.

## 7. User interface task

The installer creates a separate task named:

```text
GHTraffic UI
```

The UI task starts at user logon and runs only under the logged-on user's interactive session. It does not require elevated privileges or the user's Windows password.

The UI remains available at:

```text
http://127.0.0.1:8501
```

## 8. Test the deployment

After installation:

1. Open `http://127.0.0.1:8501` and verify the repository list and chart.
2. Query the collector task:

   ```cmd
   schtasks /query /tn "\GHTraffic Collector" /v /fo LIST
   ```

3. Query the UI task:

   ```cmd
   schtasks /query /tn "\GHTraffic UI" /v /fo LIST
   ```

4. Confirm that successful collector runs report `Last Result: 0` and that the production database is being updated.

See [DEPLOYMENT.md](DEPLOYMENT.md) for the detailed manual Windows deployment procedure.
