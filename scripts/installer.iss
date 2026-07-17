#define MyAppName "Internet-Protokoll"
#define MyAppVersion "1.13.0"
#define MyAppPublisher "Skymenn"
#define MyAppExeName "InternetMonitorPro.exe"

[Setup]
AppId={{B3D42D40-0F06-4B0F-8C8A-3A78F2C3C5E1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
OutputDir=..\dist_installer
OutputBaseFilename=Internet-Protokoll-Setup-v26
SetupIconFile=..\assets\icon.ico

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Aufgaben:"
Name: "autostart"; Description: "Mit Windows starten"; GroupDescription: "Zusätzliche Aufgaben:"; Flags: checkedonce

[Dirs]
Name: "{localappdata}\Internet-Protokoll"
Name: "{localappdata}\Internet-Protokoll\logs"

[Files]
Source: "..\dist\InternetMonitorPro\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "InternetProtokoll"; ValueData: """{app}\{#MyAppExeName}"" --minimized"; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Internet-Protokoll starten"; Flags: nowait postinstall skipifsilent


[Code]
var
  ProviderPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  ProviderPage := CreateInputQueryPage(
    wpSelectTasks,
    'Anbieter-Leitung',
    'Geschwindigkeit vom Anbieter eintragen',
    'Bitte die vertragliche Geschwindigkeit eintragen. Diese Werte werden direkt in die Startkonfiguration übernommen.'
  );
  ProviderPage.Add('Download in Mbit/s:', False);
  ProviderPage.Add('Upload in Mbit/s (optional):', False);
  ProviderPage.Values[0] := '250';
  ProviderPage.Values[1] := '50';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigDir: string;
  ConfigPath: string;
  Json: string;
  DownloadValue: string;
  UploadValue: string;
begin
  if CurStep <> ssPostInstall then
    exit;

  DownloadValue := Trim(ProviderPage.Values[0]);
  UploadValue := Trim(ProviderPage.Values[1]);
  if DownloadValue = '' then DownloadValue := '250';
  if UploadValue = '' then UploadValue := '50';

  ConfigDir := ExpandConstant('{localappdata}\Skymenn\Internet-Protokoll');
  ForceDirectories(ConfigDir);
  ConfigPath := ConfigDir + '\config.json';

  Json :=
    '{' + #13#10 +
    '  "connection_watch": {' + #13#10 +
    '    "enabled": true,' + #13#10 +
    '    "interval_seconds": 0.5,' + #13#10 +
    '    "socket_targets": [' + #13#10 +
    '      {"host": "1.1.1.1", "port": 53, "timeout": 2.0},' + #13#10 +
    '      {"host": "8.8.8.8", "port": 53, "timeout": 2.0}' + #13#10 +
    '    ]' + #13#10 +
    '  },' + #13#10 +
    '  "speedtest": {' + #13#10 +
    '    "enabled": true,' + #13#10 +
    '    "interval_minutes": 5,' + #13#10 +
    '    "provider": "speedtest-cli",' + #13#10 +
    '    "timeout_seconds": 120,' + #13#10 +
    '    "provider_download_mbps": ' + DownloadValue + ',' + #13#10 +
    '    "provider_upload_mbps": ' + UploadValue + ',' + #13#10 +
    '    "provider_download_mbps_set_by_installer": true,' + #13#10 +
    '    "provider_upload_mbps_set_by_installer": true,' + #13#10 +
    '    "warn_download_mbps_below": 0,' + #13#10 +
    '    "warn_upload_mbps_below": 0,' + #13#10 +
    '    "warn_ping_ms_above": 0' + #13#10 +
    '  },' + #13#10 +
    '  "ip_monitor": {' + #13#10 +
    '    "enabled": true,' + #13#10 +
    '    "interval_seconds": 10,' + #13#10 +
    '    "providers": [' + #13#10 +
    '      "https://api.ipify.org",' + #13#10 +
    '      "https://checkip.amazonaws.com",' + #13#10 +
    '      "https://ipv4.icanhazip.com"' + #13#10 +
    '    ]' + #13#10 +
    '  },' + #13#10 +
    '  "notifications": {' + #13#10 +
    '    "enabled": true,' + #13#10 +
    '    "show_online": true,' + #13#10 +
    '    "show_offline": true,' + #13#10 +
    '    "show_ip_change": true,' + #13#10 +
    '    "show_speed_warnings": true,' + #13#10 +
    '    "cooldown_seconds": 5,' + #13#10 +
    '    "show_windows_toasts": false,' + #13#10 +
    '    "show_app_toasts": true' + #13#10 +
    '  },' + #13#10 +
    '  "reporting": {"enabled": true, "daily_report_time": "23:55"},' + #13#10 +
    '  "logging": {"max_bytes": 5000000, "backup_count": 5, "max_lines_soft": 50000},' + #13#10 +
    '  "startup": {"start_with_windows": true, "start_minimized_to_tray": false},' + #13#10 +
    '  "ui": {"minimize_to_tray": true, "close_to_tray": true, "event_filter": "Alle anzeigen"}' + #13#10 +
    '}' + #13#10;

  if not FileExists(ConfigPath) then
    SaveStringToFile(ConfigPath, Json, False);
end;
