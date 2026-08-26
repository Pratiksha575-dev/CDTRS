from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from components.state_widgets import EmptyStateWidget
from models.document import DocumentModel
from services.document_service import document_service


class InboxPage(QWidget):
    """
    Director Secretary (DS) Incoming Communications & Document Intake Queue.
    Displays incoming dispatches, government emails, and departmental communications
    awaiting OCR text extraction and canonical workflow registration.
    """

    process_requested = Signal(object)

    def __init__(self):
        super().__init__()
        self.documents: List[DocumentModel] = []
        self.setup_ui()
        self.load_documents()
        from services.event_bus import event_bus
        event_bus.inbox_updated.connect(self.load_documents)
        event_bus.data_changed.connect(self.load_documents)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_documents()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 25, 30, 30)
        main_layout.setSpacing(15)

        # --------------------------------
        # PAGE HEADER
        # --------------------------------
        title = QLabel("Incoming Communications & Intake")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Official incoming dispatches, government emails, and departmental communications awaiting DS intake and OCR extraction."
        )
        subtitle.setObjectName("pageSubtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # --------------------------------
        # TABLE & EMPTY STATE CONTAINER
        # --------------------------------
        self.table_stack = QStackedWidget()

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Source",
            "Sender / Origin",
            "Subject / Document Title",
            "Ingestion Mode",
            "Format",
            "Attachments",
            "Received",
            "Intake Status"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self.process_selected)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)

        self.empty_widget = EmptyStateWidget(
            title="No new incoming documents",
            message="All incoming mail, dispatches, and emails have been processed and registered."
        )

        self.table_stack.addWidget(self.table)
        self.table_stack.addWidget(self.empty_widget)
        main_layout.addWidget(self.table_stack, 1)

        # --------------------------------
        # BOTTOM ACTION BAR
        # --------------------------------
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.process_button = QPushButton("⚡ Run OCR & Process Document")
        self.process_button.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 8px 24px; border-radius: 5px;")
        self.process_button.clicked.connect(self.process_selected)
        button_layout.addWidget(self.process_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def load_documents(self):
        """Loads raw intake documents pending initial registration."""
        self.documents = document_service.get_inbox()

        if not self.documents:
            self.table_stack.setCurrentWidget(self.empty_widget)
            self.process_button.setEnabled(False)
            return

        self.table_stack.setCurrentWidget(self.table)
        self.process_button.setEnabled(True)
        self.table.setRowCount(len(self.documents))

        for row, doc in enumerate(self.documents):
            source = (doc.source if isinstance(doc, DocumentModel) else doc.get("source")) or "External"

            # Use actual sender data from backend — prefer created_by (email/username), fall back to source
            sender_label = (
                (doc.created_by if isinstance(doc, DocumentModel) else doc.get("created_by"))
                or source
                or "External Dispatch"
            )

            title = (doc.title if isinstance(doc, DocumentModel) else doc.get("title")) or ""
            mode = (doc.mode if isinstance(doc, DocumentModel) else doc.get("mode")) or "Government Mail"
            fmt = (doc.format or doc.file_type if isinstance(doc, DocumentModel) else doc.get("format", doc.get("file_type"))) or "PDF"

            att_cnt = (doc.attachment_count if isinstance(doc, DocumentModel) else doc.get("attachment_count")) or 0
            if att_cnt > 1:
                att_str = f"📎 {att_cnt} attachments"
            elif att_cnt == 1:
                att_str = "📎 1 attachment"
            else:
                att_str = "No attachments"

            received = (doc.date if isinstance(doc, DocumentModel) else doc.get("date")) or "Today"
            status = (doc.status if isinstance(doc, DocumentModel) else doc.get("status")) or "New / Received"

            self.table.setItem(row, 0, QTableWidgetItem(str(source)))
            self.table.setItem(row, 1, QTableWidgetItem(str(sender_label)))
            self.table.setItem(row, 2, QTableWidgetItem(str(title)))
            self.table.setItem(row, 3, QTableWidgetItem(str(mode)))
            self.table.setItem(row, 4, QTableWidgetItem(str(fmt or "PDF")))
            self.table.setItem(row, 5, QTableWidgetItem(str(att_str)))
            self.table.setItem(row, 6, QTableWidgetItem(str(received)))

            status_item = QTableWidgetItem(str(status))
            status_item.setForeground(Qt.darkBlue)
            self.table.setItem(row, 7, status_item)


    def process_selected(self):
        """Emits selected intake item for OCR extraction and document processing."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.documents):
            QMessageBox.information(
                self,
                "No Document Selected",
                "Please select an incoming document from the queue to process."
            )
            return

        selected_item = self.documents[row]
        self.process_requested.emit(selected_item)
