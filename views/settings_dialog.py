from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QFileDialog, QLabel, QHBoxLayout

class SettingsDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("設定")
        self.layout = QVBoxLayout(self)

        # Root Save Directory
        self.root_dir_layout = QHBoxLayout()
        self.root_dir_label = QLabel("ルート保存ディレクトリ:")
        self.root_dir_edit = QLineEdit()
        self.root_dir_button = QPushButton("参照")
        self.root_dir_button.clicked.connect(self.browse_root_dir)
        self.root_dir_layout.addWidget(self.root_dir_label)
        self.root_dir_layout.addWidget(self.root_dir_edit)
        self.root_dir_layout.addWidget(self.root_dir_button)
        self.layout.addLayout(self.root_dir_layout)

        # Buttons
        self.button_layout = QHBoxLayout()
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_settings)
        self.cancel_button = QPushButton("キャンセル")
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.cancel_button)
        self.layout.addLayout(self.button_layout)

        self.load_settings()

    def load_settings(self):
        root_dir = self.config_manager.get('Paths', 'root_save_directory')
        self.root_dir_edit.setText(root_dir)

    def browse_root_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "ルート保存ディレクトリを選択")
        if directory:
            self.root_dir_edit.setText(directory)

    def save_settings(self):
        root_dir = self.root_dir_edit.text()
        self.config_manager.set('Paths', 'root_save_directory', root_dir)
        self.accept()