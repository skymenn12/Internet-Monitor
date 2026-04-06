# Internet Monitor Pro

Desktop-App für Windows zur Überwachung der Internetverbindung in Echtzeit.

## Funktionen

- erkennt Online/Offline-Wechsel zuverlässig
- überwacht öffentliche und lokale IP
- führt automatische und manuelle Speedtests aus
- zeigt Download, Upload, Ping und Prozentwerte an
- führt ein Ereignislog mit Filtern und Export
- kann App-Pop-ups für Störungen und Speedwarnungen anzeigen
- speichert Einstellungen direkt und unterstützt Windows-Autostart

## Voraussetzungen

- Windows 10/11
- Python 3.11+

## Entwicklung starten

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
python -m internet_monitor_pro.main
```

Alternativ kannst du `scripts\run_dev.bat` nutzen.

## EXE bauen

```bat
scripts\build_exe.bat
```

## Installer bauen

1. Inno Setup installieren
2. `scripts\installer.iss` öffnen
3. kompilieren

## Projektstruktur

- `src/internet_monitor_pro/` – Anwendungscode
- `assets/` – Icons und Grafiken
- `scripts/` – Start-, Build- und Installer-Skripte

## GitHub-Kurzbeschreibung

Internet Monitor Pro überwacht deine Internetverbindung in Echtzeit. Erfasst Verbindungsabbrüche, IP-Änderungen und Speedtests automatisch. Mit Live-Status, Ereignislog, Filtern, Pop-ups und anpassbaren Intervallen. Zeigt Leistung inkl. Prozentwerten und erkennt Probleme sofort.
