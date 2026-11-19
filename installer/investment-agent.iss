#define MyAppName "Investment Agent"
#define MyAppVersion "0.30.1"
#define MyAppExeName "InvestmentAgent.exe"

[Setup]
AppId={{B7D2F5E1-8C4A-4D3B-9E12-6A5F019C8E42}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
DefaultDirName={localappdata}\InvestmentAgent
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=no
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=InvestmentAgent-Setup-win64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=120,120
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\app_icon_v031.ico
ChangesAssociations=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\InvestmentAgent\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\assets\icon.ico"; DestDir: "{app}"; DestName: "icon.ico"; Flags: ignoreversion
Source: "..\assets\icon.ico"; DestDir: "{app}"; DestName: "app_icon_v031.ico"; Flags: ignoreversion
Source: "..\assets\icon.png"; DestDir: "{app}"; DestName: "icon.png"; Flags: ignoreversion
Source: "..\assets\icon.ico"; DestDir: "{app}\assets"; DestName: "icon.ico"; Flags: ignoreversion
Source: "..\assets\icon.png"; DestDir: "{app}\assets"; DestName: "icon.png"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon_v031.ico"; AppUserModelID: "InvestmentAgent.MacroWorkbench.0.31"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon_v031.ico"; AppUserModelID: "InvestmentAgent.MacroWorkbench.0.31"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
