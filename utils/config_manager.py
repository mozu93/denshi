import configparser
import logging

class ConfigManager:
    def __init__(self, config_path='config.ini'):
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        try:
            # config.iniの読み込み
            # - ファイルが存在しない、または読み取り権限がない場合にIOErrorが発生する可能性がある
            # - ファイルの内容がINI形式として不正な場合にParsingErrorが発生する可能性がある
            self.config.read(self.config_path, encoding='utf-8')
        except (IOError, configparser.Error) as e:
            # 読み込みに失敗した場合はログを出力し、空のコンフィグとして処理を続行する。
            # これにより、アプリケーション起動時に設定が読み込めなくてもクラッシュせず、
            # デフォルト値で動作し、終了時に新しい設定ファイルが作成されることを期待する。
            logging.error(f"設定ファイル '{self.config_path}' の読み込みに失敗しました: {e}")

    def get(self, section, key, fallback=None):
        # 指定されたセクションやキーが存在しない場合に備え、fallback値を提供する
        return self.config.get(section, key, fallback=fallback)

    def get_section(self, section):
        # 指定されたセクションが存在しない場合、空の辞書を返す
        if self.config.has_section(section):
            return dict(self.config.items(section))
        return {}

    def set_section(self, section, data):
        if self.config.has_section(section):
            self.config.remove_section(section)
        self.config.add_section(section)
        for key, value in data.items():
            # 値はすべて文字列に変換して保存する
            self.config.set(section, key, str(value))
        self.save()

    def set(self, section, key, value):
        if not self.config.has_section(section):
            self.config.add_section(section)
        # 値はすべて文字列に変換して保存する
        self.config.set(section, key, str(value))
        self.save()

    def save(self):
        try:
            # config.iniへの書き込み
            # - 書き込み権限がない場合にIOError/OSErrorが発生する可能性がある
            with open(self.config_path, 'w', encoding='utf-8') as configfile:
                self.config.write(configfile)
        except (IOError, OSError) as e:
            # 書き込み失敗はクリティカルなため、ログを出力し例外を再送出する。
            # 呼び出し元でこのエラーを捕捉し、ユーザーに通知する必要がある。
            logging.error(f"設定ファイル '{self.config_path}' の保存に失敗しました: {e}")
            raise RuntimeError(f"設定ファイルの保存に失敗しました: {e}")

    def get_last_input(self, key, fallback=None):
        return self.get('LastInputs', key, fallback=fallback)

    def set_last_input(self, key, value):
        self.set('LastInputs', key, value)
        # set()内でsave()が呼ばれるため、ここでは不要

    def get_tesseract_path(self):
        return self.get('Tesseract', 'Path', fallback='')

    def set_tesseract_path(self, path):
        self.set('Tesseract', 'Path', path)
