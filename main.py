import sys
import os
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow

def get_base_path():
    """Get the base path for the application, whether running from source or as a bundle."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running as a PyInstaller bundle
        return sys._MEIPASS
    else:
        # Running from source
        return os.path.dirname(os.path.abspath(__file__))

def main():
    app = QApplication(sys.argv)
    
    base_path = get_base_path()
    config_path = os.path.join(base_path, 'config.ini')
    
    main_win = MainWindow(config_file=config_path)
    main_win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()