@echo off
setlocal
cd /d %~dp0\..

where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher ^(py^) wurde nicht gefunden.
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

if not exist InternetMonitorPro.spec (
  echo Die Datei InternetMonitorPro.spec wurde nicht gefunden.
  pause
  exit /b 1
)

pyinstaller --clean --noconfirm InternetMonitorPro.spec
if errorlevel 1 goto :fail

echo.
echo EXE-Build abgeschlossen.
pause
exit /b 0

:fail
echo.
echo Beim Build ist ein Fehler aufgetreten.
pause
exit /b 1
