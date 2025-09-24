import send2trash
import os
import sys
import subprocess
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout, QLabel,
    QComboBox, QDateEdit, QMessageBox, QSplitter, QHBoxLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QDate
from functools import partial

# Import the new dialog
from views.edit_dialog import EditDialog
from utils.validator import Validator

class FileSearchTab(QWidget):
    def __init__(self, config_manager, metadata_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.metadata_manager = metadata_manager
        self.validator = Validator()
        
        main_layout = QVBoxLayout(self)

        # スプリッターで検索条件と結果を分割
        search_splitter = QSplitter(Qt.Orientation.Vertical)

        # Search Conditions
        search_group = self._create_search_group()
        search_splitter.addWidget(search_group)

        # Search Results
        results_group = self._create_results_group()
        search_splitter.addWidget(results_group)

        # スプリッターサイズの復元
        saved_sizes = self.config_manager.get_splitter_sizes('search_splitter')
        if saved_sizes and len(saved_sizes) == 2:
            search_splitter.setSizes(saved_sizes)
        else:
            search_splitter.setSizes([200, 400])  # 検索条件:200, 結果:400

        self.search_splitter = search_splitter
        main_layout.addWidget(search_splitter)
        self.setLayout(main_layout)
        self._populate_year_combo()
        self._populate_doc_type_combo()

    def _create_search_group(self):
        """Creates the search conditions group box."""
        search_group = QGroupBox("検索条件")
        layout = QGridLayout()

        # Search fields
        self.year_combo = QComboBox()
        self.reload_year_button = QPushButton(QIcon.fromTheme("view-refresh"), "再読込")
        self.reload_year_button.clicked.connect(self._populate_year_combo)
        year_layout = QHBoxLayout()
        year_layout.addWidget(self.year_combo, 1)
        year_layout.addWidget(self.reload_year_button)

        self.doc_type_combo = QComboBox()
        self.client_name_edit = QLineEdit()
        self.date_from_edit = QDateEdit(calendarPopup=True)
        self.date_from_edit.setDate(QDate.currentDate().addYears(-1))
        self.date_to_edit = QDateEdit(calendarPopup=True)
        self.date_to_edit.setDate(QDate.currentDate())
        self.amount_from_edit = QLineEdit()
        self.amount_to_edit = QLineEdit()
        self.memo_edit = QLineEdit()

        # Connect returnPressed signal to search button click
        self.client_name_edit.returnPressed.connect(self._search_files)
        self.amount_from_edit.returnPressed.connect(self._search_files)
        self.amount_to_edit.returnPressed.connect(self._search_files)
        self.memo_edit.returnPressed.connect(self._search_files)

        # Layout setup
        form_layout = QFormLayout()
        form_layout.addRow("年:", year_layout)
        form_layout.addRow("書類種別:", self.doc_type_combo)
        form_layout.addRow("取引先名:", self.client_name_edit)
        form_layout.addRow("発行日 (From):", self.date_from_edit)
        form_layout.addRow("発行日 (To):", self.date_to_edit)
        form_layout.addRow("金額 (From):", self.amount_from_edit)
        form_layout.addRow("金額 (To):", self.amount_to_edit)
        form_layout.addRow("メモ:", self.memo_edit)
        
        layout.addLayout(form_layout, 0, 0, 1, 2)

        # Buttons
        self.search_button = QPushButton(QIcon.fromTheme("edit-find"), "検索実行")
        self.search_button.clicked.connect(self._search_files)
        self.clear_button = QPushButton(QIcon.fromTheme("edit-clear"), "クリア")
        self.clear_button.clicked.connect(self._clear_search_fields)
        
        layout.addWidget(self.search_button, 1, 0)
        layout.addWidget(self.clear_button, 1, 1)

        search_group.setLayout(layout)
        return search_group

    def _populate_year_combo(self):
        available_years = self.metadata_manager.get_available_years()
        self.year_combo.clear()
        if available_years:
            self.year_combo.addItems(available_years)
            self.year_combo.setCurrentIndex(0)
        else:
            self.year_combo.addItem("年なし")

    def _populate_doc_type_combo(self):
        self.doc_type_combo.clear()
        self.doc_type_combo.addItem("すべて")
        
        expenditure_types = self.config_manager.get_section('FolderNames_Expenditure').values()
        income_types = self.config_manager.get_section('FolderNames_Income').values()
        
        all_types = sorted(list(set(list(expenditure_types) + list(income_types))))
        
        self.doc_type_combo.addItems(all_types)

    def _create_results_group(self):
        """Creates the search results group box."""
        results_group = QGroupBox("検索結果")
        layout = QVBoxLayout()

        self.results_table = QTableWidget()
        # テーブルの最小高さを設定（約５行分）
        self.results_table.setMinimumHeight(150)
        self.results_table.setColumnCount(9)
        self.results_table.setHorizontalHeaderLabels([
            "ID", "通し番号", "発行日", "金額(税込)", "取引先名",
            "書類種別", "メモ", "", ""
        ])
        self.results_table.setColumnHidden(0, True) # Hide ID column
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # Make table read-only
        self.results_table.cellDoubleClicked.connect(self._open_pdf)
        
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.results_table.setWordWrap(True)
        
        # Adjust column widths
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.results_table)
        results_group.setLayout(layout)
        return results_group

    def _search_files(self):
        year_nendo = self.year_combo.currentText()
        if year_nendo == "年なし" or not year_nendo: # Handle case where no years are found
            QMessageBox.warning(self, "入力エラー", "検索する年を選択してください。")
            return
        # No need for isdigit() check as it comes from valid folder names
        
        # Collect search criteria
        criteria = {
            "year_nendo": year_nendo,
            "doc_type": self.doc_type_combo.currentText(),
            "client_name": self.client_name_edit.text(),
            "date_from": self.date_from_edit.date(),
            "date_to": self.date_to_edit.date(),
            "amount_from": self.amount_from_edit.text(),
            "amount_to": self.amount_to_edit.text(),
            "memo": self.memo_edit.text()
        }

        try:
            results_df = self.metadata_manager.search_entries(**criteria)
            self._populate_table(results_df)
        except Exception as e:
            QMessageBox.critical(self, "検索エラー", f"検索中にエラーが発生しました。\n{e}")

    def _populate_table(self, df):
        self.results_table.setRowCount(0)
        if df.empty:
            return

        for index, row in df.iterrows():
            row_position = self.results_table.rowCount()
            self.results_table.insertRow(row_position)

            # Populate cells
            self.results_table.setItem(row_position, 0, QTableWidgetItem(str(row.get('id', ''))))
            self.results_table.setItem(row_position, 1, QTableWidgetItem(str(row.get('doc_id', ''))))
            self.results_table.setItem(row_position, 2, QTableWidgetItem(str(row.get('issue_date', ''))))
            self.results_table.setItem(row_position, 3, QTableWidgetItem(str(row.get('amount', ''))))
            self.results_table.setItem(row_position, 4, QTableWidgetItem(str(row.get('client_name', ''))))
            self.results_table.setItem(row_position, 5, QTableWidgetItem(str(row.get('doc_type', ''))))
            self.results_table.setItem(row_position, 6, QTableWidgetItem(str(row.get('memo', ''))))

            # Add buttons
            record_id = row.get('id')
            edit_btn = QPushButton(QIcon.fromTheme("document-edit"), "編集")
            edit_btn.clicked.connect(partial(self._edit_row, record_id))
            self.results_table.setCellWidget(row_position, 7, edit_btn)

            delete_btn = QPushButton(QIcon.fromTheme("edit-delete"), "削除")
            delete_btn.clicked.connect(partial(self._delete_row, record_id))
            self.results_table.setCellWidget(row_position, 8, delete_btn)

    def _open_pdf(self, row, column):
        record_id_item = self.results_table.item(row, 0)
        if not record_id_item:
            return
        
        record_id = record_id_item.text()
        year_nendo = self.year_combo.currentText()

        record = self.metadata_manager.get_entry_by_id(year_nendo, record_id)
        if not record:
            QMessageBox.warning(self, "エラー", "選択されたレコードが見つかりませんでした。")
            return

        relative_path = record.get('file_path')
        if not relative_path:
            QMessageBox.warning(self, "エラー", "ファイルパスが記録されていません。")
            return

        pdf_path = os.path.join(self.metadata_manager.root_path, year_nendo, relative_path)
        pdf_path = os.path.normpath(pdf_path)

        if not os.path.exists(pdf_path):
            QMessageBox.warning(self, "ファイルエラー", f"ファイルが見つかりません。\n{pdf_path}")
            return

        try:
            if sys.platform == "win32":
                os.startfile(pdf_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", pdf_path])
            else:
                subprocess.run(["xdg-open", pdf_path])
        except Exception as e:
            QMessageBox.critical(self, "起動エラー", f"ファイルを開けませんでした。\n{e}")

    def _edit_row(self, record_id):
        if not record_id:
            return

        year_nendo = self.year_combo.currentText()
        if not year_nendo or year_nendo == "年なし":
            QMessageBox.warning(self, "エラー", "編集操作を行う前に、有効な年を検索してください。")
            return

        # Get current data
        current_data = self.metadata_manager.get_entry_by_id(year_nendo, record_id)
        if not current_data:
            QMessageBox.warning(self, "エラー", "編集対象のレコードが見つかりませんでした。")
            return

        # Open dialog
        dialog = EditDialog(current_data, self)
        if dialog.exec():
            new_data = dialog.get_updated_data()
            
            # Validation
            if not self.validator.is_valid_date(new_data['issue_date']):
                QMessageBox.warning(self, "入力エラー", "発行日の形式が正しくありません。(YYYYMMDD)")
                return
            
            is_valid_amount, amount_val = self.validator.is_valid_amount(new_data['amount'])
            if not is_valid_amount:
                QMessageBox.warning(self, "入力エラー", "金額の形式が正しくありません。")
                return
            new_data['amount'] = amount_val # Use the normalized integer value

            # Update data
            try:
                success = self.metadata_manager.update_entry(year_nendo, record_id, new_data)
                if success:
                    QMessageBox.information(self, "成功", "レコードを更新しました。")
                    self._search_files() # Refresh table
                else:
                    QMessageBox.warning(self, "エラー", "レコードの更新に失敗しました。")
            except Exception as e:
                QMessageBox.critical(self, "更新エラー", f"更新中にエラーが発生しました。\n{e}")

    def _delete_row(self, record_id):
        if not record_id:
            return

        year_nendo = self.year_combo.currentText()
        if not year_nendo or year_nendo == "年なし":
            QMessageBox.warning(self, "エラー", "削除操作を行う前に、有効な年を検索してください。")
            return

        reply = QMessageBox.question(self, '削除確認',
                                     f"ID: {record_id} のレコードと関連するPDFファイルを完全に削除しますか？\nこの操作は元に戻せません。",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                relative_path = self.metadata_manager.delete_entry(year_nendo, record_id)

                if relative_path:
                    pdf_path = os.path.join(self.metadata_manager.root_path, year_nendo, relative_path)
                    pdf_path = os.path.normpath(pdf_path)
                    if os.path.exists(pdf_path):
                        send2trash.send2trash(pdf_path)
                        QMessageBox.information(self, "成功", f"レコードとファイルをゴミ箱に移動しました。\n{pdf_path}")
                    else:
                        QMessageBox.warning(self, "ファイルエラー", f"ファイルが見つかりませんでした（レコードは削除済み）。\n{pdf_path}")
                else:
                     QMessageBox.information(self, "成功", "レコードを削除しました。（ファイルパス情報なし）")

                self._search_files()

            except Exception as e:
                QMessageBox.critical(self, "削除エラー", f"削除中にエラーが発生しました。\n{e}")

    def _clear_search_fields(self):
        self.year_combo.setCurrentIndex(0)
        self.doc_type_combo.setCurrentIndex(0)
        self.client_name_edit.clear()
        self.date_from_edit.setDate(QDate.currentDate().addYears(-1))
        self.date_to_edit.setDate(QDate.currentDate())
        self.amount_from_edit.clear()
        self.amount_to_edit.clear()
        self.memo_edit.clear()
        self.results_table.setRowCount(0)

    def refresh_data(self):
        """Public method to allow refreshing the data in the combo boxes."""
        self._populate_year_combo()
        self._populate_doc_type_combo()

    def save_splitter_sizes(self):
        """Save splitter sizes to configuration."""
        if hasattr(self, 'search_splitter'):
            sizes = self.search_splitter.sizes()
            self.config_manager.set_splitter_sizes('search_splitter', sizes)