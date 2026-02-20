# インストーラー用リソース

このディレクトリには、インストーラー作成に必要なリソースファイルを配置します。

## 必要なファイル

### 1. icon.ico（必須）
アプリケーションアイコン。
- サイズ: 256x256推奨（複数サイズ含む.ico形式）
- 形式: .ico
- 配置先: `installer/icon.ico`

### 2. tesseract-installer.exe（推奨）
Tesseract OCRのインストーラー。
- ダウンロード元: https://github.com/UB-Mannheim/tesseract/wiki
- バージョン: 5.x系推奨
- 配置先: `installer/tesseract-installer.exe`
- 注意: ファイルサイズが大きいため、.gitignoreに追加推奨

## アイコン作成方法

### オンラインツール使用
1. PNG画像を準備（256x256推奨）
2. https://convertio.co/ja/png-ico/ などでICO形式に変換
3. `installer/icon.ico`として保存

### ImageMagick使用
```bash
# PNGからICO作成
magick convert icon.png -define icon:auto-resize=256,128,64,48,32,16 installer/icon.ico
```

## Tesseract OCRインストーラー取得

1. https://github.com/UB-Mannheim/tesseract/wiki にアクセス
2. 最新版の64bit版をダウンロード（例: tesseract-ocr-w64-setup-5.3.3.20231005.exe）
3. `installer/tesseract-installer.exe`にリネームして配置

## ビルド時の動作

- `build.py`実行時に、これらのファイルの存在をチェックします
- icon.icoがない場合は警告を表示しますが、ビルドは続行します
- tesseract-installer.exeがない場合も警告しますが、インストーラー作成時に問題が発生します

## 注意事項

- これらのファイルは容量が大きいため、Gitリポジトリには含めないことを推奨します
- `.gitignore`に以下を追加してください:
  ```
  installer/*.exe
  installer/*.ico
  ```
