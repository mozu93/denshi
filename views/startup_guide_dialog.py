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
        "ファイルを登録するには:\n" 
        "  - メニューから「ファイル」→「PDFを開く」を選択\n" 
        "  - または、PDFファイルをこのウィンドウにドラッグ＆ドロップ\n\n" 
        "登録済みのファイルを検索する場合は、上部の「ファイル検索モード」タブから検索してください。"
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
