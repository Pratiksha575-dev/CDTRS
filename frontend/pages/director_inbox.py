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


class DirectorInboxPage(QWidget):
    """
    Director Executive Review Inbox.
    Contains documents routed to the Director by the Director Secretary (DS),
    with full search and filter choices including Initial Reviews, Follow-ups, and Reviewed Archive.
    """

    view_requested = Signal(object, str)

    def __init__(self):
        super().__init__()
        self.documents: List[DocumentModel] = []
        self._displayed_docs: List[DocumentModel] = []
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
        title = QLabel("Director Review Inbox")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Executive review queue for incoming documents and employee progress follow-ups routed by Director Secretary.")
        subtitle.setObjectName("pageSubtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # --------------------------------
        # SEARCH & FILTER BAR
        # --------------------------------
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search by title, reference, origin, department, priority...")
        self.search_input.setStyleSheet("padding: 7px 12px; border: 1px solid #CBD5E1; border-radius: 5px; font-size: 12px;")
        self.search_input.textChanged.connect(self.apply_filter)

        self.category_filter = QComboBox()
        self.category_filter.addItems([
            "All Active Reviews",
            "Initial Reviews",
            "Progress Follow-ups",
            "Reviewed & Returned to DS",
            "All Documents (Active & History)"
        ])
        self.category_filter.setStyleSheet("padding: 6px 10px; border: 1px solid #CBD5E1; border-radius: 5px; font-size: 12px;")
        self.category_filter.currentIndexChanged.connect(self.apply_filter)

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("background-color: #F1F5F9; border: 1px solid #CBD5E1; padding: 6px 14px; border-radius: 4px; font-weight: 600;")
        clear_btn.clicked.connect(self._clear_filters)

        filter_layout.addWidget(self.search_input, 2)
        filter_layout.addWidget(self.category_filter, 1)
        filter_layout.addWidget(clear_btn)

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
            "Source / Origin",
            "Deadline",
            "Status"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self.review_document)

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

        self.review_btn = QPushButton("Open / Review Document")
        self.review_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 8px 22px; border-radius: 5px;")
        self.review_btn.clicked.connect(self.review_document)
        action_layout.addWidget(self.review_btn)

        main_layout.addLayout(action_layout)
        self.setLayout(main_layout)

    # ====================================
    # LOAD INBOX & FAST FILTERING
    # ====================================

    def load_inbox(self):
        """Loads all accessible documents for Director."""
        self.documents = document_service.get_documents() or []
        self.apply_filter()

    def set_filters(self, category: Optional[str] = None, priority: Optional[str] = None, search: Optional[str] = None):
        """Programmatic filter setter used by dashboard navigation."""
        if category:
            for i in range(self.category_filter.count()):
                if category.lower() in self.category_filter.itemText(i).lower():
                    self.category_filter.setCurrentIndex(i)
                    break
        if search:
            self.search_input.setText(search)
        elif priority:
            self.search_input.setText(priority)
        self.apply_filter()

    def _clear_filters(self):
        self.search_input.clear()
        self.category_filter.setCurrentIndex(0)


    def apply_filter(self):
        cat = self.category_filter.currentText()
        query = self.search_input.text().strip().lower()
        filtered = []

        for doc in self.documents:
            is_active_dir = bool(
                doc.current_stage in (WorkflowStageEnum.DIRECTOR.value, "DIRECTOR", "Director")
                or doc.status in (DocumentStatusEnum.UNDER_DIRECTOR_REVIEW.value, "Under Director Review", "UNDER_DIRECTOR_REVIEW")
            )
            has_remark = bool(doc.director_remark)
            is_returned = bool(
                (has_remark or doc.status in (DocumentStatusEnum.DIRECTOR_REVIEW_COMPLETED.value, "Director Review Completed"))
                and not is_active_dir
            )
            is_progress = bool(
                doc.status in (DocumentStatusEnum.PROGRESS_UPDATED.value, DocumentStatusEnum.IN_PROGRESS.value)
                or getattr(doc, "has_progress_updates", False)
            )

            # Determine Review Type badge
            if is_progress:
                review_type = "Progress Follow-up"
            elif is_returned:
                review_type = "Reviewed & Returned"
            else:
                review_type = "Initial Review"

            # Category filter logic
            if cat == "All Active Reviews" and not is_active_dir:
                continue
            if cat == "Initial Reviews" and not (is_active_dir and not is_progress):
                continue
            if cat == "Progress Follow-ups" and not (is_active_dir and is_progress):
                continue
            if cat == "Reviewed & Returned to DS" and not is_returned:
                continue
            if cat == "All Documents (Active & History)":
                # Include both active review and documents director has reviewed
                if not (is_active_dir or is_returned or has_remark):
                    continue

            # Search text filter
            if query:
                ref = str(doc.reference or "").lower()
                title = str(doc.title or "").lower()
                source = str(doc.source or "").lower()
                dept = str(doc.target_department_name or doc.suggested_department_name or "").lower()
                prio = str(doc.priority or "").lower()
                remark = str(doc.director_remark or "").lower()

                if not (query in ref or query in title or query in source or query in dept or query in prio or query in remark):
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
            elif r_type == "Reviewed & Returned":
                type_item.setForeground(Qt.darkGreen)
            else:
                type_item.setForeground(Qt.darkMagenta)
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
