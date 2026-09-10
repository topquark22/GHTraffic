@echo off
setlocal

set "DB_FILE="

if "%~1"=="" goto resolve_db
if /I "%~1"=="-h" goto usage
if /I "%~1"=="--help" goto usage
if /I not "%~1"=="-d" goto bad_args
if "%~2"=="" goto bad_args
if not "%~3"=="" goto bad_args
set "DB_FILE=%~2"

:resolve_db
if defined DB_FILE goto have_db
if defined GHTRAFFIC_DB (
  set "DB_FILE=%GHTRAFFIC_DB%"
  goto have_db
)
if not defined LOCALAPPDATA (
  echo Error: LOCALAPPDATA is not set 1>&2
  exit /b 1
)
set "DB_FILE=%LOCALAPPDATA%\GHTraffic\ghtraffic.db"

:have_db
set "DDL_FILE=%~dp0ddl.sql"
if not exist "%DDL_FILE%" (
  echo Error: ddl.sql not found at %DDL_FILE% 1>&2
  exit /b 1
)

for %%I in ("%DB_FILE%") do set "DB_DIR=%%~dpI"
if not exist "%DB_DIR%" mkdir "%DB_DIR%"
if errorlevel 1 exit /b 1

echo Creating database: %DB_FILE%
python -c "import pathlib, sqlite3, sys; db=pathlib.Path(sys.argv[1]); ddl=pathlib.Path(sys.argv[2]); con=sqlite3.connect(db); con.executescript(ddl.read_text(encoding='utf-8')); con.close()" "%DB_FILE%" "%DDL_FILE%"
if errorlevel 1 exit /b 1

echo Database initialized successfully.
exit /b 0

:usage
echo Usage: %~nx0 [-d database]
exit /b 0

:bad_args
echo Error: invalid arguments 1>&2
echo Usage: %~nx0 [-d database] 1>&2
exit /b 1
