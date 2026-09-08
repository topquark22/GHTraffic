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

GitHubMonitor should use its own dedicated GitHub access token rather than reusing a token created for another application or interactive GitHub work.

The recommended credential is a **fine-grained personal access token** owned by the GitHub account whose repositories are being monitored.

### Create the token

In GitHub:

1. Open your profile menu and select **Settings**.
2. Open **Developer settings**.
3. Open **Personal access tokens**.
4. Select **Fine-grained tokens**.
5. Select **Generate new token**.

Use a descriptive name such as:

```text
GitHubMonitor
```

Add a description such as:

```text
Read-only token used by GitHubMonitor to collect repository traffic statistics.
```

Choose an expiration period appropriate for the installation. If an expiration date is used, the token must be replaced before it expires or scheduled collection will begin to fail.

### Resource owner and repository access

Set **Resource owner** to the GitHub user account whose repositories GitHubMonitor will monitor.

GitHubMonitor discovers repositories automatically. To allow newly created repositories to be monitored without editing the token each time, select:

```text
All repositories
```

GitHubMonitor itself excludes forked repositories from traffic collection.

If **Only select repositories** is used instead, every repository to be monitored must be added manually, and newly created repositories will not be accessible until the token is updated.

### Repository permissions

Under **Repository permissions**, grant:

```text
Administration: Read-only
```

GitHub's repository traffic endpoints for views and clones require read access to the repository **Administration** permission.

GitHubMonitor does not require write access to repositories. Leave unrelated repository permissions at their default/no-access setting unless GitHub requires an automatically included read-only metadata permission.

### Generate and store the token

Select **Generate token**.

GitHub displays the token value only when it is created. Copy it immediately and store it securely. A fine-grained personal access token normally begins with:

```text
github_pat_
```

Treat the token like a password. Do not place it in source files, documentation, the SQLite database, shell history, or the GitHubMonitor repository.

### Configure GitHubMonitor

`githubmon.py` reads the token from the environment variable:

```text
GITHUB_TOKEN
```

For a temporary Command Prompt test:

```cmd
set GITHUB_TOKEN=github_pat_...
python githubmon.py --db githubtraffic.db collect
```

For a temporary PowerShell test:

```powershell
$env:GITHUB_TOKEN = "github_pat_..."
python githubmon.py --db githubtraffic.db collect
```

Do not commit a script containing the actual token.

### Verify the token

Before configuring unattended execution, run GitHubMonitor manually with the token set and verify that it can:

1. authenticate as the expected GitHub user;
2. enumerate the user's repositories;
3. retrieve traffic data for the monitored repositories; and
4. update `githubtraffic.db` successfully.

For example:

```cmd
python githubmon.py --db githubtraffic.db collect
```

A permissions error from the traffic endpoints usually indicates that the token does not have **Administration: Read-only** access to the affected repository.

### Task Scheduler and token rotation

The scheduled collector may run while the user is logged out, so `GITHUB_TOKEN` must be available to the task without requiring an interactive prompt.

Do not put the token directly into the Task Scheduler command line because command-line arguments can be exposed through process inspection and task configuration.

If the token expires, is revoked, or is suspected to have been exposed:

1. generate a replacement fine-grained token with the same repository access and permissions;
2. update the credential used by the scheduled task;
3. test GitHubMonitor manually; and
4. revoke the old token in GitHub.

GitHubMonitor should always have its own token so it can be rotated or revoked without affecting unrelated GitHub tools.

The same information is retained in [doc/GITHUB_SETUP.md](doc/GITHUB_SETUP.md).

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
