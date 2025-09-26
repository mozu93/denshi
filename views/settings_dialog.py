from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QFileDialog, QLabel, QHBoxLayout, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QTabWidget, QWidget, QSplitter, QFormLayout
from models.client_manager import ClientManager
from utils.ui_styles import apply_button_style, apply_small_button_style, apply_table_style

class SettingsDialog(QDialog):
    def __init__(self, config_manager, metadata_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.metadata_manager = metadata_manager
        self.client_manager = ClientManager(config_manager)
        self.new_root_dir = None
        self.editing_client_id = None  # 編集中のクライアントID
        self.setWindowTitle("設定")
        self.main_layout = QVBoxLayout(self)

        # 2カラムレイアウト用のスプリッター
        self.splitter = QSplitter()

        # 左カラム：既存の設定項目
        self.left_widget = QWidget()
        self.left_layout = QVBoxLayout(self.left_widget)

        # 右カラム：取引先名管理
        self.right_widget = QWidget()
        self.right_layout = QVBoxLayout(self.right_widget)

        self.splitter.addWidget(self.left_widget)
        self.splitter.addWidget(self.right_widget)
        self.main_layout.addWidget(self.splitter)

        # Root Save Directory
        root_dir_group = QGroupBox("保存先設定")
        root_dir_group_layout = QVBoxLayout()
        self.root_dir_layout = QHBoxLayout()
        self.root_dir_label = QLabel("ルート保存ディレクトリ:")
        self.root_dir_edit = QLineEdit()
        self.root_dir_button = QPushButton("参照")
        self.root_dir_button.clicked.connect(self.browse_root_dir)
        self.root_dir_layout.addWidget(self.root_dir_label)
        self.root_dir_layout.addWidget(self.root_dir_edit)
        self.root_dir_layout.addWidget(self.root_dir_button)
        root_dir_group_layout.addLayout(self.root_dir_layout)
        root_dir_group.setLayout(root_dir_group_layout)
        self.left_layout.addWidget(root_dir_group)

        # Tesseract Path
        tesseract_group = QGroupBox("OCR設定")
        tesseract_group_layout = QVBoxLayout()
        tesseract_layout = QHBoxLayout()
        tesseract_layout.addWidget(QLabel("Tesseract OCR のパス:"))
        self.tesseract_path_edit = QLineEdit(self)
        tesseract_layout.addWidget(self.tesseract_path_edit)
        self.browse_tesseract_button = QPushButton('参照...', self)
        self.browse_tesseract_button.clicked.connect(self.browse_tesseract_path)
        tesseract_layout.addWidget(self.browse_tesseract_button)
        tesseract_group_layout.addLayout(tesseract_layout)
        tesseract_group.setLayout(tesseract_group_layout)
        self.left_layout.addWidget(tesseract_group)

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

        # Other Organization Tab
        self.other_org_doc_type_widget = QWidget()
        self.other_org_doc_type_layout = QVBoxLayout(self.other_org_doc_type_widget)
        self.other_org_doc_type_table = QTableWidget()
        self.other_org_doc_type_table.setColumnCount(2)
        self.other_org_doc_type_table.setHorizontalHeaderLabels(["キー", "表示名"])
        self.other_org_doc_type_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.other_org_doc_type_layout.addWidget(self.other_org_doc_type_table)
        self.doc_type_tabs.addTab(self.other_org_doc_type_widget, "その他団体")

        doc_type_layout.addWidget(self.doc_type_tabs)

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

        self.delete_doc_type_button = QPushButton("選択を削除")
        self.delete_doc_type_button.clicked.connect(self.delete_selected_doc_type)
        doc_type_layout.addWidget(self.delete_doc_type_button)

        doc_type_group.setLayout(doc_type_layout)
        self.left_layout.addWidget(doc_type_group)

        # Buttons
        self.button_layout = QHBoxLayout()
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_settings)
        self.cancel_button = QPushButton("キャンセル")
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.cancel_button)

        # 右カラム：取引先名管理
        client_group = QGroupBox("取引先名管理")
        client_layout = QVBoxLayout()

        # 取引先名一覧テーブル
        self.client_table = QTableWidget()
        self.client_table.setColumnCount(2)
        self.client_table.setHorizontalHeaderLabels(["取引先名", "フリガナ"])
        self.client_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        client_layout.addWidget(self.client_table)

        # 新規追加用フォーム
        add_client_layout = QFormLayout()
        self.new_client_name_edit = QLineEdit()
        self.new_client_furigana_edit = QLineEdit()
        add_client_layout.addRow("取引先名:", self.new_client_name_edit)
        add_client_layout.addRow("フリガナ:", self.new_client_furigana_edit)

        # ボタンレイアウト
        client_button_layout = QHBoxLayout()
        self.add_client_button = QPushButton("追加")
        self.edit_client_button = QPushButton("編集")
        self.cancel_edit_button = QPushButton("キャンセル")
        self.delete_client_button = QPushButton("削除")
        self.cancel_edit_button.setVisible(False)  # 初期状態では非表示

        self.add_client_button.clicked.connect(self.add_or_update_client)
        self.edit_client_button.clicked.connect(self.edit_client)
        self.cancel_edit_button.clicked.connect(self.cancel_edit)
        self.delete_client_button.clicked.connect(self.delete_client)

        client_button_layout.addWidget(self.add_client_button)
        client_button_layout.addWidget(self.edit_client_button)
        client_button_layout.addWidget(self.cancel_edit_button)
        client_button_layout.addWidget(self.delete_client_button)

        client_layout.addLayout(add_client_layout)
        client_layout.addLayout(client_button_layout)

        client_group.setLayout(client_layout)
        self.right_layout.addWidget(client_group)

        # メインレイアウトにボタンを追加
        self.main_layout.addLayout(self.button_layout)

        self.load_settings()
        self._apply_styles()

    def load_settings(self):
        root_dir = self.config_manager.get('Paths', 'root_save_directory')
        self.root_dir_edit.setText(root_dir)

        tesseract_path = self.config_manager.get_tesseract_path()
        self.tesseract_path_edit.setText(tesseract_path)

        self.expenditure_doc_type_table.setRowCount(0)
        expenditure_folder_names = self.config_manager.get_section('FolderNames_Expenditure')
        if expenditure_folder_names:
            for key, value in expenditure_folder_names.items():
                row_position = self.expenditure_doc_type_table.rowCount()
                self.expenditure_doc_type_table.insertRow(row_position)
                self.expenditure_doc_type_table.setItem(row_position, 0, QTableWidgetItem(key))
                self.expenditure_doc_type_table.setItem(row_position, 1, QTableWidgetItem(value))

        self.income_doc_type_table.setRowCount(0)
        income_folder_names = self.config_manager.get_section('FolderNames_Income')
        if income_folder_names:
            for key, value in income_folder_names.items():
                row_position = self.income_doc_type_table.rowCount()
                self.income_doc_type_table.insertRow(row_position)
                self.income_doc_type_table.setItem(row_position, 0, QTableWidgetItem(key))
                self.income_doc_type_table.setItem(row_position, 1, QTableWidgetItem(value))

        self.other_org_doc_type_table.setRowCount(0)
        other_org_folder_names = self.config_manager.get_section('FolderNames_OtherOrganization')
        if other_org_folder_names:
            for key, value in other_org_folder_names.items():
                row_position = self.other_org_doc_type_table.rowCount()
                self.other_org_doc_type_table.insertRow(row_position)
                self.other_org_doc_type_table.setItem(row_position, 0, QTableWidgetItem(key))
                self.other_org_doc_type_table.setItem(row_position, 1, QTableWidgetItem(value))

        # 取引先データを読み込み
        self.load_clients()
    def browse_root_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "ルート保存ディレクトリを選択")
        if directory:
            self.root_dir_edit.setText(directory)

    def browse_tesseract_path(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 'Tesseract OCR を選択', '', '実行ファイル (*.exe)')
        if file_path:
            self.tesseract_path_edit.setText(file_path)

    def save_settings(self):
        root_dir = self.root_dir_edit.text()
        self.config_manager.set('Paths', 'root_save_directory', root_dir)
        self.new_root_dir = root_dir

        tesseract_path = self.tesseract_path_edit.text()
        self.config_manager.set_tesseract_path(tesseract_path)

        expenditure_doc_types_to_save = {}
        for row in range(self.expenditure_doc_type_table.rowCount()):
            key_item = self.expenditure_doc_type_table.item(row, 0)
            value_item = self.expenditure_doc_type_table.item(row, 1)
            if key_item and value_item:
                expenditure_doc_types_to_save[key_item.text()] = value_item.text()
        self.config_manager.set_section('FolderNames_Expenditure', expenditure_doc_types_to_save)

        income_doc_types_to_save = {}
        for row in range(self.income_doc_type_table.rowCount()):
            key_item = self.income_doc_type_table.item(row, 0)
            value_item = self.income_doc_type_table.item(row, 1)
            if key_item and value_item:
                income_doc_types_to_save[key_item.text()] = value_item.text()
        self.config_manager.set_section('FolderNames_Income', income_doc_types_to_save)

        other_org_doc_types_to_save = {}
        for row in range(self.other_org_doc_type_table.rowCount()):
            key_item = self.other_org_doc_type_table.item(row, 0)
            value_item = self.other_org_doc_type_table.item(row, 1)
            if key_item and value_item:
                other_org_doc_types_to_save[key_item.text()] = value_item.text()
        self.config_manager.set_section('FolderNames_OtherOrganization', other_org_doc_types_to_save)
        self.accept()

    def add_doc_type(self):
        key = self.new_doc_type_key_edit.text().strip()
        value = self.new_doc_type_value_edit.text().strip()

        if not key or not value:
            QMessageBox.warning(self, "入力エラー", "キーと表示名の両方を入力してください。")
            return

        if self.doc_type_tabs.currentIndex() == 0:
            current_table = self.expenditure_doc_type_table
        elif self.doc_type_tabs.currentIndex() == 1:
            current_table = self.income_doc_type_table
        else:  # index == 2
            current_table = self.other_org_doc_type_table

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
        if self.doc_type_tabs.currentIndex() == 0:
            current_table = self.expenditure_doc_type_table
            transaction_type_name = "支出情報"
        elif self.doc_type_tabs.currentIndex() == 1:
            current_table = self.income_doc_type_table
            transaction_type_name = "収入情報"
        else:  # index == 2
            current_table = self.other_org_doc_type_table
            transaction_type_name = "その他団体"

        selected_rows = current_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "選択なし", "削除する行を選択してください。")
            return

        selected_row_index = selected_rows[0].row()
        doc_type_value = current_table.item(selected_row_index, 1).text()

        if self.metadata_manager.has_files_for_doc_type(transaction_type_name, doc_type_value):
            QMessageBox.warning(self, "削除不可", "この書類種別に関連するファイルがフォルダ内に存在するため、削除できません。")
            return

        reply = QMessageBox.question(self, "確認", "選択した書類種別を削除しますか？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            for index in sorted(selected_rows, reverse=True):
                current_table.removeRow(index.row())

    def load_clients(self):
        """取引先データを読み込んでテーブルに表示"""
        self.client_table.setRowCount(0)
        clients = self.client_manager.get_all_clients()

        for client in clients:
            row_position = self.client_table.rowCount()
            self.client_table.insertRow(row_position)
            self.client_table.setItem(row_position, 0, QTableWidgetItem(client['name']))
            self.client_table.setItem(row_position, 1, QTableWidgetItem(client['furigana']))
            # IDを非表示データとして保存
            self.client_table.item(row_position, 0).setData(0x0100, client['id'])

    def add_or_update_client(self):
        """取引先を追加または更新"""
        name = self.new_client_name_edit.text().strip()
        furigana = self.new_client_furigana_edit.text().strip()

        if not name or not furigana:
            QMessageBox.warning(self, "入力エラー", "取引先名とフリガナの両方を入力してください。")
            return

        if self.editing_client_id:
            # 編集モード
            if self.client_manager.update_client(self.editing_client_id, name, furigana):
                QMessageBox.information(self, "成功", "取引先を更新しました。")
                self.cancel_edit()
                self.load_clients()
            else:
                # 重複チェックでエラーの場合
                if self.client_manager.is_duplicate(name, furigana, exclude_id=self.editing_client_id):
                    QMessageBox.warning(self, "重複エラー", "同じ取引先名またはフリガナが既に登録されています。")
                else:
                    QMessageBox.critical(self, "エラー", "取引先の更新に失敗しました。")
        else:
            # 追加モード
            if self.client_manager.add_client(name, furigana):
                QMessageBox.information(self, "成功", "取引先を追加しました。")
                self.new_client_name_edit.clear()
                self.new_client_furigana_edit.clear()
                self.load_clients()
            else:
                # 重複チェックでエラーの場合
                if self.client_manager.is_duplicate(name, furigana):
                    QMessageBox.warning(self, "重複エラー", "同じ取引先名またはフリガナが既に登録されています。")
                else:
                    QMessageBox.critical(self, "エラー", "取引先の追加に失敗しました。")

    def edit_client(self):
        """取引先を編集"""
        current_row = self.client_table.currentRow()
        if current_row == -1:
            QMessageBox.information(self, "選択なし", "編集する取引先を選択してください。")
            return

        # 選択されたアイテムから情報を取得
        name_item = self.client_table.item(current_row, 0)
        furigana_item = self.client_table.item(current_row, 1)

        if name_item and furigana_item:
            client_id = name_item.data(0x0100)
            current_name = name_item.text()
            current_furigana = furigana_item.text()

            # 編集モードに切り替え
            self.editing_client_id = client_id
            self.new_client_name_edit.setText(current_name)
            self.new_client_furigana_edit.setText(current_furigana)

            # ボタンの表示を変更
            self.add_client_button.setText("更新")
            self.cancel_edit_button.setVisible(True)
            self.edit_client_button.setEnabled(False)

    def cancel_edit(self):
        """編集をキャンセル"""
        self.editing_client_id = None
        self.new_client_name_edit.clear()
        self.new_client_furigana_edit.clear()

        # ボタンの表示を元に戻す
        self.add_client_button.setText("追加")
        self.cancel_edit_button.setVisible(False)
        self.edit_client_button.setEnabled(True)

    def delete_client(self):
        """取引先を削除"""
        current_row = self.client_table.currentRow()
        if current_row == -1:
            QMessageBox.information(self, "選択なし", "削除する取引先を選択してください。")
            return

        name_item = self.client_table.item(current_row, 0)
        if name_item:
            client_id = name_item.data(0x0100)
            client_name = name_item.text()

            reply = QMessageBox.question(self, "確認", f"取引先「{client_name}」を削除しますか？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                if self.client_manager.delete_client(client_id):
                    QMessageBox.information(self, "成功", "取引先を削除しました。")
                    self.load_clients()
                else:
                    QMessageBox.critical(self, "エラー", "取引先の削除に失敗しました。")

    def _apply_styles(self):
        """UIスタイルを適用"""
        # メインボタン
        apply_button_style(self.save_button)
        apply_button_style(self.cancel_button)

        # 参照ボタン
        apply_small_button_style(self.root_dir_button)
        apply_small_button_style(self.browse_tesseract_button)

        # 書類種別管理ボタン
        apply_small_button_style(self.add_doc_type_button)
        apply_small_button_style(self.delete_doc_type_button)

        # 取引先管理ボタン
        apply_small_button_style(self.add_client_button)
        apply_small_button_style(self.edit_client_button)
        apply_small_button_style(self.cancel_edit_button)
        apply_small_button_style(self.delete_client_button)

        # テーブルスタイル
        apply_table_style(self.expenditure_doc_type_table)
        apply_table_style(self.income_doc_type_table)
        apply_table_style(self.other_org_doc_type_table)
        apply_table_style(self.client_table)