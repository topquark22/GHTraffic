# GHTraffic Linux Deployment

This document describes manual deployment of GHTraffic on Linux after the initial setup and GitHub authentication steps have been completed.

For the normal installation path, run:

```bash
python3 install.py
```

The installer performs these steps automatically. This document is retained for users who want the details or need a custom deployment.

See [SETUP.md](SETUP.md) for database setup, [GITHUB_SETUP.md](GITHUB_SETUP.md) for GitHub token configuration, and [USAGE.md](USAGE.md) for command-line usage.

## Application and data directories

GHTraffic uses separate per-user locations for application files, data, configuration, and systemd units.

Recommended application directory:

```text
~/.local/lib/ghtraffic/
```

Default database location:

```text
~/.local/share/ghtraffic/github_traffic.db
```

Configuration directory:

```text
~/.config/ghtraffic/
```

Systemd user units:

```text
~/.config/systemd/user/
```

The deployed application directory should contain:

```text
~/.local/lib/ghtraffic/
    ghtraffic.py
    ghtraffic_ui.py
    static/
        chart.umd.min.js
        favicon.ico
```

The GitHub credential and database location are stored separately in:

```text
~/.config/ghtraffic/ghtraffic.properties
```

Create the required directories:

```bash
mkdir -p ~/.local/lib/ghtraffic
mkdir -p ~/.local/share/ghtraffic
mkdir -p ~/.config/ghtraffic
mkdir -p ~/.config/systemd/user
```

Copy the application files from the source tree:

```bash
cp ghtraffic.py ~/.local/lib/ghtraffic/
cp ghtraffic_ui.py ~/.local/lib/ghtraffic/
cp -R static ~/.local/lib/ghtraffic/
```

## Initialize the database

The default Linux database path is:

```text
~/.local/share/ghtraffic/github_traffic.db
```

The main `install.py` installer writes this location to `database.path` in `ghtraffic.properties`, initializes the database automatically when it does not already exist, and preserves an existing database during upgrades.

For a fresh installation, run:

```bash
python3 install.py
```

## Configure GitHub authentication

GHTraffic reads configuration from:

```text
~/.config/ghtraffic/ghtraffic.properties
```

The normal properties are:

```text
database.path=/home/user/.local/share/ghtraffic/github_traffic.db
github.token=github_pat_...
```

Restrict access to the file:

```bash
chmod 600 ~/.config/ghtraffic/ghtraffic.properties
```

When `install.py` is run and no token is already configured, it prompts for the token without echoing it to the terminal and creates or updates this file automatically. Existing configuration is preserved.

No `GITHUB_TOKEN` or database-location environment variable is required.

Do not commit the properties file or place the token in a systemd unit.

## Test the collector

Run:

```bash
python3 ~/.local/lib/ghtraffic/ghtraffic.py collect
```

Then verify the report:

```bash
python3 ~/.local/lib/ghtraffic/ghtraffic.py show
```

The collector should update the database configured by `database.path`.

## Schedule the collector with systemd

Create:

```text
~/.config/systemd/user/ghtraffic-collector.service
```

with:

```ini
[Unit]
Description=GHTraffic repository traffic collector

[Service]
Type=oneshot
WorkingDirectory=%h/.local/lib/ghtraffic
ExecStart=/usr/bin/python3 %h/.local/lib/ghtraffic/ghtraffic.py collect
```

Create:

```text
~/.config/systemd/user/ghtraffic-collector.timer
```

with:

```ini
[Unit]
Description=Run GHTraffic collector hourly

[Timer]
OnCalendar=hourly
Persistent=true
Unit=ghtraffic-collector.service

[Install]
WantedBy=timers.target
```

Reload the user systemd configuration and enable the timer:

```bash
systemctl --user daemon-reload
systemctl --user enable --now ghtraffic-collector.timer
```

Verify it with:

```bash
systemctl --user status ghtraffic-collector.timer
systemctl --user list-timers ghtraffic-collector.timer
```

Run the collector immediately for testing:

```bash
systemctl --user start ghtraffic-collector.service
```

Inspect its status and logs:

```bash
systemctl --user status ghtraffic-collector.service
journalctl --user -u ghtraffic-collector.service
```

## Run the user interface continuously

Create:

```text
~/.config/systemd/user/ghtraffic-ui.service
```

with:

```ini
[Unit]
Description=GHTraffic local web interface

[Service]
Type=simple
WorkingDirectory=%h/.local/lib/ghtraffic
ExecStart=/usr/bin/python3 %h/.local/lib/ghtraffic/ghtraffic_ui.py
Restart=on-failure

[Install]
WantedBy=default.target
```

Reload systemd and enable the service:

```bash
systemctl --user daemon-reload
systemctl --user enable --now ghtraffic-ui.service
```

Verify:

```bash
systemctl --user status ghtraffic-ui.service
```

Then open:

```text
http://127.0.0.1:8501
```

The UI listens only on `127.0.0.1`, so it is available only from the local machine.

If the traffic chart is missing, verify:

```text
~/.local/lib/ghtraffic/static/chart.umd.min.js
```

If the favicon is missing, verify:

```text
~/.local/lib/ghtraffic/static/favicon.ico
```

## Run user services without an active login session

On Linux systems using systemd-logind, user services normally start with the user's login session. If GHTraffic must continue running after logout or start at boot before an interactive login, enable lingering for the account:

```bash
loginctl enable-linger "$USER"
```

This is normally a one-time administrative configuration.

## Traffic history availability

The **Period** selector limits the chart to the requested number of days, but GHTraffic displays only traffic records that actually exist in the local database.

GitHub supplies only a short recent window of daily traffic data. GHTraffic preserves those records on each collection so longer history accumulates over time.

GHTraffic does not synthesize zero-valued records for dates before collection began or for dates for which no record exists. A missing record means that traffic is unknown; it must not be interpreted as zero views or zero clones.

GitHub traffic dates are UTC, and the graph labels its date axis accordingly.

## Updating an existing Linux deployment

The simplest update procedure is to run the current installer again:

```bash
python3 install.py
```

The installer replaces the application and static files, preserves the existing database and `ghtraffic.properties`, updates the systemd user units, and restarts the UI.

For a manual update, copy the current application files again:

```bash
cp ghtraffic.py ~/.local/lib/ghtraffic/
cp ghtraffic_ui.py ~/.local/lib/ghtraffic/
cp -R static ~/.local/lib/ghtraffic/
```

Restart the UI after updating `ghtraffic_ui.py` or files under `static`:

```bash
systemctl --user restart ghtraffic-ui.service
```

The collector service is short-lived and will use the updated `ghtraffic.py` automatically on its next run.
