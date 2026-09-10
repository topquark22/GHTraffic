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

## Usage

The interface is at `http://localhost:8501`

## Documentation

- [GitHub authentication](doc/GITHUB_SETUP.md)
- [Windows deployment](doc/DEPLOY_WIN.md)
- [Linux deployment](doc/DEPLOY_LINUX.md)
- [Command-line usage](doc/USAGE.md)
