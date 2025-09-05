import configparser

class ConfigManager:
    def __init__(self, config_path='config.ini'):
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self.config.read(self.config_path, encoding='utf-8')

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
        self.config.set(section, key, str(value))
        self.save()

    def save(self):
        with open(self.config_path, 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)

    def get_last_input(self, key, fallback=None):
        return self.get('LastInputs', key, fallback=fallback)

    def set_last_input(self, key, value):
        self.set('LastInputs', key, value)
        self.save()

    def get_tesseract_path(self):
        return self.get('Tesseract', 'Path', fallback='')

    def set_tesseract_path(self, path):
        self.set('Tesseract', 'Path', path)
