from PyQt6.QtWidgets import QMessageBox
import sys
import os

# バージョン情報を取得
def get_version_info():
    try:
        # main.pyからバージョン情報をインポート
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from main import APP_VERSION, APP_BUILD_DATE
        return APP_VERSION, APP_BUILD_DATE
    except ImportError:
        return "v1.2.0", "2025-09-30"

def show_help_dialog(parent=None):
    """
    Displays the help dialog for the application.
    """
    version, build_date = get_version_info()
    help_message = (
        f"電子帳簿保存システム ヘルプ\n"
        f"バージョン: {version}\n"
        f"ビルド日: {build_date}\n\n"
        "このアプリケーションは、電子帳簿保存法に対応した電子取引データの管理を支援します。\n\n"
        "【ファイル登録モード】\n"
        "PDFファイルを登録し、ファイル名を自動生成します。\n"
        "- ファイルの追加: メニューから「ファイル」→「PDFを開く」を選択するか、PDFファイルをウィンドウにドラッグ＆ドロップしてください。\n"
        "- データ入力: PDFプレビューを見ながら、発行日、取引先名、金額などを入力します。OCR機能で自動読み取りも可能です。\n"
        "- 保存: 「保存して次へ」ボタンでファイルを保存し、次の処理へ進みます。\n\n"
        "【ファイル検索モード】\n"
        "登録済みのファイルを検索・管理します。\n"
        "- 検索: 年度や取引先名などの条件でファイルを検索できます。Enterキーでも検索を実行できます。\n"
        "- 編集・削除: 検索結果からファイルの情報を編集したり、削除したりできます。\n\n"
        "【設定】\n"
        "保存先フォルダや書類分類などをカスタマイズできます。\n\n"
        "【インデックス再構築】\n"
        "ファイルシステムとメタデータの整合性を再構築します。"
    )
    QMessageBox.information(parent, "電子帳簿保存システム ヘルプ", help_message)