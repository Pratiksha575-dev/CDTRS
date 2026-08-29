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
from services.document_service import document_service


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
        main_layout.setSpacing(15)

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
        # FILTER BAR
        # --------------------------------
        filter_layout = QHBoxLayout()

        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Department Documents",
            "Awaiting Assignment",
            "Assigned / In Progress",
            "Progress Updated"
        ])
        self.filter_combo.currentIndexChanged.connect(self.apply_filter)

        filter_layout.addWidget(QLabel("Workload View:"))
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
            "Title / Subject",
            "Priority",
            "Assigned Employee",
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

        self.open_btn = QPushButton("Open Document / Assign")
        self.open_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 8px 22px; border-radius: 5px;")
        self.open_btn.clicked.connect(self.open_document)
        action_layout.addWidget(self.open_btn)

        main_layout.addLayout(action_layout)
        self.setLayout(main_layout)

    def load_inbox(self):
        """Loads documents formally routed to the authenticated HOD's department."""
        all_docs = document_service.get_documents()
        self.documents = [
            d for d in all_docs
            if d.current_stage in (WorkflowStageEnum.HOD.value, WorkflowStageEnum.EMPLOYEE.value, WorkflowStageEnum.CLOSED.value)
        ]
        self.apply_filter()

    def apply_filter(self):
        filter_text = self.filter_combo.currentText()
        filtered = []

        for doc in self.documents:
            is_unassigned = doc.current_stage == WorkflowStageEnum.HOD.value and not doc.assigned_employee_name
            is_assigned = doc.current_stage == WorkflowStageEnum.EMPLOYEE.value or bool(doc.assigned_employee_name)
            is_progress = doc.status == DocumentStatusEnum.PROGRESS_UPDATED.value

            if filter_text == "Awaiting Assignment" and not is_unassigned:
                continue
            if filter_text == "Assigned / In Progress" and not (is_assigned and not is_progress):
                continue
            if filter_text == "Progress Updated" and not is_progress:
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
            self.table.setItem(row, 6, QTableWidgetItem(doc.current_stage or "-"))

    def open_document(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(getattr(self, "_displayed_docs", [])):
            QMessageBox.information(self, "Selection Required", "Please select a document from the queue to open.")
            return

        selected_doc = self._displayed_docs[row]
        self.view_requested.emit(selected_doc, "HOD")
