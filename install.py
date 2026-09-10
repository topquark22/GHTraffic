#!/usr/bin/env python3

import csv
import getpass
import html
import io
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path, PureWindowsPath


DB_FILENAME = "ghtraffic.db"
PROPERTIES_FILENAME = "ghtraffic.properties"
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


def cygwin_posix_path(path):
    windows_path = PureWindowsPath(str(path))
    drive = windows_path.drive.rstrip(":").lower()
    if not drive:
        raise RuntimeError(f"Windows path has no drive letter: {path}")

    parts = windows_path.parts[1:]
    return Path("/cygdrive") / drive / Path(*parts)


def cygwin_windows_path(path):
    path = Path(path)
    parts = path.parts
    if len(parts) >= 4 and parts[0] == "/" and parts[1] == "cygdrive":
        drive = parts[2].upper()
        return str(PureWindowsPath(f"{drive}:/", *parts[3:]))

    raise RuntimeError(f"cannot convert Cygwin path to Windows path: {path}")


def windows_paths():
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is not set")

    if sys.platform == "cygwin":
        app_dir = cygwin_posix_path(local_app_data) / "GHTraffic"
    else:
        app_dir = Path(local_app_data) / "GHTraffic"

    return app_dir, app_dir / DB_FILENAME, app_dir / PROPERTIES_FILENAME


def linux_paths():
    data_home = Path(
        os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
    ).expanduser()
    config_home = Path(
        os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
    ).expanduser()
    app_dir = Path.home() / ".local" / "lib" / "ghtraffic"
    return (
        app_dir,
        data_home / "ghtraffic" / DB_FILENAME,
        config_home / "ghtraffic" / PROPERTIES_FILENAME,
    )


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


def read_properties(path):
    properties = {}
    if not path.exists():
        return properties

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        properties[key.strip()] = value.strip()

    return properties


def configure_credentials(properties_path):
    properties = read_properties(properties_path)
    token = properties.get("github.token")
    if token:
        print(f"Preserving existing credentials: {properties_path}")
        return True

    print()
    print("GHTraffic needs a GitHub access token to collect traffic statistics.")
    print("The token will be stored only in the local properties file:")
    print(properties_path)
    token = getpass.getpass("GitHub access token (leave blank to skip): ").strip()
    if not token:
        print("No token supplied; initial and scheduled collection will not authenticate yet.")
        return False

    properties_path.parent.mkdir(parents=True, exist_ok=True)
    properties_path.write_text(f"github.token={token}\n", encoding="utf-8")
    if sys.platform != "win32" and sys.platform != "cygwin":
        properties_path.chmod(0o600)
    print(f"Saved credentials: {properties_path}")
    return True


def windows_user_sid():
    result = subprocess.run(
        ["whoami.exe", "/user", "/fo", "csv", "/nh"],
        check=True,
        capture_output=True,
        text=True,
    )
    row = next(csv.reader(io.StringIO(result.stdout)))
    if len(row) < 2 or not row[1]:
        raise RuntimeError("could not determine the current Windows user SID")
    return row[1]


def native_windows_python():
    if sys.platform == "win32":
        return str(Path(sys.executable))

    launcher = shutil.which("py.exe")
    if launcher:
        result = subprocess.run(
            [launcher, "-3", "-c", "import sys; print(sys.executable)"],
            check=True,
            capture_output=True,
            text=True,
        )
        python = result.stdout.strip()
        if python:
            return python

    result = subprocess.run(
        ["where.exe", "python"],
        check=True,
        capture_output=True,
        text=True,
    )
    candidates = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    for candidate in candidates:
        if "WindowsApps" not in candidate:
            return candidate

    raise RuntimeError("native Windows python.exe was not found")


def native_windows_path(path):
    if sys.platform == "cygwin":
        return cygwin_windows_path(path)
    return str(path)


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
        ["schtasks.exe", "/End", "/TN", name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def register_windows_task(name, xml):
    xml_path = Path(tempfile.gettempdir()) / f"{name.replace(' ', '_')}.xml"
    xml_path.write_text(xml, encoding="utf-16")
    native_xml_path = native_windows_path(xml_path)
    try:
        run(["schtasks.exe", "/Create", "/TN", name, "/XML", native_xml_path, "/F"])
    finally:
        try:
            xml_path.unlink()
        except FileNotFoundError:
            pass


def install_windows_tasks(app_dir):
    user_sid = windows_user_sid()
    python = native_windows_python()
    native_app_dir = native_windows_path(app_dir)
    native_collector = native_windows_path(app_dir / "ghtraffic.py")
    native_ui = native_windows_path(app_dir / "ghtraffic_ui.py")
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
        f'"{native_collector}" collect',
        native_app_dir,
        collector_trigger,
    )
    ui_xml = windows_task_xml(
        user_sid,
        python,
        f'"{native_ui}"',
        native_app_dir,
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


def run_initial_collection(app_dir, credentials_available):
    if not credentials_available:
        print("No GitHub token is configured; skipping initial collection.")
        return

    print("Running initial collection...")
    if sys.platform == "cygwin":
        command = [
            native_windows_python(),
            native_windows_path(app_dir / "ghtraffic.py"),
            "collect",
        ]
    else:
        command = [sys.executable, str(app_dir / "ghtraffic.py"), "collect"]

    result = subprocess.run(command)
    if result.returncode != 0:
        print("Initial collection failed; scheduled collection is still configured.")


def main():
    verify_python()
    verify_sources()

    if sys.platform in ("win32", "cygwin"):
        app_dir, db_path, properties_path = windows_paths()
        install_files(app_dir)
        initialize_database(db_path)
        credentials_available = configure_credentials(properties_path)
        install_windows_tasks(app_dir)
        run_initial_collection(app_dir, credentials_available)
        run(["schtasks.exe", "/Run", "/TN", "GHTraffic UI"])
    elif sys.platform.startswith("linux"):
        app_dir, db_path, properties_path = linux_paths()
        install_files(app_dir)
        initialize_database(db_path)
        credentials_available = configure_credentials(properties_path)
        install_linux_units(app_dir)
        run_initial_collection(app_dir, credentials_available)
    else:
        raise RuntimeError(f"unsupported operating system: {sys.platform}")

    print()
    print("GHTraffic installation complete.")
    print(f"Database: {db_path}")
    print(f"Properties: {properties_path}")
    print("User interface: http://127.0.0.1:8501")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, sqlite3.Error, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
