from PyQt6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget, QStatusBar, QMenuBar, QMessageBox, QApplication, QLabel
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer
from views.file_registration_tab import FileRegistrationTab
from views.file_search_tab import FileSearchTab
from utils.config_manager import ConfigManager
from models.metadata_manager import MetadataManager
from models.ocr_processor import OcrProcessor
from views.settings_dialog import SettingsDialog
from views.help_dialog import show_help_dialog
from views.startup_guide_dialog import show_startup_guide
from utils.constants import HARDCODED_ROOT_SAVE_DIRECTORY, DEFAULT_FONT_SIZE, MIN_FONT_SIZE, MAX_FONT_SIZE
import os
import threading

class MainWindow(QMainWindow):
    def __init__(self, config_file, parent=None, progress_callback=None):
        super().__init__(parent)
        _progress = progress_callback or (lambda v, m: None)

        self.setAcceptDrops(True)
        self.setWindowTitle("電子帳簿保存システム")
        self.test_mode = False

        central_widget = QWidget(self)
        central_widget.setAutoFillBackground(True)
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        self.tabs = QTabWidget()

        _progress(25, "設定ファイルを読み込み中...")
        self.config_manager = ConfigManager(config_path=config_file)

        # ウィンドウサイズの復元
        width, height = self.config_manager.get_window_size()
        self.setGeometry(100, 100, width, height)

        # フォントサイズの復元
        font_size = self.config_manager.get_ui_font_size()
        self.apply_font_size(font_size)

        # 設定ファイルからルート保存ディレクトリを読み込む（未設定ならデフォルト値）
        root_save_directory = self.config_manager.get('Paths', 'root_save_directory', fallback=HARDCODED_ROOT_SAVE_DIRECTORY)

        _progress(35, "データを初期化中...")
        self.metadata_manager = MetadataManager(root_save_directory)

        # 起動時に通し番号を再計算（バックグラウンドで実行してUIブロックを回避）
        threading.Thread(
            target=self.metadata_manager.recalculate_all_doc_ids,
            daemon=True
        ).start()

        _progress(50, "登録画面を構築中...")
        self.registration_tab = FileRegistrationTab(config_manager=self.config_manager, metadata_manager=self.metadata_manager)

        _progress(72, "検索画面を構築中...")
        self.search_tab = FileSearchTab(config_manager=self.config_manager, metadata_manager=self.metadata_manager)
        self.tabs.addTab(self.registration_tab, QIcon.fromTheme("document-new"), "ファイル登録モード")
        self.tabs.addTab(self.search_tab, QIcon.fromTheme("edit-find"), "ファイル検索モード")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs)

        _progress(85, "メニューを構築中...")
        # Actions must be created before menus and toolbars
        self._create_actions()

        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)
        self._create_menus()

        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("準備完了")
        self._check_ocr_engine()

        _progress(95, "起動処理を開始中...")
        if not root_save_directory:
            QTimer.singleShot(0, lambda: self._prompt_configure_root_dir())
        QTimer.singleShot(0, lambda: show_startup_guide(self.config_manager, self))
        QTimer.singleShot(100, lambda: threading.Thread(
            target=OcrProcessor.warm_up,
            args=(self.config_manager,),
            daemon=True
        ).start())
        self._check_for_updates()

    def _create_actions(self):
        self.open_folder_action = QAction("フォルダを開く", self)
        self.open_folder_action.triggered.connect(self.registration_tab.open_folder_dialog)
        self.open_action = QAction("ファイルを開く", self)
        self.open_action.triggered.connect(self.registration_tab.open_file_dialog)
        self.exit_action = QAction("終了", self)
        self.exit_action.triggered.connect(self.close)
        self.reindex_action = QAction("インデックス再構築", self)
        self.reindex_action.triggered.connect(self.rebuild_index)
        self.settings_action = QAction("設定", self)
        self.settings_action.triggered.connect(self.open_settings)
        self.help_action = QAction("ヘルプを表示", self)
        self.help_action.triggered.connect(self._show_help_dialog)
        self.zoom_in_font_action = QAction("文字を大きく", self)
        self.zoom_in_font_action.triggered.connect(self.increase_font_size)
        self.zoom_out_font_action = QAction("文字を小さく", self)
        self.zoom_out_font_action.triggered.connect(self.decrease_font_size)
        self.reset_font_action = QAction("文字サイズリセット", self)
        self.reset_font_action.triggered.connect(self.reset_font_size)
        self.test_mode_action = QAction("テストモード", self)
        self.test_mode_action.setCheckable(True)
        self.test_mode_action.triggered.connect(self._toggle_test_mode)

    def _create_menus(self):
        file_menu = self.menu_bar.addMenu("ファイル")
        file_menu.addAction(self.open_folder_action)
        file_menu.addAction(self.open_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        self.menu_bar.addAction(self.reindex_action)

        view_menu = self.menu_bar.addMenu("表示")
        view_menu.addAction(self.zoom_in_font_action)
        view_menu.addAction(self.zoom_out_font_action)
        view_menu.addAction(self.reset_font_action)

        self.menu_bar.addAction(self.settings_action)

        help_menu = self.menu_bar.addMenu("ヘルプ")
        help_menu.addAction(self.help_action)
        help_menu.addSeparator()
        help_menu.addAction(self.test_mode_action)

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
                QMessageBox.critical(self, "エラー", f"インデックスの再構築に失敗しました。\n{e}")

    def _toggle_test_mode(self, checked):
        self.test_mode = checked
        if checked:
            self.setWindowTitle("電子帳簿保存システム [テストモード]")
            self.status_bar.showMessage("テストモード")
        else:
            self.setWindowTitle("電子帳簿保存システム")
            self.status_bar.showMessage("準備完了")

    def _prompt_configure_root_dir(self):
        QMessageBox.information(
            self, "保存先の設定",
            "ルート保存ディレクトリが設定されていません。\n設定画面からフォルダを選択してください。"
        )
        self.open_settings()

    def open_settings(self):
        dialog = SettingsDialog(self.config_manager, self.metadata_manager, self, test_mode=self.test_mode)
        if dialog.exec():
            new_root_directory = dialog.new_root_dir
            if new_root_directory is not None:
                self.metadata_manager.update_root_directory(new_root_directory)
            QMessageBox.information(self, "設定", "設定を保存しました。")

    def _show_help_dialog(self):
        show_help_dialog(self)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if self.tabs.currentWidget() is not self.registration_tab:
            return

        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.pdf'):
                self.registration_tab.add_file_to_list(file_path)

    def _on_tab_changed(self, index):
        """When the tab is changed, refresh the search tab if it's selected."""
        if self.tabs.widget(index) == self.search_tab:
            self.search_tab.refresh_data()

    def apply_font_size(self, font_size):
        """Apply the specified font size to the entire application."""
        from utils.ui_styles import get_app_style
        QApplication.instance().setStyleSheet(get_app_style(font_size))

    def increase_font_size(self):
        current_size = self.config_manager.get_ui_font_size()
        new_size = min(current_size + 2, MAX_FONT_SIZE)
        self.apply_font_size(new_size)
        try:
            self.config_manager.set_ui_font_size(new_size)
        except Exception:
            pass

    def decrease_font_size(self):
        current_size = self.config_manager.get_ui_font_size()
        new_size = max(current_size - 2, MIN_FONT_SIZE)
        self.apply_font_size(new_size)
        try:
            self.config_manager.set_ui_font_size(new_size)
        except Exception:
            pass

    def reset_font_size(self):
        self.apply_font_size(DEFAULT_FONT_SIZE)
        try:
            self.config_manager.set_ui_font_size(DEFAULT_FONT_SIZE)
        except Exception:
            pass

    def _check_ocr_engine(self):
        """Windows OCR（WinRT）の日本語サポートを確認する。"""
        try:
            from winsdk.windows.media.ocr import OcrEngine
            from winsdk.windows.globalization import Language
            if not OcrEngine.is_language_supported(Language("ja")):
                warn = QLabel(
                    "⚠ Windows OCR 日本語未対応　―　"
                    "Windowsの設定で日本語言語パックをインストールしてください。"
                )
                warn.setStyleSheet("color: #cc0000; font-weight: bold; padding: 0 8px;")
                self.status_bar.addPermanentWidget(warn)
        except Exception:
            pass

    def _check_for_updates(self):
        """アップデートをバックグラウンドでチェックします（メインスレッドから呼ぶこと）。"""
        from views.update_dialog import check_and_notify_update
        check_and_notify_update(self, self.config_manager)

    def closeEvent(self, event):
        """Save window size and splitter positions before closing."""
        self.status_bar.showMessage("終了中...")
        self.setEnabled(False)
        QApplication.processEvents()

        try:
            self.config_manager.set_window_size(self.width(), self.height())
        except Exception:
            pass

        try:
            from models.ocr_processor import OcrProcessor
            OcrProcessor.shutdown()
        except Exception:
            pass

        try:
            if hasattr(self.registration_tab, 'save_splitter_sizes'):
                self.registration_tab.save_splitter_sizes()
            if hasattr(self.search_tab, 'save_splitter_sizes'):
                self.search_tab.save_splitter_sizes()
        except Exception:
            pass

        event.accept()
