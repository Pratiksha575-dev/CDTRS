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
from services.document_service import document_service
from services.auth_service import auth_service



class HODInboxPage(QWidget):
    """
    Department Head (HOD) Inbox & Department Workload Queue.
    Displays documents routed to the department by DS, tracks employee assignment,
    and monitors execution progress updates.
    """

    view_requested = Signal(object, str)

    def __init__(self):
        super().__init__()
        self.documents: List[DocumentModel] = []
        self.setup_ui()
        self.load_inbox()
        from services.event_bus import event_bus
        event_bus.data_changed.connect(self.load_inbox)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_inbox()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 25, 30, 30)
        main_layout.setSpacing(14)

        # --------------------------------
        # HEADER
        # --------------------------------
        title = QLabel("Department Documents & Tasks")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Manage departmental documents routed by Director Secretary, delegate work to staff, and track progress.")
        subtitle.setObjectName("pageSubtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # --------------------------------
        # SEARCH & FILTER BAR
        # --------------------------------
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search by title, reference, staff, priority, status...")
        self.search_input.setStyleSheet("padding: 7px 12px; border: 1px solid #CBD5E1; border-radius: 5px; font-size: 12px;")
        self.search_input.textChanged.connect(self.apply_filter)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Active Documents",
            "Awaiting Assignment",
            "Assigned / In Progress",
            "Progress Updates Received",
            "Closed Documents"
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
            "Title / Subject",
            "Priority",
            "Assigned Employee",
            "Deadline",
            "Status"
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

        main_layout.addWidget(self.table)

        # --------------------------------
        # ACTION BAR
        # --------------------------------
        action_layout = QHBoxLayout()
        action_layout.addStretch()

        self.open_btn = QPushButton("Open Document / Assign")
        self.open_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 8px 22px; border-radius: 5px;")
        self.open_btn.clicked.connect(self.open_document)
        action_layout.addWidget(self.open_btn)

        main_layout.addLayout(action_layout)
        self.setLayout(main_layout)

    def load_inbox(self):
        """Loads documents routed to HOD's active department."""
        all_docs = document_service.get_documents()
        active_dept = auth_service.get_active_department()

        filtered_docs = []
        for d in all_docs:
            if d.current_stage in (WorkflowStageEnum.HOD.value, WorkflowStageEnum.EMPLOYEE.value, WorkflowStageEnum.CLOSED.value):
                if active_dept and d.target_department_name and d.target_department_name.upper() != active_dept.upper():
                    continue
                filtered_docs.append(d)

        self.documents = filtered_docs
        self.apply_filter()



    def _clear_filters(self):
        self.search_input.clear()
        self.filter_combo.setCurrentIndex(0)

    def apply_filter(self):
        filter_text = self.filter_combo.currentText()
        query = self.search_input.text().strip().lower()
        filtered = []

        for doc in self.documents:
            is_closed = doc.current_stage == WorkflowStageEnum.CLOSED.value or (doc.status or "").lower() == "closed"
            is_unassigned = doc.current_stage == WorkflowStageEnum.HOD.value and not doc.assigned_employee_name
            is_assigned = doc.current_stage == WorkflowStageEnum.EMPLOYEE.value or bool(doc.assigned_employee_name)
            is_progress = doc.status == DocumentStatusEnum.PROGRESS_UPDATED.value

            # Default "All Active Documents" excludes closed — must explicitly choose "Closed Documents"
            if filter_text == "All Active Documents" and is_closed:
                continue
            if filter_text == "Awaiting Assignment" and not is_unassigned:
                continue
            if filter_text == "Assigned / In Progress" and not (is_assigned and not is_progress):
                continue
            if filter_text == "Progress Updates Received" and not is_progress:
                continue
            if filter_text == "Closed Documents" and not is_closed:
                continue

            if query:
                ref = str(doc.reference or "").lower()
                title = str(doc.title or "").lower()
                emp = str(doc.assigned_employee_name or "").lower()
                prio = str(doc.priority or "").lower()
                status = str(doc.status or "").lower()

                if not (query in ref or query in title or query in emp or query in prio or query in status):
                    continue

            filtered.append(doc)

        self.table.setRowCount(len(filtered))
        self._displayed_docs = filtered

        for row, doc in enumerate(filtered):
            self.table.setItem(row, 0, QTableWidgetItem(doc.reference or "-"))
            self.table.setItem(row, 1, QTableWidgetItem(doc.title or "Untitled"))
            self.table.setItem(row, 2, QTableWidgetItem(doc.priority or "-"))

            emp_item = QTableWidgetItem(doc.assigned_employee_name or "— Unassigned —")
            if not doc.assigned_employee_name:
                emp_item.setForeground(Qt.red)
            self.table.setItem(row, 3, emp_item)

            self.table.setItem(row, 4, QTableWidgetItem(doc.deadline or "-"))
            self.table.setItem(row, 5, QTableWidgetItem(doc.status or "-"))


    def open_document(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(getattr(self, "_displayed_docs", [])):
            QMessageBox.information(self, "Selection Required", "Please select a document from the queue to open.")
            return

        selected_doc = self._displayed_docs[row]
        self.view_requested.emit(selected_doc, "HOD")
