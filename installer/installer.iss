[Setup]
AppName=Sistema de Comprobantes
AppVersion=1.0.0
DefaultDirName={localappdata}\SistemaComprobantes
DefaultGroupName=Sistema de Comprobantes
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=SistemaComprobantes_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
WizardImageFile={#SourcePath}\resources\installer_sidebar_large.bmp
WizardSmallImageFile={#SourcePath}\resources\installer_header_small.bmp
ArchitecturesAllowed=arm64 x64
ArchitecturesInstallIn64BitMode=arm64

[Files]
Source: "..\dist\Launcher\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Icons]
Name: "{group}\Sistema de Comprobantes"; Filename: "{app}\Launcher.exe"
Name: "{userdesktop}\Sistema de Comprobantes"; Filename: "{app}\Launcher.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Launcher.exe"; Description: "Abrir Sistema de Comprobantes"; Flags: nowait postinstall skipifsilent
