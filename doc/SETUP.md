# GHTraffic Setup

This document describes the Windows setup for GHTraffic.

## 1. Python

GHTraffic runs using native Windows Python 3. Python's standard library includes the `sqlite3` module, so no separate Python SQLite package is required.

Verify Python and SQLite support from Command Prompt or PowerShell:

```cmd
python -c "import sys, sqlite3; print(sys.executable); print(sqlite3.sqlite_version)"
```

For unattended execution, use the full path to the real Python interpreter rather than the WindowsApps Python alias. The interpreter path can be found with:

```cmd
where python
```

For the current development machine, the native interpreter is:

```text
%LOCALAPPDATA%\Python\bin\python.exe
```

## 2. SQLite

GHTraffic uses Python's built-in `sqlite3` module to access the database. The standalone SQLite command-line program is optional and is useful for inspecting and querying the database manually.

On Windows, use the native Windows SQLite command-line tools rather than the Cygwin SQLite package.

## 3. Database location

The database file is named:

```text
githubtraffic.db
```

On Windows, its default location is:

```text
%LOCALAPPDATA%\GHTraffic\githubtraffic.db
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
python ghtraffic.py --db githubtraffic.db show
```

The live database should not be stored in or committed to the GHTraffic source repository.

## 4. Initialize the database

Run:

```bash
./install_db.sh
```

To initialize an alternate database for testing:

```bash
./install_db.sh -d ./githubtraffic.db
```

The installer expects the target database not to exist already. It runs `ddl.sql` to create the schema.

## 5. Windows scheduled task

GHTraffic runs once per day using Windows Task Scheduler. It does not require a continuously running Windows service.

Create the task using **Task Scheduler -> Create Task** rather than Create Basic Task.

### General

Use:

```text
Name: GHTraffic
```

Configure the task to run under the Windows user account that owns the GHTraffic data and credentials.

Select:

```text
Run whether user is logged on or not
```

GHTraffic does not normally require **Run with highest privileges**.

### Trigger

Create a daily trigger. The exact collection time is not critical because each collection run refreshes the recent traffic window returned by GitHub rather than collecting only a single day's values.

### Action

Configure the action as **Start a program**.

Program/script:

```text
%LOCALAPPDATA%\Python\bin\python.exe
```

Use the actual full path to `python.exe` when configuring Task Scheduler.

Add arguments:

```text
<path-to-GHTraffic>\ghtraffic.py collect
```

If the project path contains spaces, quote the script path in the arguments field.

Start in:

```text
<path-to-GHTraffic>
```

Do not use Cygwin `/usr/bin/python3` for the scheduled Windows task.

### Settings

Enable:

```text
Run task as soon as possible after a scheduled start is missed
```

This allows collection to occur after startup if the computer was powered off at the scheduled time.

For:

```text
If the task is already running
```

select:

```text
Do not start a new instance
```

This prevents overlapping collectors from accessing the same SQLite database unnecessarily.

If appropriate for the machine, configure Task Scheduler to wake the computer for the task.

## 6. Unattended execution

The scheduled task runs under the user's Windows account even when that user is not logged in. GHTraffic must therefore be fully non-interactive during scheduled collection.

In particular:

- GitHub authentication must not require an interactive prompt.
- The database directory must be writable by the scheduled-task user.
- Collection errors are reported through process exit status and console output.
- A failed collection must not damage previously collected traffic data.

See [GITHUB_SETUP.md](GITHUB_SETUP.md) for creation of a dedicated GitHub access token and configuration of `GITHUB_TOKEN`.

## 7. Test the deployment

Before relying on the daily trigger:

1. Run the collector manually and verify the database contents.
2. Use Task Scheduler's **Run** command or:

   ```cmd
   schtasks /run /tn "\GHTraffic"
   ```

3. Inspect the result with:

   ```cmd
   schtasks /query /tn "\GHTraffic" /v /fo LIST
   ```

4. Confirm that `Last Result` is `0` and that the production database has been updated.

The deployed configuration has been verified to run successfully under the user's Windows account while the user is logged out.
