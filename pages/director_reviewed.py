from typing import List, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from components.document_table import DocumentTable
from models.document import DocumentModel
from services.document_service import document_service


class DirectorReviewedPage(QWidget):
    """
    Reviewed & Returned Documents Archive for the Director.
    Displays documents that have previously received executive review/remarks.
    """

    view_requested = Signal(object, str)

    def __init__(self):
        super().__init__()
        self.documents: List[DocumentModel] = []
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

        # Header
        title = QLabel("Reviewed / Returned Documents")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Archive of documents previously reviewed and returned to Director Secretary.")
        subtitle.setObjectName("pageSubtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # Table
        self.table = DocumentTable()
        main_layout.addWidget(self.table)

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
        """Filters documents that have a Director Remark recorded."""
        all_docs = document_service.get_documents()
        self.documents = [d for d in all_docs if d.director_remark is not None and d.current_stage != "DIRECTOR"]
        self.table.load_documents(self.documents)

    def _handle_view(self):
        if getattr(self, "_action_busy", False):
            return
        self._action_busy = True
        try:
            doc = self.table.get_selected_document()
            if doc:
                self.view_requested.emit(doc, "Director")
        finally:
            self._action_busy = False
