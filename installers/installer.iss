; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "SasView"
#define MyAppVersion "6.0.0"
#define MyAppPublisher "(c) 2009 - 2021, UTK, UMD, NIST, ORNL, ISIS, ESS, ILL, ANSTO, TU Delft and DLS"
#define MyAppURL "http://www.sasview.org"
#define MyAppExeName "sasview.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{3498B749-1A91-4B17-B354-458D838C1C71}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName}-{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName=c:\{#MyAppName}-{#MyAppVersion}
UsePreviousAppDir=no
UninstallDisplayName={#MyAppName}-{#MyAppVersion}
DirExistsWarning=yes
DefaultGroupName={#MyAppName}-{#MyAppVersion}
DisableProgramGroupPage=yes
DisableDirPage=no
UsedUserAreasWarning=no
LicenseFile=license.txt
ArchitecturesInstallIn64BitMode=x64
OutputBaseFilename=setupSasView
SetupIconFile=dist\sasview\images\ball.ico


; Uncomment the following line to run in non administrative install mode (install for current user only.)
;PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Code]
{ If there is a command-line parameter "skiplicense=true", don't display license page }
begin
    // delete all files in the installation directory to prevent install conflicts
    DelTree('{app}', True, True, True);
end;
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False
  if PageId = wpLicense then
    if ExpandConstant('{param:skiplicense|false}') = 'true' then
      Result := True;
end;

[Files]
Source: "dist\sasview\sasview.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\sasview\plugin_models\*"; DestDir: "{%USERPROFILE}\.sasview\plugin_models"
Source: "dist\sasview\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon
Name: "{group}\SasView";	Filename: "{app}\SasView.exe";	WorkingDir: "{app}"; IconFilename: "{app}\images\ball.ico" 
Name: "{group}\{cm:UninstallProgram, SasView}";	 Filename: "{uninstallexe}" 

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Delete directories and files that are dynamically created by the application (i.e. at runtime).
Type: filesandordirs; Name: "{app}\.matplotlib"
Type: files; Name: "{app}\*.*"
; The following is a workaround for the case where the application is installed and uninstalled but the
;{app} directory is not deleted because it has user files.  Then the application is installed into the
; existing directory, user files are deleted, and the application is un-installed again.  Without the
; directive below, {app} will not be deleted because Inno Setup did not create it during the previous
; installation.
Type: dirifempty; Name: "{app}"

[Registry]
Root: HKCR;	Subkey: ".xml\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCR;	Subkey: ".ses\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCR;	Subkey: ".h5\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCR;	Subkey: ".nxs\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCR;	Subkey: ".txt\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCR;	Subkey: ".dat\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCR;	Subkey: ".abs\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCR;	Subkey: ".cor\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCR;	Subkey: ".sans\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCR;	Subkey: ".pdh\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCR; Subkey: "applications\SasView.exe\shell\open\command";	ValueType: string; ValueName: "";	ValueData: """{app}\SasView.exe""  ""%1"""; 	 Flags: uninsdeletevalue noerror
Root: HKCU;	Subkey: "Software\Classes\.xml\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCU;	Subkey: "Software\Classes\.ses\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCU;	Subkey: "Software\Classes\.h5\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCU;	Subkey: "Software\Classes\.nxs\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCU;	Subkey: "Software\Classes\.txt\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCU;	Subkey: "Software\Classes\.dat\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCU;	Subkey: "Software\Classes\.abs\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCU;	Subkey: "Software\Classes\.cor\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCU;	Subkey: "Software\Classes\.sans\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCU;	Subkey: "Software\Classes\.pdh\OpenWithList\SasView.exe";	 Flags: uninsdeletekey noerror
Root: HKCU; Subkey: "Software\Classes\applications\SasView.exe\shell\open\command";	ValueType: string; ValueName: "";	ValueData: """{app}\SasView.exe""  ""%1"""; 	 Flags: uninsdeletevalue noerror
Root: HKCR;	Subkey: ".svs";	ValueType: string;	ValueName: "";	ValueData: "{app}\SasView.exe";	 Flags: uninsdeletevalue  noerror
Root: HKCR;	Subkey: ".fitv";	ValueType: string;	ValueName: "";	ValueData: "{app}\SasView.exe";	 Flags: uninsdeletevalue  noerror
Root: HKCR;	Subkey: ".inv";	ValueType: string;	ValueName: "";	ValueData: "{app}\SasView.exe";	 Flags: uninsdeletevalue  noerror
Root: HKCR;	Subkey: ".prv";	ValueType: string;	ValueName: "";	ValueData: "{app}\SasView.exe";	 Flags: uninsdeletevalue  noerror
Root: HKCR;	Subkey: ".crf";	ValueType: string;	ValueName: "";	ValueData: "{app}\SasView.exe";	 Flags: uninsdeletevalue  noerror
Root: HKCR; Subkey: "{app}\SasView.exe";	ValueType: string; ValueName: "";	ValueData: "{app}\SasView File";	 Flags: uninsdeletekey  noerror 	
Root: HKCR; Subkey: "{app}\SasView.exe\shell\open\command";	ValueType: string; ValueName: "";	ValueData: """{app}\SasView.exe""  ""%1""";	 Flags: uninsdeletevalue noerror 	
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment";	ValueType: expandsz; ValueName: "SASVIEWPATH";	ValueData: "{app}";	 Flags: uninsdeletevalue noerror


