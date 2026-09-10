# GHTraffic Setup

This document describes the Windows setup for GHTraffic.

Run the installer from native Windows Command Prompt (`cmd.exe`), not from Cygwin:

```cmd
cd C:\path\to\GHTraffic
python install.py
```

When no GitHub token is already configured, the installer prompts for it securely and stores it in `%LOCALAPPDATA%\GHTraffic\ghtraffic.properties`. See [GITHUB_SETUP.md](GITHUB_SETUP.md) for token creation and credential details.

The installer performs the application deployment, database initialization, hourly Task Scheduler configuration, and UI startup. The remaining sections document the underlying Windows setup in more detail.

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

Cygwin is not a supported environment for `install.py`. If the installer is launched from Cygwin, it exits with instructions to rerun it from Windows Command Prompt.

## 2. SQLite

GHTraffic uses Python's built-in `sqlite3` module to access the database. The standalone SQLite command-line program is optional and is useful for inspecting and querying the database manually.

No Cygwin SQLite package is required.

## 3. Database location

The database file is normally named:

```text
ghtraffic.db
```

On Windows, the installer initially configures:

```text
%LOCALAPPDATA%\GHTraffic\ghtraffic.db
```

The configured database location is stored in:

```text
%LOCALAPPDATA%\GHTraffic\ghtraffic.properties
```

using the property:

```text
database.path=C:\Users\name\AppData\Local\GHTraffic\ghtraffic.db
```

Both the collector and the UI read the database location from this property. The `--db` command-line option overrides it for a single invocation and is useful for local testing:

```cmd
python ghtraffic.py --db ghtraffic.db show
```

The live database should not be stored in or committed to the GHTraffic source repository.

## 4. Initialize the database

The main `install.py` installer initializes the configured database automatically when it does not already exist and preserves an existing database during upgrades.

To initialize a fresh installation, run:

```cmd
python install.py
```

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

The installer computes a valid first start time automatically, a few minutes in the future. It does not invoke the collector during installation; the first scheduled run performs the initial collection.

The task runs under the Windows user account that owns the GHTraffic data and credentials, uses `pythonw.exe` so no console window appears, and is configured not to start overlapping collector instances.

Short interruptions do not normally create gaps because each collection refreshes the recent daily traffic window returned by GitHub. If no collection succeeds for longer than GitHub's retention window, older daily traffic that GitHub no longer returns cannot be reconstructed.

For users who require collection while logged out, see [DEPLOYMENT.md](DEPLOYMENT.md). That optional configuration may require Windows credentials.

## 7. User interface task

The installer creates a separate task named:

```text
GHTraffic UI
```

The UI task starts at user logon and runs only under the logged-on user's interactive session. It uses `pythonw.exe`, so no console window remains open. It does not require elevated privileges or the user's Windows password.

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
