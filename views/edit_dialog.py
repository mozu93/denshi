from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit, 
    QDialogButtonBox, QGroupBox, QLabel, QComboBox, QHBoxLayout
)

class EditDialog(QDialog):
    def __init__(self, data, year_nendo, config_manager, metadata_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("データ編集")
        self.setMinimumWidth(500)

        self.data = data
        self.current_year = year_nendo
        self.config_manager = config_manager
        self.metadata_manager = metadata_manager

        # Layouts
        main_layout = QVBoxLayout(self)

        # --- Metadata Group ---
        metadata_group = QGroupBox("メタデータ編集")
        form_layout = QFormLayout()
        self.client_name_edit = QLineEdit(str(data.get('client_name', '')))
        self.issue_date_edit = QLineEdit(str(data.get('issue_date', '')))
        self.amount_edit = QLineEdit(str(data.get('amount', '')))
        self.memo_edit = QTextEdit(str(data.get('memo', '')))
        form_layout.addRow("取引先名:", self.client_name_edit)
        form_layout.addRow("発行日 (YYYYMMDD):", self.issue_date_edit)
        form_layout.addRow("金額(税込):", self.amount_edit)
        form_layout.addRow("メモ:", self.memo_edit)
        metadata_group.setLayout(form_layout)
        main_layout.addWidget(metadata_group)

        # --- Location Group ---
        location_group = QGroupBox("ファイル場所")
        location_layout = QHBoxLayout()

        # Current Location
        current_location_group = QGroupBox("現在の場所")
        current_layout = QFormLayout()
        self.current_year_label = QLineEdit(self.current_year)
        self.current_year_label.setReadOnly(True)
        self.current_category_label = QLineEdit(data.get('category', ''))
        self.current_category_label.setReadOnly(True)
        self.current_doc_type_label = QLineEdit(data.get('doc_type', ''))
        self.current_doc_type_label.setReadOnly(True)
        current_layout.addRow("年:", self.current_year_label)
        current_layout.addRow("取引区分:", self.current_category_label)
        current_layout.addRow("書類種別:", self.current_doc_type_label)
        current_location_group.setLayout(current_layout)

        # Destination Location
        destination_group = QGroupBox("移動先の場所")
        destination_layout = QFormLayout()
        self.year_combo = QComboBox()
        self.category_combo = QComboBox()
        self.doc_type_combo = QComboBox()
        destination_layout.addRow("年:", self.year_combo)
        destination_layout.addRow("取引区分:", self.category_combo)
        destination_layout.addRow("書類種別:", self.doc_type_combo)
        destination_group.setLayout(destination_layout)

        location_layout.addWidget(current_location_group)
        location_layout.addWidget(destination_group)
        location_group.setLayout(location_layout)
        main_layout.addWidget(location_group)

        # --- Buttons ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self._populate_combos()
        self.category_combo.currentTextChanged.connect(self._update_doc_type_combo)

    def _populate_combos(self):
        # Populate Year ComboBox
        available_years = self.metadata_manager.get_available_years()
        if available_years:
            self.year_combo.addItems(available_years)
        if self.current_year in available_years:
            self.year_combo.setCurrentText(self.current_year)

        # Populate Category ComboBox
        categories = ["支出情報", "収入情報", "その他団体"]
        self.category_combo.addItems(categories)
        current_category = self.data.get('category', '')
        if current_category in categories:
            self.category_combo.setCurrentText(current_category)

        # Populate Doc Type ComboBox based on current category
        self._update_doc_type_combo(current_category)
        current_doc_type = self.data.get('doc_type', '')
        if self.doc_type_combo.findText(current_doc_type) > -1:
            self.doc_type_combo.setCurrentText(current_doc_type)

    def _update_doc_type_combo(self, category):
        self.doc_type_combo.clear()
        doc_types = []
        if category == "支出情報":
            doc_types = self.config_manager.get_section('FolderNames_Expenditure').values()
        elif category == "収入情報":
            doc_types = self.config_manager.get_section('FolderNames_Income').values()
        elif category == "その他団体":
            doc_types = self.config_manager.get_section('FolderNames_OtherOrganization').values()
        self.doc_type_combo.addItems(sorted(list(set(doc_types))))

    def get_updated_data(self):
        return {
            # Metadata
            'client_name': self.client_name_edit.text(),
            'issue_date': self.issue_date_edit.text(),
            'amount': self.amount_edit.text(),
            'memo': self.memo_edit.toPlainText(),
            # Destination
            'destination_year': self.year_combo.currentText(),
            'destination_category': self.category_combo.currentText(),
            'destination_doc_type': self.doc_type_combo.currentText(),
        }