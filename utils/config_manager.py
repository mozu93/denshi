import configparser
import logging
from filelock import Timeout, FileLock

class ConfigManager:
    def __init__(self, config_path='config.ini'):
        self.config_path = config_path
        self.lock_path = self.config_path + ".lock"
        # タイムアウトを5秒に設定
        self.lock = FileLock(self.lock_path, timeout=5)
        self.config = configparser.ConfigParser()
        
        try:
            # 読み込み時にもロックを試みる
            with self.lock.acquire(timeout=5):
                self.config.read(self.config_path, encoding='utf-8')
        except Timeout:
            # 起動時に他のユーザーが編集中でも、とりあえず読み込みは試みる
            logging.warning(f"設定ファイル '{self.config_path}' のロックを取得できませんでした（読み込み時）。読み込みを続行します。")
            self.config.read(self.config_path, encoding='utf-8')
        except (IOError, configparser.Error) as e:
            logging.error(f"設定ファイル '{self.config_path}' の読み込みに失敗しました: {e}")

    def get(self, section, key, fallback=None):
        return self.config.get(section, key, fallback=fallback)

    def get_section(self, section):
        if self.config.has_section(section):
            return dict(self.config.items(section))
        return {}

    def set_section(self, section, data):
        if self.config.has_section(section):
            self.config.remove_section(section)
        self.config.add_section(section)
        for key, value in data.items():
            self.config.set(section, key, str(value))
        self.save()

    def set(self, section, key, value):
        if not self.config.has_section(section):
            self.config.add_section(section)
        str_value = str(value)
        if '../' in str_value or '..' in str_value:
            logging.warning(f"危険なパス文字列が検出されました: {str_value}")
            str_value = str_value.replace('../', '').replace('..', '')
        self.config.set(section, key, str_value)
        self.save()

    def save(self):
        try:
            # 書き込み時にロックを取得
            with self.lock.acquire(timeout=5):
                with open(self.config_path, 'w', encoding='utf-8') as configfile:
                    self.config.write(configfile)
        except Timeout:
            logging.warning(f"設定ファイル '{self.config_path}' のロック取得に失敗しました。")
            # ユーザーフレンドリーなエラーメッセージを投げる
            raise RuntimeError("他のユーザーが設定を編集中です。しばらくしてから再度お試しください。")
        except (IOError, OSError) as e:
            logging.error(f"設定ファイル '{self.config_path}' の保存に失敗しました: {e}")
            raise RuntimeError(f"設定ファイルの保存に失敗しました: {e}")

    def get_last_input(self, key, fallback=None):
        return self.get('LastInputs', key, fallback=fallback)

    def set_last_input(self, key, value):
        self.set('LastInputs', key, value)

    def get_tesseract_path(self):
        return self.get('Tesseract', 'Path', fallback='')

    def set_tesseract_path(self, path):
        self.set('Tesseract', 'Path', path)

    def get_ui_font_size(self, fallback=10):
        try:
            return int(self.get('UI', 'font_size', fallback=str(fallback)))
        except (ValueError, TypeError):
            return fallback

    def set_ui_font_size(self, size):
        self.set('UI', 'font_size', str(size))

    def get_window_size(self):
        width = self.get('UI', 'window_width', fallback='1200')
        height = self.get('UI', 'window_height', fallback='800')
        try:
            return int(width), int(height)
        except (ValueError, TypeError):
            return 1200, 800

    def set_window_size(self, width, height):
        self.set('UI', 'window_width', str(width))
        self.set('UI', 'window_height', str(height))

    def get_splitter_sizes(self, splitter_name):
        sizes_str = self.get('UI', f'{splitter_name}_sizes', fallback='')
        if sizes_str:
            try:
                return [int(s) for s in sizes_str.split(',')]
            except (ValueError, TypeError):
                pass
        return None

    def set_splitter_sizes(self, splitter_name, sizes):
        sizes_str = ','.join(str(s) for s in sizes)
        self.set('UI', f'{splitter_name}_sizes', sizes_str)

    def get_last_folder_path(self, fallback=''):
        return self.get('LastInputs', 'last_folder_path', fallback=fallback)

    def set_last_folder_path(self, folder_path):
        self.set('LastInputs', 'last_folder_path', folder_path)