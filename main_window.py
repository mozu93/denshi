from PyQt6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget, QStatusBar, QMenuBar, QMessageBox
from views.file_registration_tab import FileRegistrationTab
from views.file_search_tab import FileSearchTab
from utils.config_manager import ConfigManager
from models.metadata_manager import MetadataManager

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True) # Accept drops on the main window
        self.setWindowTitle("PDF請求書リネーム支援ツール")
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
        dialog = SettingsDialog(self.config_manager, self)
        if dialog.exec():
            self.metadata_manager = MetadataManager(self.config_manager.get('Paths', 'root_save_directory'))
            QMessageBox.information(self, "設定", "設定を保存しました。")

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