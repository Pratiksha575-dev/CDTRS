from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton
)

from PySide6.QtCore import Signal

from components.document_table import DocumentTable
from data.mock_data import DOCUMENTS


class DocumentsPage(QWidget):

    # Send selected document to MainWindow
    view_requested = Signal(dict, str)

    def __init__(self):
        super().__init__()

        self.all_documents = DOCUMENTS.copy()

        self.setup_ui()
        self.load_documents()

    def setup_ui(self):

        main_layout = QVBoxLayout()

        main_layout.setContentsMargins(
            30, 25, 30, 30
        )

        main_layout.setSpacing(15)

        # --------------------------------
        # HEADER
        # --------------------------------

        title = QLabel("Documents")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Search and review documents across the workflow."
        )
        subtitle.setObjectName("pageSubtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # --------------------------------
        # FILTER BAR
        # --------------------------------

        filter_layout = QHBoxLayout()

        self.status_filter = QComboBox()

        self.status_filter.addItems([
            "All Status",
            "New",
            "Director Review",
            "HOD Review",
            "In Progress",
            "Completed"
        ])

        self.department_filter = QComboBox()

        self.department_filter.addItems([
            "All Departments",
            "Finance",
            "Procurement",
            "HR",
            "FCTD",
            "Maintenance"
        ])

        self.source_filter = QComboBox()

        self.source_filter.addItems([
            "All Sources",
            "Outlook",
            "Fax",
            "Intranet",
            "Scanned"
        ])

        filter_button = QPushButton(
            "Apply Filters"
        )

        filter_button.clicked.connect(
            self.apply_filters
        )

        clear_button = QPushButton(
            "Clear"
        )

        clear_button.clicked.connect(
            self.clear_filters
        )

        filter_layout.addWidget(
            self.status_filter
        )

        filter_layout.addWidget(
            self.department_filter
        )

        filter_layout.addWidget(
            self.source_filter
        )

        filter_layout.addWidget(
            filter_button
        )

        filter_layout.addWidget(
            clear_button
        )

        filter_layout.addStretch()

        main_layout.addLayout(
            filter_layout
        )

        # --------------------------------
        # DOCUMENT TABLE
        # --------------------------------

        self.table = DocumentTable()

        self.table.document_selected.connect(
            self.document_selected
        )

        main_layout.addWidget(
            self.table
        )

        # --------------------------------
        # ACTIONS
        # --------------------------------

        action_layout = QHBoxLayout()

        action_layout.addStretch()

        self.view_button = QPushButton(
            "View Document"
        )

        self.view_button.clicked.connect(
            self.view_document
        )

        action_layout.addWidget(
            self.view_button
        )

        main_layout.addLayout(
            action_layout
        )

        self.setLayout(
            main_layout
        )

    # ====================================
    # LOAD
    # ====================================

    def load_documents(self):

        self.table.load_documents(
            self.all_documents
        )

    # ====================================
    # FILTER
    # ====================================

    def apply_filters(self):

        status = self.status_filter.currentText()
        department = self.department_filter.currentText()
        source = self.source_filter.currentText()

        filtered = []

        for document in self.all_documents:

            if (
                status != "All Status"
                and document["status"] != status
            ):
                continue

            if (
                department != "All Departments"
                and document["department"] != department
            ):
                continue

            if (
                source != "All Sources"
                and document["source"] != source
            ):
                continue

            filtered.append(document)

        self.table.load_documents(
            filtered
        )

    # ====================================
    # CLEAR FILTERS
    # ====================================

    def clear_filters(self):

        self.status_filter.setCurrentIndex(0)
        self.department_filter.setCurrentIndex(0)
        self.source_filter.setCurrentIndex(0)

        self.load_documents()

    # ====================================
    # SELECTION
    # ====================================

    def document_selected(self, document):

        self.selected_document = document

    # ====================================
    # VIEW DOCUMENT
    # ====================================

    def view_document(self):

        document = self.table.get_selected_document()

        if document is None:
            return

        # Send document + role to MainWindow
        self.view_requested.emit(
            document,
            "Master"
        )