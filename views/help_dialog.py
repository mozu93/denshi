from PyQt6.QtWidgets import QMessageBox
import sys
import os

# バージョン情報を取得
def get_version_info():
    try:
        # VERSION.pyからバージョン情報をインポート
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from VERSION import __version__, __build_date__
        return __version__, __build_date__
    except ImportError:
        return "v2.6.0", "2026-05-24"

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
        "- ファイルの追加: メニュー「ファイル」→「フォルダを開く」でフォルダ内を一括追加、\n"
        "  「ファイルを開く」で個別に選択、またはウィンドウにドラッグ＆ドロップ。\n"
        "- 自動入力: PDFを選択すると発行日・取引先名・金額の自動抽出を試みます。\n"
        "- OCR手動読み取り: 入力項目をクリックして選択後、PDFプレビュー上でドラッグすると\n"
        "  その範囲をOCRで読み取ります。※ 初回のみ約12秒かかります。\n"
        "- 学習機能: OCRで読み取った範囲は取引先ごとに記憶され、次回から自動で適用されます。\n"
        "- 保存: 「保存して次へ」ボタンでファイルを保存し、次の処理へ進みます。\n\n"
        "【ファイル検索モード】\n"
        "登録済みのファイルを検索・管理します。\n"
        "- 検索: 年度・取引区分・書類種別・取引先名などの条件でファイルを検索できます。\n"
        "  Enterキーでも検索を実行できます。\n"
        "- 編集・削除: 検索結果からファイルの情報を編集したり、削除したりできます。\n\n"
        "【設定】\n"
        "保存先フォルダや書類分類などをカスタマイズできます。\n\n"
        "【インデックス再構築】\n"
        "ファイルシステムとメタデータの整合性を再構築します。\n\n"
        "【文字サイズ変更】\n"
        "メニュー「表示」→「文字を大きく／小さく／リセット」で変更できます。"
    )
    QMessageBox.information(parent, "電子帳簿保存システム ヘルプ", help_message)
