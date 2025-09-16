import os
import shutil
import io
from functools import partial
import re

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QListWidget, QLabel, QLineEdit, QFormLayout,
    QPushButton, QVBoxLayout, QGroupBox, QRadioButton, QComboBox, QTextEdit,
    QSplitter, QMessageBox, QFileDialog, QScrollArea, QToolBar, QApplication
)
from PyQt6.QtGui import QPixmap, QImage, QColor, QPainter, QPen, QAction, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QBuffer, QIODevice, QPoint, QRect, QSize
from PIL import Image, ImageQt # Import ImageQt

from models.pdf_processor import PdfProcessor
from models.ocr_processor import OcrProcessor
from utils.date_converter import DateConverter
from utils.validator import Validator

from PyQt6.QtWidgets import QFileDialog



class SelectablePdfPreviewLabel(QLabel):
    """A QLabel that allows drawing a selection rectangle and emits a signal with the selected region."""
    selection_changed = pyqtSignal(QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True) # Enable mouse tracking even when no button is pressed
        self.selecting_region = False
        self.selection_start_point = QPoint()
        self.selection_end_point = QPoint()
        self.current_pixmap = None

    def setPixmap(self, pixmap):
        super().setPixmap(pixmap)
        self.current_pixmap = pixmap
        self.update() # Redraw to clear any old selection

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selecting_region = True
            self.selection_start_point = event.pos()
            self.selection_end_point = event.pos()
            self.update() # Start drawing selection
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.selecting_region:
            self.selection_end_point = event.pos()
            self.update() # Redraw selection rectangle
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.selecting_region:
            self.selecting_region = False
            selection_rect = QRect(self.selection_start_point, self.selection_end_point).normalized()
            self.selection_changed.emit(selection_rect)
            self.update() # Final redraw
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.selecting_region or (self.selection_start_point != self.selection_end_point and not self.selecting_region):
            painter = QPainter(self)
            painter.setPen(QPen(Qt.GlobalColor.red, 2, Qt.PenStyle.DotLine))
            selection_rect = QRect(self.selection_start_point, self.selection_end_point).normalized()
            painter.drawRect(selection_rect)

class FileRegistrationTab(QWidget):
    def __init__(self, config_manager, metadata_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.metadata_manager = metadata_manager
        self.active_field = None
        self.overlay_labels = []
        self.pixmap_display_scale_factor = 1.0
        self.ocr_scale_factor = 4
        self.zoom_level = 1.0
        self.date_converter = DateConverter()
        self.validator = Validator()

        self._create_widgets()
        self._setup_layout()
        self._connect_signals()
        self._load_initial_state()

    def _play_warning_sound(self):
        """システム警告音を再生"""
        try:
            # Windowsのシステム警告音を再生
            QApplication.beep()
            # 追加でプラットフォーム固有の音も試行
            import platform
            if platform.system() == 'Windows':
                try:
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                except ImportError:
                    pass
        except Exception as e:
            print(f"DEBUG: 警告音再生エラー: {e}")

    def _play_error_sound(self):
        """システムエラー音を再生"""
        try:
            # Windowsのシステムエラー音を再生
            QApplication.beep()
            import platform
            if platform.system() == 'Windows':
                try:
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONERROR)
                except ImportError:
                    pass
        except Exception as e:
            print(f"DEBUG: エラー音再生エラー: {e}")

    def _create_widgets(self):
        """Create all the widgets for the tab."""
        self.file_list_widget = QListWidget()
        # ファイルリストの最小サイズを設定
        self.file_list_widget.setMinimumHeight(120)  # 約5行分の高さ
        
        # Toolbar widgets
        self.toolbar = QToolBar()
        self.zoom_in_action = QAction(QIcon.fromTheme("zoom-in"), "Zoom In", self)
        self.zoom_out_action = QAction(QIcon.fromTheme("zoom-out"), "Zoom Out", self)
        self.reset_zoom_action = QAction(QIcon.fromTheme("zoom-original"), "Reset Zoom", self)

        # PDF Preview widgets
        self.scroll_area = QScrollArea()
        self.pdf_preview_label = SelectablePdfPreviewLabel()

        # Data input widgets
        self.ocr_instruction_label = QLabel("入力したい項目を選択後、右のPDF上で範囲をドラッグしてOCRで読み取れます。")
        self.year_edit = QLineEdit()
        self.transaction_type_expenditure_radio = QRadioButton("支出情報")
        self.transaction_type_income_radio = QRadioButton("収入情報")
        self.document_type_combo = QComboBox()
        self.doc_id_label = QLabel("(自動採番)")
        self.issue_date_edit = QLineEdit()
        self.client_name_edit = QLineEdit()
        self.amount_edit = QLineEdit()
        self.memo_edit = QTextEdit()
        self.filename_preview_label = QLabel("(ファイル名プレビュー)")
        self.save_button = QPushButton("保存して次へ")

    def _setup_layout(self):
        """Set up the layout of the tab."""
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setLayout(QHBoxLayout()) # Set a dummy layout to be replaced
        self.layout().addWidget(main_splitter)

        # --- Left Column ---
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        file_list_group = QGroupBox("登録ファイル")
        file_list_layout = QVBoxLayout()
        file_list_layout.addWidget(self.file_list_widget)
        file_list_group.setLayout(file_list_layout)
        left_splitter.addWidget(file_list_group)

        data_input_group = QGroupBox("データ入力")
        form_layout = QFormLayout()
        self.ocr_instruction_label.setWordWrap(True)
        form_layout.addRow(self.ocr_instruction_label)
        transaction_radio_layout = QHBoxLayout()
        transaction_radio_layout.addWidget(self.transaction_type_expenditure_radio)
        transaction_radio_layout.addWidget(self.transaction_type_income_radio)
        form_layout.addRow("年度:", self.year_edit)
        form_layout.addRow("取引区分:", transaction_radio_layout)
        form_layout.addRow("書類種別:", self.document_type_combo)
        form_layout.addRow("通し番号:", self.doc_id_label)
        form_layout.addRow("発行日:", self.issue_date_edit)
        form_layout.addRow("取引先名:", self.client_name_edit)
        form_layout.addRow("金額(税込):", self.amount_edit)
        form_layout.addRow("メモ:", self.memo_edit)
        form_layout.addRow("ファイル名:", self.filename_preview_label)
        form_layout.addRow(self.save_button)
        data_input_group.setLayout(form_layout)
        left_splitter.addWidget(data_input_group)

        # スプリッターサイズの復元
        saved_left_sizes = self.config_manager.get_splitter_sizes('left_splitter')
        if saved_left_sizes and len(saved_left_sizes) == 2:
            left_splitter.setSizes(saved_left_sizes)
        else:
            left_splitter.setSizes([150, 400])  # ファイルリストの最小サイズを150に増加

        # スプリッターの参照を保存
        self.left_splitter = left_splitter

        # --- Right Column ---
        right_column_widget = QWidget()
        right_column_layout = QVBoxLayout(right_column_widget)
        self.toolbar.addAction(self.zoom_in_action)
        self.toolbar.addAction(self.zoom_out_action)
        self.toolbar.addAction(self.reset_zoom_action)
        right_column_layout.addWidget(self.toolbar)

        pdf_preview_group = QGroupBox("PDFプレビュー")
        pdf_preview_layout = QVBoxLayout()
        self.scroll_area.setWidgetResizable(True)
        self.pdf_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.pdf_preview_label)
        pdf_preview_layout.addWidget(self.scroll_area)
        pdf_preview_group.setLayout(pdf_preview_layout)
        right_column_layout.addWidget(pdf_preview_group)

        # Add columns to main splitter
        main_splitter.addWidget(left_splitter)
        main_splitter.addWidget(right_column_widget)

        # メインスプリッターサイズの復元
        saved_main_sizes = self.config_manager.get_splitter_sizes('main_splitter')
        if saved_main_sizes and len(saved_main_sizes) == 2:
            main_splitter.setSizes(saved_main_sizes)
        else:
            main_splitter.setSizes([400, 800])  # 左パネルを少し大きく

        # スプリッターの参照を保存
        self.main_splitter = main_splitter

    def _connect_signals(self):
        """Connect all signals to slots."""
        self.file_list_widget.currentItemChanged.connect(self.on_file_selection_changed)
        self.pdf_preview_label.selection_changed.connect(self.on_region_selected)
        self.save_button.clicked.connect(self.save_and_next)

        # Zoom actions
        self.zoom_in_action.triggered.connect(self.zoom_in)
        self.zoom_out_action.triggered.connect(self.zoom_out)
        self.reset_zoom_action.triggered.connect(self.reset_zoom)

        # Focus events for active field highlighting
        self.year_edit.installEventFilter(self)
        self.issue_date_edit.installEventFilter(self)
        self.client_name_edit.installEventFilter(self)
        self.amount_edit.installEventFilter(self)

        # Automatic updates
        self.year_edit.textChanged.connect(self.check_save_button_state)
        self.issue_date_edit.textChanged.connect(self.check_save_button_state)
        self.client_name_edit.textChanged.connect(self.check_save_button_state)
        self.amount_edit.textChanged.connect(self.check_save_button_state)
        self.year_edit.textChanged.connect(self.update_doc_id)
        self.document_type_combo.currentIndexChanged.connect(self.update_doc_id)
        self.issue_date_edit.textChanged.connect(self.update_filename_preview)
        self.client_name_edit.textChanged.connect(self.update_filename_preview)
        self.amount_edit.textChanged.connect(self.update_filename_preview)
        self.transaction_type_expenditure_radio.toggled.connect(self.update_document_types)
        self.transaction_type_expenditure_radio.toggled.connect(self.update_doc_id)

    def _load_initial_state(self):
        """Load last used inputs and set initial UI state."""
        self.transaction_type_expenditure_radio.setChecked(True)
        self.update_document_types()

        last_year = self.config_manager.get_last_input('year')
        if last_year:
            self.year_edit.setText(last_year)
        
        last_doc_type_index = self.config_manager.get_last_input('doc_type_index')
        if last_doc_type_index is not None:
            try:
                self.document_type_combo.setCurrentIndex(int(last_doc_type_index))
            except ValueError:
                pass

        self.check_save_button_state()
        self.update_doc_id()

    def open_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "PDFファイルを選択", "", "PDF Files (*.pdf)")
        if files:
            for file in files:
                self.add_file_to_list(file)

        # Removed: self.pdf_preview_label.selection_changed.connect(self.on_region_selected)

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.FocusIn:
            if source in [self.year_edit, self.issue_date_edit, self.client_name_edit, self.amount_edit]:
                self.set_active_field(source)
        return super().eventFilter(source, event)

    def set_active_field(self, field):
        for f in [self.year_edit, self.issue_date_edit, self.client_name_edit, self.amount_edit]:
            f.setStyleSheet("")
        field.setStyleSheet("background-color: #e0e0ff;")
        self.active_field = field

    def add_file_to_list(self, file_path):
        # Prevent duplicate file registration
        for i in range(self.file_list_widget.count()):
            if self.file_list_widget.item(i).text() == file_path:
                self._play_warning_sound()
                QMessageBox.warning(self, "警告", "このファイルは既にリストに追加されています。")
                return

        was_empty = self.file_list_widget.count() == 0 # Check if list is empty before adding

        self.file_list_widget.addItem(file_path)

        if was_empty: # If it was empty, the newly added item is the first
            self.file_list_widget.setCurrentRow(0) # Select the first item

    def clear_overlays(self):
        for label in self.overlay_labels:
            label.deleteLater()
        self.overlay_labels.clear()

    def on_file_selection_changed(self, current, previous):
        """Handle file selection changes - update both PDF preview and document ID."""
        self.display_pdf_preview(current, previous)
        self.update_doc_id()

    def display_pdf_preview(self, current, previous):
        self.clear_overlays()
        if current is None or ("[処理済]" in current.text() and current.foreground() == QColor('gray')):
            self.pdf_preview_label.clear()
            self.pdf_preview_label.setText("ここにPDFのプレビューが表示されます")
            return
        
        file_path = current.text()
        pdf_processor = PdfProcessor(file_path)
        if not pdf_processor.open():
            self.pdf_preview_label.setText("PDFを開けませんでした")
            return

        fitz_pixmap_high_res = pdf_processor.get_page_as_pixmap(0, scale_factor=self.ocr_scale_factor)
        
        fitz_pixmap_display = pdf_processor.get_page_as_pixmap(0, scale_factor=self.zoom_level) # Get display resolution
        pdf_processor.close() # Close after getting both pixmaps

        if not fitz_pixmap_high_res or not fitz_pixmap_display:
            self.pdf_preview_label.setText("プレビューの生成に失敗しました")
            return

        qimage_high_res = QImage(fitz_pixmap_high_res.samples, fitz_pixmap_high_res.width, fitz_pixmap_high_res.height, fitz_pixmap_high_res.stride, QImage.Format.Format_RGB888)
        pil_image_high_res = ImageQt.fromqimage(qimage_high_res) # Use ImageQt.fromqimage

        qimage_display = QImage(fitz_pixmap_display.samples, fitz_pixmap_display.width, fitz_pixmap_display.height, fitz_pixmap_display.stride, QImage.Format.Format_RGB888)
        original_display_pixmap = QPixmap.fromImage(qimage_display)

        self.pdf_preview_label.setPixmap(original_display_pixmap)

        self.pixmap_display_scale_factor = original_display_pixmap.width() / fitz_pixmap_high_res.width

        

    def zoom_in(self):
        self.zoom_level *= 1.2
        self.display_pdf_preview(self.file_list_widget.currentItem(), None)

    def zoom_out(self):
        self.zoom_level /= 1.2
        self.display_pdf_preview(self.file_list_widget.currentItem(), None)

    def reset_zoom(self):
        self.zoom_level = 1.0
        self.display_pdf_preview(self.file_list_widget.currentItem(), None)

    def on_region_selected(self, selection_rect):
        if self.active_field is None:
            return

        # Get the high-resolution image
        current_item = self.file_list_widget.currentItem()
        if current_item is None:
            return
        file_path = current_item.text()
        pdf_processor = PdfProcessor(file_path)
        if not pdf_processor.open():
            return
        fitz_pixmap_high_res = pdf_processor.get_page_as_pixmap(0, scale_factor=self.ocr_scale_factor)
        pdf_processor.close()
        if not fitz_pixmap_high_res:
            return
        qimage_high_res = QImage(fitz_pixmap_high_res.samples, fitz_pixmap_high_res.width, fitz_pixmap_high_res.height, fitz_pixmap_high_res.stride, QImage.Format.Format_RGB888)
        pil_image_high_res = ImageQt.fromqimage(qimage_high_res)

        # --- FIX: Translate selection coordinates to be relative to the pixmap ---
        pixmap_on_label = self.pdf_preview_label.pixmap()
        if pixmap_on_label.isNull():
            return

        pixmap_rect = pixmap_on_label.rect()
        label_rect = self.pdf_preview_label.rect()
        offset_x = (label_rect.width() - pixmap_rect.width()) / 2
        offset_y = (label_rect.height() - pixmap_rect.height()) / 2
        translated_selection_rect = selection_rect.translated(-int(offset_x), -int(offset_y))
        # --- END FIX ---

        # Scale the selection rectangle to the high-resolution image
        pixmap_width = pixmap_on_label.width()
        pixmap_height = pixmap_on_label.height()
        
        # Ensure pixmap_width and pixmap_height are not zero to avoid division by zero
        if pixmap_width == 0 or pixmap_height == 0:
            return

        x_scale = fitz_pixmap_high_res.width / pixmap_width
        y_scale = fitz_pixmap_high_res.height / pixmap_height

        x = int(translated_selection_rect.x() * x_scale)
        y = int(translated_selection_rect.y() * y_scale)
        w = int(translated_selection_rect.width() * x_scale)
        h = int(translated_selection_rect.height() * y_scale)

        # Validate cropped region dimensions
        if w <= 0 or h <= 0:
            return

        # Ensure crop coordinates are within image bounds
        img_width, img_height = pil_image_high_res.size
        x = max(0, x)
        y = max(0, y)
        w = min(w, img_width - x)
        h = min(h, img_height - y)

        if w <= 0 or h <= 0:
            return

        # Crop the high-resolution image
        cropped_image = pil_image_high_res.crop((x, y, x + w, y + h))

        # Perform OCR on the cropped image
        ocr_processor = OcrProcessor(cropped_image, self.config_manager)
        ocr_results = ocr_processor.get_text_and_boxes()
        if ocr_results:
            text = "".join([result['text'] for result in ocr_results]) # Remove spaces
        else:
            text = ""

        # Set the text to the active field
        if self.active_field is self.issue_date_edit:
            converted_date = self.date_converter.to_seireki(text)
            self.active_field.setText(converted_date)
        elif self.active_field is self.amount_edit:
            # Use the validator's internal normalization method
            normalized_amount = self.validator._normalize_amount_string(text)
            self.active_field.setText(normalized_amount)
        else:
            self.active_field.setText(text)
        self.update_filename_preview() # Explicitly update filename preview after setting text

    

    def update_document_types(self):
        self.document_type_combo.clear()
        if self.transaction_type_expenditure_radio.isChecked():
            expenditure_types = self.config_manager.get_section('FolderNames_Expenditure')
            # Filter out the top-level 'expenditure' entry
            filtered_types = {k: v for k, v in expenditure_types.items() if k != 'expenditure'}
            self.document_type_combo.addItems(list(filtered_types.values()))
        else:
            income_types = self.config_manager.get_section('FolderNames_Income')
            # Filter out the top-level 'income' entry
            filtered_types = {k: v for k, v in income_types.items() if k != 'income'}
            self.document_type_combo.addItems(list(filtered_types.values()))
        self.update_doc_id()

    def update_doc_id(self):
        year_raw = self.year_edit.text()
        if not year_raw:
            self.doc_id_label.setText("(年度未入力)")
            return
        try:
            year_int = int(year_raw)
            formatted_year = f"{year_int}年度"
        except ValueError:
            self.doc_id_label.setText("(年度形式エラー)")
            return

        transaction_type = "支出情報" if self.transaction_type_expenditure_radio.isChecked() else "収入情報"
        doc_type = self.document_type_combo.currentText()
        if not doc_type:
            self.doc_id_label.setText("(書類種別未選択)")
            return
        next_id = self.metadata_manager.get_next_doc_id(formatted_year, transaction_type, doc_type)
        self.doc_id_label.setText(next_id)
        self.update_filename_preview() # Trigger preview update

    def update_filename_preview(self, *args):
        doc_id = self.doc_id_label.text()
        issue_date = self.issue_date_edit.text()
        client_name = self.client_name_edit.text()
        
        is_valid_amount, extracted_amount = self.validator.is_valid_amount(self.amount_edit.text())
        if is_valid_amount:
            amount = str(extracted_amount)
        else:
            amount = "0"

        doc_id = doc_id if "(" not in doc_id else "XXXX"
        issue_date = issue_date if issue_date else "YYYYMMDD"
        client_name = client_name if client_name else "取引先名"

        filename = f"{doc_id}_{issue_date}_{amount}_{client_name}.pdf"
        self.filename_preview_label.setText(filename)

    def check_save_button_state(self):
        year = self.year_edit.text()
        issue_date = self.issue_date_edit.text()
        client_name = self.client_name_edit.text()
        amount = self.amount_edit.text()

        enabled = bool(year and issue_date and client_name and amount)
        self.save_button.setEnabled(enabled)

    def save_and_next(self):
        current_item = self.file_list_widget.currentItem()
        if not current_item:
            self._play_warning_sound()
            QMessageBox.warning(self, "注意", "処理対象のファイルが選択されていません。")
            return
        source_path = current_item.text()
        if "[処理済]" in source_path:
            QMessageBox.information(self, "情報", "このファイルは既に処理済みです。")
            return

        year_raw = self.year_edit.text()
        issue_date = self.issue_date_edit.text()
        client_name_raw = self.client_name_edit.text()
        amount_raw = self.amount_edit.text()
        memo = self.memo_edit.toPlainText()
        doc_type = self.document_type_combo.currentText()
        transaction_type = "支出情報" if self.transaction_type_expenditure_radio.isChecked() else "収入情報"
        doc_id = self.doc_id_label.text()
        root_path = self.config_manager.get('Paths', 'root_save_directory')

        # Validate and get extracted amount
        is_valid_amount, extracted_amount = self.validator.is_valid_amount(amount_raw)
        if not is_valid_amount:
            self._play_error_sound()
            QMessageBox.warning(self, "入力エラー", "金額には半角数字のみ入力してください。")
            return

        # Sanitize client_name for filename
        sanitized_client_name = re.sub(r'[\\/:*?"<>|]', '', client_name_raw) # Remove invalid filename characters

        # Convert year to Western year and append "年度"
        try:
            year_int = int(year_raw)
            formatted_year = f"{year_int}年度"
        except ValueError:
            self._play_error_sound()
            QMessageBox.warning(self, "入力エラー", "年度は半角数字で入力してください。")
            return

        # Construct new filename using extracted and sanitized values
        new_filename = f"{doc_id}_{issue_date}_{extracted_amount}_{sanitized_client_name}.pdf"
        target_dir = os.path.join(root_path, formatted_year, transaction_type, doc_type)
        target_path = os.path.normpath(os.path.join(target_dir, new_filename))

        # 重複ファイルのチェック
        print(f"DEBUG: 重複チェック対象パス: {target_path}")
        print(f"DEBUG: ファイル存在チェック結果: {os.path.exists(target_path)}")

        # より包括的な重複チェック
        duplicate_found = False
        duplicate_reason = ""

        # 1. 完全一致チェック
        if os.path.exists(target_path):
            duplicate_found = True
            duplicate_reason = f"同じファイル名のファイルが既に存在します:\n{target_path}"
            print(f"DEBUG: 同一ファイル名で重複検出")

        # 2. 元ファイル名での重複チェック（メタデータベース）
        if not duplicate_found:
            try:
                # 同じ年度のメタデータを検索
                csv_path = self.metadata_manager._get_csv_path(formatted_year)
                if os.path.exists(csv_path):
                    import pandas as pd
                    df = pd.read_csv(csv_path, encoding='utf-8-sig')

                    # 元のファイル名をチェック（拡張子なし）
                    original_filename_base = os.path.splitext(os.path.basename(source_path))[0]

                    # 既存エントリで同じ元ファイル名があるかチェック
                    existing_files = df['file_path'].apply(
                        lambda x: os.path.splitext(os.path.basename(x))[0] if pd.notna(x) else ""
                    )

                    for idx, existing_file in existing_files.items():
                        if existing_file:
                            # ファイル名の一部が元ファイル名と一致するかチェック
                            if original_filename_base in existing_file or existing_file in original_filename_base:
                                duplicate_found = True
                                existing_path = df.iloc[idx]['file_path']
                                duplicate_reason = f"同じ元ファイルが既に登録されている可能性があります:\n\n元ファイル: {os.path.basename(source_path)}\n既存登録: {existing_path}"
                                print(f"DEBUG: 元ファイル名で重複検出: {original_filename_base} vs {existing_file}")
                                break

            except Exception as e:
                print(f"DEBUG: メタデータチェックエラー: {e}")

        if duplicate_found:
            print(f"DEBUG: 重複ファイルが検出されました")
            # 警告音を再生
            self._play_warning_sound()

            duplicate_reply = QMessageBox.question(
                self,
                '重複ファイル',
                f"{duplicate_reason}\n\n重複して登録していないか確認してください。\n\nそれでも登録しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )

            if duplicate_reply == QMessageBox.StandardButton.Cancel:
                print("DEBUG: ユーザーがキャンセルを選択しました")
                return
            else:
                print("DEBUG: ユーザーが重複登録を承認しました")
        else:
            print("DEBUG: 重複ファイルは検出されませんでした")

        message = f"""以下の内容で保存しますか？

元ファイル: {os.path.basename(source_path)}
保存先: {target_path}

年度: {year_raw}
取引区分: {transaction_type}
書類種別: {doc_type}
発行日: {issue_date}
取引先: {client_name_raw}
金額: {amount_raw}
"""

        reply = QMessageBox.question(self, '保存確認', message, 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Validation
                if not self.validator.is_valid_date(issue_date):
                    self._play_error_sound()
                    QMessageBox.warning(self, "入力エラー", "発行日の形式が正しくありません。(YYYYMMDD)")
                    return

                os.makedirs(target_dir, exist_ok=True)
                shutil.copy(source_path, target_path)

                metadata = {
                    'doc_id': doc_id,
                    'category': transaction_type,
                    'doc_type': doc_type,
                    'issue_date': issue_date,
                    'client_name': client_name_raw,
                    'amount': extracted_amount,
                    'memo': memo,
                    'file_path': os.path.relpath(target_path, os.path.join(root_path, formatted_year))
                }
                self.metadata_manager.add_entry(formatted_year, metadata)

                QMessageBox.information(self, "成功", f"ファイルを保存しました。\n{target_path}")
                
                current_item.setText(f"[処理済] {os.path.basename(source_path)}")
                current_item.setForeground(QColor('gray'))
                self.clear_input_fields()
                self.select_next_file()

                # Save last inputs
                self.config_manager.set_last_input('year', year_raw)
                self.config_manager.set_last_input('doc_type_index', str(self.document_type_combo.currentIndex()))

            except Exception as e:
                self._play_error_sound()
                QMessageBox.critical(self, "エラー", f"ファイルの保存に失敗しました。\n{e}")

    def clear_input_fields(self):
        self.issue_date_edit.clear()
        self.client_name_edit.clear()
        self.amount_edit.clear()
        self.memo_edit.clear()

    def select_next_file(self):
        current_row = self.file_list_widget.currentRow()
        for i in range(self.file_list_widget.count()):
            next_item = self.file_list_widget.item(i)
            if "[処理済]" not in next_item.text():
                self.file_list_widget.setCurrentItem(next_item)
                return
        self.file_list_widget.setCurrentRow(-1)

    def save_splitter_sizes(self):
        """Save splitter sizes to configuration."""
        if hasattr(self, 'main_splitter'):
            sizes = self.main_splitter.sizes()
            self.config_manager.set_splitter_sizes('main_splitter', sizes)

        if hasattr(self, 'left_splitter'):
            sizes = self.left_splitter.sizes()
            self.config_manager.set_splitter_sizes('left_splitter', sizes)