#!/usr/bin/env bash

set -euo pipefail

usage() {
  echo "Usage: $0 [-d database]"
}

db_override=""
while getopts ":d:h" opt; do
  case "$opt" in
    d)
      db_override="$OPTARG"
      ;;
    h)
      usage
      exit 0
      ;;
    :)
      echo "Error: -$OPTARG requires an argument" >&2
      usage >&2
      exit 1
      ;;
    \?)
      echo "Error: unknown option -$OPTARG" >&2
      usage >&2
      exit 1
      ;;
  esac
done

shift $((OPTIND - 1))
if [[ $# -ne 0 ]]; then
  usage >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ddl_file="$script_dir/ddl.sql"

if [[ ! -f "$ddl_file" ]]; then
  echo "Error: ddl.sql not found at $ddl_file" >&2
  exit 1
fi

platform="$(uname -s)"

if [[ -n "$db_override" ]]; then
  db_file="$db_override"
elif [[ -n "${GITHUBMONITOR_DB:-}" ]]; then
  db_file="$GITHUBMONITOR_DB"
elif [[ "$platform" == CYGWIN* || "$platform" == MINGW* || "$platform" == MSYS* ]]; then
  if [[ -z "${LOCALAPPDATA:-}" ]]; then
    echo "Error: LOCALAPPDATA is not set" >&2
    exit 1
  fi

  db_file="$LOCALAPPDATA/GitHubMonitor/githubtraffic.db"
else
  data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
  db_file="$data_home/githubmonitor/githubtraffic.db"
fi

if [[ "$platform" == CYGWIN* || "$platform" == MINGW* || "$platform" == MSYS* ]]; then
  db_dir="$(dirname "$db_file")"
  mkdir -p "$db_dir"

  if command -v sqlite3.exe >/dev/null 2>&1; then
    sqlite_cmd="sqlite3.exe"
  elif command -v sqlite3 >/dev/null 2>&1; then
    sqlite_cmd="sqlite3"
  else
    echo "Error: sqlite3 executable not found" >&2
    exit 1
  fi

  if command -v cygpath >/dev/null 2>&1; then
    sqlite_db_file="$(cygpath -w "$db_file")"
  else
    sqlite_db_file="$db_file"
  fi
else
  db_dir="$(dirname "$db_file")"
  mkdir -p "$db_dir"

  if ! command -v sqlite3 >/dev/null 2>&1; then
    echo "Error: sqlite3 executable not found" >&2
    exit 1
  fi

  sqlite_cmd="sqlite3"
  sqlite_db_file="$db_file"
fi

printf 'Creating database: %s\n' "$db_file"
"$sqlite_cmd" "$sqlite_db_file" < "$ddl_file"
printf 'Database initialized successfully.\n'
