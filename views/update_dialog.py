# -*- coding: utf-8 -*-
"""
アップデート通知ダイアログ
新しいバージョンが利用可能な場合に通知ダイアログを表示します。
"""

import logging
import webbrowser
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from utils.update_checker import check_for_updates, UpdateInfo
from utils.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class UpdateDialog(QDialog):
    """アップデート通知ダイアログ"""

    def __init__(self, update_info: UpdateInfo, config_manager: ConfigManager, parent=None):
        """
        Args:
            update_info: アップデート情報
            config_manager: 設定マネージャー
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self.update_info = update_info
        self.config_manager = config_manager
        self.skip_version = False

        self._init_ui()

    def _init_ui(self):
        """UIを初期化"""
        self.setWindowTitle("アップデートの確認")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        layout = QVBoxLayout()

        # タイトル
        title_label = QLabel("新しいバージョンが利用可能です")
        title_font = QFont("Meiryo UI", 12, QFont.Weight.Bold)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # バージョン情報
        version_layout = QHBoxLayout()
        version_info = QLabel(
            f"現在のバージョン: {self.update_info.current_version}\n"
            f"最新バージョン: {self.update_info.latest_version}"
        )
        version_layout.addWidget(version_info)
        version_layout.addStretch()
        layout.addLayout(version_layout)

        layout.addSpacing(10)

        # リリースノート
        release_notes_label = QLabel("リリースノート:")
        layout.addWidget(release_notes_label)

        self.release_notes_text = QTextEdit()
        self.release_notes_text.setReadOnly(True)
        self.release_notes_text.setPlainText(self.update_info.release_notes)
        self.release_notes_text.setMaximumHeight(200)
        layout.addWidget(self.release_notes_text)

        layout.addSpacing(10)

        # スキップチェックボックス
        self.skip_checkbox = QCheckBox(f"このバージョン ({self.update_info.latest_version}) をスキップ")
        layout.addWidget(self.skip_checkbox)

        # ボタン
        button_layout = QHBoxLayout()

        self.download_button = QPushButton("ダウンロードページを開く")
        self.download_button.clicked.connect(self._on_download_clicked)
        button_layout.addWidget(self.download_button)

        self.later_button = QPushButton("後で")
        self.later_button.clicked.connect(self._on_later_clicked)
        button_layout.addWidget(self.later_button)

        self.skip_button = QPushButton("スキップ")
        self.skip_button.clicked.connect(self._on_skip_clicked)
        button_layout.addWidget(self.skip_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _on_download_clicked(self):
        """ダウンロードボタンクリック時の処理"""
        try:
            # ブラウザでダウンロードページを開く
            webbrowser.open(self.update_info.release_url)
            logger.info(f"ダウンロードページを開きました: {self.update_info.release_url}")
            self.accept()
        except Exception as e:
            logger.error(f"ダウンロードページを開くのに失敗しました: {e}")
            QMessageBox.warning(
                self,
                "エラー",
                f"ダウンロードページを開くのに失敗しました。\n\n"
                f"手動で以下のURLを開いてください:\n{self.update_info.release_url}"
            )

    def _on_later_clicked(self):
        """後でボタンクリック時の処理"""
        logger.info("アップデートを後回しにしました")
        self.reject()

    def _on_skip_clicked(self):
        """スキップボタンクリック時の処理"""
        if self.skip_checkbox.isChecked():
            # スキップバージョンをconfig.iniに保存
            self.config_manager.set('Update', 'skip_version', self.update_info.latest_version)
            logger.info(f"バージョン {self.update_info.latest_version} をスキップしました")
            self.skip_version = True

        self.reject()


def check_and_notify_update(parent, config_manager: ConfigManager):
    """
    アップデートをチェックし、新しいバージョンがあれば通知ダイアログを表示します。

    Args:
        parent: 親ウィジェット
        config_manager: 設定マネージャー
    """
    try:
        # 起動時チェックが無効の場合はスキップ
        check_enabled = config_manager.get('Update', 'check_on_startup', fallback='True') == 'True'
        if not check_enabled:
            logger.info("起動時のアップデートチェックは無効です")
            return

        # アップデートチェック
        update_info = check_for_updates()

        if update_info is None:
            # 最新バージョンを使用中、またはチェックに失敗
            logger.info("アップデートチェック完了（新しいバージョンはありません）")
            _update_last_check_date(config_manager)
            return

        # スキップバージョンのチェック
        skip_version = config_manager.get('Update', 'skip_version', fallback='')
        if skip_version and skip_version == update_info.latest_version:
            logger.info(f"バージョン {update_info.latest_version} はスキップ設定されています")
            _update_last_check_date(config_manager)
            return

        # アップデート通知ダイアログを表示
        logger.info("アップデート通知ダイアログを表示します")
        dialog = UpdateDialog(update_info, config_manager, parent)
        dialog.exec()

        _update_last_check_date(config_manager)

    except Exception as e:
        logger.error(f"アップデートチェック中に予期しないエラーが発生しました: {e}", exc_info=True)


def _update_last_check_date(config_manager: ConfigManager):
    """最終チェック日時を更新"""
    try:
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        config_manager.set('Update', 'last_check_date', current_date)
    except Exception as e:
        logger.warning(f"最終チェック日時の更新に失敗しました: {e}")
