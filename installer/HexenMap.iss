; Compile with /DAppVersion=... /DPackageDir=... /DLauncherFile=... /DOutputDir=...
#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef TestSuffix
  #define TestSuffix ""
#endif

[Setup]
AppId=HexenMap{#TestSuffix}
AppName=Hexen Map{#TestSuffix}
AppVersion={#AppVersion}
AppPublisher=Hexen Map
AppPublisherURL=https://github.com/victoregit/HexenMap-Releases
DefaultDirName={localappdata}\Programs\Hexen Map{#TestSuffix}
DefaultGroupName=Hexen Map{#TestSuffix}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputDir}
OutputBaseFilename=HexenMap-{#AppVersion}-Setup-x64{#TestSuffix}
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\data\assets\brand\app.ico
UninstallDisplayIcon={app}\HexenMap.exe
#if TestSuffix == ""
AppMutex=Local\HexenMap.LiveOverlay,Local\GenshinGemWish.LiveOverlay
#else
AppMutex=HexenMapInstallerSmokeOverlay
#endif
SetupMutex=HexenMapInstaller{#TestSuffix}
CloseApplications=yes
CloseApplicationsFilter=HexenMapLauncher.exe
RestartApplications=no
DisableProgramGroupPage=yes
UsePreviousAppDir=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; Flags: unchecked

[Files]
Source: "{#PackageDir}\HexenMap.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PackageDir}\HexenMapBridge.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#LauncherFile}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PackageDir}\BUILD.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "LEIA-ME.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PackageDir}\creditos\*"; DestDir: "{app}\creditos"; Flags: ignoreversion recursesubdirs createallsubdirs
; NEVER overwrite or uninstall a downloader's saved data, including settings/progress.
Source: "{#PackageDir}\userData\*"; DestDir: "{app}\userData"; Flags: onlyifdoesntexist uninsneveruninstall recursesubdirs createallsubdirs
Source: "Restore-Previous.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "Restaurar versao anterior.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "Start-HexenMap.cmd"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\Hexen Map{#TestSuffix}"; Filename: "{app}\HexenMapLauncher.exe"; WorkingDir: "{app}"; IconFilename: "{app}\HexenMap.exe"; AppUserModelID: "HexenMap.Launcher{#TestSuffix}"
Name: "{userdesktop}\Hexen Map{#TestSuffix}"; Filename: "{app}\HexenMapLauncher.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{cmd}"; Parameters: "/D /C .\Start-HexenMap.cmd"; WorkingDir: "{app}"; Description: "Abrir Hexen Map"; Flags: nowait postinstall skipifsilent runhidden; Check: ShouldLaunch
Filename: "{cmd}"; Parameters: "/D /C .\Start-HexenMap.cmd"; WorkingDir: "{app}"; Flags: nowait runascurrentuser runhidden; Check: IsUpdate

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var Owner: AnsiString;
begin
  Result := '';
  if LoadStringFromFile(ExpandConstant('{app}\installed-user.txt'), Owner) then
    if CompareText(Trim(String(Owner)), GetUserNameString) <> 0 then
      Result := 'Atualize usando a conta que instalou o Hexen Map. Os dados existentes foram preservados.';
end;

function ShouldLaunch: Boolean;
begin
  Result := ExpandConstant('{param:NORUN|0}') <> '1';
end;

function IsUpdate: Boolean;
begin
  Result := (ExpandConstant('{param:UPDATE|0}') = '1') and ShouldLaunch;
end;

procedure BackupFile(Name: String);
var Source, Target: String;
begin
  Source := ExpandConstant('{app}\') + Name;
  Target := ExpandConstant('{app}\.previous\') + Name;
  if FileExists(Source) and not FileCopy(Source, Target, False) then
    RaiseException('Não foi possível salvar a versão anterior. Feche o Hexen Map e tente novamente.');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var PreviousVersion: AnsiString;
begin
  if CurStep = ssInstall then begin
    LoadStringFromFile(ExpandConstant('{app}\installed-version.txt'), PreviousVersion);
    if (Trim(String(PreviousVersion)) <> '{#AppVersion}') and
       FileExists(ExpandConstant('{app}\HexenMap.exe')) then begin
      if not ForceDirectories(ExpandConstant('{app}\.previous')) then
        RaiseException('Não foi possível preparar o backup da versão anterior.');
      BackupFile('HexenMap.exe');
      BackupFile('HexenMapLauncher.exe');
      BackupFile('HexenMapBridge.exe');
      BackupFile('BUILD.json');
      BackupFile('installed-version.txt');
    end;
  end;
  if CurStep = ssPostInstall then begin
    SaveStringToFile(ExpandConstant('{app}\installed-version.txt'), '{#AppVersion}', False);
    if not FileExists(ExpandConstant('{app}\installed-user.txt')) then
      SaveStringToFile(ExpandConstant('{app}\installed-user.txt'), GetUserNameString, False);
    if not FileExists(ExpandConstant('{app}\state-dir.txt')) then
      SaveStringToFile(ExpandConstant('{app}\state-dir.txt'), UTF8Encode(ExpandConstant('{localappdata}\HexenMap\state')), False);
  end;
end;
