from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
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
        self._displayed_docs: List[DocumentModel] = []
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
        main_layout.setSpacing(14)

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
        # SEARCH & FILTER BAR
        # --------------------------------
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search by task title, reference, sender/origin, priority, status...")
        self.search_input.setStyleSheet("padding: 7px 12px; border: 1px solid #CBD5E1; border-radius: 5px; font-size: 12px;")
        self.search_input.textChanged.connect(self.apply_filter)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Assigned Tasks",
            "Not Yet Started",
            "In Progress / Updated",
            "High Priority / Urgent"
        ])
        self.filter_combo.setStyleSheet("padding: 6px 10px; border: 1px solid #CBD5E1; border-radius: 5px; font-size: 12px;")
        self.filter_combo.currentIndexChanged.connect(self.apply_filter)

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("background-color: #F1F5F9; border: 1px solid #CBD5E1; padding: 6px 14px; border-radius: 4px; font-weight: 600;")
        clear_btn.clicked.connect(self._clear_filters)

        filter_layout.addWidget(self.search_input, 2)
        filter_layout.addWidget(self.filter_combo, 1)
        filter_layout.addWidget(clear_btn)

        main_layout.addLayout(filter_layout)

        # --------------------------------
        # TABLE
        # --------------------------------
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Reference No",
            "Task / Subject",
            "Priority",
            "Source / Origin",
            "Deadline",
            "HOD Remark"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self.open_task)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)


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
        Enforces strict employee isolation: only includes tasks where assigned_employee_id == auth_id
        or user is assigned via multi-department assignments.
        """
        emp_id = self.get_authenticated_employee_id()
        all_docs = document_service.get_documents()

        if emp_id is None:
            self.documents = []
        else:
            self.documents = [
                d for d in all_docs
                if (
                    d.assigned_employee_id == emp_id
                    or d.current_owner_id == emp_id
                    or getattr(d, "employee_id", None) == emp_id
                    or any(
                        isinstance(da, dict) and da.get("assigned_employee_id") == emp_id
                        for da in getattr(d, "doc_assignments", [])
                    )
                )
                and d.current_stage in (WorkflowStageEnum.EMPLOYEE.value, WorkflowStageEnum.CLOSED.value, "EMPLOYEE", "Employee", "Closed")
            ]

        self.apply_filter()

    def _clear_filters(self):
        self.search_input.clear()
        self.filter_combo.setCurrentIndex(0)

    def apply_filter(self):
        filter_text = self.filter_combo.currentText()
        query = self.search_input.text().strip().lower()
        filtered = []

        for doc in self.documents:
            has_progress = bool(
                doc.status == DocumentStatusEnum.PROGRESS_UPDATED.value
                or getattr(doc, "has_progress_updates", False)
            )
            is_urgent = (doc.priority or "").lower() in ("high", "urgent", "red")

            if filter_text == "Not Yet Started" and has_progress:
                continue
            if filter_text == "In Progress / Updated" and not has_progress:
                continue
            if filter_text == "High Priority / Urgent" and not is_urgent:
                continue

            if query:
                ref = str(doc.reference or "").lower()
                title = str(doc.title or "").lower()
                source = str(doc.source or doc.created_by or "").lower()
                prio = str(doc.priority or "").lower()
                status = str(doc.status or "").lower()
                hod_rem_text = str(doc.hod_remark or getattr(doc, "hod_instructions", "") or getattr(doc, "assignment_instructions", "") or "").lower()

                if not (query in ref or query in title or query in source or query in prio or query in status or query in hod_rem_text):
                    continue

            filtered.append(doc)

        self.table.setRowCount(len(filtered))
        self._displayed_docs = filtered

        for row, doc in enumerate(filtered):
            self.table.setItem(row, 0, QTableWidgetItem(doc.reference or "-"))
            self.table.setItem(row, 1, QTableWidgetItem(doc.title or "Untitled"))
            self.table.setItem(row, 2, QTableWidgetItem(doc.priority or "-"))
            self.table.setItem(row, 3, QTableWidgetItem(doc.source or "Official Dispatch"))
            self.table.setItem(row, 4, QTableWidgetItem(doc.deadline or "-"))
            # HOD Remark — shows the HOD's remark/guidance for this assignment
            hod_rem = doc.hod_remark or getattr(doc, "hod_instructions", None) or getattr(doc, "assignment_instructions", None) or "—"
            self.table.setItem(row, 5, QTableWidgetItem(str(hod_rem)))



    def open_task(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(getattr(self, "_displayed_docs", [])):
            QMessageBox.information(self, "Selection Required", "Please select a task from the list to open.")
            return

        selected_doc = self._displayed_docs[row]
        self.view_requested.emit(selected_doc, "Employee")
