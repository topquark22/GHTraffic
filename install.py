#!/usr/bin/env python3

import csv
import html
import io
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path


DB_FILENAME = "ghtraffic.db"
SOURCE_DIR = Path(__file__).resolve().parent


def run(command, **kwargs):
    print("+", " ".join(str(part) for part in command))
    return subprocess.run(command, check=True, **kwargs)


def verify_sources():
    required = [
        SOURCE_DIR / "ghtraffic.py",
        SOURCE_DIR / "ghtraffic_ui.py",
        SOURCE_DIR / "ddl.sql",
        SOURCE_DIR / "static" / "chart.umd.min.js",
        SOURCE_DIR / "static" / "favicon.ico",
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise RuntimeError(
            "required installation file(s) missing: "
            + ", ".join(str(path) for path in missing)
        )


def verify_python():
    if sys.version_info < (3, 10):
        raise RuntimeError("GHTraffic requires Python 3.10 or later")

    print(f"Python: {sys.executable}")
    print(f"SQLite: {sqlite3.sqlite_version}")


def prompt_yes_no(prompt, default=True):
    suffix = " [Y/n] " if default else " [y/N] "
    response = input(prompt + suffix).strip().lower()
    if not response:
        return default
    return response in ("y", "yes")


def windows_paths():
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is not set")

    app_dir = Path(local_app_data) / "GHTraffic"
    return app_dir, app_dir / DB_FILENAME


def linux_paths():
    data_home = Path(
        os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
    ).expanduser()
    app_dir = Path.home() / ".local" / "lib" / "ghtraffic"
    return app_dir, data_home / "ghtraffic" / DB_FILENAME


def install_files(app_dir):
    app_dir.mkdir(parents=True, exist_ok=True)
    static_dir = app_dir / "static"
    static_dir.mkdir(parents=True, exist_ok=True)

    for filename in ("ghtraffic.py", "ghtraffic_ui.py"):
        source = SOURCE_DIR / filename
        destination = app_dir / filename
        shutil.copy2(source, destination)
        print(f"Installed: {destination}")

    for filename in ("chart.umd.min.js", "favicon.ico"):
        source = SOURCE_DIR / "static" / filename
        destination = static_dir / filename
        shutil.copy2(source, destination)
        print(f"Installed: {destination}")


def initialize_database(db_path):
    if db_path.exists():
        print(f"Preserving existing database: {db_path}")
        return

    db_path.parent.mkdir(parents=True, exist_ok=True)
    ddl = (SOURCE_DIR / "ddl.sql").read_text(encoding="utf-8")

    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(ddl)
        connection.commit()
    finally:
        connection.close()

    print(f"Created database: {db_path}")


def windows_environment_token():
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, "GITHUB_TOKEN")
            return value or None
    except FileNotFoundError:
        return None


def set_windows_environment_token(token):
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        winreg.SetValueEx(key, "GITHUB_TOKEN", 0, winreg.REG_SZ, token)


def configure_windows_credentials():
    stored_token = windows_environment_token()
    if stored_token:
        print("Using existing GITHUB_TOKEN from the Windows user environment.")
        return os.environ.get("GITHUB_TOKEN") or stored_token

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print(
            "GITHUB_TOKEN is not configured. Scheduled collection will require "
            "it to be added to the Windows user environment."
        )
        return None

    if prompt_yes_no(
        "Save the current GITHUB_TOKEN in the Windows user environment for scheduled collection?"
    ):
        set_windows_environment_token(token)
        print("Saved GITHUB_TOKEN in the Windows user environment.")
    else:
        print(
            "GITHUB_TOKEN was not persisted. The initial collection can use the "
            "current shell value, but scheduled collection may not authenticate."
        )

    return token


def linux_environment_path():
    return Path.home() / ".config" / "ghtraffic" / "environment"


def read_linux_environment_token(path):
    if not path.exists():
        return None

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("GITHUB_TOKEN="):
            return line.partition("=")[2] or None

    return None


def configure_linux_credentials():
    environment_path = linux_environment_path()
    stored_token = read_linux_environment_token(environment_path)
    if stored_token:
        print(f"Using existing credential file: {environment_path}")
        return os.environ.get("GITHUB_TOKEN") or stored_token

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print(
            f"GITHUB_TOKEN is not configured. Scheduled collection will require "
            f"it in {environment_path}."
        )
        return None

    if prompt_yes_no(
        f"Save the current GITHUB_TOKEN in {environment_path} for scheduled collection?"
    ):
        environment_path.parent.mkdir(parents=True, exist_ok=True)
        environment_path.write_text(f"GITHUB_TOKEN={token}\n", encoding="utf-8")
        environment_path.chmod(0o600)
        print(f"Saved GITHUB_TOKEN in {environment_path}.")
    else:
        print(
            "GITHUB_TOKEN was not persisted. The initial collection can use the "
            "current shell value, but scheduled collection may not authenticate."
        )

    return token


def windows_user_sid():
    result = subprocess.run(
        ["whoami", "/user", "/fo", "csv", "/nh"],
        check=True,
        capture_output=True,
        text=True,
    )
    row = next(csv.reader(io.StringIO(result.stdout)))
    if len(row) < 2 or not row[1]:
        raise RuntimeError("could not determine the current Windows user SID")
    return row[1]


def windows_task_xml(user_sid, command, arguments, working_directory, trigger_xml):
    return f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    {trigger_xml}
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{html.escape(user_sid)}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{html.escape(str(command))}</Command>
      <Arguments>{html.escape(arguments)}</Arguments>
      <WorkingDirectory>{html.escape(str(working_directory))}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
'''


def stop_windows_task(name):
    subprocess.run(
        ["schtasks", "/End", "/TN", name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def register_windows_task(name, xml):
    xml_path = Path(tempfile.gettempdir()) / f"{name.replace(' ', '_')}.xml"
    xml_path.write_text(xml, encoding="utf-16")
    try:
        run(["schtasks", "/Create", "/TN", name, "/XML", str(xml_path), "/F"])
    finally:
        try:
            xml_path.unlink()
        except FileNotFoundError:
            pass


def install_windows_tasks(app_dir):
    user_sid = windows_user_sid()
    python = Path(sys.executable)
    start = datetime.now().astimezone() + timedelta(minutes=5)
    start_boundary = start.isoformat(timespec="seconds")

    collector_trigger = f'''<TimeTrigger>
      <StartBoundary>{start_boundary}</StartBoundary>
      <Enabled>true</Enabled>
      <Repetition>
        <Interval>PT1H</Interval>
      </Repetition>
    </TimeTrigger>'''

    ui_trigger = f'''<LogonTrigger>
      <Enabled>true</Enabled>
      <UserId>{html.escape(user_sid)}</UserId>
    </LogonTrigger>'''

    collector_xml = windows_task_xml(
        user_sid,
        python,
        f'"{app_dir / "ghtraffic.py"}" collect',
        app_dir,
        collector_trigger,
    )
    ui_xml = windows_task_xml(
        user_sid,
        python,
        f'"{app_dir / "ghtraffic_ui.py"}"',
        app_dir,
        ui_trigger,
    )

    stop_windows_task("GHTraffic Collector")
    stop_windows_task("GHTraffic UI")
    register_windows_task("GHTraffic Collector", collector_xml)
    register_windows_task("GHTraffic UI", ui_xml)
    print("Configured password-free Windows tasks for the logged-on user.")


def systemd_quote(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def install_linux_units(app_dir):
    if not shutil.which("systemctl"):
        raise RuntimeError("systemctl is required for Linux installation")

    systemd_dir = Path.home() / ".config" / "systemd" / "user"
    systemd_dir.mkdir(parents=True, exist_ok=True)

    collector_service = f'''[Unit]
Description=GHTraffic repository traffic collector

[Service]
Type=oneshot
EnvironmentFile=-%h/.config/ghtraffic/environment
WorkingDirectory={systemd_quote(app_dir)}
ExecStart={systemd_quote(sys.executable)} {systemd_quote(app_dir / "ghtraffic.py")} collect
'''

    collector_timer = '''[Unit]
Description=Run GHTraffic collector hourly

[Timer]
OnCalendar=hourly
Persistent=true
Unit=ghtraffic-collector.service

[Install]
WantedBy=timers.target
'''

    ui_service = f'''[Unit]
Description=GHTraffic local web interface

[Service]
Type=simple
WorkingDirectory={systemd_quote(app_dir)}
ExecStart={systemd_quote(sys.executable)} {systemd_quote(app_dir / "ghtraffic_ui.py")}
Restart=on-failure

[Install]
WantedBy=default.target
'''

    units = {
        "ghtraffic-collector.service": collector_service,
        "ghtraffic-collector.timer": collector_timer,
        "ghtraffic-ui.service": ui_service,
    }

    for filename, content in units.items():
        path = systemd_dir / filename
        path.write_text(content, encoding="utf-8")
        print(f"Installed: {path}")

    run(["systemctl", "--user", "daemon-reload"])
    run(["systemctl", "--user", "enable", "ghtraffic-collector.timer"])
    run(["systemctl", "--user", "restart", "ghtraffic-collector.timer"])
    run(["systemctl", "--user", "enable", "ghtraffic-ui.service"])
    run(["systemctl", "--user", "restart", "ghtraffic-ui.service"])


def run_initial_collection(app_dir, token):
    if not token:
        print("No GITHUB_TOKEN is available; skipping initial collection.")
        return

    print("Running initial collection...")
    environment = os.environ.copy()
    environment["GITHUB_TOKEN"] = token
    result = subprocess.run(
        [sys.executable, str(app_dir / "ghtraffic.py"), "collect"],
        env=environment,
    )
    if result.returncode != 0:
        print("Initial collection failed; scheduled collection is still configured.")


def main():
    verify_python()
    verify_sources()

    if sys.platform == "win32":
        app_dir, db_path = windows_paths()
        install_files(app_dir)
        initialize_database(db_path)
        token = configure_windows_credentials()
        install_windows_tasks(app_dir)
        run_initial_collection(app_dir, token)
        run(["schtasks", "/Run", "/TN", "GHTraffic UI"])
    elif sys.platform.startswith("linux"):
        app_dir, db_path = linux_paths()
        install_files(app_dir)
        initialize_database(db_path)
        token = configure_linux_credentials()
        install_linux_units(app_dir)
        run_initial_collection(app_dir, token)
    else:
        raise RuntimeError(f"unsupported operating system: {sys.platform}")

    print()
    print("GHTraffic installation complete.")
    print(f"Database: {db_path}")
    print("User interface: http://127.0.0.1:8501")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, sqlite3.Error, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
