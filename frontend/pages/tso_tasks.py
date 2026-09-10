from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.document import DocumentModel
from services.document_service import document_service
from core.context.context_manager import context_manager


class TSOTasksPage(QWidget):
    """Operational TSO queue.

    The backend already scopes GET /documents to the active TSO context.
    Therefore this page deliberately does not apply Employee/HOD filters
    such as current_owner, department, or employee stage.
    """

    view_requested = Signal(object, str)

    def __init__(self):
        super().__init__()
        self.documents: List[DocumentModel] = []
        self._displayed_docs: List[DocumentModel] = []
        self.setup_ui()
        self.load_tasks()

        try:
            from services.event_bus import event_bus
            event_bus.data_changed.connect(lambda *_: self.load_tasks())
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self.load_tasks()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 25, 30, 30)
        layout.setSpacing(12)

        title = QLabel("TSO Documents & Tasks")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        context = context_manager.active_context()
        context_label = "TSO Workspace"
        if context is not None:
            context_label = (
                getattr(context, "display_name", None)
                or getattr(context, "context_name", None)
                or getattr(context, "label", None)
                or "TSO Workspace"
            )
        self.context_label = QLabel(f"Active Workspace: {context_label}")
        self.context_label.setObjectName("pageSubtitle")
        layout.addWidget(self.context_label)

        action_row = QHBoxLayout()
        action_row.addStretch()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_tasks)
        action_row.addWidget(refresh_btn)
        open_btn = QPushButton("Open Document")
        open_btn.clicked.connect(self.open_document)
        action_row.addWidget(open_btn)
        layout.addLayout(action_row)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Reference No",
            "Title / Subject",
            "Priority",
            "Source",
            "Deadline",
            "Status",
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(lambda *_: self.open_document())

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in range(2, 6):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_tasks(self):
        try:
            self.documents = list(document_service.get_documents() or [])
        except Exception as exc:
            print(f"[TSO TASKS] Failed to load TSO documents: {exc}")
            self.documents = []

        context = context_manager.active_context()
        context_label = "TSO Workspace"
        if context is not None:
            context_label = (
                getattr(context, "display_name", None)
                or getattr(context, "context_name", None)
                or getattr(context, "label", None)
                or "TSO Workspace"
            )
        self.context_label.setText(f"Active Workspace: {context_label}")
        self.apply_filter()

    def refresh(self):
        self.load_tasks()

    def apply_filter(self):
        self._displayed_docs = list(self.documents)
        self.table.setRowCount(len(self._displayed_docs))

        for row, doc in enumerate(self._displayed_docs):
            values = [
                getattr(doc, "reference", None) or "-",
                getattr(doc, "title", None) or "Untitled",
                getattr(doc, "priority", None) or "-",
                getattr(doc, "source", None) or "-",
                getattr(doc, "deadline", None) or "-",
                getattr(doc, "status", None) or "-",
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))

    def open_document(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._displayed_docs):
            QMessageBox.information(
                self,
                "Selection Required",
                "Please select a document from the TSO queue.",
            )
            return

        self.view_requested.emit(self._displayed_docs[row], "TSO")
