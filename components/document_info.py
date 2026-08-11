from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QFormLayout
)


class DocumentInfo(QFrame):

    def __init__(self, document=None):
        super().__init__()

        self.document = document or {}

        self.setObjectName(
            "contentCard"
        )

        self.setup_ui()

    def setup_ui(self):

        layout = QVBoxLayout()

        layout.setContentsMargins(
            20, 20, 20, 20
        )

        layout.setSpacing(12)

        # --------------------------------
        # TITLE
        # --------------------------------

        title = QLabel(
            "Document Information"
        )

        title.setObjectName(
            "sectionTitle"
        )

        layout.addWidget(title)

        # --------------------------------
        # INFORMATION
        # --------------------------------

        self.form = QFormLayout()

        self.form.setSpacing(10)

        self.fields = {}

        self.add_field(
            "Reference",
            "reference"
        )

        self.add_field(
            "Subject",
            "subject"
        )

        self.add_field(
            "Department",
            "department"
        )

        self.add_field(
            "Employee",
            "employee"
        )

        self.add_field(
            "Source",
            "source"
        )

        self.add_field(
            "Date",
            "date"
        )

        self.add_field(
            "Deadline",
            "deadline"
        )

        self.add_field(
            "Status",
            "status"
        )

        layout.addLayout(
            self.form
        )

        layout.addStretch()

        self.setLayout(layout)

    # ====================================
    # ADD FIELD
    # ====================================

    def add_field(self, label, key):

        value = QLabel(
            str(
                self.document.get(
                    key,
                    "-"
                )
            )
        )

        value.setWordWrap(True)

        self.fields[key] = value

        self.form.addRow(
            f"{label}:",
            value
        )

    # ====================================
    # UPDATE
    # ====================================

    def set_document(self, document):

        self.document = document or {}

        for key, label in self.fields.items():

            label.setText(
                str(
                    self.document.get(
                        key,
                        "-"
                    )
                )
            )