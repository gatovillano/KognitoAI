; Script de Inno Setup para Kognito Sync
; Genera un instalador ejecutable independiente (Setup.exe) para Windows

#define MyAppName "Kognito Sync"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Kognito AI"
#define MyAppURL "https://kognito.ai"
#define MyAppExeName "KognitoSync.exe"

[Setup]
AppId={{D37E61A8-142B-4A19-9B21-0B6B18D3F95C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
; Permite instalar sin permisos de administrador si el usuario lo desea
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=dist-installer
OutputBaseFilename=KognitoSync-Setup
SetupIconFile=icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Iniciar Kognito Sync automáticamente al encender el equipo"; GroupDescription: "Opciones de inicio:"

[Files]
; Todos los archivos generados por PyInstaller en dist/KognitoSync/
Source: "dist\KognitoSync\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\icon.ico"

[Registry]
; Iniciar automáticamente con Windows si la casilla está marcada
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "KognitoSync"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
