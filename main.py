import sys
import os
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow

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

    # Set global font size
    font = app.font()
    font.setPointSize(14)
    
    base_path = get_base_path()
    config_path = os.path.join(base_path, 'config.ini')
    
    # Load and apply QSS stylesheet
    try:
        style_path = os.path.join(base_path, 'styles', 'main_style.qss')
        with open(style_path, "r", encoding='utf-8') as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Stylesheet not found. Using default style.")

    main_win = MainWindow(config_file=config_path)
    main_win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()