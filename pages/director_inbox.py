from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox
)

from PySide6.QtCore import Signal

from components.document_table import DocumentTable
from services.workflow_service import WorkflowService


class DirectorInboxPage(QWidget):

    view_requested = Signal(dict, str)

    def __init__(self):

        super().__init__()

        self.setup_ui()

        self.load_inbox()

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

        title = QLabel(
            "Director Inbox"
        )

        title.setObjectName(
            "pageTitle"
        )

        subtitle = QLabel(
            "Documents forwarded by the Master "
            "for Director review."
        )

        subtitle.setObjectName(
            "pageSubtitle"
        )

        main_layout.addWidget(
            title
        )

        main_layout.addWidget(
            subtitle
        )

        # =================================
        # TABLE
        # =================================

        self.table = DocumentTable()

        main_layout.addWidget(
            self.table
        )

        # =================================
        # ACTIONS
        # =================================

        action_layout = QHBoxLayout()

        refresh_button = QPushButton(
            "Refresh"
        )

        refresh_button.clicked.connect(
            self.load_inbox
        )

        view_button = QPushButton(
            "View Document"
        )

        view_button.clicked.connect(
            self.view_document
        )

        action_layout.addWidget(
            refresh_button
        )

        action_layout.addStretch()

        action_layout.addWidget(
            view_button
        )

        main_layout.addLayout(
            action_layout
        )

        self.setLayout(
            main_layout
        )

    # ====================================
    # LOAD DIRECTOR INBOX
    # ====================================

    def load_inbox(self):

        documents = (
            WorkflowService.get_director_inbox()
        )

        print(
            "Loading Director Inbox:",
            [
                d.get("reference")
                for d in documents
            ]
        )

        self.table.load_documents(
            documents
        )

    # ====================================
    # VIEW DOCUMENT
    # ====================================

    def view_document(self):

        document = (
            self.table.get_selected_document()
        )

        if document is None:

            QMessageBox.information(
                self,
                "No Selection",
                "Please select a document first."
            )

            return

        self.view_requested.emit(
            document,
            "Director"
        )