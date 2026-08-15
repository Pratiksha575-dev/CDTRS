from typing import List, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from components.document_table import DocumentTable
from models.document import DocumentModel
from models.enums import DocumentStatusEnum, WorkflowStageEnum
from services.document_service import document_service
from services.notification_service import notification_service


class PriorityPage(QWidget):
    """
    Priority and deadline monitoring page.
    Enables tracking of high-priority documents and centralized action reminders.
    """

    view_requested = Signal(object, str)

    def __init__(self):
        super().__init__()
        self.selected_document: Optional[DocumentModel] = None
        self.setup_ui()
        self.load_documents()
        from services.event_bus import event_bus
        event_bus.data_changed.connect(self.load_documents)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_documents()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 25, 30, 30)
        main_layout.setSpacing(15)

        # --------------------------------
        # HEADER
        # --------------------------------
        title = QLabel("Priority / Deadlines")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Monitor document deadlines and dispatch targeted action reminders.")
        subtitle.setObjectName("pageSubtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # --------------------------------
        # FILTER BAR
        # --------------------------------
        filter_layout = QHBoxLayout()

        self.priority_filter = QComboBox()
        self.priority_filter.addItems([
            "All Priority",
            "Urgent / High",
            "Red",
            "Orange",
            "Yellow",
            "Green"
        ])
        self.priority_filter.currentIndexChanged.connect(self.apply_filters)

        self.status_filter = QComboBox()
        self.status_filter.addItems([
            "All Status",
            "Received",
            "Under Director Review",
            "Director Review Completed",
            "Under HOD Processing",
            "Assigned for Execution",
            "In Progress",
            "Progress Updated",
            "Closed"
        ])
        self.status_filter.currentIndexChanged.connect(self.apply_filters)

        self.clear_button = QPushButton("✕ Clear Filters")
        self.clear_button.setStyleSheet("background-color: #FEF2F2; color: #DC2626; border: 1px solid #FCA5A5; padding: 5px 12px; border-radius: 4px; font-weight: 600;")
        self.clear_button.clicked.connect(self.clear_filters)
        self.clear_button.setVisible(False)

        filter_layout.addWidget(QLabel("Priority:"))
        filter_layout.addWidget(self.priority_filter)
        filter_layout.addWidget(QLabel("Status:"))
        filter_layout.addWidget(self.status_filter)
        filter_layout.addWidget(self.clear_button)
        filter_layout.addStretch()

        main_layout.addLayout(filter_layout)

        # --------------------------------
        # DOCUMENT TABLE
        # --------------------------------
        self.table = DocumentTable()
        self.table.document_selected.connect(self.document_selected)
        main_layout.addWidget(self.table)

        # --------------------------------
        # ACTIONS
        # --------------------------------
        action_layout = QHBoxLayout()

        self.view_button = QPushButton("View Document")
        self.view_button.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 7px 18px; border-radius: 5px;")
        self.view_button.clicked.connect(self.view_document)

        self.reminder_button = QPushButton("⏰ Send Action Reminder")
        self.reminder_button.setStyleSheet("background-color: #F8FAFC; color: #0F172A; border: 1px solid #CBD5E1; font-weight: 600; padding: 7px 16px; border-radius: 5px;")
        self.reminder_button.clicked.connect(self.send_reminder)

        self.all_due_button = QPushButton("📢 Send All Due Reminders")
        self.all_due_button.setStyleSheet("background-color: #F59E0B; color: white; font-weight: 600; padding: 7px 18px; border-radius: 5px;")
        self.all_due_button.clicked.connect(self.send_all_due)

        action_layout.addWidget(self.view_button)
        action_layout.addStretch()
        action_layout.addWidget(self.reminder_button)
        action_layout.addWidget(self.all_due_button)

        main_layout.addLayout(action_layout)
        self.setLayout(main_layout)

    def load_documents(self):
        docs = document_service.get_documents()
        self.table.load_documents(docs)

    def apply_filters(self):
        priority = self.priority_filter.currentText()
        status = self.status_filter.currentText()

        is_filtered = (self.priority_filter.currentIndex() > 0 or self.status_filter.currentIndex() > 0)
        self.clear_button.setVisible(is_filtered)

        all_docs = document_service.get_documents(
            status=status if status != "All Status" else None
        )

        if priority != "All Priority":
            if priority == "Urgent / High":
                docs = [d for d in all_docs if (d.priority or "").lower() in ("high", "urgent", "red", "orange")]
            else:
                docs = [d for d in all_docs if (d.priority or "").lower() == priority.lower()]
        else:
            docs = all_docs

        self.table.load_documents(docs)

    def clear_filters(self):
        self.priority_filter.setCurrentIndex(0)
        self.status_filter.setCurrentIndex(0)
        self.clear_button.setVisible(False)
        self.load_documents()

    def document_selected(self, document):
        self.selected_document = document

    def view_document(self):
        if getattr(self, "_action_busy", False):
            return
        self._action_busy = True
        try:
            document = self.table.get_selected_document() or self.selected_document
            if document is None:
                QMessageBox.information(self, "No Selection", "Please select a document first.")
                return

            self.view_requested.emit(document, "Director Secretary")
        finally:
            self._action_busy = False

    def send_reminder(self):
        if getattr(self, "_action_busy", False):
            return
        self._action_busy = True
        try:
            document = self.table.get_selected_document() or self.selected_document
            if document is None:
                QMessageBox.information(self, "No Selection", "Please select a document first.")
                return

            ref = getattr(document, "reference", None) or getattr(document, "reference_no", "-")
            doc_id = document.id if isinstance(document, DocumentModel) else getattr(document, "id", None)

            recipient = notification_service.send_action_reminder(doc_id)
            if not recipient:
                status_val = (getattr(document, "status", None) or "").lower()
                if status_val == DocumentStatusEnum.CLOSED.value.lower():
                    QMessageBox.information(
                        self,
                        "Document Closed",
                        f"Document {ref} is finalized and closed. Action reminders cannot be sent for closed documents."
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "No Recipient Available",
                        f"No downstream reminder recipient is currently available for document {ref}. Please route the document to a department or assign an employee first."
                    )
                return

            QMessageBox.information(
                self,
                "Reminder Dispatched",
                f"Action reminder successfully sent to {recipient['user_name']} ({recipient['role']}) for {ref}."
            )
        finally:
            self._action_busy = False

    def send_all_due(self):
        if getattr(self, "_action_busy", False):
            return
        self._action_busy = True
        try:
            dispatched = notification_service.send_all_due_reminders()
            if not dispatched:
                QMessageBox.information(self, "Reminders", "No actionable pending documents found for reminder dispatch.")
                return

            lines = [
                f"• {item['document'].reference} → {item['recipient']['user_name']} ({item['recipient']['role']})"
                for item in dispatched
            ]
            msg = f"Action reminders successfully dispatched for {len(dispatched)} document(s):\n\n" + "\n".join(lines)
            QMessageBox.information(self, "Reminders Dispatched", msg)
        finally:
            self._action_busy = False