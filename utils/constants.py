# NASパス（初期デフォルト値）
HARDCODED_ROOT_SAVE_DIRECTORY = r"\\yc-nas01\Ycci共通\000全体業務\000職員共通\070電子帳簿保存法関係\電子帳簿保存"
HARDCODED_SHARED_CONFIG_PATH  = r"\\yc-nas01\Ycci共通\000全体業務\000職員共通\070電子帳簿保存法関係\電子帳簿保存\config.ini"

# 取引区分
CATEGORY_EXPENDITURE = "支出情報"
CATEGORY_INCOME      = "収入情報"
CATEGORY_OTHER_ORG   = "その他団体"
CATEGORIES = [CATEGORY_EXPENDITURE, CATEGORY_INCOME, CATEGORY_OTHER_ORG]

# フォントサイズ
DEFAULT_FONT_SIZE = 10
MIN_FONT_SIZE     = 8
MAX_FONT_SIZE     = 24

# 日付番兵値
DATE_UNSPECIFIED_YEAR = 1900

# アプリケーションパス取得関数
import sys
import os

def get_application_path():
    """
    アプリケーションのベースパスを取得します。

    Returns:
        str: 開発環境ではスクリプトのディレクトリ、
             インストール環境ではexeのあるディレクトリ
    """
    if getattr(sys, 'frozen', False):
        # PyInstallerでパッケージ化された環境
        if hasattr(sys, '_MEIPASS'):
            # One-file bundle: 一時展開ディレクトリ
            return sys._MEIPASS
        else:
            # One-folder bundle: exeのあるディレクトリ
            return os.path.dirname(sys.executable)
    else:
        # 開発環境: スクリプトのディレクトリ
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_tesseract_path():
    """
    Tesseract OCRのパスを取得します。

    Returns:
        str: 開発環境ではシステムインストールパス、
             インストール環境では同梱Tesseractのパス
    """
    if getattr(sys, 'frozen', False):
        # インストール環境: 同梱Tesseract
        app_path = get_application_path()
        return os.path.join(app_path, 'Tesseract-OCR', 'tesseract.exe')
    else:
        # 開発環境: システムインストール
        return r"C:/Program Files/Tesseract-OCR/tesseract.exe"
