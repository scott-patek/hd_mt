; Inno Setup installer script for Half Deaf Mastering Tool

#define MyAppName "Half Deaf Mastering Tool"
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#ifndef OutputBaseFilename
  #define OutputBaseFilename "half-deaf-mastering-tool-setup"
#endif

[Setup]
AppId={{3A60531D-FF2D-48AB-B684-0F4A765B67AA}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Half Deaf
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename={#OutputBaseFilename}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\..\dist\Half Deaf Mastering Tool\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\Half Deaf Mastering Tool.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\Half Deaf Mastering Tool.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Half Deaf Mastering Tool.exe"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
