; Script generated for Rewards Bot Pro

#define MyAppName "Rewards Bot Pro"
#define MyAppVersion "1.0"
#define MyAppPublisher "Sourabh Sahu"
#define MyAppExeName "RewardsBotPro.exe"

[Setup]
AppId={{A3C25D8B-1E4F-4C8A-9B2D-7F1E5G6H7I8J}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
WizardStyle=modern
OutputDir=.
OutputBaseFilename=RewardsBotPro_Setup_v1.0
SetupIconFile=C:\Users\soura\OneDrive\Desktop\EdgeRewardTool\logo.ico
Compression=lzma
SolidCompression=yes
; CORRECTED LINE BELOW:
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Ensure these paths point to your actual dist folder
Source: "C:\Users\soura\OneDrive\Desktop\EdgeRewardTool\dist\RewardsBotPro\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\soura\OneDrive\Desktop\EdgeRewardTool\dist\RewardsBotPro\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\logo.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\logo.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent