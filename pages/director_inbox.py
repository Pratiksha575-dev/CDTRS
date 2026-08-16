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
from services.progress_service import progress_service


class DirectorInboxPage(QWidget):
    """
    Director Executive Review Inbox.
    Contains strictly documents routed to the Director by the Director Secretary (DS).
    Distinguishes Initial Review submissions from Employee Progress Follow-ups.
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
        title = QLabel("Director Review Inbox")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Executive review queue for incoming documents and employee progress follow-ups routed by Director Secretary.")
        subtitle.setObjectName("pageSubtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # --------------------------------
        # FILTER BAR
        # --------------------------------
        filter_layout = QHBoxLayout()

        self.category_filter = QComboBox()
        self.category_filter.addItems([
            "All Review Submissions",
            "Initial Reviews",
            "Progress Follow-ups"
        ])
        self.category_filter.currentIndexChanged.connect(self.apply_filter)

        filter_layout.addWidget(QLabel("Category:"))
        filter_layout.addWidget(self.category_filter)
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
            "Review Type",
            "Priority",
            "Source",
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
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        main_layout.addWidget(self.table)

        # --------------------------------
        # ACTIONS
        # --------------------------------
        action_layout = QHBoxLayout()
        action_layout.addStretch()

        self.review_btn = QPushButton("Review Document")
        self.review_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 8px 22px; border-radius: 5px;")
        self.review_btn.clicked.connect(self.review_document)
        action_layout.addWidget(self.review_btn)

        main_layout.addLayout(action_layout)
        self.setLayout(main_layout)

    # ====================================
    # LOAD INBOX
    # ====================================

    def load_inbox(self):
        """Loads documents currently routed to Director (Stage = DIRECTOR)."""
        all_docs = document_service.get_documents()
        self.documents = [
            d for d in all_docs
            if d.current_stage == WorkflowStageEnum.DIRECTOR.value or d.status == DocumentStatusEnum.UNDER_DIRECTOR_REVIEW.value
        ]
        self.apply_filter()

    def apply_filter(self):
        cat = self.category_filter.currentText()
        filtered = []

        for doc in self.documents:
            # Check if this document has progress updates attached
            has_progress = False
            if doc.id:
                updates = progress_service.get_progress_updates(doc.id)
                has_progress = len(updates) > 0

            review_type = "Progress Follow-up" if has_progress else "Initial Review"

            if cat == "Initial Reviews" and review_type != "Initial Review":
                continue
            if cat == "Progress Follow-ups" and review_type != "Progress Follow-up":
                continue

            filtered.append((doc, review_type))

        self.table.setRowCount(len(filtered))
        self._displayed_docs = [item[0] for item in filtered]

        for row, (doc, r_type) in enumerate(filtered):
            self.table.setItem(row, 0, QTableWidgetItem(doc.reference or "-"))
            self.table.setItem(row, 1, QTableWidgetItem(doc.title or "Untitled"))
            
            type_item = QTableWidgetItem(r_type)
            if r_type == "Progress Follow-up":
                type_item.setForeground(Qt.blue)
            self.table.setItem(row, 2, type_item)

            self.table.setItem(row, 3, QTableWidgetItem(doc.priority or "-"))
            self.table.setItem(row, 4, QTableWidgetItem(doc.source or "-"))
            self.table.setItem(row, 5, QTableWidgetItem(doc.deadline or "-"))
            self.table.setItem(row, 6, QTableWidgetItem(doc.status or "-"))

    # ====================================
    # VIEW / REVIEW DOCUMENT
    # ====================================

    def review_document(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(getattr(self, "_displayed_docs", [])):
            QMessageBox.information(self, "Selection Required", "Please select a document from the queue to review.")
            return

        selected_doc = self._displayed_docs[row]
        self.view_requested.emit(selected_doc, "Director")
