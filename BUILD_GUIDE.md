# ビルド手順書

電子帳簿保存システムのビルドとリリース手順を説明します。

## 前提条件

### 必須ソフトウェア

1. **Python 3.9以降**
   - インストール: https://www.python.org/downloads/

2. **PyInstaller**
   - インストール: `pip install -r requirements_build.txt`

3. **Inno Setup 6.x** (インストーラー作成に必要)
   - ダウンロード: https://jrsoftware.org/isdl.php
   - インストール先: `C:\Program Files (x86)\Inno Setup 6\`

### 推奨ソフトウェア

1. **Git** (バージョン管理)
   - インストール: https://git-scm.com/downloads

## リソースファイルの準備

ビルドを実行する前に、以下のリソースファイルを準備してください。

### 1. アプリケーションアイコン

**必須**: `installer/icon.ico`

アイコンファイルを作成して配置します。

```bash
# オンラインツールで作成する場合
1. PNG画像を256x256pxで準備
2. https://convertio.co/ja/png-ico/ などでICO形式に変換
3. installer/icon.ico として保存
```

### 2. Tesseract OCRインストーラー（オプション）

**推奨**: `installer/tesseract-installer.exe`

Tesseract OCRをインストーラーに同梱する場合は、以下の手順で準備します。

```bash
1. https://github.com/UB-Mannheim/tesseract/wiki にアクセス
2. 最新版の64bit版をダウンロード
   例: tesseract-ocr-w64-setup-5.3.3.20231005.exe
3. ダウンロードしたファイルを installer/tesseract-installer.exe にリネームして配置
```

**注意**: Tesseractインストーラーはファイルサイズが大きいため、Gitリポジトリには含めないでください。

## ビルド手順

### ステップ1: 依存関係のインストール

```bash
# プロジェクトルートディレクトリで実行
pip install -r requirements_build.txt
```

### ステップ2: バージョン情報の更新

`VERSION.py`を編集して、バージョン番号とビルド日を更新します。

```python
# VERSION.py
__version__ = "v2.1.0"  # 新しいバージョン番号
__build_date__ = "2026-02-20"  # 現在の日付
```

### ステップ3: ビルドの実行

#### オプション1: exeのみビルド（インストーラーなし）

```bash
python build.py --skip-installer
```

- 出力先: `dist/DenshiChobohozoSystem/`
- 実行ファイル: `dist/DenshiChobohozoSystem/DenshiChobohozoSystem.exe`

#### オプション2: exeとインストーラーをビルド

```bash
python build.py
```

- exe出力先: `dist/DenshiChobohozoSystem/`
- インストーラー出力先: `installer/Output/DenshiChobohozoSystem_v2.1.0_setup.exe`

### ステップ4: ビルド結果の確認

```bash
# exeの動作確認
dist\DenshiChobohozoSystem\DenshiChobohozoSystem.exe

# ファイルサイズの確認
dir dist\DenshiChobohozoSystem\DenshiChobohozoSystem.exe
dir installer\Output\*.exe
```

## リリース手順

### ステップ1: Gitタグの作成

```bash
# バージョンタグを作成
git tag v2.1.0
git push origin v2.1.0
```

### ステップ2: GitHub Releaseの作成

1. GitHubリポジトリページにアクセス
2. 「Releases」→「Draft a new release」をクリック
3. タグを選択: `v2.1.0`
4. リリースタイトル: `v2.1.0`
5. リリースノートを記載:

```markdown
## 新機能
- 機能Aを追加
- 機能Bを改善

## バグ修正
- バグXを修正

## インストール方法
1. DenshiChobohozoSystem_v2.1.0_setup.exeをダウンロード
2. インストーラーを実行
3. 画面の指示に従ってインストール

## システム要件
- Windows 10/11 (64bit)
- .NET Framework 4.7.2以降
```

6. インストーラーファイルをアップロード:
   - `installer/Output/DenshiChobohozoSystem_v2.1.0_setup.exe`

7. 「Publish release」をクリック

### ステップ3: リリース確認

1. GitHub Releasesページでリリースが公開されていることを確認
2. ダウンロードリンクが機能することを確認
3. アプリケーションの自動アップデートチェックが動作することを確認

## トラブルシューティング

### PyInstallerのエラー

**エラー**: `ModuleNotFoundError: No module named 'xxx'`

**解決方法**:
```bash
# 不足しているモジュールをインストール
pip install xxx

# または、denshi.specのhiddenimportsに追加
hiddenimports = [
    'xxx',
    # 既存のモジュール...
]
```

### Inno Setupが見つからない

**エラー**: `Inno Setup Compilerが見つかりません`

**解決方法**:
1. Inno Setup 6.xをインストール
2. インストール先が `C:\Program Files (x86)\Inno Setup 6\` であることを確認
3. または、`build.py`の`iscc_paths`リストにインストール先を追加

### アイコンが表示されない

**エラー**: `installer/icon.ico が見つかりません`

**解決方法**:
1. アイコンファイルを作成して `installer/icon.ico` に配置
2. または、アイコンなしでビルドを続行（警告は出るが動作する）

### exeファイルが大きい

**原因**: 不要なライブラリが含まれている

**解決方法**:
1. `denshi.spec`の`excludes`リストに不要なモジュールを追加
```python
excludes=[
    'matplotlib',
    'numpy',
    'scipy',
    'tkinter',
    'unittest',
    'test',
    # 追加の不要モジュール...
]
```

2. UPX圧縮を有効化（すでに有効）
```python
upx=True,
```

### ウイルス対策ソフトの誤検知

**問題**: ビルドしたexeがウイルスとして検出される

**解決方法**:
1. 一時的にウイルス対策ソフトを無効化
2. exeファイルを除外リストに追加
3. 将来的にコード署名証明書の取得を検討

## ビルド設定のカスタマイズ

### バージョン情報のカスタマイズ

`VERSION.py`を編集:

```python
__version__ = "v2.1.0"
__build_date__ = "2026-02-20"
GITHUB_REPO_OWNER = "your-username"  # GitHubユーザー名
GITHUB_REPO_NAME = "denshi"
APP_PUBLISHER = "Your Organization"  # 組織名
```

### インストーラーのカスタマイズ

`installer/denshi.iss`を編集:

- アプリケーション名
- 発行者情報
- インストール先
- デスクトップアイコンのデフォルト設定
- Tesseract OCRの自動インストール有効化

### PyInstallerのカスタマイズ

`denshi.spec`を編集:

- データファイルの追加/除外
- 隠れたインポートの追加
- 除外するモジュールの追加
- 圧縮設定の変更

## 参考リンク

- [PyInstaller公式ドキュメント](https://pyinstaller.org/en/stable/)
- [Inno Setup公式サイト](https://jrsoftware.org/isinfo.php)
- [GitHub Releases公式ドキュメント](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [packaging (Pythonバージョン比較)](https://packaging.pypa.io/)

## サポート

ビルドに関する問題が発生した場合は、以下の情報を添えてIssueを作成してください：

- Pythonバージョン: `python --version`
- PyInstallerバージョン: `pyinstaller --version`
- エラーメッセージの全文
- ビルドログファイル: `build/build.log`
