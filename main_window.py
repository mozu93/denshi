from PyQt6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget, QStatusBar, QMenuBar, QMessageBox
from views.file_registration_tab import FileRegistrationTab
from views.file_search_tab import FileSearchTab
from utils.config_manager import ConfigManager
from models.metadata_manager import MetadataManager
from PyQt6.QtCore import QTimer # Add this line

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True) # Accept drops on the main window
        self.setWindowTitle("電子帳簿保存システム")
        self.setGeometry(100, 100, 1200, 800)

        # Central Widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        # Layout
        layout = QVBoxLayout(central_widget)

        # Tab Widget
        self.tabs = QTabWidget()
        self.config_manager = ConfigManager()
        self.metadata_manager = MetadataManager(self.config_manager.get('Paths', 'root_save_directory'))
        self.registration_tab = FileRegistrationTab(config_manager=self.config_manager, metadata_manager=self.metadata_manager)
        self.search_tab = FileSearchTab(metadata_manager=self.metadata_manager)
        self.tabs.addTab(self.registration_tab, "ファイル登録モード")
        self.tabs.addTab(self.search_tab, "ファイル検索モード")
        layout.addWidget(self.tabs)

        # Menu Bar
        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)
        self._create_menus()

        # Status Bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("準備完了")
        self._show_startup_guide() # Show guide after everything is set up

    def _create_menus(self):
        # File Menu
        file_menu = self.menu_bar.addMenu("ファイル")
        
        open_action = file_menu.addAction("PDFを開く")
        open_action.triggered.connect(self.registration_tab.open_file_dialog)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("終了")
        exit_action.triggered.connect(self.close)

        # Tool Menu
        tool_menu = self.menu_bar.addMenu("ツール")

        reindex_action = tool_menu.addAction("インデックス再構築")
        reindex_action.triggered.connect(self.rebuild_index)

        settings_action = tool_menu.addAction("設定")
        settings_action.triggered.connect(self.open_settings)

        # Help Menu
        help_menu = self.menu_bar.addMenu("ヘルプ")
        view_help_action = help_menu.addAction("ヘルプを表示")
        view_help_action.triggered.connect(self._show_help_dialog)

    def _show_startup_guide(self):
        # Check if the guide should be shown based on config
        show_guide = self.config_manager.get('Settings', 'show_startup_guide', fallback='True').lower() == 'true'
        if not show_guide:
            return

        # Use QTimer.singleShot to display the message after the main window is shown
        QTimer.singleShot(100, self._display_guide_message)

    def _display_guide_message(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("ご利用ガイド")
        msg_box.setText(
            "ファイルを登録するには:\n"
            "  - メニューから「ファイル」→「PDFを開く」を選択\n"
            "  - または、PDFファイルをこのウィンドウにドラッグ＆ドロップ\n\n"
            "登録済みのファイルを検索する場合は、上部の「ファイル検索モード」タブから検索してください。"
        )
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

        # Add "Don't show again" checkbox
        from PyQt6.QtWidgets import QCheckBox # Import QCheckBox here
        dont_show_again_checkbox = QCheckBox("今後、このメッセージを表示しない", msg_box)
        msg_box.setCheckBox(dont_show_again_checkbox)

        msg_box.exec() # Show the message box and wait for user interaction

        # Save preference if checkbox is checked
        if dont_show_again_checkbox.isChecked():
            self.config_manager.set('Settings', 'show_startup_guide', 'False')

    def rebuild_index(self):
        reply = QMessageBox.question(self, 'インデックス再構築', 
                                     '本当にインデックスを再構築しますか？既存のインデックスは上書きされます。',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.metadata_manager.rebuild_index()
                QMessageBox.information(self, "成功", "インデックスを再構築しました。")
            except Exception as e:
                QMessageBox.information(self, "エラー", f"インデックスの再構築に失敗しました。\n{e}")

    def open_settings(self):
        from views.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.config_manager, self.metadata_manager, self)
        if dialog.exec():
            self.metadata_manager = MetadataManager(self.config_manager.get('Paths', 'root_save_directory'))
            QMessageBox.information(self, "設定", "設定を保存しました。")

    def _show_help_dialog(self):
        help_message = (
            "電子帳簿保存システム ヘルプ\n\n"
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
        QMessageBox.information(self, "電子帳簿保存システム ヘルプ", help_message)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        # Check if the drop is on the registration tab
        if self.tabs.currentWidget() is not self.registration_tab:
            return

        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.pdf'):
                self.registration_tab.add_file_to_list(file_path)