from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.document import DocumentModel
from models.enums import DocumentStatusEnum, WorkflowStageEnum
from services.auth_service import auth_service
from services.document_service import document_service
from services.progress_service import progress_service


class EmployeeTasksPage(QWidget):
    """
    Employee Tasks & Execution Queue.
    Displays documents assigned or routed specifically to the authenticated employee.
    Enforces strict employee isolation: an employee cannot see documents assigned to other employees.
    """

    view_requested = Signal(object, str)

    def __init__(self, employee_id: Optional[int] = None):
        super().__init__()
        self._custom_employee_id = employee_id
        self.documents: List[DocumentModel] = []
        self.setup_ui()
        self.load_tasks()
        from services.event_bus import event_bus
        event_bus.data_changed.connect(self.load_tasks)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_tasks()

    def get_authenticated_employee_id(self) -> Optional[int]:
        """Obtains the authenticated employee ID from the active user session."""
        if self._custom_employee_id is not None:
            return self._custom_employee_id
        current_user = auth_service.get_current_user()
        if current_user and current_user.id:
            return current_user.id
        return None

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 25, 30, 30)
        main_layout.setSpacing(15)

        # --------------------------------
        # HEADER
        # --------------------------------
        title = QLabel("My Tasks & Assigned Work")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Review assigned tasks from Department Head (HOD) or Director Secretary (DS) and submit progress updates.")
        subtitle.setObjectName("pageSubtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # --------------------------------
        # FILTER BAR
        # --------------------------------
        filter_layout = QHBoxLayout()

        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Assigned Tasks",
            "New Assignments",
            "In Progress / Updated",
            "High Priority / Urgent"
        ])
        self.filter_combo.currentIndexChanged.connect(self.apply_filter)

        filter_layout.addWidget(QLabel("Task Filter:"))
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addStretch()

        main_layout.addLayout(filter_layout)

        # --------------------------------
        # TABLE
        # --------------------------------
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Reference No",
            "Task / Subject",
            "Priority",
            "Department / Origin",
            "Deadline",
            "Status",
            "Stage"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        main_layout.addWidget(self.table)

        # --------------------------------
        # ACTION BAR
        # --------------------------------
        action_layout = QHBoxLayout()
        action_layout.addStretch()

        self.open_btn = QPushButton("Open Task / Submit Progress")
        self.open_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 8px 22px; border-radius: 5px;")
        self.open_btn.clicked.connect(self.open_task)
        action_layout.addWidget(self.open_btn)

        main_layout.addLayout(action_layout)
        self.setLayout(main_layout)

    def load_tasks(self):
        """
        Loads tasks assigned strictly to the authenticated employee.
        Enforces strict employee isolation: only includes tasks where assigned_employee_id == auth_id.
        """
        emp_id = self.get_authenticated_employee_id()
        all_docs = document_service.get_documents()

        if emp_id is None:
            self.documents = []
        else:
            self.documents = [
                d for d in all_docs
                if d.assigned_employee_id == emp_id
                and d.current_stage in (WorkflowStageEnum.EMPLOYEE.value, WorkflowStageEnum.CLOSED.value)
            ]

        self.apply_filter()

    def apply_filter(self):
        filter_text = self.filter_combo.currentText()
        filtered = []

        for doc in self.documents:
            p_updates = progress_service.get_progress_updates(doc.id) if doc.id else []
            has_progress = len(p_updates) > 0
            is_urgent = (doc.priority or "").lower() in ("red", "orange")

            if filter_text == "New Assignments" and has_progress:
                continue
            if filter_text == "In Progress / Updated" and not has_progress:
                continue
            if filter_text == "High Priority / Urgent" and not is_urgent:
                continue

            filtered.append(doc)

        self.table.setRowCount(len(filtered))
        self._displayed_docs = filtered

        for row, doc in enumerate(filtered):
            self.table.setItem(row, 0, QTableWidgetItem(doc.reference or "-"))
            self.table.setItem(row, 1, QTableWidgetItem(doc.title or "Untitled"))
            self.table.setItem(row, 2, QTableWidgetItem(doc.priority or "-"))
            self.table.setItem(row, 3, QTableWidgetItem(doc.department or doc.source or "-"))
            self.table.setItem(row, 4, QTableWidgetItem(doc.deadline or "-"))
            self.table.setItem(row, 5, QTableWidgetItem(doc.status or "-"))
            self.table.setItem(row, 6, QTableWidgetItem(doc.current_stage or "-"))

    def open_task(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(getattr(self, "_displayed_docs", [])):
            QMessageBox.information(self, "Selection Required", "Please select a task from the list to open.")
            return

        selected_doc = self._displayed_docs[row]
        self.view_requested.emit(selected_doc, "Employee")
