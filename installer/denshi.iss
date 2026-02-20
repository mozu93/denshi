; Inno Setup スクリプト - 電子帳簿保存システム
; このファイルはbuild.pyから自動的に使用されます

#define MyAppName "電子帳簿保存システム"
#define MyAppNameEn "DenshiChobohozoSystem"
#define MyAppPublisher "Your Organization"
#define MyAppURL "https://github.com/your-username/denshi"
#define MyAppExeName "DenshiChobohozoSystem.exe"

; バージョン情報（build.pyで自動的に置き換えられる）
#define MyAppVersion "v2.0.0"

[Setup]
; アプリケーション情報
AppId={{B3E8F2A1-5C9D-4E7B-9A3C-1D6F8E2A4C5B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppNameEn}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
OutputDir=Output
OutputBaseFilename={#MyAppNameEn}_{#MyAppVersion}_setup
SetupIconFile=icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin

; 言語設定
[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

; タスク設定（ユーザーが選択可能なオプション）
[Tasks]
Name: "desktopicon"; Description: "デスクトップアイコンを作成する(&D)"; GroupDescription: "追加のアイコン:"
Name: "quicklaunchicon"; Description: "クイック起動アイコンを作成する(&Q)"; GroupDescription: "追加のアイコン:"; Flags: unchecked

; ファイルのインストール
[Files]
; アプリケーション本体（PyInstallerでビルドされたディレクトリ全体）
Source: "..\dist\{#MyAppNameEn}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; 初期設定ファイル（ユーザーデータディレクトリに配置）
Source: "..\config.ini"; DestDir: "{userappdata}\{#MyAppNameEn}"; Flags: onlyifdoesntexist uninsneveruninstall

; Tesseract OCRインストーラー（同梱する場合）
Source: "tesseract-installer.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

; アイコンの作成
[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

; 実行処理
[Run]
; Tesseract OCRの自動インストール（オプション）
Filename: "{tmp}\tesseract-installer.exe"; Parameters: "/VERYSILENT /NORESTART /DIR=""{autopf}\Tesseract-OCR"""; StatusMsg: "Tesseract OCRをインストールしています..."; Flags: waituntilterminated

; インストール完了後にアプリケーションを起動（ユーザーが選択可能）
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; アンインストール時の処理
[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\{#MyAppNameEn}"

; レジストリ設定（オプション）
[Registry]
; ファイル関連付けなどが必要な場合はここに追加

; カスタムメッセージ
[Messages]
japanese.WelcomeLabel1=ようこそ、[name] セットアップウィザードへ
japanese.WelcomeLabel2=このプログラムは、電子帳簿保存法に対応した電子取引データの管理を支援します。%n%n続行する前に、他のすべてのアプリケーションを終了してください。

[Code]
// インストール前のチェック
function InitializeSetup(): Boolean;
begin
  Result := True;

  // .NET Frameworkやその他の依存関係のチェックをここに追加可能

end;

// アンインストール時の確認
function InitializeUninstall(): Boolean;
var
  Response: Integer;
begin
  Response := MsgBox('電子帳簿保存システムをアンインストールしますか？' + #13#10 +
                     'ユーザーデータ（設定ファイルと登録済みファイル）は保持されます。',
                     mbConfirmation, MB_YESNO);
  Result := Response = IDYES;
end;

// インストール完了後の処理
procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigDir: String;
  ConfigFile: String;
begin
  if CurStep = ssPostInstall then
  begin
    // ユーザーデータディレクトリの作成
    ConfigDir := ExpandConstant('{userappdata}\{#MyAppNameEn}');
    if not DirExists(ConfigDir) then
    begin
      CreateDir(ConfigDir);
    end;

    // 設定ファイルが存在しない場合は初期ファイルをコピー
    ConfigFile := ConfigDir + '\config.ini';
    if not FileExists(ConfigFile) then
    begin
      FileCopy(ExpandConstant('{app}\config.ini'), ConfigFile, False);
    end;
  end;
end;
