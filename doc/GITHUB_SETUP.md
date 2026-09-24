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

For a fine-grained personal access token, GHTraffic requires:

```text
Repository permissions
  Administration: Read-only
  Metadata: Read-only
```

**Administration: Read-only** is the permission GitHub requires for the repository
traffic endpoints used by GHTraffic, including views, clones, and popular
referrers.

**Metadata: Read-only** is used to enumerate repositories through GitHub's
authenticated-user repository endpoint. GitHub normally includes this permission
automatically when repository access is granted.

No other repository permissions are required. In particular, GHTraffic does not
need Contents, Issues, Pull requests, Actions, or any write permission.

The token must also have access to every repository that GHTraffic is expected to
monitor. Selecting **All repositories** is recommended as described above.

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
4. update `github_traffic.db` successfully.

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


## Multiple GitHub accounts

GHTraffic can collect traffic for more than one GitHub account. Keep the existing
`github.token` entry for the first account and add additional tokens with unique
property suffixes:

```text
github.token=github_pat_...
github.token.work=github_pat_...
github.token.other=github_pat_...
```

The suffix is only a local configuration key; GHTraffic determines the GitHub
account name by authenticating each token with GitHub. The web interface presents
one **Account** dropdown entry for each token property, labelled with both the
discovered GitHub login and the property key. Multiple tokens for the same GitHub
account therefore appear as separate entries and select the same repository set.

Scheduled collection uses every configured token. To collect only one configured
account manually, use:

```bash
python ghtraffic.py collect --account topquark22
```

Each token should have the repository access and read-only Administration
permission described above for its own account.


## Expired, revoked, or removed tokens

Each configured token is authenticated independently during collection. If one
token has expired, been revoked, or is otherwise invalid, GHTraffic records the
authentication failure, reports it, continues collecting all other valid
accounts, and exits with a failure status after the remaining work is complete.

Removing or commenting out a token in `ghtraffic.properties` does not remove
its credential record or the account's historical traffic from the database.
The web interface rereads `ghtraffic.properties` whenever the page loads, so a
removed or commented-out token is omitted from the Account dropdown immediately;
a collector run is not required for that configuration change to appear.

The Account dropdown contains one entry per known token property rather than one
entry per GitHub login. This makes duplicate tokens for the same GitHub account
visible independently, including the status of each token. Selecting either token
for the same login displays the same repository set.

A token that is still configured but fails authentication remains in the Account
dropdown with a warning marker. A token that is no longer configured is not shown.
Historical repository traffic and referrer data are not deleted in either case.
With only one configured token entry, the Account dropdown remains hidden as in
the single-account interface; an authentication failure is indicated in the page
title instead.

Replacing or restoring a valid token causes that token entry to return to normal
status on the next successful collection.
