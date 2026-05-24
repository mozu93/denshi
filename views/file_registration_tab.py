import os
import sys
import shutil
import io
import logging
from functools import partial
import re
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QListWidget, QLabel, QLineEdit, QFormLayout,
    QPushButton, QVBoxLayout, QGroupBox, QRadioButton, QComboBox, QTextEdit,
    QSplitter, QMessageBox, QFileDialog, QScrollArea, QToolBar, QApplication,
    QGridLayout, QListWidgetItem, QInputDialog
)
from PyQt6.QtGui import QPixmap, QImage, QColor, QPainter, QPen, QAction, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QBuffer, QIODevice, QPoint, QRect, QSize, QThread
from PIL import Image, ImageQt

from models.pdf_processor import PdfProcessor
from models.ocr_processor import OcrProcessor
from models.pdf_text_extractor import PdfTextExtractor
from models.learning_manager import LearningManager
from utils.date_converter import DateConverter
from utils.validator import Validator
from utils.file_hasher import get_file_hash
from utils.processed_file_manager import ProcessedFileManager
from models.client_manager import ClientManager
from utils.ui_styles import apply_button_style, apply_small_button_style, apply_list_widget_style
from utils.constants import CATEGORY_EXPENDITURE, CATEGORY_INCOME, CATEGORY_OTHER_ORG

logger = logging.getLogger(__name__)


def _remove_repetition_pattern(text: str) -> str:
    """
    文字列が繰り返しパターン（部分繰り返し含む）になっている場合に
    単位文字列を返す。そうでなければ元の文字列を返す。

    検出する2種類のパターン:
    Case1: 完全2回以上の繰り返し (末尾部分一致を許容)
        例: '三重交通三重交通' (完全2回)         -> '三重交通'
        例: '124500124500124500' (完全3回)       -> '124500'
        例: '224000224000224' (完全2回+部分3)    -> '224000'
    Case2: 完全1回 + 末尾の部分繰り返し（モデル出力が打ち切られたケース）
        例: '22400022' (1回+部分2)               -> '224000'
        例: '224000224' (1回+部分3)              -> '224000'

    誤検出回避の制約:
    - 最小文字数 8: '100100'(=100,100円) 等の正規6桁金額を保護
    - 単位長 >= 4: 短すぎる単位での誤検出を防止
    - 単位内ユニーク文字数 >= 2: '5555' '55555555' 等の同一文字反復を保護
    - Case2 の部分長 <= 単位長/2 かつ >= 2:
        '20240202'(日付) 等の正規8桁値を保護しつつ短い部分繰り返しのみ検出
    """
    n = len(text)
    if n < 8:
        return text

    # ---- Case 1: 完全2回以上 ----
    for unit_len in range(4, n // 2 + 1):
        unit = text[:unit_len]
        if len(set(unit)) < 2:
            continue
        if text[unit_len:2 * unit_len] != unit:
            continue
        valid = True
        i = 2 * unit_len
        while i < n:
            remaining = n - i
            if remaining >= unit_len:
                if text[i:i + unit_len] == unit:
                    i += unit_len
                else:
                    valid = False
                    break
            else:
                if text[i:] == unit[:remaining]:
                    i = n
                else:
                    valid = False
                    break
        if valid:
            return unit

    # ---- Case 2: 完全1回 + 末尾部分繰り返し ----
    for unit_len in range(4, n):
        partial_len = n - unit_len
        if partial_len < 2:
            break  # これ以上 unit_len を増やすと partial が短すぎる
        if partial_len * 2 > unit_len:  # partial > unit_len/2 → 過剰検出回避のためスキップ
            continue
        unit = text[:unit_len]
        if len(set(unit)) < 2:
            continue
        partial = text[unit_len:]
        if unit.startswith(partial):
            return unit
    return text


def _dedup_ocr_text(results: list) -> str:
    """
    OCR結果リストからテキストを結合し、繰り返しパターンを除去する。
    """
    seen: set = set()
    unique_parts: list = []
    for r in (results or []):
        t = r.get('text', '').strip()
        if t and t not in seen:
            seen.add(t)
            unique_parts.append(t)
    return _remove_repetition_pattern("".join(unique_parts))


class _PageOcrWorker(QThread):
    """1ページ全体のOCRをバックグラウンドで実行するワーカー。
    結果はインスタンス属性に格納し、完了通知のみシグナルで送信する。"""
    done = pyqtSignal(str)  # file_path

    def __init__(self, file_path: str, pil_image, config_manager):
        super().__init__()
        self._file_path = file_path
        self._image = pil_image
        self._config_manager = config_manager
        self.results: list = []
        self.error_message: str = ""

    def run(self):
        try:
            self.results = OcrProcessor(self._image, self._config_manager).get_text_and_boxes() or []
        except Exception as e:
            self.error_message = str(e)
            logger.error(f"ページOCRワーカーエラー: {e}", exc_info=True)
        self.done.emit(self._file_path)



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
        self.pdf_text_extractor = PdfTextExtractor()
        # frozen（インストール済みexe）の場合は APPDATA に保存（Program Files は書き込み禁止）
        if getattr(sys, 'frozen', False):
            _appdata = os.environ.get('APPDATA', '')
            if _appdata:
                _user_data_dir = os.path.join(_appdata, 'DenshiChobohozoSystem')
                os.makedirs(_user_data_dir, exist_ok=True)
                _learning_path = os.path.join(_user_data_dir, 'learning_data.json')
            else:
                _learning_path = os.path.join(os.path.dirname(sys.executable), 'learning_data.json')
        else:
            _learning_path = os.path.normpath(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'learning_data.json')
            )
        self.learning_manager = LearningManager(_learning_path)
        self.last_ocr_regions: dict = {}  # field_name -> (x_pct, y_pct, w_pct, h_pct)
        self.last_reg_number: Optional[str] = None  # 現在表示中PDFの登録番号

        # ページ単位のOCRキャッシュ（小領域OCRではなく全体OCRで繰り返し問題を回避）
        self._page_ocr_cache: dict = {}      # file_path -> [ {text, left, top, width, height, conf} ]
        self._page_ocr_workers: dict = {}    # file_path -> _PageOcrWorker (進行中のもの)

        self._create_widgets()
        self._setup_layout()
        self._connect_signals()
        self._load_initial_state()
        self._update_placeholder_visibility()
        self._apply_styles()

    def _play_sound(self, sound_type: str):
        """システム音を再生 ('warning' or 'error')"""
        import platform
        if platform.system() == 'Windows':
            try:
                import winsound
                freq, duration = (440, 200) if sound_type == 'warning' else (880, 500)
                winsound.Beep(freq, duration)
            except Exception as e:
                logger.warning(f"サウンド再生エラー: {e}")

    def _get_transaction_type(self) -> str:
        """選択中のラジオボタンに基づいて取引区分を返す"""
        if self.transaction_type_expenditure_radio.isChecked():
            return CATEGORY_EXPENDITURE
        elif self.transaction_type_income_radio.isChecked():
            return CATEGORY_INCOME
        return CATEGORY_OTHER_ORG

    def _create_widgets(self):
        """Create all the widgets for the tab."""
        self.file_list_widget = QListWidget()
        self.file_list_widget.setMinimumHeight(120)

        self.placeholder_label = QLabel("ファイルメニューからフォルダを選択するか、ファイルを選択、または\nここへPDFファイルをドラッグアンドドロップしてください。")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #888;")

        self.toolbar = QToolBar()
        self.zoom_in_action = QAction(QIcon.fromTheme("zoom-in"), "Zoom In", self)
        self.zoom_out_action = QAction(QIcon.fromTheme("zoom-out"), "Zoom Out", self)
        self.reset_zoom_action = QAction(QIcon.fromTheme("zoom-original"), "Reset Zoom", self)

        self.scroll_area = QScrollArea()
        self.pdf_preview_label = SelectablePdfPreviewLabel()

        self.ocr_instruction_label = QLabel(
            "入力したい項目を選択後、右のPDF上で範囲をドラッグしてOCRで読み取れます。\n"
            "※ 初回のみ約12秒かかります。2回目以降は快適に読み取れます。"
        )
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
        self.remove_file_button = QPushButton(QIcon.fromTheme("list-remove"), "リストから削除")
        self.filename_preview_label = QLabel("(ファイル名プレビュー)")
        self.save_button = QPushButton("保存して次へ")

        self.extraction_status_label = QLabel("")
        self.extraction_status_label.setWordWrap(True)
        self.auto_fill_button = QPushButton("自動入力")

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
        remove_btn_layout = QHBoxLayout()
        remove_btn_layout.addWidget(self.remove_file_button)
        remove_btn_layout.addStretch()
        file_list_layout.addLayout(remove_btn_layout, 1, 0)
        file_list_group.setLayout(file_list_layout)

        left_splitter.addWidget(file_list_group)

        data_input_group = QGroupBox("データ入力")
        form_layout = QFormLayout()
        self.ocr_instruction_label.setWordWrap(True)
        form_layout.addRow(self.ocr_instruction_label)

        status_widget = QWidget()
        status_layout_h = QHBoxLayout(status_widget)
        status_layout_h.setContentsMargins(0, 0, 0, 0)
        status_layout_h.addWidget(self.extraction_status_label, 1)
        status_layout_h.addWidget(self.auto_fill_button)
        form_layout.addRow(status_widget)

        transaction_radio_layout = QHBoxLayout()
        transaction_radio_layout.addWidget(self.transaction_type_expenditure_radio)
        transaction_radio_layout.addWidget(self.transaction_type_income_radio)
        transaction_radio_layout.addWidget(self.transaction_type_other_org_radio)
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
        self.remove_file_button.clicked.connect(self._remove_from_list)
        self.register_client_button.clicked.connect(self.register_client)
        self.recall_client_button.clicked.connect(self.show_client_selection)

        self.zoom_in_action.triggered.connect(self.zoom_in)
        self.zoom_out_action.triggered.connect(self.zoom_out)
        self.reset_zoom_action.triggered.connect(self.reset_zoom)
        self.auto_fill_button.clicked.connect(self._trigger_auto_extract)

        self.issue_date_edit.installEventFilter(self)
        self.client_name_edit.installEventFilter(self)
        self.amount_edit.installEventFilter(self)

        self.issue_date_edit.textChanged.connect(self.check_save_button_state)
        self.client_name_edit.textChanged.connect(self.check_save_button_state)
        self.amount_edit.textChanged.connect(self.check_save_button_state)
        self.issue_date_edit.textChanged.connect(self.update_doc_id)
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

    def open_folder_dialog(self):
        """フォルダダイアログを開いてフォルダ内のPDFを全て登録"""
        last_folder = self.config_manager.get_last_folder_path()

        folder = QFileDialog.getExistingDirectory(
            self,
            "フォルダを選択",
            last_folder,
        )

        if folder:
            try:
                self.config_manager.set_last_folder_path(folder)
            except Exception:
                pass

            pdf_files = sorted(
                os.path.join(folder, f)
                for f in os.listdir(folder)
                if f.lower().endswith('.pdf')
            )
            for file_path in pdf_files:
                self.add_file_to_list(file_path)

    def open_file_dialog(self):
        """ファイルダイアログを開いてPDFファイルを選択"""
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
            try:
                self.config_manager.set_last_folder_path(first_file_folder)
            except Exception:
                pass

            # ファイルをリストに追加
            for file in files:
                self.add_file_to_list(file)

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.FocusIn:
            if source in [self.issue_date_edit, self.client_name_edit, self.amount_edit]:
                self.set_active_field(source)
        return super().eventFilter(source, event)

    def set_active_field(self, field):
        for f in [self.issue_date_edit, self.client_name_edit, self.amount_edit]:
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
            self._play_sound('warning')
            QMessageBox.warning(self, "重複ファイルの検出", msg)
            return

        for i in range(self.file_list_widget.count()):
            if self.file_list_widget.item(i).text() == file_path:
                self._play_sound('warning')
                QMessageBox.warning(self, "警告", "このファイルは既にリストに追加されています。")
                return

        was_empty = self.file_list_widget.count() == 0
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
        if current is not None:
            # バックグラウンドで全ページOCRを開始（手動領域選択時に瞬時に応答するため）
            self._ensure_page_ocr(current.text())
        self._try_auto_extract(current)
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
        """ユーザーが選択した領域に対応するテキストを、ページ全体OCRのキャッシュ
        から取得してアクティブフィールドに入力する。"""
        if self.active_field is None:
            return

        current_item = self.file_list_widget.currentItem()
        if current_item is None:
            return
        file_path = current_item.text()

        # 高解像度ページサイズを取得（座標計算用、画像本体は不要）
        pdf_processor = PdfProcessor(file_path)
        if not pdf_processor.open():
            return
        fitz_pixmap_high_res = pdf_processor.get_page_as_pixmap(0, scale_factor=self.ocr_scale_factor)
        pdf_processor.close()
        if not fitz_pixmap_high_res:
            return
        page_w = fitz_pixmap_high_res.width
        page_h = fitz_pixmap_high_res.height

        # 選択矩形を高解像度ピクセル座標に変換
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
        x_scale = page_w / pixmap_width
        y_scale = page_h / pixmap_height
        x = int(translated_selection_rect.x() * x_scale)
        y = int(translated_selection_rect.y() * y_scale)
        w = int(translated_selection_rect.width() * x_scale)
        h = int(translated_selection_rect.height() * y_scale)
        if w <= 0 or h <= 0:
            return
        x = max(0, x)
        y = max(0, y)
        w = min(w, page_w - x)
        h = min(h, page_h - y)
        if w <= 0 or h <= 0:
            return

        # ページ全体OCRキャッシュを確保（未起動なら開始、進行中なら同期待ち）
        if file_path not in self._page_ocr_cache:
            self._ensure_page_ocr(file_path)
            if not self._wait_for_page_ocr_sync(file_path):
                QMessageBox.warning(
                    self, "OCRエラー",
                    "OCRの実行に失敗しました。\nWindows の日本語言語パックがインストールされているか確認してください。"
                )
                return

        # キャッシュから選択領域のテキストを抽出
        text = self._get_text_from_region(file_path, x, y, w, h)

        if not text:
            try:
                mw = self.window()
                if hasattr(mw, 'status_bar'):
                    mw.status_bar.showMessage("選択領域に文字が見つかりませんでした", 3000)
            except Exception:
                pass
            return

        # フィールド別の正規化
        if self.active_field is self.issue_date_edit:
            text = self.date_converter.to_seireki(text)
        elif self.active_field is self.amount_edit:
            text = self.validator._normalize_amount_string(text)

        self.active_field.setText(text)
        self.update_filename_preview()

        # 学習: OCR領域をページ比率で記録
        if text:
            field_name = self._field_to_name(self.active_field)
            if field_name:
                region_pct = (x / page_w, y / page_h, w / page_w, h / page_h)
                self.last_ocr_regions[field_name] = region_pct
                issuer = self.client_name_edit.text().strip()
                if issuer:
                    self.learning_manager.learn_ocr_region(issuer, field_name, region_pct)

    def _try_auto_extract(self, item):
        """テキストPDFから帳票情報を自動抽出して空フィールドに入力する"""
        if item is None:
            self.extraction_status_label.setText("")
            return

        file_path = item.text()
        try:
            result = self.pdf_text_extractor.extract(file_path)
        except Exception as e:
            logger.warning(f"自動抽出エラー: {e}")
            self.extraction_status_label.setText("自動抽出に失敗しました。")
            self.extraction_status_label.setStyleSheet("color: #c0392b;")
            return

        if not result.is_text_pdf:
            self.extraction_status_label.setText(
                "スキャンPDF: OCRまたは手動で入力してください。"
            )
            self.extraction_status_label.setStyleSheet("color: #888;")
            return

        # 登録番号（T+13桁）を記憶（保存時の学習に使用）
        self.last_reg_number = result.reg_number

        # T番号で学習済みの取引先名があれば最優先で使用
        # 自動抽出より精度が高い（ユーザーが一度確認した正確な名前）
        if result.reg_number:
            cached = self.learning_manager.get_issuer_by_reg_number(result.reg_number)
            if cached:
                result.client_name = cached
                result.field_confidences['client_name'] = 0.95

        # 取引先名が未取得の場合、Windows OCR キャッシュでフォールバック
        if (not result.client_name
                or result.field_confidences.get('client_name', 0) < PdfTextExtractor.CONFIDENCE_THRESHOLD):
            ocr_client = self._extract_client_from_ocr(file_path)
            if ocr_client:
                result.client_name = ocr_client
                result.field_confidences['client_name'] = 0.6

        threshold = PdfTextExtractor.CONFIDENCE_THRESHOLD
        filled = []

        if (not self.issue_date_edit.text()
                and result.issue_date
                and result.field_confidences.get('issue_date', 0) >= threshold):
            self.issue_date_edit.setText(_remove_repetition_pattern(result.issue_date))
            filled.append("発行日")

        if (not self.amount_edit.text()
                and result.amount
                and result.field_confidences.get('amount', 0) >= threshold):
            # PDFテキストレイヤー重複等による '224000224000' のような繰り返し値を補正
            self.amount_edit.setText(_remove_repetition_pattern(str(result.amount)))
            filled.append("金額")

        if (not self.client_name_edit.text()
                and result.client_name
                and result.field_confidences.get('client_name', 0) >= threshold):
            self.client_name_edit.setText(_remove_repetition_pattern(result.client_name))
            filled.append("取引先")

        # 書類種別：コンボボックスのアイテムにキーワードが含まれるか検索
        if result.doc_type_hint and result.field_confidences.get('doc_type', 0) >= threshold:
            for i in range(self.document_type_combo.count()):
                if result.doc_type_hint in self.document_type_combo.itemText(i):
                    self.document_type_combo.setCurrentIndex(i)
                    filled.append("書類種別")
                    break

        # 学習データの適用（取引先名が判明している場合）
        issuer = self.client_name_edit.text().strip()
        learned_filled = self._apply_learning(file_path, issuer)
        filled.extend(learned_filled)

        if filled:
            self.extraction_status_label.setText(f"自動入力: {', '.join(filled)}")
            self.extraction_status_label.setStyleSheet("color: #2a7a2a;")
        else:
            self.extraction_status_label.setText(
                "テキストPDFですが、情報を自動抽出できませんでした。"
            )
            self.extraction_status_label.setStyleSheet("color: #888;")

    def _extract_client_from_ocr(self, file_path: str):
        """ページOCRキャッシュから企業名を抽出するフォールバック。
        キャッシュ未準備の場合は None を返す（バックグラウンドOCR完了時に再試行される）。"""
        if file_path not in self._page_ocr_cache:
            self._ensure_page_ocr(file_path)
            return None

        _CORP_SUFFIX = (
            r'(?:株式会社|有限会社|合同会社|合資会社|合名会社'
            r'|一般社団法人|公益社団法人|社会福祉法人|医療法人'
            r'|学校法人|協同組合|農業協同組合|信用組合|信用金庫)'
        )

        ocr_results = self._page_ocr_cache.get(file_path, [])
        recipient_names: set = set()
        issuer_names: list = []

        for r in ocr_results:
            text = (r.get('text') or '').strip()
            if not text:
                continue
            # 御中・様の直前は宛先なので発行元候補から除外
            if re.search(r'(?:御中|様)(?:\s|$)', text):
                m = re.search(rf'(.{{2,30}}?){_CORP_SUFFIX}', text)
                if m:
                    recipient_names.add(m.group(0).strip())
                continue
            # 接尾パターン: ○○株式会社
            m = re.search(rf'(.{{0,20}}{_CORP_SUFFIX})', text)
            if m:
                name = m.group(1).strip()
                if name not in recipient_names and 2 <= len(name) <= 30:
                    issuer_names.append(name)
                    continue
            # 接頭パターン: 株式会社○○
            m = re.search(rf'({_CORP_SUFFIX}.{{1,20}})', text)
            if m:
                name = m.group(1).strip()
                if name not in recipient_names and 2 <= len(name) <= 30:
                    issuer_names.append(name)

        return issuer_names[0] if issuer_names else None

    def _trigger_auto_extract(self):
        """「自動入力」ボタン押下時：フィールドをクリアして再抽出する"""
        self.clear_input_fields()
        self.last_ocr_regions = {}
        self.last_reg_number = None
        self.extraction_status_label.setText("")
        self._try_auto_extract(self.file_list_widget.currentItem())

    def _apply_learning(self, file_path: str, issuer: str) -> list[str]:
        """
        学習データを参照して書類種別とOCR領域を適用する。
        空フィールドのみ対象。適用したフィールド名のリストを返す。
        """
        if not issuer:
            return []
        suggestion = self.learning_manager.get_suggestion(issuer)
        if not suggestion:
            return []

        filled = []

        # 書類種別・取引区分の適用
        learned_doc_type = suggestion.get("doc_type")
        learned_tx_type = suggestion.get("transaction_type")
        if learned_doc_type and learned_tx_type:
            # 取引区分ラジオボタンを先に設定（コンボ内容が変わるため）
            from utils.constants import CATEGORY_EXPENDITURE, CATEGORY_INCOME
            if learned_tx_type == CATEGORY_EXPENDITURE:
                self.transaction_type_expenditure_radio.setChecked(True)
            elif learned_tx_type == CATEGORY_INCOME:
                self.transaction_type_income_radio.setChecked(True)
            else:
                self.transaction_type_other_org_radio.setChecked(True)
            self.update_document_types()

            for i in range(self.document_type_combo.count()):
                if self.document_type_combo.itemText(i) == learned_doc_type:
                    self.document_type_combo.setCurrentIndex(i)
                    filled.append(f"書類種別(学習)")
                    break

        # 学習済みOCR領域の自動適用
        ocr_regions = suggestion.get("ocr_regions", {})
        if ocr_regions:
            ocr_filled = self._apply_learned_ocr(file_path, ocr_regions)
            filled.extend(ocr_filled)

        return filled

    def _apply_learned_ocr(self, file_path: str, regions: dict) -> list[str]:
        """
        学習済みOCR領域を使って空フィールドを自動入力する。
        ページOCRキャッシュから領域フィルタで該当テキストを取得（個別小領域OCRは行わない）。
        """
        field_map = {
            'issue_date': self.issue_date_edit,
            'amount': self.amount_edit,
            'client_name': self.client_name_edit,
        }
        target_fields = {k: v for k, v in field_map.items() if k in regions and not v.text()}
        if not target_fields:
            return []
        # キャッシュ未準備ならスキップ（バックグラウンドOCR完了時に再試行される）
        if file_path not in self._page_ocr_cache:
            self._ensure_page_ocr(file_path)
            return []

        # ページサイズ取得（学習領域(比率) → ピクセル座標に変換するため）
        pdf_processor = PdfProcessor(file_path)
        if not pdf_processor.open():
            return []
        fitz_pixmap = pdf_processor.get_page_as_pixmap(0, scale_factor=self.ocr_scale_factor)
        pdf_processor.close()
        if not fitz_pixmap:
            return []
        pw, ph = fitz_pixmap.width, fitz_pixmap.height

        filled = []
        for field_name, field_widget in target_fields.items():
            region = regions.get(field_name)
            if not region or len(region) != 4:
                continue
            x = max(0, int(region[0] * pw))
            y = max(0, int(region[1] * ph))
            w = min(int(region[2] * pw), pw - x)
            h = min(int(region[3] * ph), ph - y)
            if w <= 0 or h <= 0:
                continue

            text = self._get_text_from_region(file_path, x, y, w, h)
            if not text:
                continue
            if field_widget is self.issue_date_edit:
                text = self.date_converter.to_seireki(text)
            elif field_widget is self.amount_edit:
                text = self.validator._normalize_amount_string(text)
            if text:
                field_widget.setText(text)
                filled.append(f"{field_name}(OCR学習)")

        return filled

    # ------------------------------------------------------------------
    # ページ単位OCRキャッシュ
    # ------------------------------------------------------------------

    def _ensure_page_ocr(self, file_path: str):
        """ファイルのページOCRを開始（既にキャッシュ済み or 進行中なら何もしない）。"""
        if not file_path:
            return
        if file_path in self._page_ocr_cache:
            return
        if file_path in self._page_ocr_workers:
            return
        try:
            pdf_processor = PdfProcessor(file_path)
            if not pdf_processor.open():
                return
            fitz_pixmap = pdf_processor.get_page_as_pixmap(0, scale_factor=self.ocr_scale_factor)
            pdf_processor.close()
            if not fitz_pixmap:
                return
            qimage = QImage(
                fitz_pixmap.samples, fitz_pixmap.width, fitz_pixmap.height,
                fitz_pixmap.stride, QImage.Format.Format_RGB888
            )
            pil_image = ImageQt.fromqimage(qimage)
        except Exception as e:
            logger.warning(f"ページ画像準備エラー: {e}")
            return

        worker = _PageOcrWorker(file_path, pil_image, self.config_manager)
        worker.done.connect(self._on_page_ocr_done)
        self._page_ocr_workers[file_path] = worker
        worker.start()

    def _finalize_page_ocr(self, file_path: str) -> bool:
        """ワーカーの結果をキャッシュに反映する。成功時 True を返す。"""
        worker = self._page_ocr_workers.get(file_path)
        if worker is None:
            return file_path in self._page_ocr_cache
        if not worker.isFinished():
            return False
        self._page_ocr_workers.pop(file_path, None)
        if worker.error_message:
            logger.warning(f"ページOCRエラー: {worker.error_message}")
            return False
        self._page_ocr_cache[file_path] = worker.results
        return True

    def _on_page_ocr_done(self, file_path: str):
        """ワーカー完了通知（メインスレッドで処理される）。"""
        if not self._finalize_page_ocr(file_path):
            return
        # 現在表示中ファイルなら学習適用と取引先名フォールバックを再試行
        current_item = self.file_list_widget.currentItem()
        if current_item and current_item.text() == file_path:
            # 取引先名がまだ空ならOCRキャッシュから抽出
            if not self.client_name_edit.text():
                ocr_client = self._extract_client_from_ocr(file_path)
                if ocr_client:
                    self.client_name_edit.setText(_remove_repetition_pattern(ocr_client))
            issuer = self.client_name_edit.text().strip()
            if issuer:
                self._apply_learning(file_path, issuer)

    def _wait_for_page_ocr_sync(self, file_path: str, timeout_ms: int = 120000) -> bool:
        """ページOCR完了を同期的に待ち、キャッシュに反映する。成功時 True。"""
        if file_path in self._page_ocr_cache:
            return True
        worker = self._page_ocr_workers.get(file_path)
        if worker is None:
            return False

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            main_win = self.window()
            if hasattr(main_win, 'status_bar'):
                main_win.status_bar.showMessage("OCR処理中...（数秒お待ちください）")
            worker.wait(timeout_ms)
            ok = self._finalize_page_ocr(file_path)
        finally:
            QApplication.restoreOverrideCursor()
        try:
            mw = self.window()
            if hasattr(mw, 'status_bar'):
                mw.status_bar.showMessage("OCR完了" if ok else "OCRエラー", 3000)
        except Exception:
            pass
        return ok

    def _get_text_from_region(self, file_path: str, x: int, y: int, w: int, h: int) -> str:
        """キャッシュされたOCR結果から、指定領域(高解像度ピクセル座標)に含まれる
        テキストを読み順で結合して返す。"""
        results = self._page_ocr_cache.get(file_path) or []
        if not results:
            return ""

        sel_right = x + w
        sel_bottom = y + h
        matched_strict: list = []   # box_ratio >= 0.5
        matched_loose: list = []    # box_ratio >= 0.2 (厳格条件でヒットなしの場合フォールバック)
        for r in results:
            bx = r.get('left', 0)
            by = r.get('top', 0)
            bw = r.get('width', 0)
            bh = r.get('height', 0)
            if bw <= 0 or bh <= 0:
                continue
            ov_x = max(0, min(bx + bw, sel_right) - max(bx, x))
            ov_y = max(0, min(by + bh, sel_bottom) - max(by, y))
            overlap = ov_x * ov_y
            if overlap <= 0:
                continue
            box_area = bw * bh
            box_ratio = overlap / box_area if box_area > 0 else 0
            if box_ratio >= 0.5:
                matched_strict.append(r)
            elif box_ratio >= 0.2:
                matched_loose.append(r)

        # 厳格条件でヒットした場合はそちらを優先。
        # ヒットゼロの場合（ユーザーが長いOCRラインの一部だけを選択した場合など）
        # のみ緩和条件の結果を採用する。
        selected = matched_strict if matched_strict else matched_loose

        # 読み順（上→下、左→右）
        selected.sort(key=lambda r: (r.get('top', 0), r.get('left', 0)))
        return _dedup_ocr_text([{'text': r.get('text', '')} for r in selected])

    def _field_to_name(self, field) -> str | None:
        """アクティブフィールドを学習キー名に変換する"""
        if field is self.issue_date_edit:
            return 'issue_date'
        if field is self.amount_edit:
            return 'amount'
        if field is self.client_name_edit:
            return 'client_name'
        return None

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
        issue_date = self.issue_date_edit.text()
        if len(issue_date) < 4:
            self.doc_id_label.setText("(発行日未入力)")
            return
        try:
            year_int = int(issue_date[:4])
            formatted_year = f"{year_int}年"
        except ValueError:
            self.doc_id_label.setText("(発行日形式エラー)")
            return

        transaction_type = self._get_transaction_type()
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
        issue_date = self.issue_date_edit.text()
        client_name = self.client_name_edit.text()
        amount = self.amount_edit.text()

        enabled = bool(issue_date and client_name and amount)
        self.save_button.setEnabled(enabled)

    def save_and_next(self):
        current_item = self.file_list_widget.currentItem()
        if not current_item:
            self._play_sound('warning')
            QMessageBox.warning(self, "注意", "処理対象のファイルが選択されていません。")
            return
        source_path = current_item.text()

        issue_date = self.issue_date_edit.text()
        client_name_raw = self.client_name_edit.text()
        amount_raw = self.amount_edit.text()
        memo = self.memo_edit.toPlainText()
        doc_type = self.document_type_combo.currentText()
        transaction_type = self._get_transaction_type()
        doc_id = self.doc_id_label.text()
        root_path = self.config_manager.get('Paths', 'root_save_directory')

        is_valid_amount, extracted_amount = self.validator.is_valid_amount(amount_raw)
        if not is_valid_amount:
            self._play_sound('error')
            QMessageBox.warning(self, "入力エラー", "金額には半角数字のみ入力してください。")
            return

        sanitized_client_name = re.sub(r'[\\/:*?"<>|]', '', client_name_raw)

        try:
            year_int = int(issue_date[:4])
            formatted_year = f"{year_int}年"
        except (ValueError, IndexError):
            self._play_sound('error')
            QMessageBox.warning(self, "入力エラー", "発行日の形式が正しくありません。(YYYYMMDD)")
            return

        new_filename = f"{doc_id}_{issue_date}_{extracted_amount}_{sanitized_client_name}.pdf"
        target_dir = os.path.join(root_path, formatted_year, transaction_type, doc_type)
        target_path = os.path.normpath(os.path.join(target_dir, new_filename))

        if os.path.exists(target_path):
            self._play_sound('warning')
            reply = QMessageBox.question(self, '重複ファイル', f"同じファイル名のファイルが既に存在します:\n{target_path}\n\n上書きしますか？",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Cancel:
                return

        message = (
            f"以下の内容で保存しますか？\n\n"
            f"元ファイル: {os.path.basename(source_path)}\n"
            f"保存先: {target_path}\n\n"
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
                    self._play_sound('error')
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

                # 学習: 書類種別・取引区分・OCR領域を記録
                self.learning_manager.learn_from_save(
                    client_name_raw, doc_type, transaction_type, self.last_ocr_regions
                )
                self.last_ocr_regions = {}
                # 学習: 登録番号→取引先名の紐付けを記録
                if self.last_reg_number and client_name_raw:
                    self.learning_manager.learn_reg_number(self.last_reg_number, client_name_raw)
                self.last_reg_number = None

                QMessageBox.information(self, "成功", f"ファイルを保存しました。\n{target_path}")

                # 元ファイルを処理済フォルダに移動
                try:
                    source_file_path = current_item.data(Qt.ItemDataRole.UserRole)
                    if source_file_path and os.path.exists(source_file_path):
                        moved_path = self.processed_file_manager.move_to_processed_folder(source_file_path)
                    else:
                        logger.warning(f"ソースファイルが見つかりません: {source_file_path}")
                except Exception as move_error:
                    logger.error(f"ファイル移動エラーの詳細: {move_error}")
                    QMessageBox.warning(self, "警告", f"ファイルの移動に失敗しました。\n元ファイル: {source_file_path}\nエラー: {move_error}")

                row = self.file_list_widget.row(current_item)
                self.file_list_widget.takeItem(row)

                self.clear_input_fields()
                self.select_next_file()

                self.config_manager.set_last_input('doc_type_index', str(self.document_type_combo.currentIndex()))

            except Exception as e:
                self._play_sound('error')
                QMessageBox.critical(self, "エラー", f"ファイルの保存に失敗しました。\n{e}")

    def clear_input_fields(self):
        self.issue_date_edit.clear()
        self.client_name_edit.clear()
        self.amount_edit.clear()
        self.memo_edit.clear()

    def _remove_from_list(self):
        """選択中のファイルを登録リストから除外する（ファイル自体は削除しない）"""
        current_item = self.file_list_widget.currentItem()
        if not current_item:
            return
        row = self.file_list_widget.row(current_item)
        self.file_list_widget.takeItem(row)
        self.select_next_file()

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
        apply_small_button_style(self.remove_file_button)
        apply_small_button_style(self.reload_doc_id_button)
        apply_small_button_style(self.register_client_button)
        apply_small_button_style(self.recall_client_button)
        apply_small_button_style(self.auto_fill_button)

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
