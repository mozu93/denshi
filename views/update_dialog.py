# -*- coding: utf-8 -*-
"""
アップデート通知ダイアログ
バックグラウンドスレッドでバージョンチェック → ダウンロード → 自動インストール
"""

import logging
import queue
import sys
import threading
import webbrowser
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QCheckBox, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal
from PyQt6.QtGui import QFont

from utils.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class _UpdateBridge(QObject):
    """バックグラウンドスレッド → メインスレッドへシグナルを届けるブリッジ。
    メインスレッドで生成すること。"""
    update_available = pyqtSignal(object)  # UpdateInfo を渡す


class UpdateDialog(QDialog):
    """アップデート通知・ダウンロード・インストールダイアログ"""

    def __init__(self, update_info, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.config_manager = config_manager
        self._installer_path = None
        self._dl_queue: queue.Queue = queue.Queue()

        self._init_ui()

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_queue)
        self._poll_timer.start(100)

    def _init_ui(self):
        self.setWindowTitle("アップデートの確認")
        self.setMinimumWidth(520)

        layout = QVBoxLayout()

        title_label = QLabel("新しいバージョンが利用可能です")
        title_font = QFont("Meiryo UI", 12, QFont.Weight.Bold)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        version_info = QLabel(
            f"現在のバージョン: {self.update_info.current_version}\n"
            f"最新バージョン: {self.update_info.latest_version}"
        )
        layout.addWidget(version_info)
        layout.addSpacing(8)

        layout.addWidget(QLabel("リリースノート:"))
        self.release_notes_text = QTextEdit()
        self.release_notes_text.setReadOnly(True)
        self.release_notes_text.setPlainText(self.update_info.release_notes)
        self.release_notes_text.setMaximumHeight(180)
        layout.addWidget(self.release_notes_text)
        layout.addSpacing(8)

        # 進捗バー（ダウンロード中のみ表示）
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        layout.addSpacing(4)

        self.skip_checkbox = QCheckBox(
            f"このバージョン ({self.update_info.latest_version}) をスキップ"
        )
        layout.addWidget(self.skip_checkbox)

        button_layout = QHBoxLayout()

        if self.update_info.download_url:
            self.download_button = QPushButton("今すぐダウンロード")
            self.download_button.clicked.connect(self._start_download)
        else:
            self.download_button = QPushButton("ダウンロードページを開く")
            self.download_button.clicked.connect(self._open_browser)
        button_layout.addWidget(self.download_button)

        self.install_button = QPushButton("インストールして再起動")
        self.install_button.setVisible(False)
        self.install_button.clicked.connect(self._install)
        button_layout.addWidget(self.install_button)

        button_layout.addStretch()

        self.later_button = QPushButton("後で")
        self.later_button.clicked.connect(self.reject)
        button_layout.addWidget(self.later_button)

        self.skip_button = QPushButton("スキップ")
        self.skip_button.clicked.connect(self._on_skip_clicked)
        button_layout.addWidget(self.skip_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _open_browser(self):
        try:
            webbrowser.open(self.update_info.release_url)
            self.accept()
        except Exception:
            QMessageBox.warning(
                self, "エラー",
                f"ページを開けませんでした。\n{self.update_info.release_url}"
            )

    def _start_download(self):
        self.download_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setText("ダウンロード中...")
        self.progress_label.setVisible(True)
        threading.Thread(target=self._do_download, daemon=True).start()

    def _do_download(self):
        from utils.update_checker import download_installer

        def on_progress(received: int, total: int):
            self._dl_queue.put(('progress', received, total))

        path = download_installer(self.update_info.download_url, on_progress)
        self._dl_queue.put(('ready', path) if path else ('failed',))

    def _poll_queue(self):
        try:
            while True:
                item = self._dl_queue.get_nowait()
                if item[0] == 'progress':
                    _, received, total = item
                    if total > 0:
                        self.progress_bar.setValue(int(received * 100 / total))
                        self.progress_label.setText(
                            f"{received / 1048576:.1f} / {total / 1048576:.1f} MB"
                        )
                    else:
                        self.progress_label.setText(
                            f"{received / 1048576:.1f} MB ダウンロード中..."
                        )
                elif item[0] == 'ready':
                    self._installer_path = item[1]
                    self.progress_bar.setValue(100)
                    self.progress_label.setText("ダウンロード完了！インストールできます。")
                    self.install_button.setVisible(True)
                elif item[0] == 'failed':
                    self.download_button.setEnabled(True)
                    self.download_button.setText("再試行")
                    self.progress_bar.setVisible(False)
                    self.progress_label.setText("ダウンロードに失敗しました。")
        except queue.Empty:
            pass

    def _install(self):
        if not self._installer_path:
            return
        self._poll_timer.stop()
        from utils.update_checker import launch_installer
        if getattr(sys, 'frozen', False):
            launch_installer(self._installer_path)
        else:
            import subprocess
            subprocess.Popen([self._installer_path])

    def _on_skip_clicked(self):
        if self.skip_checkbox.isChecked():
            self.config_manager.set(
                'Update', 'skip_version', self.update_info.latest_version
            )
            logger.info(f"バージョン {self.update_info.latest_version} をスキップしました")
        self.reject()

    def closeEvent(self, event):
        self._poll_timer.stop()
        super().closeEvent(event)


def check_and_notify_update(parent, config_manager: ConfigManager):
    """
    メインスレッドから呼ぶこと。
    シグナルブリッジをメインスレッドで生成してからバックグラウンドでHTTPチェックを実行する。
    """
    # ブリッジはメインスレッドで生成（シグナルはスレッドセーフ）
    bridge = _UpdateBridge(parent)
    bridge.update_available.connect(
        lambda info: _show_update_dialog(info, config_manager, parent),
        Qt.ConnectionType.QueuedConnection,
    )

    def _bg():
        try:
            from utils.update_checker import check_for_updates

            check_enabled = (
                config_manager.get('Update', 'check_on_startup', fallback='True') == 'True'
            )
            if not check_enabled:
                return

            update_info = check_for_updates()
            _update_last_check_date(config_manager)

            if update_info is None:
                return

            skip_version = config_manager.get('Update', 'skip_version', fallback='')
            if skip_version and skip_version == update_info.latest_version:
                logger.info(f"バージョン {update_info.latest_version} はスキップ設定されています")
                return

            logger.info("アップデート通知ダイアログを表示します")
            bridge.update_available.emit(update_info)
        except Exception as e:
            logger.error(f"アップデートチェック中にエラーが発生しました: {e}", exc_info=True)

    threading.Thread(target=_bg, daemon=True).start()


def _show_update_dialog(update_info, config_manager, parent):
    dialog = UpdateDialog(update_info, config_manager, parent)
    dialog.exec()


def _update_last_check_date(config_manager: ConfigManager):
    try:
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        config_manager.set('Update', 'last_check_date', current_date)
    except Exception as e:
        logger.warning(f"最終チェック日時の更新に失敗しました: {e}")
