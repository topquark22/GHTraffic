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

GHTraffic stores its token in a local properties file using:

```text
github.token=github_pat_...
```

The default Windows properties file is:

```text
%LOCALAPPDATA%\GHTraffic\ghtraffic.properties
```

The default Linux properties file is:

```text
~/.config/ghtraffic/ghtraffic.properties
```

The normal installation command:

```text
python install.py
```

prompts for the GitHub token when no token is already configured. The prompt does not echo the token to the terminal. If a properties file containing `github.token` already exists, the installer preserves it rather than silently replacing the credential.

On Linux, the installer restricts the properties file to the current user with mode `0600`. On Windows, the file is stored under the current user's Local AppData directory and inherits that directory's access controls.

The collector reads the properties file directly. No `GITHUB_TOKEN` environment variable is required for interactive or scheduled collection.

## 7. Manual configuration

The properties file can also be created or edited manually.

On Windows:

```text
%LOCALAPPDATA%\GHTraffic\ghtraffic.properties
```

On Linux:

```text
~/.config/ghtraffic/ghtraffic.properties
```

The required property is:

```text
github.token=github_pat_...
```

Do not commit the properties file or copy its contents into documentation or shell commands.

## 8. Verify the token

Run GHTraffic manually and verify that it can:

1. authenticate as the expected GitHub user;
2. enumerate the user's repositories;
3. retrieve traffic data for the monitored repositories; and
4. update `ghtraffic.db` successfully.

For example:

```cmd
python ghtraffic.py collect
```

A permissions error from the traffic endpoints usually indicates that the token does not have **Administration: Read-only** access to the affected repository.

Because scheduled collection reads the same properties file, no separate Task Scheduler or systemd credential configuration is required.

## 9. Token rotation

If the token expires, is revoked, or is suspected to have been exposed:

1. generate a replacement fine-grained token with the same repository access and permissions;
2. replace the `github.token` value in `ghtraffic.properties`;
3. test GHTraffic manually;
4. revoke the old token in GitHub.

GHTraffic should always have its own token so it can be rotated or revoked without affecting unrelated GitHub tools.
