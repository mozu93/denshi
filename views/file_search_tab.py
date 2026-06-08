import send2trash
import os
import sys
import subprocess
import logging
import math
import traceback
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout, QLabel,
    QComboBox, QDateEdit, QMessageBox, QSplitter, QHBoxLayout
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QIcon
from functools import partial

from views.edit_dialog import EditDialog
from utils.validator import Validator
from utils.ui_styles import apply_button_style, apply_table_style
from utils.constants import (
    CATEGORY_EXPENDITURE, CATEGORY_INCOME, CATEGORY_OTHER_ORG,
    DATE_UNSPECIFIED_YEAR
)

logger = logging.getLogger(__name__)

class FileSearchTab(QWidget):
    def __init__(self, config_manager, metadata_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.metadata_manager = metadata_manager
        self.validator = Validator()

        main_layout = QVBoxLayout(self)

        # スプリッターで検索条件（左）と結果（右）を横並びに分割
        search_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Search Conditions（左）
        search_group = self._create_search_group()
        search_splitter.addWidget(search_group)

        # Search Results（右）
        results_group = self._create_results_group()
        search_splitter.addWidget(results_group)

        # スプリッターサイズの復元
        saved_sizes = self.config_manager.get_splitter_sizes('search_splitter')
        if saved_sizes and len(saved_sizes) == 2:
            search_splitter.setSizes(saved_sizes)
        else:
            search_splitter.setSizes([400, 800])  # 検索条件:1/3, 結果:2/3

        self.search_splitter = search_splitter
        main_layout.addWidget(search_splitter)
        self.setLayout(main_layout)
        self._populate_year_combo()
        self._populate_doc_type_combo()

    def _create_search_group(self):
        """Creates the search conditions group box."""
        search_group = QGroupBox("検索条件")

        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.setSpacing(5)

        # 検索条件フォームのウィジェット（左カラム全体を使用）
        form_widget = QWidget()
        layout = QVBoxLayout(form_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Search fields
        self.year_combo = QComboBox()
        self.year_combo.currentTextChanged.connect(self._on_year_changed)
        self.reload_year_button = QPushButton(QIcon.fromTheme("view-refresh"), "再読込")
        self.reload_year_button.clicked.connect(self._populate_year_combo)
        apply_button_style(self.reload_year_button)
        year_layout = QHBoxLayout()
        year_layout.addWidget(self.year_combo, 1)
        year_layout.addWidget(self.reload_year_button)

        # 取引区分
        self.transaction_category_combo = QComboBox()
        self.transaction_category_combo.addItem("すべて")
        self.transaction_category_combo.addItem(CATEGORY_EXPENDITURE)
        self.transaction_category_combo.addItem(CATEGORY_INCOME)
        self.transaction_category_combo.addItem(CATEGORY_OTHER_ORG)
        self.transaction_category_combo.currentTextChanged.connect(self._on_transaction_category_changed)

        self.doc_type_combo = QComboBox()

        # その他団体のサブフォルダ選択
        self.other_org_subfolder_combo = QComboBox()
        self.other_org_subfolder_combo.setVisible(False)  # 初期は非表示
        self.client_name_edit = QLineEdit()
        self.date_from_edit = QDateEdit(calendarPopup=True)
        self.date_from_edit.setSpecialValueText("指定なし")  # 空欄表示用
        self.date_from_edit.setMinimumDate(QDate(DATE_UNSPECIFIED_YEAR, 1, 1))
        self.date_from_edit.setDate(QDate(DATE_UNSPECIFIED_YEAR, 1, 1))
        self.date_from_edit.dateChanged.connect(self._on_from_date_changed)

        self.date_to_edit = QDateEdit(calendarPopup=True)
        self.date_to_edit.setSpecialValueText("指定なし")  # 空欄表示用
        self.date_to_edit.setMinimumDate(QDate(DATE_UNSPECIFIED_YEAR, 1, 1))
        self.date_to_edit.setDate(QDate(DATE_UNSPECIFIED_YEAR, 1, 1))
        self.amount_from_edit = QLineEdit()
        self.amount_to_edit = QLineEdit()
        self.memo_edit = QLineEdit()

        # Connect returnPressed signal to search button click
        self.client_name_edit.returnPressed.connect(self._search_files)
        self.amount_from_edit.returnPressed.connect(self._search_files)
        self.amount_to_edit.returnPressed.connect(self._search_files)
        self.memo_edit.returnPressed.connect(self._search_files)

        # 発行日のFromとToを同じ行に配置
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("From:"))
        date_layout.addWidget(self.date_from_edit)
        date_layout.addWidget(QLabel("To:"))
        date_layout.addWidget(self.date_to_edit)

        # 金額のFromとToを同じ行に配置
        amount_layout = QHBoxLayout()
        amount_layout.addWidget(QLabel("From:"))
        amount_layout.addWidget(self.amount_from_edit)
        amount_layout.addWidget(QLabel("To:"))
        amount_layout.addWidget(self.amount_to_edit)

        # Layout setup - FormLayoutでコンパクトに配置
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(8)  # 行間を狭くする
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.addRow("年:", year_layout)
        form_layout.addRow("取引区分:", self.transaction_category_combo)
        form_layout.addRow("書類種別:", self.doc_type_combo)
        form_layout.addRow("サブフォルダ:", self.other_org_subfolder_combo)
        form_layout.addRow("取引先名:", self.client_name_edit)
        form_layout.addRow("発行日:", date_layout)
        form_layout.addRow("金額:", amount_layout)
        form_layout.addRow("メモ:", self.memo_edit)

        layout.addLayout(form_layout)

        # Buttonsをメモの直下に配置（スペースを完全に削除）
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)  # 全てのマージンを削除

        self.search_button = QPushButton(QIcon.fromTheme("edit-find"), "検索実行")
        self.search_button.clicked.connect(self._search_files)
        apply_button_style(self.search_button)

        self.clear_button = QPushButton(QIcon.fromTheme("edit-clear"), "クリア")
        self.clear_button.clicked.connect(self._clear_search_fields)
        apply_button_style(self.clear_button)

        button_layout.addWidget(self.search_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()  # 右側にスペースを追加

        layout.addLayout(button_layout)

        container_layout.addWidget(form_widget)
        container_layout.addStretch()

        search_group.setLayout(container_layout)
        return search_group

    def _populate_year_combo(self):
        available_years = self.metadata_manager.get_available_years()
        self.year_combo.clear()
        if available_years:
            self.year_combo.addItems(available_years)
            self.year_combo.setCurrentIndex(0)
            # 初期選択年に基づいて日付フィールドを更新
            if len(available_years) > 0:
                self._on_year_changed(available_years[0])
        else:
            self.year_combo.addItem("年なし")
            self._reset_date_fields()

    def _populate_doc_type_combo(self):
        """取引区分に基づいて書類種別を更新"""
        self.doc_type_combo.clear()
        self.doc_type_combo.addItem("すべて")

        transaction_category = self.transaction_category_combo.currentText()

        if transaction_category == "すべて":
            expenditure_types = self.config_manager.get_section('FolderNames_Expenditure').values()
            income_types = self.config_manager.get_section('FolderNames_Income').values()
            all_types = sorted(list(set(list(expenditure_types) + list(income_types))))
            self.doc_type_combo.addItems(all_types)
        elif transaction_category == CATEGORY_EXPENDITURE:
            expenditure_types = self.config_manager.get_section('FolderNames_Expenditure').values()
            self.doc_type_combo.addItems(sorted(list(expenditure_types)))
        elif transaction_category == CATEGORY_INCOME:
            income_types = self.config_manager.get_section('FolderNames_Income').values()
            self.doc_type_combo.addItems(sorted(list(income_types)))
        elif transaction_category == CATEGORY_OTHER_ORG:
            # その他団体の場合は書類種別は表示しない
            self.doc_type_combo.setVisible(False)

    def _populate_other_org_subfolder_combo(self):
        """その他団体のサブフォルダを読み込む"""
        self.other_org_subfolder_combo.clear()
        self.other_org_subfolder_combo.addItem("すべて")

        other_org_section = self.config_manager.get_section('FolderNames_OtherOrganization')
        if other_org_section:
            subfolders = sorted(list(other_org_section.values()))
            self.other_org_subfolder_combo.addItems(subfolders)

    def _on_transaction_category_changed(self, category):
        """取引区分が変更された時の処理"""
        if category == CATEGORY_OTHER_ORG:
            # その他団体の場合、書類種別を非表示にしてサブフォルダを表示
            self.doc_type_combo.setVisible(False)
            self.other_org_subfolder_combo.setVisible(True)
            self._populate_other_org_subfolder_combo()
        else:
            # それ以外の場合、書類種別を表示してサブフォルダを非表示
            self.doc_type_combo.setVisible(True)
            self.other_org_subfolder_combo.setVisible(False)
            self._populate_doc_type_combo()

    def _create_results_group(self):
        """Creates the search results group box."""
        results_group = QGroupBox("検索結果")
        layout = QVBoxLayout()

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(9)
        self.results_table.setHorizontalHeaderLabels([
            "ID", "通し番号", "発行日", "金額(税込)", "取引先名",
            "取引区分", "書類種別", "メモ", ""
        ])
        self.results_table.setColumnHidden(0, True) # Hide ID column
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # Make table read-only
        self.results_table.cellDoubleClicked.connect(self._open_pdf)

        self.results_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.results_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        apply_table_style(self.results_table)

        # 行の高さを2倍に設定
        self.results_table.verticalHeader().setDefaultSectionSize(60)

        header = self.results_table.horizontalHeader()

        # データ列（1〜7）はインタラクティブ（ユーザーが手動リサイズ可能）
        # データ読み込み後に resizeColumnsToContents() でコンテンツに合わせて自動調整する
        for col in range(1, 8):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)

        # 編集ボタン列は常にボタン幅に合わせる
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)

        self.results_table.setWordWrap(True)

        layout.addWidget(self.results_table)
        results_group.setLayout(layout)
        return results_group

    def _search_files(self):
        logger.debug("検索ボタンがクリックされました")
        year_nendo = self.year_combo.currentText()
        logger.debug(f"選択された年: {year_nendo}")

        if year_nendo == "年なし" or not year_nendo:
            logger.debug("年が選択されていない")
            QMessageBox.warning(self, "入力エラー", "検索する年を選択してください。")
            return

        # Collect search criteria
        # 最小日付（1900/1/1）または年の1月1日の場合は検索条件に含めない
        year = int(year_nendo.replace("年", "")) if year_nendo and year_nendo != "年なし" else None
        current_from_date = self.date_from_edit.date()
        current_to_date = self.date_to_edit.date()

        # 年の1月1日かどうかをチェック
        is_year_start_from = (year and current_from_date == QDate(year, 1, 1))
        is_year_start_to = (year and current_to_date == QDate(year, 1, 1))

        # 最小日付または年の1月1日の場合は条件に含めない
        date_from = None if (current_from_date <= QDate(DATE_UNSPECIFIED_YEAR, 1, 1) or is_year_start_from) else current_from_date
        date_to = None if (current_to_date <= QDate(DATE_UNSPECIFIED_YEAR, 1, 1) or is_year_start_to) else current_to_date

        # 取引区分とサブフォルダの処理
        transaction_category = self.transaction_category_combo.currentText()
        doc_type = None
        other_org_subfolder = None

        if transaction_category == CATEGORY_OTHER_ORG:
            # その他団体の場合はサブフォルダを検索条件に追加
            subfolder = self.other_org_subfolder_combo.currentText()
            if subfolder and subfolder != "すべて":
                other_org_subfolder = subfolder
        else:
            # それ以外は書類種別を使用
            doc_type = self.doc_type_combo.currentText()

        criteria = {
            "year_nendo": year_nendo,
            "transaction_category": transaction_category if transaction_category != "すべて" else None,
            "doc_type": doc_type,
            "other_org_subfolder": other_org_subfolder,
            "client_name": self.client_name_edit.text(),
            "date_from": date_from,
            "date_to": date_to,
            "amount_from": self.amount_from_edit.text(),
            "amount_to": self.amount_to_edit.text(),
            "memo": self.memo_edit.text()
        }

        logger.debug(f"検索条件: {criteria}")

        try:
            logger.debug("metadata_manager.search_entries を呼び出し中...")
            results_df = self.metadata_manager.search_entries(**criteria)
            logger.debug(f"検索結果: {len(results_df)} 件")
            self._populate_table(results_df)
            logger.debug("テーブルに結果を表示完了")

            # ステータスバーに結果件数を表示
            parent = self.window()
            if hasattr(parent, 'status_bar'):
                parent.status_bar.showMessage(f"検索完了: {len(results_df)} 件")

        except Exception as e:
            logger.debug(f"検索エラー: {e}")
            logger.debug(traceback.format_exc())
            QMessageBox.critical(self, "検索エラー", f"検索中にエラーが発生しました。\n{e}")

    @staticmethod
    def _fmt_num(val):
        """float(例: 10800.0)を整数文字列に変換。NaN/None は空文字列。"""
        if val is None:
            return ''
        if isinstance(val, float):
            return '' if math.isnan(val) else str(int(val))
        return str(val)

    @staticmethod
    def _fmt_str(val):
        """NaN/None を空文字列に変換する。"""
        if val is None:
            return ''
        if isinstance(val, float) and math.isnan(val):
            return ''
        return str(val)

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
            self.results_table.setItem(row_position, 2, QTableWidgetItem(self._fmt_num(row.get('issue_date'))))
            self.results_table.setItem(row_position, 3, QTableWidgetItem(self._fmt_num(row.get('amount'))))
            self.results_table.setItem(row_position, 4, QTableWidgetItem(self._fmt_str(row.get('client_name'))))
            self.results_table.setItem(row_position, 5, QTableWidgetItem(self._fmt_str(row.get('category'))))
            self.results_table.setItem(row_position, 6, QTableWidgetItem(self._fmt_str(row.get('doc_type'))))
            self.results_table.setItem(row_position, 7, QTableWidgetItem(self._fmt_str(row.get('memo'))))

            # Add buttons
            record_id = row.get('id')
            edit_btn = QPushButton(QIcon.fromTheme("document-edit"), "編集")
            edit_btn.clicked.connect(partial(self._edit_row, record_id))
            apply_button_style(edit_btn)
            self.results_table.setCellWidget(row_position, 8, edit_btn)

        # データ内容に応じて列幅を自動調整（列1〜7）
        for col in range(1, 8):
            self.results_table.resizeColumnToContents(col)

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
        try:
            current_data = self.metadata_manager.get_entry_by_id(year_nendo, record_id)
            if not current_data:
                QMessageBox.warning(self, "エラー", "編集対象のレコードが見つかりませんでした。")
                return
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"レコード取得に失敗しました。\n{e}")
            return

        # Open dialog
        try:
            dialog = EditDialog(current_data, year_nendo, self.config_manager, self.metadata_manager, self)
        except ValueError as e:
            QMessageBox.critical(self, "エラー", f"編集ダイアログの初期化に失敗しました。\n{e}")
            return
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"予期しないエラーが発生しました。\n{e}")
            return

        if dialog.exec():
            new_data = dialog.get_updated_data()

            # 移動かどうか判定
            is_location_changed = (
                new_data['destination_year'] != year_nendo or
                new_data['destination_category'] != current_data.get('category') or
                new_data['destination_doc_type'] != current_data.get('doc_type')
            )

            # Validation
            if not self.validator.is_valid_date(new_data['issue_date']):
                QMessageBox.warning(self, "入力エラー", "発行日の形式が正しくありません。(YYYYMMDD)")
                return

            is_valid_amount, amount_val = self.validator.is_valid_amount(new_data['amount'])
            if not is_valid_amount:
                QMessageBox.warning(self, "入力エラー", "金額の形式が正しくありません。")
                return
            new_data['amount'] = amount_val

            # Update data
            try:
                self.metadata_manager.update_entry(year_nendo, record_id, new_data)
                if is_location_changed:
                    try:
                        self.metadata_manager.rebuild_index()
                    except Exception as rebuild_e:
                        logger.warning(f"インデックス再構築に失敗しました: {rebuild_e}")
                    QMessageBox.information(self, "成功", "ファイルを移動し、インデックスを再構築しました。")
                else:
                    QMessageBox.information(self, "成功", "レコードを更新しました。")
                self._search_files()
            except RuntimeError as e:
                QMessageBox.critical(self, "更新エラー", str(e))
            except Exception as e:
                QMessageBox.critical(self, "更新エラー", f"予期しないエラーが発生しました。\n{e}")

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
        self.transaction_category_combo.setCurrentIndex(0)
        self.doc_type_combo.setCurrentIndex(0)
        self.other_org_subfolder_combo.setCurrentIndex(0)
        self.client_name_edit.clear()
        self.date_from_edit.setDate(QDate(DATE_UNSPECIFIED_YEAR, 1, 1))
        self.date_to_edit.setDate(QDate(DATE_UNSPECIFIED_YEAR, 1, 1))
        self.amount_from_edit.clear()
        self.amount_to_edit.clear()
        self.memo_edit.clear()
        self.results_table.setRowCount(0)

    def _on_year_changed(self, year_text):
        """年が変更された時に日付フィールドを更新"""
        if year_text and year_text != "年なし":
            try:
                year = int(year_text.replace("年", ""))
                # From日付を年の1月1日に設定
                from_date = QDate(year, 1, 1)
                self.date_from_edit.setDate(from_date)

                # To日付も年の1月1日に設定（後でFrom日付変更イベントで調整される）
                self.date_to_edit.setDate(from_date)

                # カレンダーの表示年を設定
                self.date_from_edit.setMinimumDate(QDate(year, 1, 1))
                self.date_from_edit.setMaximumDate(QDate(year, 12, 31))
                self.date_to_edit.setMinimumDate(QDate(year, 1, 1))
                self.date_to_edit.setMaximumDate(QDate(year, 12, 31))

            except ValueError:
                # 年の解析に失敗した場合は「指定なし」に戻す
                self._reset_date_fields()
        else:
            self._reset_date_fields()

    def _on_from_date_changed(self, date):
        """From日付が変更された時にTo日付を更新"""
        if date > QDate(DATE_UNSPECIFIED_YEAR, 1, 1):  # 「指定なし」でない場合
            # To日付をFrom日付以降に設定（同じ日付から開始）
            if self.date_to_edit.date() < date:
                self.date_to_edit.setDate(date)
            # To日付の最小値をFrom日付に設定
            self.date_to_edit.setMinimumDate(date)

    def _reset_date_fields(self):
        """日付フィールドを初期状態にリセット"""
        self.date_from_edit.setMinimumDate(QDate(DATE_UNSPECIFIED_YEAR, 1, 1))
        self.date_from_edit.setMaximumDate(QDate(2100, 12, 31))
        self.date_from_edit.setDate(QDate(DATE_UNSPECIFIED_YEAR, 1, 1))

        self.date_to_edit.setMinimumDate(QDate(DATE_UNSPECIFIED_YEAR, 1, 1))
        self.date_to_edit.setMaximumDate(QDate(2100, 12, 31))
        self.date_to_edit.setDate(QDate(DATE_UNSPECIFIED_YEAR, 1, 1))

    def refresh_data(self):
        """Public method to allow refreshing the data in the combo boxes."""
        self._populate_year_combo()
        self._populate_doc_type_combo()

    def save_splitter_sizes(self):
        """Save splitter sizes to configuration."""
        if hasattr(self, 'search_splitter'):
            sizes = self.search_splitter.sizes()
            self.config_manager.set_splitter_sizes('search_splitter', sizes)
