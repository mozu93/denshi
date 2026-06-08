"""
UI統一スタイル定義

このモジュールでは、アプリケーション全体で使用される
統一されたUIスタイルを定義します。
"""

def get_app_style(font_size=10):
    """アプリケーション全体のスタイルを取得"""
    return f"""
        QWidget {{
            font-family: 'Meiryo UI', 'Meiryo', sans-serif;
            font-size: {font_size}pt;
            background-color: #e8e8e8;
        }}
        QLabel {{
            font-family: 'Meiryo UI', 'Meiryo', sans-serif;
            background-color: transparent;
        }}
        QLineEdit {{
            font-family: 'Meiryo UI', 'Meiryo', sans-serif;
            background-color: #ffffff;
            border: 1px solid #999999;
            padding: 4px;
            border-radius: 3px;
        }}
        QLineEdit:focus {{
            border-color: #4a90e2;
            background-color: #ffffff;
        }}
        QComboBox {{
            font-family: 'Meiryo UI', 'Meiryo', sans-serif;
            background-color: #ffffff;
            border: 1px solid #999999;
            padding: 4px;
            border-radius: 3px;
        }}
        QComboBox:focus {{
            border-color: #4a90e2;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
            background-color: #ffffff;
        }}
        QComboBox::down-arrow {{
            image: none;
            border: 2px solid #666666;
            width: 6px;
            height: 6px;
            border-top: none;
            border-left: none;
            margin-right: 5px;
        }}
        QTextEdit {{
            font-family: 'Meiryo UI', 'Meiryo', sans-serif;
            background-color: #ffffff;
            border: 1px solid #999999;
            padding: 4px;
            border-radius: 3px;
        }}
        QTextEdit:focus {{
            border-color: #4a90e2;
        }}
        QSpinBox {{
            font-family: 'Meiryo UI', 'Meiryo', sans-serif;
            background-color: #ffffff;
            border: 1px solid #999999;
            padding: 4px;
            border-radius: 3px;
        }}
        QSpinBox:focus {{
            border-color: #4a90e2;
        }}
        QDateEdit {{
            font-family: 'Meiryo UI', 'Meiryo', sans-serif;
            background-color: #ffffff;
            border: 1px solid #999999;
            padding: 4px;
            border-radius: 3px;
        }}
        QDateEdit:focus {{
            border-color: #4a90e2;
        }}
        QCalendarWidget {{
            font-family: 'Meiryo UI', 'Meiryo', sans-serif;
            background-color: #ffffff;
        }}
        QCalendarWidget QAbstractItemView {{
            background-color: #ffffff;
            color: #000000;
            selection-background-color: #b3e5fc;
            selection-color: #000000;
        }}
        QCalendarWidget QWidget {{
            color: #000000;
        }}
        QCalendarWidget QTableView {{
            background-color: #ffffff;
            color: #000000;
            gridline-color: #d0d0d0;
        }}
        QCalendarWidget QToolButton {{
            color: #000000;
            background-color: #f0f0f0;
            border: 1px solid #cccccc;
        }}
        QCalendarWidget QToolButton:hover {{
            background-color: #e0e0e0;
        }}
        QCalendarWidget QSpinBox {{
            color: #000000;
            background-color: #ffffff;
            border: 1px solid #cccccc;
        }}
        QCalendarWidget QMenu {{
            color: #000000;
            background-color: #ffffff;
        }}
        QGroupBox {{
            font-family: 'Meiryo UI', 'Meiryo', sans-serif;
            background-color: #e8e8e8;
            border: 1px solid #999999;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            background-color: #e8e8e8;
        }}
        QTableWidget {{
            font-family: 'Meiryo UI', 'Meiryo', sans-serif;
            background-color: #ffffff;
        }}
        QListWidget {{
            font-family: 'Meiryo UI', 'Meiryo', sans-serif;
            background-color: #ffffff;
        }}
    """

def get_button_style():
    """統一されたボタンスタイルを取得"""
    return """
        QPushButton {
            background-color: #cccccc;
            color: #333333;
            border: 1px solid #999999;
            padding: 5px 10px;
            border-radius: 4px;
            font-family: 'Meiryo UI', 'Meiryo', sans-serif;
            font-weight: normal;
        }
        QPushButton:hover {
            background-color: #b8b8b8;
            border-color: #808080;
        }
        QPushButton:pressed {
            background-color: #a4a4a4;
            border-color: #666666;
        }
        QPushButton:disabled {
            background-color: #f5f5f5;
            color: #9e9e9e;
            border-color: #e0e0e0;
        }
    """

def get_small_button_style():
    """小さなボタン用のスタイルを取得"""
    return """
        QPushButton {
            background-color: #cccccc;
            color: #333333;
            border: 1px solid #999999;
            padding: 3px 8px;
            border-radius: 3px;
            font-family: 'Meiryo UI', 'Meiryo', sans-serif;
            font-weight: normal;
        }
        QPushButton:hover {
            background-color: #b8b8b8;
            border-color: #808080;
        }
        QPushButton:pressed {
            background-color: #a4a4a4;
            border-color: #666666;
        }
        QPushButton:disabled {
            background-color: #f5f5f5;
            color: #9e9e9e;
            border-color: #e0e0e0;
        }
    """

def get_table_style():
    """テーブルの選択ハイライトスタイルを取得"""
    return """
        QTableWidget {
            selection-background-color: #b3e5fc;
            selection-color: #000000;
            gridline-color: #d0d0d0;
            background-color: #ffffff;
            alternate-background-color: #f5f5f5;
            font-family: 'Meiryo UI', 'Meiryo', sans-serif;
        }
        QTableWidget::item:selected {
            background-color: #b3e5fc;
            color: #000000;
        }
        QTableWidget::item:hover {
            background-color: #e1f5fe;
        }
        QHeaderView::section {
            background-color: #f0f0f0;
            padding: 4px;
            border: 1px solid #d0d0d0;
            font-weight: bold;
            font-family: 'Meiryo UI', 'Meiryo', sans-serif;
        }
    """

def get_list_widget_style():
    """リストウィジェットの選択ハイライトスタイルを取得"""
    return """
        QListWidget {
            selection-background-color: #b3e5fc;
            selection-color: #000000;
            background-color: #ffffff;
            border: 1px solid #d0d0d0;
            font-family: 'Meiryo UI', 'Meiryo', sans-serif;
        }
        QListWidget::item:selected {
            background-color: #b3e5fc;
            color: #000000;
        }
        QListWidget::item:hover {
            background-color: #e1f5fe;
        }
    """

def apply_app_style(app, font_size=10):
    """アプリケーション全体にスタイルを適用"""
    app.setStyleSheet(get_app_style(font_size))

def apply_button_style(button):
    """ボタンにスタイルを適用"""
    button.setStyleSheet(get_button_style())

def apply_small_button_style(button):
    """小さなボタンにスタイルを適用"""
    button.setStyleSheet(get_small_button_style())

def apply_table_style(table):
    """テーブルにスタイルを適用"""
    table.setStyleSheet(get_table_style())
    table.setAlternatingRowColors(True)

def apply_list_widget_style(list_widget):
    """リストウィジェットにスタイルを適用"""
    list_widget.setStyleSheet(get_list_widget_style())