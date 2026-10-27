; Inno Setup-script voor de installer van Uitslagen. Bouwen via bouw-installer.bat.

#define AppName "Uitslagen"
#define AppVersion "1.0"

[Setup]
AppId={{6F1C2B7E-4A3D-4E8B-9C21-5D7A8E3F1B40}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Henk Binnendijk
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=yes
; Installeren voor de huidige gebruiker, zodat er geen beheerdersrechten nodig zijn.
PrivilegesRequired=lowest
OutputDir=installer
OutputBaseFilename=Uitslagen-installatie
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=uitslagen.ico
UninstallDisplayIcon={app}\Uitslagen.exe

[Languages]
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\Uitslagen\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\Uitslagen.exe"
Name: "{group}\{#AppName} verwijderen"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\Uitslagen.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Uitslagen.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
