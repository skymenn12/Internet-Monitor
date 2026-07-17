@echo off
setlocal
cd /d %~dp0\..

where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher ^(py^) wurde nicht gefunden.
  echo Bitte Python 3.11 oder neuer installieren.
  pause
  exit /b 1
)

if not exist .venv (
  py -3.11 -m venv .venv
  if errorlevel 1 (
    echo Virtuelle Umgebung konnte nicht erstellt werden.
    pause
    exit /b 1
  )
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo Virtuelle Umgebung konnte nicht aktiviert werden.
  pause
  exit /b 1
)

python -m pip install --upgrade pip
if errorlevel 1 goto :fail

pip install -r requirements.txt
if errorlevel 1 goto :fail

pip install -e .
if errorlevel 1 goto :fail

echo.
echo Starte Internet Monitor Pro ...
python -m internet_monitor_pro.main
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" (
  echo.
  echo Das Programm wurde mit Fehlercode %EXITCODE% beendet.
  pause
)
exit /b %EXITCODE%

:fail
echo.
echo Beim Einrichten oder Starten ist ein Fehler aufgetreten.
pause
exit /b 1
