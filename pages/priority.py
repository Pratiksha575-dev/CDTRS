from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QMessageBox
)

from PySide6.QtCore import Signal

from components.document_table import DocumentTable
from data.mock_data import DOCUMENTS


class PriorityPage(QWidget):

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

        title = QLabel(
            "Priority / Deadlines"
        )

        title.setObjectName(
            "pageTitle"
        )

        subtitle = QLabel(
            "Monitor document deadlines and send reminders."
        )

        subtitle.setObjectName(
            "pageSubtitle"
        )

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # --------------------------------
        # FILTER BAR
        # --------------------------------

        filter_layout = QHBoxLayout()

        self.priority_filter = QComboBox()

        self.priority_filter.addItems([
            "All Priority",
            "Red",
            "Orange",
            "Yellow",
            "Green"
        ])

        self.status_filter = QComboBox()

        self.status_filter.addItems([
            "All Status",
            "New",
            "Director Review",
            "HOD Review",
            "In Progress",
            "Completed"
        ])

        apply_button = QPushButton(
            "Apply Filters"
        )

        apply_button.clicked.connect(
            self.apply_filters
        )

        clear_button = QPushButton(
            "Clear"
        )

        clear_button.clicked.connect(
            self.clear_filters
        )

        filter_layout.addWidget(
            self.priority_filter
        )

        filter_layout.addWidget(
            self.status_filter
        )

        filter_layout.addWidget(
            apply_button
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

        self.view_button = QPushButton(
            "View Document"
        )

        self.view_button.clicked.connect(
            self.view_document
        )

        self.reminder_button = QPushButton(
            "Send Reminder"
        )

        self.reminder_button.clicked.connect(
            self.send_reminder
        )

        self.all_due_button = QPushButton(
            "Send All Due"
        )

        self.all_due_button.clicked.connect(
            self.send_all_due
        )

        action_layout.addWidget(
            self.view_button
        )

        action_layout.addStretch()

        action_layout.addWidget(
            self.reminder_button
        )

        action_layout.addWidget(
            self.all_due_button
        )

        main_layout.addLayout(
            action_layout
        )

        self.setLayout(
            main_layout
        )

    # ====================================
    # LOAD DOCUMENTS
    # ====================================

    def load_documents(self):

        self.table.load_documents(
            self.all_documents
        )

    # ====================================
    # FILTER
    # ====================================

    def apply_filters(self):

        priority = (
            self.priority_filter.currentText()
        )

        status = (
            self.status_filter.currentText()
        )

        filtered = []

        for document in self.all_documents:

            if (
                priority != "All Priority"
                and document["priority"] != priority
            ):
                continue

            if (
                status != "All Status"
                and document["status"] != status
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

        self.priority_filter.setCurrentIndex(0)
        self.status_filter.setCurrentIndex(0)

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
            "Master"
        )

    # ====================================
    # SEND REMINDER
    # ====================================

    def send_reminder(self):

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

        reference = document.get(
            "reference",
            "-"
        )

        QMessageBox.information(
            self,
            "Reminder",
            f"Reminder queued for {reference}."
        )

        print(
            f"Reminder sent for {reference}"
        )

    # ====================================
    # SEND ALL DUE
    # ====================================

    def send_all_due(self):

        due_documents = []

        for document in self.all_documents:

            if document.get("priority") in [
                "Red",
                "Orange"
            ]:

                due_documents.append(
                    document
                )

        if not due_documents:

            QMessageBox.information(
                self,
                "Reminders",
                "No due documents found."
            )

            return

        references = "\n".join(
            document.get(
                "reference",
                "-"
            )
            for document in due_documents
        )

        QMessageBox.information(
            self,
            "Reminders",
            "Reminders queued for:\n\n"
            + references
        )

        print(
            "Reminders sent for:",
            references
        )