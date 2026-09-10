#!/usr/bin/env python3

import getpass
import html
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path


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


def windows_paths():
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is not set")

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
    if sys.platform != "win32":
        properties_path.chmod(0o600)
    print(f"Saved credentials: {properties_path}")
    return True


def windows_user_id():
    username = os.environ.get("USERNAME")
    if not username:
        raise RuntimeError("could not determine the current Windows user")

    domain = os.environ.get("USERDOMAIN")
    if domain:
        return f"{domain}\\{username}"
    return username


def windows_task_xml(user_id, command, arguments, working_directory, trigger_xml):
    return f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    {trigger_xml}
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{html.escape(user_id)}</UserId>
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
    try:
        print("+", " ".join([
            "schtasks.exe", "/Create", "/TN", name, "/XML", str(xml_path), "/F"
        ]))
        result = subprocess.run(
            ["schtasks.exe", "/Create", "/TN", name, "/XML", str(xml_path), "/F"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            message = (result.stderr or result.stdout).strip()
            if "Access is denied" in message:
                raise RuntimeError(
                    f"Windows would not replace the existing scheduled task '{name}'. "
                    "It was probably created previously with administrator privileges. "
                    "Delete that old task once from an Administrator Command Prompt with: "
                    f'schtasks /Delete /TN "{name}" /F  '
                    "Then return to a normal Command Prompt and run: python install.py"
                )
            raise RuntimeError(
                f"could not create Windows scheduled task '{name}': {message}"
            )
    finally:
        try:
            xml_path.unlink()
        except FileNotFoundError:
            pass


def install_windows_tasks(app_dir):
    user_id = windows_user_id()
    python = Path(sys.executable)
    pythonw = python.with_name("pythonw.exe")
    if not pythonw.exists():
        raise RuntimeError(f"pythonw.exe was not found next to python.exe: {pythonw}")

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
      <UserId>{html.escape(user_id)}</UserId>
    </LogonTrigger>'''

    collector_xml = windows_task_xml(
        user_id,
        python,
        f'"{app_dir / "ghtraffic.py"}" collect',
        app_dir,
        collector_trigger,
    )
    ui_xml = windows_task_xml(
        user_id,
        pythonw,
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
    result = subprocess.run([sys.executable, str(app_dir / "ghtraffic.py"), "collect"])
    if result.returncode != 0:
        print("Initial collection failed; scheduled collection is still configured.")


def main():
    if sys.platform == "cygwin":
        raise RuntimeError(
            "GHTraffic installation on Windows must be run from Windows Command Prompt. "
            "Open cmd.exe, change to the GHTraffic source directory, and run: python install.py"
        )

    verify_python()
    verify_sources()

    if sys.platform == "win32":
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
