import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from main_window import MainWindow
from utils.ui_styles import apply_app_style

SHARED_CONFIG_FILENAME = 'shared_config.path'

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

def get_config_path(base_path):
    """Get the path to the config file, checking for a shared config override."""
    shared_config_path_file = os.path.join(base_path, SHARED_CONFIG_FILENAME)
    if os.path.exists(shared_config_path_file):
        try:
            with open(shared_config_path_file, 'r', encoding='utf-8') as f:
                shared_path = f.read().strip()
                if os.path.exists(shared_path):
                    print(f"共有設定ファイルを読み込みます: {shared_path}")
                    return shared_path
                else:
                    print(f"警告: 共有設定ファイルが見つかりません: {shared_path}")
        except Exception as e:
            print(f"エラー: 共有設定ファイルの読み込みに失敗しました: {e}")

    # Fallback to local config file
    local_config_path = os.path.join(base_path, 'config.ini')
    print(f"ローカル設定ファイルを読み込みます: {local_config_path}")
    return local_config_path

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

    config_path = get_config_path(base_path)

    main_win = MainWindow(config_file=config_path)
    main_win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
