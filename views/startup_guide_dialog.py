from PyQt6.QtWidgets import QMessageBox, QCheckBox

def show_startup_guide(config_manager, parent=None):
    """
    Checks if the startup guide should be shown and displays it.
    """
    show_guide = config_manager.get('Settings', 'show_startup_guide', fallback='True').lower() == 'true'
    if not show_guide:
        return

    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle("ご利用ガイド")
    msg_box.setText(
        "【ファイルを登録するには】\n"
        "  - メニュー「ファイル」→「フォルダを開く」でフォルダ内の全PDFを一括追加\n"
        "  - メニュー「ファイル」→「ファイルを開く」でPDFを個別に選択\n"
        "  - または、PDFファイルをこのウィンドウにドラッグ＆ドロップ\n\n"
        "【OCRで読み取るには】\n"
        "  入力したい項目をクリックして選択後、PDFプレビュー上でドラッグしてください。\n"
        "  ※ 初回のみ約12秒かかります。2回目以降は快適に読み取れます。\n\n"
        "【登録済みのファイルを検索するには】\n"
        "  上部の「ファイル検索モード」タブから検索してください。"
    )
    msg_box.setIcon(QMessageBox.Icon.Information)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

    dont_show_again_checkbox = QCheckBox("今後、このメッセージを表示しない", msg_box)
    msg_box.setCheckBox(dont_show_again_checkbox)

    msg_box.exec()

    if dont_show_again_checkbox.isChecked():
        try:
            config_manager.set('Settings', 'show_startup_guide', 'False')
        except Exception:
            pass
