# GHTraffic GitHub Setup

GHTraffic should use its own dedicated GitHub access token rather than reusing a token created for another application or interactive GitHub work.

The recommended credential is a **fine-grained personal access token** owned by the GitHub account whose repositories are being monitored.

## 1. Create the token

In GitHub:

1. Open your profile menu and select **Settings**.
2. Open **Developer settings**.
3. Open **Personal access tokens**.
4. Select **Fine-grained tokens**.
5. Select **Generate new token**.

Use a descriptive name such as:

```text
GHTraffic
```

Add a description such as:

```text
Read-only token used by GHTraffic to collect repository traffic statistics.
```

Choose an expiration period appropriate for the installation. If an expiration date is used, the token must be replaced before it expires or scheduled collection will begin to fail.

## 2. Resource owner

Set **Resource owner** to the GitHub user account whose repositories GHTraffic will monitor.

For the current installation:

```text
topquark22
```

## 3. Repository access

GHTraffic discovers repositories automatically. To allow newly created repositories to be monitored without editing the token each time, select:

```text
All repositories
```

GHTraffic itself excludes forked repositories from traffic collection.

If **Only select repositories** is used instead, every repository to be monitored must be added manually, and newly created repositories will not be accessible until the token is updated.

## 4. Repository permissions

Under **Repository permissions**, grant:

```text
Administration: Read-only
```

GitHub's repository traffic endpoints for views and clones require read access to the repository **Administration** permission.

GHTraffic does not require write access to repositories.

Leave unrelated repository permissions at their default/no-access setting unless GitHub requires an automatically included read-only metadata permission.

## 5. Generate and copy the token

Select **Generate token**.

GitHub displays the token value only when it is created. Copy it immediately and store it securely.

A fine-grained personal access token normally begins with:

```text
github_pat_
```

Treat the token like a password. Do not place it in source files, documentation, the SQLite database, shell history, or the GHTraffic repository.

## 6. Configure GHTraffic

`ghtraffic.py` reads the token from the environment variable:

```text
GITHUB_TOKEN
```

For a temporary Command Prompt test:

```cmd
set GITHUB_TOKEN=github_pat_...
python ghtraffic.py --db ghtraffic.db collect
```

For a temporary PowerShell test:

```powershell
$env:GITHUB_TOKEN = "github_pat_..."
python ghtraffic.py --db ghtraffic.db collect
```

For a temporary Linux shell test:

```bash
export GITHUB_TOKEN='github_pat_...'
python3 ghtraffic.py --db ghtraffic.db collect
```

Do not commit a script containing the actual token.

When `install.py` is run and `GITHUB_TOKEN` is available only in the current shell, the installer offers to persist it for scheduled collection. On Windows it can save the token in the current user's environment. On Linux it can save the token in `~/.config/ghtraffic/environment` with user-only permissions. Existing credential configuration is preserved and is not silently replaced.

## 7. Verify the token

Before configuring scheduled execution, run GHTraffic manually with the token set and verify that it can:

1. authenticate as the expected GitHub user;
2. enumerate the user's repositories;
3. retrieve traffic data for the monitored repositories; and
4. update `ghtraffic.db` successfully.

For example:

```cmd
python ghtraffic.py --db ghtraffic.db collect
```

A permissions error from the traffic endpoints usually indicates that the token does not have **Administration: Read-only** access to the affected repository.

## 8. Scheduled collection

The token must be available to the scheduled collector without requiring an interactive prompt.

Do not put the token directly into a Task Scheduler or systemd command line because command-line arguments and service definitions can be exposed through process inspection or configuration files.

On Windows, the default installer configuration uses the current user's environment and runs the collector only while that user is logged on. This avoids storing the user's Windows password in Task Scheduler.

On Linux, the systemd user service reads the token from:

```text
~/.config/ghtraffic/environment
```

## 9. Token rotation

If the token expires, is revoked, or is suspected to have been exposed:

1. generate a replacement fine-grained token with the same repository access and permissions;
2. update the stored `GITHUB_TOKEN` used by scheduled collection;
3. test GHTraffic manually;
4. revoke the old token in GitHub.

GHTraffic should always have its own token so it can be rotated or revoked without affecting unrelated GitHub tools.
