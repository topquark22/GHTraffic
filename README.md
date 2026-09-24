# GHTraffic

GHTraffic collects GitHub repository traffic statistics and stores them in a local SQLite database so that historical data is retained beyond GitHub's short traffic-retention window.

The current version monitors all non-fork repositories owned by the authenticated GitHub user and provides both command-line reporting and a local web interface for views, clones, and referrer traffic.

## Installation

After configuring a GitHub access token as described in [GitHub authentication](doc/GITHUB_SETUP.md), run:

```text
python install.py
```

The installer supports Windows and Linux. It installs the application, initializes the database when necessary, configures hourly collection and UI startup, preserves an existing database during upgrades, and starts the local web interface.

For manual installation and platform-specific details, see the deployment documents below.

## Upgrading to 4.0.0

Version 4.0.0 introduces multi-account authentication and a database migration
framework. Existing installations should be upgraded by running the installer
normally:

```text
python install.py
```

The installer preserves the existing traffic database and configuration, then
applies any unapplied SQL files under `migrations/`. For the 4.0.0 upgrade,
`001_account_credentials.sql` adds credential-status tracking used by the
multi-account interface. Applied migrations are recorded in the
`schema_migrations` table and are not run again on subsequent installations.

Existing traffic history is not deleted or recreated during the migration.

## Usage

The [interface](http://localhost:8501) is at `http://localhost:8501`

## Documentation

- [GitHub authentication](doc/GITHUB_SETUP.md)
- [Windows deployment](doc/DEPLOY_WIN.md)
- [Linux deployment](doc/DEPLOY_LINUX.md)
- [Command-line usage](doc/USAGE.md)
