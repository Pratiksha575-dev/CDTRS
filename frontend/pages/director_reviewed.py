from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.document import DocumentModel
from services.document_service import document_service


class DirectorReviewedPage(QWidget):
    """
    Reviewed & Returned Documents Archive for the Director.
    Displays documents that have previously received executive review/remarks.
    Includes live search by title, reference, source, or department.
    """

    view_requested = Signal(object, str)

    def __init__(self):
        super().__init__()
        self.documents: List[DocumentModel] = []
        self._displayed_docs: List[DocumentModel] = []
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
        main_layout.setSpacing(14)

        # Header
        title = QLabel("Reviewed / Returned Documents")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Archive of documents previously reviewed and returned to Director Secretary.")
        subtitle.setObjectName("pageSubtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # --------------------------------
        # SEARCH BAR
        # --------------------------------
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search by title, reference, source, or director remark...")
        self.search_input.setStyleSheet("padding: 7px 12px; border: 1px solid #CBD5E1; border-radius: 5px; font-size: 12px;")
        self.search_input.textChanged.connect(self._apply_search)

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("background-color: #F1F5F9; border: 1px solid #CBD5E1; padding: 6px 14px; border-radius: 4px; font-weight: 600;")
        clear_btn.clicked.connect(self._clear_search)

        filter_layout.addWidget(self.search_input, 1)
        filter_layout.addWidget(clear_btn)
        main_layout.addLayout(filter_layout)

        # --------------------------------
        # TABLE
        # --------------------------------
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Reference No",
            "Title / Subject",
            "Source / Sender",
            "Director Remark (Preview)",
            "Status"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self._handle_view)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        main_layout.addWidget(self.table, 1)

        # Action Bar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        view_btn = QPushButton("View Document")
        view_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 7px 18px; border-radius: 5px;")
        view_btn.clicked.connect(self._handle_view)
        btn_layout.addWidget(view_btn)

        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

    def load_documents(self):
        """Filters documents that have been reviewed/returned by Director or have a Director Remark."""
        all_docs = document_service.get_documents()
        self.documents = [
            d for d in all_docs
            if (bool(d.director_remark) or d.status == "Director Review Completed")
            and d.current_stage != "DIRECTOR"
        ]
        self._apply_search()

    def _apply_search(self):
        """In-memory search filter across title, reference, source, and remark."""
        query = self.search_input.text().strip().lower()
        if not query:
            filtered = list(self.documents)
        else:
            filtered = [
                d for d in self.documents
                if query in (d.reference or "").lower()
                or query in (d.title or "").lower()
                or query in (d.source or "").lower()
                or query in (d.target_department_name or "").lower()
                or query in (d.director_remark or "").lower()
            ]

        self._displayed_docs = filtered
        self.table.setRowCount(len(filtered))
        for row, doc in enumerate(filtered):
            self.table.setItem(row, 0, QTableWidgetItem(doc.reference or "-"))
            self.table.setItem(row, 1, QTableWidgetItem(doc.title or "Untitled"))
            self.table.setItem(row, 2, QTableWidgetItem(doc.source or "-"))
            remark_preview = (doc.director_remark or "")[:80] + ("..." if len(doc.director_remark or "") > 80 else "")
            self.table.setItem(row, 3, QTableWidgetItem(remark_preview))
            self.table.setItem(row, 4, QTableWidgetItem(doc.status or "-"))

    def _clear_search(self):
        self.search_input.clear()

    def _handle_view(self):
        if getattr(self, "_action_busy", False):
            return
        self._action_busy = True
        try:
            row = self.table.currentRow()
            if row < 0 or row >= len(self._displayed_docs):
                return
            doc = self._displayed_docs[row]
            if doc:
                self.view_requested.emit(doc, "Director")
        finally:
            self._action_busy = False

