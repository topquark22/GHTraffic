# GitHubMonitor Setup

This document describes the initial Windows setup for GitHubMonitor.

## 1. Python

GitHubMonitor runs using native Windows Python 3. Python's standard library includes the `sqlite3` module, so no separate Python SQLite package is required.

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

GitHubMonitor uses Python's built-in `sqlite3` module to access the database. The standalone SQLite command-line program is optional and is useful for inspecting and querying the database manually.

On Windows, use the native Windows SQLite command-line tools rather than the Cygwin SQLite package.

## 3. Database location

The database file is named:

```text
githubtraffic.db
```

On Windows, its default location is:

```text
%LOCALAPPDATA%\GitHubMonitor\githubtraffic.db
```

Create the directory if it does not already exist:

```cmd
mkdir "%LOCALAPPDATA%\GitHubMonitor"
```

The application shall determine this location at runtime from the `LOCALAPPDATA` environment variable rather than hard-coding a user profile path.

An explicit database path may be supplied through the environment variable:

```text
GITHUBMONITOR_DB
```

When set, `GITHUBMONITOR_DB` overrides the platform default.

The live database should not be stored in or committed to the GitHubMonitor source repository.

## 4. Windows scheduled task

GitHubMonitor is intended to run once per day using Windows Task Scheduler. It does not require a continuously running Windows service.

Create the task using **Task Scheduler -> Create Task** rather than Create Basic Task.

### General

Use:

```text
Name: GitHubMonitor
```

Configure the task to run under the Windows user account that owns the GitHubMonitor data and credentials.

Select:

```text
Run whether user is logged on or not
```

GitHubMonitor does not normally require **Run with highest privileges**.

### Trigger

Create a daily trigger. The exact collection time is not critical because each collection run refreshes the recent traffic window returned by GitHub rather than collecting only a single day's values.

The task may initially be disabled until the collector script has been installed and tested.

### Action

Configure the action as **Start a program**.

The Program/script field should contain the full path to native Windows Python, for example:

```text
C:\Users\gtf\AppData\Local\Python\bin\python.exe
```

The arguments and working directory will be documented once the GitHubMonitor command-line interface is implemented.

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

## 5. Unattended execution

The scheduled task runs under the user's Windows account even when that user is not logged in. GitHubMonitor must therefore be fully non-interactive during scheduled collection.

In particular:

- GitHub authentication must not require an interactive prompt.
- The database directory must be writable by the scheduled-task user.
- Collection errors must be reported through logging and process exit status rather than GUI dialogs.
- A failed collection must not damage previously collected traffic data.

## 6. GitHub authentication

GitHubMonitor requires credentials with sufficient permission to retrieve repository traffic statistics for the repositories being monitored.

The final credential-storage mechanism will be documented separately before unattended collection is enabled.

Credentials must not be committed to the GitHubMonitor repository or stored in `githubtraffic.db`.

## 7. Enabling the task

Leave the scheduled task disabled while the collector is under development.

Before enabling it:

1. Install the completed GitHubMonitor code locally.
2. Configure unattended GitHub authentication.
3. Run the collector manually and verify the database contents.
4. Configure the final Task Scheduler action and working directory.
5. Use Task Scheduler's **Run** command to test the task manually.
6. Confirm a successful exit and updated traffic data.
7. Enable the daily trigger.
