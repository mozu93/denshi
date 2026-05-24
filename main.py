import sys
import os
import logging
import ctypes
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon
from main_window import MainWindow
from utils.ui_styles import apply_app_style
from utils.constants import HARDCODED_SHARED_CONFIG_PATH

logger = logging.getLogger(__name__)

# アプリケーションバージョン情報（VERSION.pyから取得）
from VERSION import __version__, __build_date__
APP_VERSION = __version__
APP_BUILD_DATE = __build_date__

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
    # ハードコードされた共有設定ファイルパスを優先的に使用
    if os.path.exists(HARDCODED_SHARED_CONFIG_PATH):
        logger.info(f"ハードコードされた共有設定ファイルを読み込みます: {HARDCODED_SHARED_CONFIG_PATH}")
        return HARDCODED_SHARED_CONFIG_PATH

    shared_config_path_file = os.path.join(base_path, SHARED_CONFIG_FILENAME)
    if os.path.exists(shared_config_path_file):
        try:
            with open(shared_config_path_file, 'r', encoding='utf-8') as f:
                shared_path = f.read().strip()
                if os.path.exists(shared_path):
                    logger.info(f"共有設定ファイルを読み込みます: {shared_path}")
                    return shared_path
                else:
                    logger.warning(f"共有設定ファイルが見つかりません: {shared_path}")
        except Exception as e:
            logger.error(f"共有設定ファイルの読み込みに失敗しました: {e}")

    # Fallback to local config file
    local_config_path = os.path.join(base_path, 'config.ini')
    logger.info(f"ローカル設定ファイルを読み込みます: {local_config_path}")
    return local_config_path

def main():
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s [%(name)s] %(levelname)s - %(message)s'
    )

    # Windowsタスクバーで独立したアプリアイコンを表示するために必要
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('mozu93.DenshiChobo.App')
    except Exception:
        pass

    app = QApplication(sys.argv)

    # 作業ディレクトリをスクリプトの場所に変更（ダブルクリック起動対応）
    base_path = get_base_path()
    os.chdir(base_path)

    # アプリアイコンを設定（タスクバー・ウィンドウ共通）
    icon_path = os.path.join(base_path, 'installer', 'icon.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Set global font to Meiryo
    font = QFont("Meiryo UI", 10)
    app.setFont(font)

    # Apply unified style
    apply_app_style(app)

    from views.splash_screen import SplashScreen
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    splash.update_progress(10, "設定ファイルを確認中...")
    config_path = get_config_path(base_path)

    splash.update_progress(20, "アプリケーションを初期化中...")
    try:
        main_win = MainWindow(
            config_file=config_path,
            progress_callback=splash.update_progress,
        )
        splash.update_progress(100, "準備完了")
        main_win.show()
    except Exception as e:
        logger.error(f"アプリケーションの起動に失敗しました: {e}", exc_info=True)
        splash.close()
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None, "起動エラー",
            f"アプリケーションの起動中にエラーが発生しました。\n\n{e}"
        )
        sys.exit(1)
    finally:
        splash.close()

    # Windows APIで直接HWNDにアイコンをセット（タスクバー反映に必要）
    if os.path.exists(icon_path):
        try:
            LR_LOADFROMFILE = 0x0010
            LR_DEFAULTSIZE  = 0x0040
            IMAGE_ICON      = 1
            WM_SETICON      = 0x0080
            hicon = ctypes.windll.user32.LoadImageW(
                None, icon_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE
            )
            if hicon:
                hwnd = int(main_win.winId())
                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 0, hicon)  # ICON_SMALL
                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, 1, hicon)  # ICON_BIG
        except Exception:
            pass

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
