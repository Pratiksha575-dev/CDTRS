from datetime import datetime, timedelta
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from components.document_table import DocumentTable
from components.state_widgets import EmptyStateWidget
from models.document import DocumentModel
from models.enums import PriorityEnum, RoleEnum
from services.document_service import document_service


class DocumentsPage(QWidget):
    """
    Central Registered Documents Management Page for CDTRS.
    Provides comprehensive document exploration, search, priority badges, deadline tracking,
    departmental filtering, and DS reminder actions.
    """

    view_requested = Signal(object, str)

    def __init__(self, user_role: str = "Director Secretary"):
        super().__init__()
        self.user_role = RoleEnum.normalize(user_role)
        self.selected_document: Optional[DocumentModel] = None
        self.all_documents: List[DocumentModel] = []
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
        title = QLabel("Registered Documents")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Search, track deadlines, monitor priorities, and manage registered workflow documents across all departments.")
        subtitle.setObjectName("pageSubtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # --------------------------------
        # SEARCH & FILTER BAR
        # --------------------------------
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search title, ref #, or source...")
        self.search_input.textChanged.connect(self.apply_filters)

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

        self.priority_filter = QComboBox()
        self.priority_filter.addItems([
            "All Priorities",
            "High Priority",
            "Medium Priority",
            "Low Priority"
        ])
        self.priority_filter.currentIndexChanged.connect(self.apply_filters)

        self.deadline_filter = QComboBox()
        self.deadline_filter.addItems([
            "All Deadlines",
            "Due Within 7 Days",
            "Overdue"
        ])
        self.deadline_filter.currentIndexChanged.connect(self.apply_filters)

        self.department_filter = QComboBox()
        self.department_filter.addItems([
            "All Departments",
            "Finance",
            "Procurement",
            "HR",
            "FCTD",
            "Maintenance"
        ])
        self.department_filter.currentIndexChanged.connect(self.apply_filters)

        clear_button = QPushButton("Clear")
        clear_button.setStyleSheet("background-color: #F1F5F9; border: 1px solid #CBD5E1; padding: 5px 12px; border-radius: 4px; font-weight: 600;")
        clear_button.clicked.connect(self.clear_filters)

        filter_layout.addWidget(self.search_input, 2)
        filter_layout.addWidget(self.status_filter, 1)
        filter_layout.addWidget(self.priority_filter, 1)
        filter_layout.addWidget(self.deadline_filter, 1)
        filter_layout.addWidget(self.department_filter, 1)
        filter_layout.addWidget(clear_button)

        main_layout.addLayout(filter_layout)

        # --------------------------------
        # TABLE & EMPTY STATE STACK
        # --------------------------------
        self.content_stack = QStackedWidget()

        self.table = DocumentTable()
        self.table.document_selected.connect(self.on_document_selected)
        self.table.doubleClicked.connect(self.view_document)

        self.empty_widget = EmptyStateWidget(
            title="No registered documents found",
            message="No documents match the current search filters, or no dispatches have been registered yet."
        )

        self.content_stack.addWidget(self.table)
        self.content_stack.addWidget(self.empty_widget)
        main_layout.addWidget(self.content_stack, 1)

        # --------------------------------
        # ACTIONS BAR
        # --------------------------------
        action_layout = QHBoxLayout()
        action_layout.addStretch()

        if self.user_role in (RoleEnum.DIRECTOR_SECRETARY.value, "Director Secretary", "Master"):
            self.remind_button = QPushButton("⏰ Send Action Reminder")
            self.remind_button.setStyleSheet("background-color: #F8FAFC; color: #0F172A; border: 1px solid #CBD5E1; font-weight: 600; padding: 7px 16px; border-radius: 5px;")
            self.remind_button.clicked.connect(self.send_reminder)
            action_layout.addWidget(self.remind_button)

        self.view_button = QPushButton("View Document Details")
        self.view_button.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 7px 20px; border-radius: 5px;")
        self.view_button.clicked.connect(self.view_document)
        action_layout.addWidget(self.view_button)

        main_layout.addLayout(action_layout)
        self.setLayout(main_layout)

    def load_documents(self):
        self.all_documents = document_service.get_documents()
        self.apply_filters()

    def apply_filters(self):
        search_query = self.search_input.text().strip().lower()
        status_sel = self.status_filter.currentText()
        prio_sel = self.priority_filter.currentText()
        deadline_sel = self.deadline_filter.currentText()
        dept_sel = self.department_filter.currentText()

        filtered = list(self.all_documents)

        # 1. Search Query Filter
        if search_query:
            filtered = [
                d for d in filtered
                if search_query in (d.title or "").lower()
                or search_query in (d.reference or "").lower()
                or search_query in (d.source or "").lower()
            ]

        # 2. Status Filter
        if status_sel != "All Status":
            filtered = [d for d in filtered if (d.status or "").lower() == status_sel.lower()]

        # 3. Priority Filter
        if prio_sel == "High Priority":
            filtered = [d for d in filtered if (d.priority or "").lower() in ("high", "red")]
        elif prio_sel == "Medium Priority":
            filtered = [d for d in filtered if (d.priority or "").lower() in ("medium", "orange", "yellow")]
        elif prio_sel == "Low Priority":
            filtered = [d for d in filtered if (d.priority or "").lower() in ("low", "green")]

        # 4. Department Filter
        if dept_sel != "All Departments":
            filtered = [
                d for d in filtered
                if (d.department or d.target_department_name or "").lower() == dept_sel.lower()
            ]

        # 5. Deadline Filter
        if deadline_sel != "All Deadlines":
            today = datetime.now().date()
            due_soon_cutoff = today + timedelta(days=7)

            if deadline_sel == "Due Within 7 Days":
                filtered = [
                    d for d in filtered
                    if d.deadline and self._parse_date(d.deadline) and today <= self._parse_date(d.deadline) <= due_soon_cutoff
                ]
            elif deadline_sel == "Overdue":
                filtered = [
                    d for d in filtered
                    if d.deadline and self._parse_date(d.deadline) and self._parse_date(d.deadline) < today
                ]

        if not filtered:
            self.content_stack.setCurrentWidget(self.empty_widget)
            self.view_button.setEnabled(False)
        else:
            self.content_stack.setCurrentWidget(self.table)
            self.table.load_documents(filtered)
            self.view_button.setEnabled(True)

    def _parse_date(self, date_str: str):
        try:
            return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        except Exception:
            return None

    def clear_filters(self):
        self.search_input.clear()
        self.status_filter.setCurrentIndex(0)
        self.priority_filter.setCurrentIndex(0)
        self.deadline_filter.setCurrentIndex(0)
        self.department_filter.setCurrentIndex(0)
        self.load_documents()

    def on_document_selected(self, document):
        self.selected_document = document

    def view_document(self):
        doc = self.table.get_selected_document() or self.selected_document
        if not doc:
            QMessageBox.information(self, "No Selection", "Please select a document from the table.")
            return

        self.view_requested.emit(doc, self.user_role)

    def send_reminder(self):
        doc = self.table.get_selected_document() or self.selected_document
        if not doc:
            QMessageBox.information(self, "No Selection", "Please select a document to send a deadline reminder.")
            return

        ref = doc.reference if isinstance(doc, DocumentModel) else doc.get("reference", "Document")
        doc_id = doc.id if isinstance(doc, DocumentModel) else doc.get("id")

        from services.notification_service import notification_service
        recipient = notification_service.send_action_reminder(doc_id)
        if not recipient:
            status_str = (doc.status or "").lower() if isinstance(doc, DocumentModel) else (doc.get("status") or "").lower()
            if status_str == "closed":
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
            "Action Reminder Dispatched",
            f"Official deadline reminder successfully dispatched to {recipient['user_name']} ({recipient['role']}) for {ref}."
        )
