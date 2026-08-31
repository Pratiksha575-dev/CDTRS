from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
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
        self._displayed_docs: List[Any] = []
        self.setup_ui()

        from services.event_bus import event_bus
        event_bus.inbox_updated.connect(self.load_documents)
        event_bus.data_changed.connect(self.load_documents)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_documents()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 25, 30, 30)
        main_layout.setSpacing(14)

        # --------------------------------
        # PAGE HEADER & ACTIONS
        # --------------------------------
        header_row = QHBoxLayout()
        header_vbox = QVBoxLayout()
        header_vbox.setSpacing(2)

        title = QLabel("Incoming Communications & Intake")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Official incoming dispatches, government emails, and departmental communications awaiting DS intake and OCR extraction."
        )
        subtitle.setObjectName("pageSubtitle")

        header_vbox.addWidget(title)
        header_vbox.addWidget(subtitle)
        header_row.addLayout(header_vbox, 1)

        # Sync Status Badge
        self.sync_badge = QLabel("🟢 Ready")
        self.sync_badge.setStyleSheet(
            "background-color: #F0FDF4; color: #166534; border: 1px solid #BBF7D0; border-radius: 4px; padding: 6px 12px; font-size: 11px; font-weight: 600;"
        )
        header_row.addWidget(self.sync_badge)

        self.sync_outlook_btn = QPushButton("🔄 Sync Now")
        self.sync_outlook_btn.setStyleSheet(
            "background-color: #0F172A; color: white; font-weight: 600; padding: 8px 16px; border-radius: 5px; font-size: 12px;"
        )
        self.sync_outlook_btn.clicked.connect(self._sync_outlook)
        header_row.addWidget(self.sync_outlook_btn)

        main_layout.addLayout(header_row)

        # --------------------------------
        # SEARCH & FILTER BAR
        # --------------------------------
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search by sender, subject, reference, or keywords...")
        self.search_input.setStyleSheet("padding: 7px 12px; border: 1px solid #CBD5E1; border-radius: 5px; font-size: 12px;")
        self.search_input.textChanged.connect(self.apply_filters)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Incoming Items",
            "With Attached Files",
            "Email Body / No Attachment"
        ])
        self.filter_combo.setStyleSheet("padding: 6px 10px; border: 1px solid #CBD5E1; border-radius: 5px; font-size: 12px;")
        self.filter_combo.currentIndexChanged.connect(self.apply_filters)

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("background-color: #F1F5F9; border: 1px solid #CBD5E1; padding: 6px 14px; border-radius: 4px; font-weight: 600;")
        clear_btn.clicked.connect(self._clear_filters)

        filter_row.addWidget(self.search_input, 2)
        filter_row.addWidget(self.filter_combo, 1)
        filter_row.addWidget(clear_btn)
        main_layout.addLayout(filter_row)

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
        # Enable process button only when a row is actually selected
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

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
            title="No incoming documents found",
            message="All incoming mail, dispatches, and emails have been processed, or no items match your search."
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
        self.process_button.setEnabled(False)  # Disabled until a row is selected
        self.process_button.clicked.connect(self.process_selected)
        button_layout.addWidget(self.process_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)


    def load_documents(self):
        raw_inbox = document_service.get_inbox()
        # Strict Mail-Only Intake Queue: Only Outlook and Government Mail incoming communications
        self.documents = [
            d for d in raw_inbox
            if (d.mode if isinstance(d, DocumentModel) else (d.get("mode") or d.get("source_type"))) not in ("Manual Upload", "MANUAL_UPLOAD")
        ]
        self.apply_filters()

    def apply_filters(self):
        search_query = self.search_input.text().strip().lower()
        filter_type = self.filter_combo.currentText()

        filtered = []
        for doc in self.documents:
            source = str((doc.source if isinstance(doc, DocumentModel) else doc.get("source")) or "").lower()
            sender = str((doc.created_by if isinstance(doc, DocumentModel) else doc.get("created_by")) or "").lower()
            title = str((doc.title if isinstance(doc, DocumentModel) else doc.get("title")) or "").lower()
            mode = str((doc.mode if isinstance(doc, DocumentModel) else doc.get("mode")) or "").lower()
            att_cnt = (doc.attachment_count if isinstance(doc, DocumentModel) else doc.get("attachment_count")) or 0

            # Filter Dropdown (matching renamed labels)
            if filter_type == "With Attached Files" and att_cnt < 1:
                continue
            if filter_type == "Email Body / No Attachment" and att_cnt > 0:
                continue

            # Search Text Filter
            if search_query:
                match = (
                    search_query in source
                    or search_query in sender
                    or search_query in title
                    or search_query in mode
                )
                if not match:
                    continue

            filtered.append(doc)

        self._displayed_docs = filtered
        if not filtered:
            self.table_stack.setCurrentWidget(self.empty_widget)
            self.process_button.setEnabled(False)
            return

        self.table_stack.setCurrentWidget(self.table)
        # Don't auto-enable button here — only enable when a row is selected
        self.process_button.setEnabled(self.table.currentRow() >= 0)
        self.table.setRowCount(len(filtered))


        for row, doc in enumerate(filtered):
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

    def _clear_filters(self):
        self.search_input.clear()
        self.filter_combo.setCurrentIndex(0)

    def _on_selection_changed(self):
        """Enable process button only when a row is actually selected."""
        has_selection = self.table.currentRow() >= 0
        self.process_button.setEnabled(has_selection)

    def process_selected(self):
        """Emits selected intake item for OCR extraction and document processing."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self._displayed_docs):
            QMessageBox.information(
                self,
                "No Document Selected",
                "Please select an incoming document from the queue to process."
            )
            return

        selected_item = self._displayed_docs[row]
        self.process_requested.emit(selected_item)

    def _background_autosync(self):
        """Silently auto-syncs mailbox in background without intrusive popups."""
        try:
            from datetime import datetime
            from repositories.provider import get_repository
            repo = get_repository()
            result = repo.sync_outlook()

            status = result.get("status")
            now_str = datetime.now().strftime("%H:%M:%S")

            if status == "success":
                synced_cnt = result.get("synced_count", 0)
                if synced_cnt > 0:
                    self.sync_badge.setText(f"🟢 Auto-Synced ({now_str}) • {synced_cnt} new mail(s)")
                    self.load_documents()
                else:
                    self.sync_badge.setText(f"🟢 Auto-Synced ({now_str})")
            elif status == "not_configured":
                self.sync_badge.setText("⚪ Standby (Manual Mode)")
        except Exception:
            pass

    def _sync_outlook(self):
        """Triggers manual mailbox sync with responsive button state."""
        self.sync_outlook_btn.setEnabled(False)
        self.sync_outlook_btn.setText("⏳ Syncing...")
        try:
            from datetime import datetime
            from repositories.provider import get_repository
            repo = get_repository()
            result = repo.sync_outlook()

            status = result.get("status")
            message = result.get("message", "Mailbox synchronization complete.")
            now_str = datetime.now().strftime("%H:%M:%S")

            if status == "success":
                synced_cnt = result.get("synced_count", 0)
                self.sync_badge.setText(f"🟢 Synced ({now_str}) • {synced_cnt} new mail(s)")
                QMessageBox.information(self, "Outlook Synchronized", message)
            elif status == "not_configured":
                self.sync_badge.setText("⚪ Standby (Manual Mode)")
                QMessageBox.information(
                    self,
                    "Outlook Notice",
                    f"{message}\n\nManual upload and existing intake documents remain fully accessible."
                )
            else:
                QMessageBox.warning(self, "Sync Issue", message)

            self.load_documents()

        except Exception as ex:
            QMessageBox.warning(self, "Sync Error", f"Could not complete Outlook sync: {str(ex)}")
        finally:
            self.sync_outlook_btn.setEnabled(True)
            self.sync_outlook_btn.setText("🔄 Sync Now")
