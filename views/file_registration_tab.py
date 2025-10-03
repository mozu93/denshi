import os
import shutil
import io
from functools import partial
import re

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QListWidget, QLabel, QLineEdit, QFormLayout,
    QPushButton, QVBoxLayout, QGroupBox, QRadioButton, QComboBox, QTextEdit,
    QSplitter, QMessageBox, QFileDialog, QScrollArea, QToolBar, QApplication, QGridLayout
)
from PyQt6.QtGui import QPixmap, QImage, QColor, QPainter, QPen, QAction, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QBuffer, QIODevice, QPoint, QRect, QSize
from PIL import Image, ImageQt # Import ImageQt

from models.pdf_processor import PdfProcessor
from models.ocr_processor import OcrProcessor
from utils.date_converter import DateConverter
from utils.validator import Validator
from utils.file_hasher import get_file_hash
from utils.processed_file_manager import ProcessedFileManager
from models.client_manager import ClientManager
from utils.ui_styles import apply_button_style, apply_small_button_style, apply_list_widget_style

from PyQt6.QtWidgets import QFileDialog

class SelectablePdfPreviewLabel(QLabel):
    """A QLabel that allows drawing a selection rectangle and emits a signal with the selected region."""
    selection_changed = pyqtSignal(QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.selecting_region = False
        self.selection_start_point = QPoint()
        self.selection_end_point = QPoint()
        self.current_pixmap = None

    def setPixmap(self, pixmap):
        super().setPixmap(pixmap)
        self.current_pixmap = pixmap
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selecting_region = True
            self.selection_start_point = event.pos()
            self.selection_end_point = event.pos()
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.selecting_region:
            self.selection_end_point = event.pos()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.selecting_region:
            self.selecting_region = False
            selection_rect = QRect(self.selection_start_point, self.selection_end_point).normalized()
            self.selection_changed.emit(selection_rect)
            self.update()
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
        self.processed_file_manager = ProcessedFileManager()
        self.client_manager = ClientManager(config_manager)

        self._create_widgets()
        self._setup_layout()
        self._connect_signals()
        self._load_initial_state()
        self._update_placeholder_visibility()
        self._apply_styles()

    def _play_warning_sound(self):
        """システム警告音を再生"""
        try:
            QApplication.beep()
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
        self.file_list_widget.setMinimumHeight(120)

        self.placeholder_label = QLabel("ここへPDFファイルをドラッグアンドドロップしてください。")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #888;")
        
        self.toolbar = QToolBar()
        self.zoom_in_action = QAction(QIcon.fromTheme("zoom-in"), "Zoom In", self)
        self.zoom_out_action = QAction(QIcon.fromTheme("zoom-out"), "Zoom Out", self)
        self.reset_zoom_action = QAction(QIcon.fromTheme("zoom-original"), "Reset Zoom", self)

        self.scroll_area = QScrollArea()
        self.pdf_preview_label = SelectablePdfPreviewLabel()

        self.ocr_instruction_label = QLabel("入力したい項目を選択後、右のPDF上で範囲をドラッグしてOCRで読み取れます。")
        self.year_edit = QLineEdit()
        self.transaction_type_expenditure_radio = QRadioButton("支出情報")
        self.transaction_type_income_radio = QRadioButton("収入情報")
        self.transaction_type_other_org_radio = QRadioButton("その他団体")
        self.document_type_combo = QComboBox()
        self.doc_id_label = QLabel("(自動採番)")
        self.reload_doc_id_button = QPushButton(QIcon.fromTheme("view-refresh"), "再計算")
        self.issue_date_edit = QLineEdit()
        self.client_name_edit = QLineEdit()
        self.register_client_button = QPushButton("登録")
        self.recall_client_button = QPushButton("呼出")
        self.amount_edit = QLineEdit()
        self.memo_edit = QTextEdit()
        self.filename_preview_label = QLabel("(ファイル名プレビュー)")
        self.save_button = QPushButton("保存して次へ")

    def _setup_layout(self):
        """Set up the layout of the tab."""
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setLayout(QHBoxLayout()) 
        self.layout().addWidget(main_splitter)

        left_splitter = QSplitter(Qt.Orientation.Vertical)
        file_list_group = QGroupBox("登録ファイル")
        
        file_list_layout = QGridLayout()
        file_list_layout.addWidget(self.file_list_widget, 0, 0)
        file_list_layout.addWidget(self.placeholder_label, 0, 0)
        file_list_group.setLayout(file_list_layout)

        left_splitter.addWidget(file_list_group)

        data_input_group = QGroupBox("データ入力")
        form_layout = QFormLayout()
        self.ocr_instruction_label.setWordWrap(True)
        form_layout.addRow(self.ocr_instruction_label)
        transaction_radio_layout = QHBoxLayout()
        transaction_radio_layout.addWidget(self.transaction_type_expenditure_radio)
        transaction_radio_layout.addWidget(self.transaction_type_income_radio)
        transaction_radio_layout.addWidget(self.transaction_type_other_org_radio)
        form_layout.addRow("年:", self.year_edit)
        form_layout.addRow("取引区分:", transaction_radio_layout)
        form_layout.addRow("書類種別:", self.document_type_combo)

        doc_id_layout = QHBoxLayout()
        doc_id_layout.addWidget(self.doc_id_label, 1)
        doc_id_layout.addWidget(self.reload_doc_id_button)
        form_layout.addRow("通し番号:", doc_id_layout)

        form_layout.addRow("発行日:", self.issue_date_edit)

        # 取引先名のレイアウト（フィールド + ボタン）
        client_name_layout = QHBoxLayout()
        client_name_layout.addWidget(self.client_name_edit)
        client_name_layout.addWidget(self.register_client_button)
        client_name_layout.addWidget(self.recall_client_button)
        form_layout.addRow("取引先名:", client_name_layout)

        form_layout.addRow("金額(税込):", self.amount_edit)
        form_layout.addRow("メモ:", self.memo_edit)
        form_layout.addRow("ファイル名:", self.filename_preview_label)
        form_layout.addRow(self.save_button)
        data_input_group.setLayout(form_layout)
        left_splitter.addWidget(data_input_group)

        saved_left_sizes = self.config_manager.get_splitter_sizes('left_splitter')
        if saved_left_sizes and len(saved_left_sizes) == 2:
            left_splitter.setSizes(saved_left_sizes)
        else:
            left_splitter.setSizes([150, 400])

        self.left_splitter = left_splitter

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

        main_splitter.addWidget(left_splitter)
        main_splitter.addWidget(right_column_widget)

        saved_main_sizes = self.config_manager.get_splitter_sizes('main_splitter')
        if saved_main_sizes and len(saved_main_sizes) == 2:
            main_splitter.setSizes(saved_main_sizes)
        else:
            main_splitter.setSizes([400, 800])

        self.main_splitter = main_splitter

    def _connect_signals(self):
        """Connect all signals to slots."""
        self.file_list_widget.currentItemChanged.connect(self.on_file_selection_changed)
        self.file_list_widget.model().rowsInserted.connect(self._update_placeholder_visibility)
        self.file_list_widget.model().rowsRemoved.connect(self._update_placeholder_visibility)
        self.pdf_preview_label.selection_changed.connect(self.on_region_selected)
        self.save_button.clicked.connect(self.save_and_next)
        self.register_client_button.clicked.connect(self.register_client)
        self.recall_client_button.clicked.connect(self.show_client_selection)

        self.zoom_in_action.triggered.connect(self.zoom_in)
        self.zoom_out_action.triggered.connect(self.zoom_out)
        self.reset_zoom_action.triggered.connect(self.reset_zoom)

        self.year_edit.installEventFilter(self)
        self.issue_date_edit.installEventFilter(self)
        self.client_name_edit.installEventFilter(self)
        self.amount_edit.installEventFilter(self)

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
        self.transaction_type_income_radio.toggled.connect(self.update_document_types)
        self.transaction_type_income_radio.toggled.connect(self.update_doc_id)
        self.transaction_type_other_org_radio.toggled.connect(self.update_document_types)
        self.transaction_type_other_org_radio.toggled.connect(self.update_doc_id)
        self.reload_doc_id_button.clicked.connect(self.update_doc_id)

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

    def _update_placeholder_visibility(self):
        """Show or hide the placeholder label based on list widget content."""
        if self.file_list_widget.count() > 0:
            self.placeholder_label.hide()
        else:
            self.placeholder_label.show()

    def open_file_dialog(self):
        """ファイルダイアログを開いてPDFファイルを選択

        機能:
        - 最後に使用したフォルダを記憶し次回表示
        - 選択したフォルダの古いファイルをクリーンアップ（30日経過後削除）
        """
        # 最後に使用したフォルダパスを取得
        last_folder = self.config_manager.get_last_folder_path()

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "PDFファイルを選択",
            last_folder,
            "PDF Files (*.pdf)"
        )

        if files:
            # 最初のファイルのフォルダパスを保存（次回用）
            first_file_folder = os.path.dirname(files[0])
            self.config_manager.set_last_folder_path(first_file_folder)

            # 選択したフォルダの処理済ファイルをクリーンアップ
            try:
                deleted_count = self.processed_file_manager.cleanup_old_files(first_file_folder)
                if deleted_count > 0:
                    print(f"INFO: 30日経過した処理済ファイル {deleted_count}件を削除しました")
            except Exception as e:
                print(f"WARNING: 古いファイルの削除でエラー: {e}")

            # ファイルをリストに追加
            for file in files:
                self.add_file_to_list(file)

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
        file_hash = get_file_hash(file_path)
        is_registered, existing_record, year = self.metadata_manager.is_hash_registered(file_hash)
        if is_registered:
            original_filename = os.path.basename(file_path)
            registered_filename = os.path.basename(existing_record.get('file_path', '不明なファイル'))
            msg = (
                f"このファイルは既に登録されている可能性があります。\n\n"
                f"追加しようとしたファイル: {original_filename}\n"
                f"登録済みのファイル名: {registered_filename}\n"
                f"登録先: {year}"
            )
            self._play_warning_sound()
            QMessageBox.warning(self, "重複ファイルの検出", msg)
            return

        for i in range(self.file_list_widget.count()):
            if self.file_list_widget.item(i).text() == file_path:
                self._play_warning_sound()
                QMessageBox.warning(self, "警告", "このファイルは既にリストに追加されています。")
                return

        was_empty = self.file_list_widget.count() == 0
        from PyQt6.QtWidgets import QListWidgetItem
        item = QListWidgetItem(file_path)
        item.setData(Qt.ItemDataRole.UserRole, file_path)
        self.file_list_widget.addItem(item)

        if was_empty:
            self.file_list_widget.setCurrentRow(0)

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
        if current is None:
            self.pdf_preview_label.clear()
            self.pdf_preview_label.setText("ここにPDFのプレビューが表示されます")
            return
        
        file_path = current.text()
        pdf_processor = PdfProcessor(file_path)
        if not pdf_processor.open():
            self.pdf_preview_label.setText("PDFを開けませんでした")
            return

        fitz_pixmap_high_res = pdf_processor.get_page_as_pixmap(0, scale_factor=self.ocr_scale_factor)
        
        fitz_pixmap_display = pdf_processor.get_page_as_pixmap(0, scale_factor=self.zoom_level)
        pdf_processor.close()

        if not fitz_pixmap_high_res or not fitz_pixmap_display:
            self.pdf_preview_label.setText("プレビューの生成に失敗しました")
            return

        qimage_high_res = QImage(fitz_pixmap_high_res.samples, fitz_pixmap_high_res.width, fitz_pixmap_high_res.height, fitz_pixmap_high_res.stride, QImage.Format.Format_RGB888)
        pil_image_high_res = ImageQt.fromqimage(qimage_high_res)

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

        pixmap_on_label = self.pdf_preview_label.pixmap()
        if pixmap_on_label.isNull():
            return

        pixmap_rect = pixmap_on_label.rect()
        label_rect = self.pdf_preview_label.rect()
        offset_x = (label_rect.width() - pixmap_rect.width()) / 2
        offset_y = (label_rect.height() - pixmap_rect.height()) / 2
        translated_selection_rect = selection_rect.translated(-int(offset_x), -int(offset_y))

        pixmap_width = pixmap_on_label.width()
        pixmap_height = pixmap_on_label.height()
        
        if pixmap_width == 0 or pixmap_height == 0:
            return

        x_scale = fitz_pixmap_high_res.width / pixmap_width
        y_scale = fitz_pixmap_high_res.height / pixmap_height

        x = int(translated_selection_rect.x() * x_scale)
        y = int(translated_selection_rect.y() * y_scale)
        w = int(translated_selection_rect.width() * x_scale)
        h = int(translated_selection_rect.height() * y_scale)

        if w <= 0 or h <= 0:
            return

        img_width, img_height = pil_image_high_res.size
        x = max(0, x)
        y = max(0, y)
        w = min(w, img_width - x)
        h = min(h, img_height - y)

        if w <= 0 or h <= 0:
            return

        cropped_image = pil_image_high_res.crop((x, y, x + w, y + h))

        ocr_processor = OcrProcessor(cropped_image, self.config_manager)
        ocr_results = ocr_processor.get_text_and_boxes()
        if ocr_results:
            text = "".join([result['text'] for result in ocr_results])
        else:
            text = ""

        if self.active_field is self.issue_date_edit:
            converted_date = self.date_converter.to_seireki(text)
            self.active_field.setText(converted_date)
        elif self.active_field is self.amount_edit:
            normalized_amount = self.validator._normalize_amount_string(text)
            self.active_field.setText(normalized_amount)
        else:
            self.active_field.setText(text)
        self.update_filename_preview()

    def update_document_types(self):
        self.document_type_combo.clear()
        if self.transaction_type_expenditure_radio.isChecked():
            expenditure_types = self.config_manager.get_section('FolderNames_Expenditure')
            filtered_types = {k: v for k, v in expenditure_types.items() if k != 'expenditure'}
            self.document_type_combo.addItems(list(filtered_types.values()))
        elif self.transaction_type_income_radio.isChecked():
            income_types = self.config_manager.get_section('FolderNames_Income')
            filtered_types = {k: v for k, v in income_types.items() if k != 'income'}
            self.document_type_combo.addItems(list(filtered_types.values()))
        elif self.transaction_type_other_org_radio.isChecked():
            other_org_types = self.config_manager.get_section('FolderNames_OtherOrganization')
            self.document_type_combo.addItems(list(other_org_types.values()))
        self.update_doc_id()

    def update_doc_id(self):
        year_raw = self.year_edit.text()
        if not year_raw:
            self.doc_id_label.setText("(年未入力)")
            return
        try:
            year_int = int(year_raw)
            formatted_year = f"{year_int}年"
        except ValueError:
            self.doc_id_label.setText("(年形式エラー)")
            return

        if self.transaction_type_expenditure_radio.isChecked():
            transaction_type = "支出情報"
        elif self.transaction_type_income_radio.isChecked():
            transaction_type = "収入情報"
        else:
            transaction_type = "その他団体"
        doc_type = self.document_type_combo.currentText()
        if not doc_type:
            self.doc_id_label.setText("(書類種別未選択)")
            return
        next_id = self.metadata_manager.get_next_doc_id(formatted_year, transaction_type, doc_type)
        self.doc_id_label.setText(next_id)
        self.update_filename_preview()

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

        year_raw = self.year_edit.text()
        issue_date = self.issue_date_edit.text()
        client_name_raw = self.client_name_edit.text()
        amount_raw = self.amount_edit.text()
        memo = self.memo_edit.toPlainText()
        doc_type = self.document_type_combo.currentText()
        if self.transaction_type_expenditure_radio.isChecked():
            transaction_type = "支出情報"
        elif self.transaction_type_income_radio.isChecked():
            transaction_type = "収入情報"
        else:
            transaction_type = "その他団体"
        doc_id = self.doc_id_label.text()
        root_path = self.config_manager.get('Paths', 'root_save_directory')

        is_valid_amount, extracted_amount = self.validator.is_valid_amount(amount_raw)
        if not is_valid_amount:
            self._play_error_sound()
            QMessageBox.warning(self, "入力エラー", "金額には半角数字のみ入力してください。")
            return

        sanitized_client_name = re.sub(r'[\\/:*?"<>|]', '', client_name_raw)

        try:
            year_int = int(year_raw)
            formatted_year = f"{year_int}年"
        except ValueError:
            self._play_error_sound()
            QMessageBox.warning(self, "入力エラー", "年は半角数字で入力してください。")
            return

        new_filename = f"{doc_id}_{issue_date}_{extracted_amount}_{sanitized_client_name}.pdf"
        target_dir = os.path.join(root_path, formatted_year, transaction_type, doc_type)
        target_path = os.path.normpath(os.path.join(target_dir, new_filename))

        if os.path.exists(target_path):
            self._play_warning_sound()
            reply = QMessageBox.question(self, '重複ファイル', f"同じファイル名のファイルが既に存在します:\n{target_path}\n\n上書きしますか？",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Cancel:
                return

        message = (
            f"以下の内容で保存しますか？\n\n"
            f"元ファイル: {os.path.basename(source_path)}\n"
            f"保存先: {target_path}\n\n"
            f"年: {year_raw}\n"
            f"取引区分: {transaction_type}\n"
            f"書類種別: {doc_type}\n"
            f"発行日: {issue_date}\n"
            f"取引先: {client_name_raw}\n"
            f"金額: {amount_raw}\n"
        )

        reply = QMessageBox.question(self, '保存確認', message, 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if not self.validator.is_valid_date(issue_date):
                    self._play_error_sound()
                    QMessageBox.warning(self, "入力エラー", "発行日の形式が正しくありません。(YYYYMMDD)")
                    return

                os.makedirs(target_dir, exist_ok=True)
                shutil.copy(source_path, target_path)

                file_hash = get_file_hash(target_path)

                metadata = {
                    'doc_id': doc_id,
                    'category': transaction_type,
                    'doc_type': doc_type,
                    'issue_date': issue_date,
                    'client_name': client_name_raw,
                    'amount': extracted_amount,
                    'memo': memo,
                    'file_path': os.path.relpath(target_path, os.path.join(root_path, formatted_year)),
                    'file_hash': file_hash
                }
                self.metadata_manager.add_entry(formatted_year, metadata)

                QMessageBox.information(self, "成功", f"ファイルを保存しました。\n{target_path}")

                # 元ファイルを処理済フォルダに移動
                try:
                    source_file_path = current_item.data(Qt.ItemDataRole.UserRole)
                    if source_file_path and os.path.exists(source_file_path):
                        moved_path = self.processed_file_manager.move_to_processed_folder(source_file_path)
                        # 30日経過後のファイル削除処理も実行
                        source_folder = os.path.dirname(source_file_path)
                        self.processed_file_manager.cleanup_old_files(source_folder)
                    else:
                        print(f"ソースファイルが見つかりません: {source_file_path}")
                except Exception as move_error:
                    print(f"ファイル移動エラーの詳細: {move_error}")
                    print(f"エラー発生時のファイルパス: {source_file_path}")
                    QMessageBox.warning(self, "警告", f"ファイルの移動に失敗しました。\n元ファイル: {source_file_path}\nエラー: {move_error}")

                row = self.file_list_widget.row(current_item)
                self.file_list_widget.takeItem(row)

                self.clear_input_fields()
                self.select_next_file()

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
        if self.file_list_widget.count() > 0:
            self.file_list_widget.setCurrentRow(0)
        else:
            self.pdf_preview_label.clear()
            self.pdf_preview_label.setText("ここにPDFのプレビューが表示されます")

    def register_client(self):
        """現在の取引先名をフリガナ付きで登録"""
        client_name = self.client_name_edit.text().strip()
        if not client_name:
            QMessageBox.warning(self, "入力エラー", "取引先名を入力してください。")
            return

        # 取引先名の重複チェック（フリガナ入力前）
        duplicate_name, _ = self.client_manager.check_duplicate_details(client_name, "")
        if duplicate_name:
            QMessageBox.warning(self, "重複エラー", f"取引先名「{client_name}」は既に登録されています。")
            return

        # フリガナ入力ダイアログを表示
        from PyQt6.QtWidgets import QInputDialog
        furigana, ok = QInputDialog.getText(
            self, "フリガナ入力",
            f"取引先名「{client_name}」のフリガナを入力してください:"
        )

        if ok and furigana.strip():
            # フリガナの重複チェック
            _, duplicate_furigana = self.client_manager.check_duplicate_details(client_name, furigana.strip())
            if duplicate_furigana:
                QMessageBox.warning(self, "重複エラー", f"フリガナ「{furigana.strip()}」は既に登録されています。")
                return

            # 登録実行
            if self.client_manager.add_client(client_name, furigana.strip()):
                QMessageBox.information(self, "成功", "取引先を登録しました。")
            else:
                QMessageBox.critical(self, "エラー", "取引先の登録に失敗しました。")
        elif ok:
            QMessageBox.warning(self, "入力エラー", "フリガナを入力してください。")

    def show_client_selection(self):
        """取引先選択ダイアログを表示"""
        clients = self.client_manager.get_all_clients()
        if not clients:
            QMessageBox.information(self, "情報", "登録されている取引先がありません。")
            return

        # 取引先名リストを作成
        client_names = [f"{client['name']} ({client['furigana']})" for client in clients]

        from PyQt6.QtWidgets import QInputDialog
        selected_item, ok = QInputDialog.getItem(
            self, "取引先選択",
            "取引先を選択してください:",
            client_names, 0, False
        )

        if ok and selected_item:
            # 選択された取引先名を抽出（フリガナ部分を除去）
            client_name = selected_item.split(' (')[0]
            self.client_name_edit.setText(client_name)

    def _apply_styles(self):
        """UIスタイルを適用"""
        # メインボタン
        apply_button_style(self.save_button)

        # 小さなボタン
        apply_small_button_style(self.reload_doc_id_button)
        apply_small_button_style(self.register_client_button)
        apply_small_button_style(self.recall_client_button)

        # リストウィジェット
        apply_list_widget_style(self.file_list_widget)

    def save_splitter_sizes(self):
        """Save splitter sizes to configuration."""
        if hasattr(self, 'main_splitter'):
            sizes = self.main_splitter.sizes()
            self.config_manager.set_splitter_sizes('main_splitter', sizes)

        if hasattr(self, 'left_splitter'):
            sizes = self.left_splitter.sizes()
            self.config_manager.set_splitter_sizes('left_splitter', sizes)
