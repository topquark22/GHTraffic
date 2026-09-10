#!/usr/bin/env python3

import os
import shutil
import sqlite3
import subprocess
import sys
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


def windows_task_xml(command, arguments, working_directory, trigger_xml):
    username = os.environ.get("USERNAME", "")
    return f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    {trigger_xml}
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{username}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{command}</Command>
      <Arguments>{arguments}</Arguments>
      <WorkingDirectory>{working_directory}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
'''


def register_windows_task(name, xml):
    temp_dir = Path(os.environ.get("TEMP", "."))
    xml_path = temp_dir / f"{name.replace(' ', '_')}.xml"
    xml_path.write_text(xml, encoding="utf-16")
    try:
        run(["schtasks", "/Create", "/TN", name, "/XML", str(xml_path), "/F"])
    finally:
        try:
            xml_path.unlink()
        except FileNotFoundError:
            pass


def install_windows_tasks(app_dir):
    python = Path(sys.executable)
    start = datetime.now() + timedelta(minutes=5)
    start_boundary = start.astimezone().isoformat(timespec="seconds")

    collector_trigger = f'''<TimeTrigger>
      <StartBoundary>{start_boundary}</StartBoundary>
      <Enabled>true</Enabled>
      <Repetition>
        <Interval>PT1H</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
    </TimeTrigger>'''

    ui_trigger = '''<LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>'''

    collector_xml = windows_task_xml(
        python,
        f'"{app_dir / "ghtraffic.py"}" collect',
        app_dir,
        collector_trigger,
    )
    ui_xml = windows_task_xml(
        python,
        f'"{app_dir / "ghtraffic_ui.py"}"',
        app_dir,
        ui_trigger,
    )

    register_windows_task("GHTraffic Collector", collector_xml)
    register_windows_task("GHTraffic UI", ui_xml)
    print("Configured Windows tasks for the logged-on user.")


def install_linux_units(app_dir):
    systemd_dir = Path.home() / ".config" / "systemd" / "user"
    systemd_dir.mkdir(parents=True, exist_ok=True)

    collector_service = f'''[Unit]
Description=Collect GitHub traffic statistics

[Service]
Type=oneshot
EnvironmentFile=-%h/.config/ghtraffic/environment
ExecStart={sys.executable} {app_dir / "ghtraffic.py"} collect
'''

    collector_timer = '''[Unit]
Description=Collect GitHub traffic statistics hourly

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
Persistent=true

[Install]
WantedBy=timers.target
'''

    ui_service = f'''[Unit]
Description=GHTraffic local web interface

[Service]
Type=simple
ExecStart={sys.executable} {app_dir / "ghtraffic_ui.py"}
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
    run(["systemctl", "--user", "enable", "--now", "ghtraffic-collector.timer"])
    run(["systemctl", "--user", "enable", "--now", "ghtraffic-ui.service"])


def run_initial_collection(app_dir):
    if not os.environ.get("GITHUB_TOKEN"):
        print("GITHUB_TOKEN is not set; skipping initial collection.")
        return

    print("Running initial collection...")
    result = subprocess.run([sys.executable, str(app_dir / "ghtraffic.py"), "collect"])
    if result.returncode != 0:
        print("Initial collection failed; scheduled collection is still configured.")


def main():
    verify_python()
    verify_sources()

    if sys.platform == "win32":
        app_dir, db_path = windows_paths()
        install_files(app_dir)
        initialize_database(db_path)
        install_windows_tasks(app_dir)
        run_initial_collection(app_dir)
        run(["schtasks", "/Run", "/TN", "GHTraffic UI"])
    elif sys.platform.startswith("linux"):
        app_dir, db_path = linux_paths()
        install_files(app_dir)
        initialize_database(db_path)
        install_linux_units(app_dir)
        run_initial_collection(app_dir)
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
