from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QFileDialog, QLabel, QHBoxLayout, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QTabWidget, QWidget

class SettingsDialog(QDialog):
    def __init__(self, config_manager, metadata_manager, parent=None): # Added metadata_manager
        super().__init__(parent)
        self.config_manager = config_manager
        self.metadata_manager = metadata_manager # Store metadata_manager
        self.setWindowTitle("設定")
        self.layout = QVBoxLayout(self)

        # Root Save Directory
        self.root_dir_layout = QHBoxLayout()
        self.root_dir_label = QLabel("ルート保存ディレクトリ:")
        self.root_dir_edit = QLineEdit()
        self.root_dir_button = QPushButton("参照")
        self.root_dir_button.clicked.connect(self.browse_root_dir)
        self.root_dir_layout.addWidget(self.root_dir_label)
        self.root_dir_layout.addWidget(self.root_dir_edit)
        self.root_dir_layout.addWidget(self.root_dir_button)
        self.layout.addLayout(self.root_dir_layout)

        # Document Types Management
        doc_type_group = QGroupBox("書類種別管理")
        doc_type_layout = QVBoxLayout()

        self.doc_type_tabs = QTabWidget()

        # Expenditure Tab
        self.expenditure_doc_type_widget = QWidget()
        self.expenditure_doc_type_layout = QVBoxLayout(self.expenditure_doc_type_widget)
        self.expenditure_doc_type_table = QTableWidget()
        self.expenditure_doc_type_table.setColumnCount(2)
        self.expenditure_doc_type_table.setHorizontalHeaderLabels(["キー", "表示名"])
        self.expenditure_doc_type_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.expenditure_doc_type_layout.addWidget(self.expenditure_doc_type_table)
        self.doc_type_tabs.addTab(self.expenditure_doc_type_widget, "支出")

        # Income Tab
        self.income_doc_type_widget = QWidget()
        self.income_doc_type_layout = QVBoxLayout(self.income_doc_type_widget)
        self.income_doc_type_table = QTableWidget()
        self.income_doc_type_table.setColumnCount(2)
        self.income_doc_type_table.setHorizontalHeaderLabels(["キー", "表示名"])
        self.income_doc_type_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.income_doc_type_layout.addWidget(self.income_doc_type_table)
        self.doc_type_tabs.addTab(self.income_doc_type_widget, "収入")

        doc_type_layout.addWidget(self.doc_type_tabs)

        # Add new document type input
        add_doc_type_layout = QHBoxLayout()
        self.new_doc_type_key_edit = QLineEdit()
        self.new_doc_type_key_edit.setPlaceholderText("例: invoice")
        self.new_doc_type_value_edit = QLineEdit()
        self.new_doc_type_value_edit.setPlaceholderText("例: 03.請求書")
        self.add_doc_type_button = QPushButton("追加")
        self.add_doc_type_button.clicked.connect(self.add_doc_type)
        add_doc_type_layout.addWidget(QLabel("キー:"))
        add_doc_type_layout.addWidget(self.new_doc_type_key_edit)
        add_doc_type_layout.addWidget(QLabel("表示名:"))
        add_doc_type_layout.addWidget(self.new_doc_type_value_edit)
        add_doc_type_layout.addWidget(self.add_doc_type_button)
        doc_type_layout.addLayout(add_doc_type_layout)

        # Delete document type button
        self.delete_doc_type_button = QPushButton("選択を削除")
        self.delete_doc_type_button.clicked.connect(self.delete_selected_doc_type)
        doc_type_layout.addWidget(self.delete_doc_type_button)

        doc_type_group.setLayout(doc_type_layout)
        self.layout.addWidget(doc_type_group)

        # Buttons
        self.button_layout = QHBoxLayout()
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_settings)
        self.cancel_button = QPushButton("キャンセル")
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.cancel_button)
        self.layout.addLayout(self.button_layout)

        self.load_settings()

    def load_settings(self):
        root_dir = self.config_manager.get('Paths', 'root_save_directory')
        self.root_dir_edit.setText(root_dir)

        # Load expenditure document types
        self.expenditure_doc_type_table.setRowCount(0)
        expenditure_folder_names = self.config_manager.get_section('FolderNames_Expenditure')
        if expenditure_folder_names:
            for key, value in expenditure_folder_names.items():
                row_position = self.expenditure_doc_type_table.rowCount()
                self.expenditure_doc_type_table.insertRow(row_position)
                self.expenditure_doc_type_table.setItem(row_position, 0, QTableWidgetItem(key))
                self.expenditure_doc_type_table.setItem(row_position, 1, QTableWidgetItem(value))

        # Load income document types
        self.income_doc_type_table.setRowCount(0)
        income_folder_names = self.config_manager.get_section('FolderNames_Income')
        if income_folder_names:
            for key, value in income_folder_names.items():
                row_position = self.income_doc_type_table.rowCount()
                self.income_doc_type_table.insertRow(row_position)
                self.income_doc_type_table.setItem(row_position, 0, QTableWidgetItem(key))
                self.income_doc_type_table.setItem(row_position, 1, QTableWidgetItem(value))

    def browse_root_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "ルート保存ディレクトリを選択")
        if directory:
            self.root_dir_edit.setText(directory)

    def save_settings(self):
        root_dir = self.root_dir_edit.text()
        self.config_manager.set('Paths', 'root_save_directory', root_dir)

        # Save expenditure document types
        expenditure_doc_types_to_save = {}
        for row in range(self.expenditure_doc_type_table.rowCount()):
            key_item = self.expenditure_doc_type_table.item(row, 0)
            value_item = self.expenditure_doc_type_table.item(row, 1)
            if key_item and value_item:
                expenditure_doc_types_to_save[key_item.text()] = value_item.text()
        self.config_manager.set_section('FolderNames_Expenditure', expenditure_doc_types_to_save)

        # Save income document types
        income_doc_types_to_save = {}
        for row in range(self.income_doc_type_table.rowCount()):
            key_item = self.income_doc_type_table.item(row, 0)
            value_item = self.income_doc_type_table.item(row, 1)
            if key_item and value_item:
                income_doc_types_to_save[key_item.text()] = value_item.text()
        self.config_manager.set_section('FolderNames_Income', income_doc_types_to_save)

        self.accept()

    def add_doc_type(self):
        key = self.new_doc_type_key_edit.text().strip()
        value = self.new_doc_type_value_edit.text().strip()

        if not key or not value:
            QMessageBox.warning(self, "入力エラー", "キーと表示名の両方を入力してください。")
            return

        current_table = None
        if self.doc_type_tabs.currentIndex() == 0: # Expenditure tab
            current_table = self.expenditure_doc_type_table
        else: # Income tab
            current_table = self.income_doc_type_table

        # Check for duplicate key in current table
        for row in range(current_table.rowCount()):
            if current_table.item(row, 0).text() == key:
                QMessageBox.warning(self, "重複エラー", "このキーは既に存在します。")
                return

        row_position = current_table.rowCount()
        current_table.insertRow(row_position)
        current_table.setItem(row_position, 0, QTableWidgetItem(key))
        current_table.setItem(row_position, 1, QTableWidgetItem(value))

        self.new_doc_type_key_edit.clear()
        self.new_doc_type_value_edit.clear()

    def delete_selected_doc_type(self):
        current_table = None
        transaction_type_name = "" # To pass to metadata_manager
        if self.doc_type_tabs.currentIndex() == 0: # Expenditure tab
            current_table = self.expenditure_doc_type_table
            transaction_type_name = "支出情報" # Assuming this is the folder name
        else: # Income tab
            current_table = self.income_doc_type_table
            transaction_type_name = "収入情報" # Assuming this is the folder name

        selected_rows = current_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "選択なし", "削除する行を選択してください。")
            return

        # Get the document type value to check for files
        # Assuming only one row can be selected for simplicity, or iterate through all selected
        # For now, let's assume only one row can be selected for deletion.
        # If multiple rows are selected, we'll check the first one.
        selected_row_index = selected_rows[0].row()
        doc_type_value = current_table.item(selected_row_index, 1).text() # Get the display name (e.g., "03.請求書")

        # Check if there are files in the folder for this document type
        # Need to get the root_save_directory from config_manager
        # The metadata_manager already has root_path initialized from config_manager
        if self.metadata_manager.has_files_for_doc_type(transaction_type_name, doc_type_value):
            QMessageBox.warning(self, "削除不可", "この書類種別に関連するファイルがフォルダ内に存在するため、削除できません。")
            return

        reply = QMessageBox.question(self, "確認", "選択した書類種別を削除しますか？",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # Delete rows from bottom to top to avoid index issues
            for index in sorted(selected_rows, reverse=True):
                current_table.removeRow(index.row())