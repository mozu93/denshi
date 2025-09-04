from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit, 
    QPushButton, QDialogButtonBox
)

class EditDialog(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("データ編集")

        self.data = data

        # Layouts
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Fields
        self.client_name_edit = QLineEdit(data.get('client_name', ''))
        self.issue_date_edit = QLineEdit(str(data.get('issue_date', '')))
        self.amount_edit = QLineEdit(str(data.get('amount', '')))
        self.memo_edit = QTextEdit(data.get('memo', ''))

        form_layout.addRow("取引先名:", self.client_name_edit)
        form_layout.addRow("発行日 (YYYYMMDD):", self.issue_date_edit)
        form_layout.addRow("金額(税込):", self.amount_edit)
        form_layout.addRow("メモ:", self.memo_edit)

        layout.addLayout(form_layout)

        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.button_box)

    def get_updated_data(self):
        return {
            'client_name': self.client_name_edit.text(),
            'issue_date': self.issue_date_edit.text(),
            'amount': self.amount_edit.text(),
            'memo': self.memo_edit.toPlainText()
        }
