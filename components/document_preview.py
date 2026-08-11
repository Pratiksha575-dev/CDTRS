from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel
)

from PySide6.QtCore import Qt


class DocumentPreview(QFrame):

    def __init__(self, document=None):
        super().__init__()

        self.document = document or {}

        self.setObjectName("contentCard")

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
            "Document Preview"
        )

        title.setObjectName(
            "sectionTitle"
        )

        layout.addWidget(title)

        # --------------------------------
        # PREVIEW AREA
        # --------------------------------

        self.preview_area = QLabel()

        self.preview_area.setAlignment(
            Qt.AlignCenter
        )

        self.preview_area.setMinimumSize(
            400,
            450
        )

        self.preview_area.setObjectName(
            "documentPreview"
        )

        self.update_preview()

        layout.addWidget(
            self.preview_area
        )

        self.setLayout(layout)

    # ====================================
    # UPDATE PREVIEW
    # ====================================

    def update_preview(self):

        file_path = self.document.get(
            "file_path",
            ""
        )

        file_type = self.document.get(
            "file_type",
            ""
        )

        if file_path:

            self.preview_area.setText(
                f"Document Preview\n\n"
                f"File: {file_path}\n\n"
                f"Type: {file_type}"
            )

        else:

            self.preview_area.setText(
                "Document Preview\n\n"
                "Actual PDF / image preview\n"
                "will appear here."
            )

    # ====================================
    # LOAD DOCUMENT
    # ====================================

    def set_document(self, document):

        self.document = document or {}

        self.update_preview()