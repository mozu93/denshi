import configparser
import logging
import threading

class ConfigManager:
    def __init__(self, config_path='config.ini'):
        self.config_path = config_path
        # スレッドセーフなリエントラントロック（同一スレッドから複数回取得可能）
        self._lock = threading.RLock()
        self.config = configparser.ConfigParser()

        try:
            with self._lock:
                self.config.read(self.config_path, encoding='utf-8')
        except (IOError, configparser.Error) as e:
            logging.error(f"設定ファイル '{self.config_path}' の読み込みに失敗しました: {e}")

    def get(self, section, key, fallback=None):
        with self._lock:
            return self.config.get(section, key, fallback=fallback)

    def get_section(self, section):
        with self._lock:
            if self.config.has_section(section):
                return dict(self.config.items(section))
            return {}

    def set_section(self, section, data):
        with self._lock:
            if self.config.has_section(section):
                self.config.remove_section(section)
            self.config.add_section(section)
            for key, value in data.items():
                self.config.set(section, key, str(value))
            self._save_locked()

    def set(self, section, key, value):
        with self._lock:
            if not self.config.has_section(section):
                self.config.add_section(section)
            str_value = str(value)
            if '../' in str_value or '..' in str_value:
                logging.warning(f"危険なパス文字列が検出されました: {str_value}")
                str_value = str_value.replace('../', '').replace('..', '')
            self.config.set(section, key, str_value)
            self._save_locked()

    def _save_locked(self):
        """_lock 取得済みの状態から呼ぶ内部メソッド。"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as configfile:
                self.config.write(configfile)
        except (IOError, OSError) as e:
            logging.error(f"設定ファイル '{self.config_path}' の保存に失敗しました: {e}")
            raise RuntimeError(f"設定ファイルの保存に失敗しました: {e}")

    def save(self):
        with self._lock:
            self._save_locked()

    def get_last_input(self, key, fallback=None):
        return self.get('LastInputs', key, fallback=fallback)

    def set_last_input(self, key, value):
        self.set('LastInputs', key, value)

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
