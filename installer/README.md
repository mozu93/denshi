# インストーラー用リソース

このディレクトリには、インストーラー作成に必要なリソースファイルを配置します。

## 必要なファイル

### 1. icon.ico（必須）
アプリケーションアイコン。
- サイズ: 256x256推奨（複数サイズ含む.ico形式）
- 形式: .ico
- 配置先: `installer/icon.ico`

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

## ビルド時の動作

- `build.py`実行時に、これらのファイルの存在をチェックします
- icon.icoがない場合は警告を表示しますが、ビルドは続行します

## 注意事項

- アイコンファイルは容量が大きい場合があるため、Gitリポジトリには含めないことを推奨します
- `.gitignore`に以下を追加してください:
  ```
  installer/*.exe
  installer/*.ico
  ```
