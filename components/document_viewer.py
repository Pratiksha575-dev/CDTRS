from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox
)

from PySide6.QtCore import Signal

from components.document_preview import DocumentPreview
from components.document_info import DocumentInfo
from components.workflow_history import WorkflowHistory

from data.mock_data import HISTORY

from services.workflow_service import WorkflowService


class DocumentViewer(QWidget):

    close_requested = Signal()

    def __init__(
        self,
        document,
        role="Master"
    ):

        super().__init__()

        self.document = document
        self.role = role

        self.setup_ui()

    # ====================================
    # UI
    # ====================================

    def setup_ui(self):

        main_layout = QVBoxLayout()

        main_layout.setContentsMargins(
            30,
            25,
            30,
            30
        )

        main_layout.setSpacing(15)

        # =================================
        # HEADER
        # =================================

        header_layout = QHBoxLayout()

        title = QLabel(
            self.document.get(
                "subject",
                "Document"
            )
        )

        title.setObjectName(
            "pageTitle"
        )

        header_layout.addWidget(
            title
        )

        header_layout.addStretch()

        main_layout.addLayout(
            header_layout
        )

        # =================================
        # REFERENCE
        # =================================

        reference = QLabel(
            "Reference: "
            + self.document.get(
                "reference",
                "-"
            )
        )

        reference.setObjectName(
            "pageSubtitle"
        )

        main_layout.addWidget(
            reference
        )

        # =================================
        # PREVIEW + INFORMATION
        # =================================

        content_layout = QHBoxLayout()

        content_layout.setSpacing(20)

        self.preview = DocumentPreview(
            self.document
        )

        self.info = DocumentInfo(
            self.document
        )

        content_layout.addWidget(
            self.preview,
            2
        )

        content_layout.addWidget(
            self.info,
            1
        )

        main_layout.addLayout(
            content_layout
        )

        # =================================
        # WORKFLOW HISTORY
        # =================================

        document_reference = (
            self.document.get(
                "reference",
                ""
            )
        )

        document_history = HISTORY.get(
            document_reference,
            []
        )

        self.history = WorkflowHistory(
            document_history
        )

        main_layout.addWidget(
            self.history
        )

        # =================================
        # ACTIONS
        # =================================

        action_layout = QHBoxLayout()

        back_button = QPushButton(
            "Back"
        )

        back_button.clicked.connect(
            self.close_requested.emit
        )

        action_layout.addWidget(
            back_button
        )

        action_layout.addStretch()

        main_layout.addLayout(
            action_layout
        )

        # IMPORTANT
        # Attach layout to the viewer
        self.setLayout(
            main_layout
        )

    # ====================================
    # FORWARD TO DIRECTOR
    # ====================================

    def forward_to_director(self):

        print(
            "Forward button clicked"
        )

        print(
            "Selected document:",
            self.document
        )

        success = (
            WorkflowService.forward_to_director(
                self.document
            )
        )

        if success:

            QMessageBox.information(
                self,
                "Document Forwarded",
                (
                    "Document "
                    f"{self.document.get('reference', '')} "
                    "has been forwarded to the Director."
                )
            )

            self.close_requested.emit()

        else:

            QMessageBox.warning(
                self,
                "Forwarding Failed",
                "The document could not be forwarded."
            )