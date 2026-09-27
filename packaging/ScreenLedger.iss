#define AppName "ScreenLedger"
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#define AppPublisher "ScreenLedger contributors"
#define AppURL "https://github.com/eraybilgin/ScreenLedger"

[Setup]
AppId={{D9744411-1F85-4B31-8EED-DF9D28F3CA96}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={localappdata}\Programs\ScreenLedger
DefaultGroupName=ScreenLedger
OutputDir=..\release
OutputBaseFilename=ScreenLedger-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
CloseApplications=no
RestartApplications=no
UninstallDisplayName=ScreenLedger
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=ScreenLedger installer

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[CustomMessages]
english.OpenReport=Open ScreenLedger report
turkish.OpenReport=ScreenLedger raporunu aç
english.StartWithWindows=Start tracking when I sign in to Windows
turkish.StartWithWindows=Windows oturumu açıldığında takibi başlat
english.OldVersionRunning=An older copy of ScreenLedger is still running. Stop it safely before installing this copy. Your records have not been changed.
turkish.OldVersionRunning=Eski ScreenLedger kopyası hâlâ çalışıyor. Bu kopyayı kurmadan önce onu güvenle durdurun. Kayıtlarınız değiştirilmedi.
english.StopFailed=The running ScreenLedger copy could not be stopped safely. Installation was cancelled to protect your records.
turkish.StopFailed=Çalışan ScreenLedger kopyası güvenle durdurulamadı. Kayıtlarınızı korumak için kurulum iptal edildi.

[Tasks]
Name: "autostart"; Description: "{cm:StartWithWindows}"

[Files]
Source: "..\dist\ScreenLedger\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\sekme-eklentisi\manifest.json"; DestDir: "{localappdata}\ScreenLedger\sekme-eklentisi"; Flags: ignoreversion uninsneveruninstall
Source: "..\sekme-eklentisi\worker.js"; DestDir: "{localappdata}\ScreenLedger\sekme-eklentisi"; Flags: ignoreversion uninsneveruninstall
Source: "..\sekme-eklentisi\bilgi.html"; DestDir: "{localappdata}\ScreenLedger\sekme-eklentisi"; Flags: ignoreversion uninsneveruninstall

[Icons]
Name: "{group}\ScreenLedger"; Filename: "{app}\ScreenLedger.exe"; Parameters: "--open-report"; Comment: "Open the local ScreenLedger report"
Name: "{group}\Uninstall ScreenLedger"; Filename: "{uninstallexe}"
Name: "{userstartup}\ScreenLedger"; Filename: "{app}\ScreenLedger.exe"; Tasks: autostart; Comment: "Start ScreenLedger tracking after sign-in"

[Run]
Filename: "{app}\ScreenLedger.exe"; Parameters: "--open-report"; Description: "{cm:OpenReport}"; Flags: nowait postinstall skipifsilent

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  OldExe: String;
  ResultCode: Integer;
begin
  Result := '';
  OldExe := ExpandConstant('{app}\ScreenLedger.exe');
  if FileExists(OldExe) then
  begin
    if not Exec(OldExe, '--stop', ExpandConstant('{app}'), SW_HIDE,
      ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
    begin
      Result := CustomMessage('StopFailed');
      exit;
    end;
  end;
  if CheckForMutexes('Global\EkranTakip_TekKopya') then
    Result := CustomMessage('OldVersionRunning');
end;

function InitializeUninstall(): Boolean;
var
  AppExe: String;
  ResultCode: Integer;
begin
  Result := True;
  AppExe := ExpandConstant('{app}\ScreenLedger.exe');
  if FileExists(AppExe) then
  begin
    if not Exec(AppExe, '--stop', ExpandConstant('{app}'), SW_HIDE,
      ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
    begin
      MsgBox(CustomMessage('StopFailed'), mbError, MB_OK);
      Result := False;
    end;
  end;
end;
