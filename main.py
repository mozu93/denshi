import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from main_window import MainWindow
from utils.ui_styles import apply_app_style

def get_base_path():
    """Get the base path for the application, whether running from source or as a bundle."""
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundle
        if hasattr(sys, '_MEIPASS'):
            # One-file bundle
            return sys._MEIPASS
        else:
            # One-folder bundle
            return os.path.dirname(sys.executable)
    else:
        # Running from source
        return os.path.dirname(os.path.abspath(__file__))

def main():
    app = QApplication(sys.argv)

    # 作業ディレクトリをスクリプトの場所に変更（ダブルクリック起動対応）
    base_path = get_base_path()
    os.chdir(base_path)

    # Set global font to Meiryo
    font = QFont("Meiryo UI", 10)
    app.setFont(font)

    # Apply unified style
    apply_app_style(app)

    base_path = get_base_path()
    config_path = os.path.join(base_path, 'config.ini')

    main_win = MainWindow(config_file=config_path)
    main_win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()