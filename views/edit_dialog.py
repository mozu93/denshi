from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QPushButton, QDialogButtonBox, QMessageBox, QGroupBox, QComboBox
)
import logging
import math
from utils.constants import CATEGORIES, CATEGORY_EXPENDITURE, CATEGORY_INCOME, CATEGORY_OTHER_ORG

logger = logging.getLogger(__name__)


def _safe_str(val, default=''):
    """NaN (float) や None を空文字列に変換する。"""
    if val is None:
        return default
    if isinstance(val, float) and math.isnan(val):
        return default
    return str(val)

class EditDialog(QDialog):
    def __init__(self, data, year_nendo, config_manager=None, metadata_manager=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("データ編集")
        self.config_manager = config_manager
        self.metadata_manager = metadata_manager

        if data is None:
            logger.error("EditDialog: data is None")
            raise ValueError("データが無効です。")
        if not isinstance(data, dict):
            logger.error(f"EditDialog: data is not a dict, got {type(data)}")
            raise ValueError("データは辞書である必要があります。")

        self.data = data

        layout = QVBoxLayout(self)

        # --- メタデータ編集フォーム ---
        form_layout = QFormLayout()
        try:
            self.client_name_edit = QLineEdit(_safe_str(data.get('client_name')))
            self.issue_date_edit = QLineEdit(_safe_str(data.get('issue_date')))
            self.amount_edit = QLineEdit(_safe_str(data.get('amount')))
            self.memo_edit = QTextEdit(_safe_str(data.get('memo')))
        except Exception as e:
            logger.error(f"EditDialog: Error initializing fields: {e}")
            raise ValueError(f"フィールドの初期化に失敗しました: {e}")

        form_layout.addRow("取引先名:", self.client_name_edit)
        form_layout.addRow("発行日 (YYYYMMDD):", self.issue_date_edit)
        form_layout.addRow("金額(税込):", self.amount_edit)
        form_layout.addRow("メモ:", self.memo_edit)
        layout.addLayout(form_layout)

        # --- 移動先グループ ---
        move_group = QGroupBox("移動先（変更しない場合はそのまま）")
        move_layout = QFormLayout()

        # 年
        self.dest_year_combo = QComboBox()
        if metadata_manager:
            available_years = metadata_manager.get_available_years()
            self.dest_year_combo.addItems(available_years)
            if year_nendo in available_years:
                self.dest_year_combo.setCurrentText(year_nendo)
        else:
            self.dest_year_combo.addItem(year_nendo)

        # 取引区分
        self.dest_category_combo = QComboBox()
        self.dest_category_combo.addItems(CATEGORIES)
        current_category = str(data.get('category', ''))
        if current_category in CATEGORIES:
            self.dest_category_combo.setCurrentText(current_category)
        self.dest_category_combo.currentTextChanged.connect(self._on_category_changed)

        # 書類種別
        self.dest_doc_type_combo = QComboBox()

        move_layout.addRow("年:", self.dest_year_combo)
        move_layout.addRow("取引区分:", self.dest_category_combo)
        move_layout.addRow("書類種別:", self.dest_doc_type_combo)
        move_group.setLayout(move_layout)
        layout.addWidget(move_group)

        # 書類種別を初期化（現在の取引区分ベース）
        self._on_category_changed(self.dest_category_combo.currentText())
        current_doc_type = str(data.get('doc_type', ''))
        if current_doc_type and self.dest_doc_type_combo.findText(current_doc_type) >= 0:
            self.dest_doc_type_combo.setCurrentText(current_doc_type)

        # Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _on_category_changed(self, category):
        """取引区分に応じて書類種別コンボを更新"""
        self.dest_doc_type_combo.clear()
        if not self.config_manager:
            return
        if category == CATEGORY_EXPENDITURE:
            doc_types = self.config_manager.get_section('FolderNames_Expenditure')
        elif category == CATEGORY_INCOME:
            doc_types = self.config_manager.get_section('FolderNames_Income')
        elif category == CATEGORY_OTHER_ORG:
            doc_types = self.config_manager.get_section('FolderNames_OtherOrganization')
        else:
            doc_types = {}
        self.dest_doc_type_combo.addItems(sorted(doc_types.values()))

    def get_updated_data(self):
        return {
            'client_name': self.client_name_edit.text(),
            'issue_date': self.issue_date_edit.text(),
            'amount': self.amount_edit.text(),
            'memo': self.memo_edit.toPlainText(),
            'destination_year': self.dest_year_combo.currentText(),
            'destination_category': self.dest_category_combo.currentText(),
            'destination_doc_type': self.dest_doc_type_combo.currentText(),
        }
