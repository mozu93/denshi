# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QPalette


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.SplashScreen | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setFixedSize(420, 170)
        self._init_ui()
        self._center_on_screen()

    def _init_ui(self):
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#2c3e50"))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 16)
        layout.setSpacing(4)

        title = QLabel("電子帳簿保存システム")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Meiryo UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)

        from VERSION import __version__
        ver = QLabel(f"Version {__version__}")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setStyleSheet("color: #95a5a6; font-family: 'Meiryo UI'; font-size: 10px;")
        layout.addWidget(ver)

        layout.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                background: #34495e;
            }
            QProgressBar::chunk {
                background: #3498db;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("初期化中...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(
            "color: #bdc3c7; font-family: 'Meiryo UI'; font-size: 10px; padding-top: 2px;"
        )
        layout.addWidget(self.status_label)

    def update_progress(self, value: int, message: str):
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
        QApplication.processEvents()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                (geo.width() - self.width()) // 2,
                (geo.height() - self.height()) // 2,
            )
