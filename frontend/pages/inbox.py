from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
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
from repositories.provider import get_repository


class InboxPage(QWidget):
    """
    Director Secretary (DS) Incoming Communications & Document Intake Queue.

    IMPORTANT ARCHITECTURE RULE:
        DS Inbox is ONLY the external/mail intake queue.

        External mail
            -> DS Inbox
            -> Process
            -> Canonical Document
            -> Documents / Workflow

        Manual Upload
            -> Documents directly

        Director returned document
            -> Documents directly

    The general document/workflow queue must never be mixed into this page.
    """

    process_requested = Signal(object)

    def __init__(self):
        super().__init__()

        self.documents: List[Any] = []
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

        # ------------------------------------------------------------
        # HEADER
        # ------------------------------------------------------------
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        title = self._make_title("Incoming Communications")
        subtitle = self._make_subtitle(
            "External mail and dispatches awaiting Director Secretary processing"
        )

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header_row.addLayout(title_box)
        header_row.addStretch()

        self.sync_badge = self._make_badge("🟢 Ready")

        self.sync_outlook_btn = QPushButton("🔄 Sync Now")
        self.sync_outlook_btn.clicked.connect(self._sync_outlook)

        header_row.addWidget(self.sync_badge)
        header_row.addWidget(self.sync_outlook_btn)

        main_layout.addLayout(header_row)

        # ------------------------------------------------------------
        # FILTER BAR
        # ------------------------------------------------------------
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search sender, subject, source or communication type..."
        )
        self.search_input.textChanged.connect(self.apply_filters)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(
            [
                "All Incoming",
                "With Attached Files",
                "Email Body / No Attachment",
            ]
        )
        self.filter_combo.currentIndexChanged.connect(self.apply_filters)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_filters)

        filter_row.addWidget(self.search_input, 1)
        filter_row.addWidget(self.filter_combo)
        filter_row.addWidget(clear_btn)

        main_layout.addLayout(filter_row)

        # ------------------------------------------------------------
        # TABLE / EMPTY STATE
        # ------------------------------------------------------------
        self.table_stack = QStackedWidget()

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            [
                "Source",
                "Sender",
                "Subject",
                "Type",
                "Format",
                "Attachments",
                "Received",
                "Status",
            ]
        )

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellDoubleClicked.connect(
            lambda *_: self.process_selected()
        )

        self.empty_widget = EmptyStateWidget(
            "No Incoming Communications",
            "There are currently no external communications waiting for processing.",
        )

        self.table_stack.addWidget(self.table)
        self.table_stack.addWidget(self.empty_widget)

        main_layout.addWidget(self.table_stack, 1)

        # ------------------------------------------------------------
        # ACTION BAR
        # ------------------------------------------------------------
        action_row = QHBoxLayout()

        action_row.addStretch()

        self.process_button = QPushButton("Process Selected")
        self.process_button.setEnabled(False)
        self.process_button.clicked.connect(self.process_selected)

        action_row.addWidget(self.process_button)

        main_layout.addLayout(action_row)

        self.setLayout(main_layout)

    # ------------------------------------------------------------
    # SMALL UI HELPERS
    # ------------------------------------------------------------

    def _make_title(self, text: str):
        from PySide6.QtWidgets import QLabel

        label = QLabel(text)
        label.setObjectName("pageTitle")
        return label

    def _make_subtitle(self, text: str):
        from PySide6.QtWidgets import QLabel

        label = QLabel(text)
        label.setObjectName("pageSubtitle")
        return label

    def _make_badge(self, text: str):
        from PySide6.QtWidgets import QLabel

        label = QLabel(text)
        label.setObjectName("statusBadge")
        return label

    # ------------------------------------------------------------
    # LOAD DS INBOX
    # ------------------------------------------------------------

    def load_documents(self):
        """
        Load ONLY the external/mail intake queue.

        Do NOT use document_service.get_inbox() here because that endpoint
        represents workflow documents, not mailbox intake.

        The repository method get_intake_items() maps to:
            GET /api/v1/intake
        """

        try:
            repo = get_repository()
            intake_items = repo.get_intake_items()

        except Exception:
            self.documents = []
            self._displayed_docs = []

            self.sync_badge.setText("🔴 Backend unavailable")
            self.table_stack.setCurrentWidget(self.empty_widget)
            self.process_button.setEnabled(False)

            return

        normalized: List[Dict[str, Any]] = []

        for item in intake_items or []:
            if not isinstance(item, dict):
                continue

            source_type = str(
                item.get("source_type")
                or item.get("mode")
                or ""
            ).upper()

            # --------------------------------------------------------
            # MANUAL UPLOADS NEVER BELONG IN DS INBOX
            # --------------------------------------------------------
            if source_type in (
                "MANUAL_UPLOAD",
                "MANUAL",
                "MANUAL UPLOAD",
            ):
                continue

            processing_status = str(
                item.get("processing_status")
                or item.get("status")
                or "NEW"
            )

            # Backend already removes PROCESSED messages, but keep this
            # frontend guard as defense-in-depth.
            if processing_status.upper() == "PROCESSED":
                continue

            received_at = (
                item.get("received_at")
                or item.get("created_at")
                or ""
            )

            received_text = str(received_at)

            if "T" in received_text:
                received_text = received_text.split("T", 1)[0]

            sender_name = (
                item.get("sender_name")
                or item.get("sender_email")
                or "External"
            )

            subject = (
                item.get("subject")
                or f"Incoming Message #{item.get('id', '')}"
            )

            normalized.append(
                {
                    "id": item.get("id"),
                    "title": subject,
                    "source": sender_name,
                    "created_by": (
                        item.get("sender_email")
                        or item.get("sender_name")
                        or "External"
                    ),
                    "mode": (
                        item.get("source_type")
                        or "Government Mail"
                    ),
                    "format": "Email",
                    "file_type": "Email",
                    "attachment_count": (
                        1 if item.get("has_attachments") else 0
                    ),
                    "date": received_text,
                    "status": processing_status,
                    "sender_name": item.get("sender_name"),
                    "sender_email": item.get("sender_email"),
                    "subject": item.get("subject"),
                    "body": item.get("body_reference") or "",
                    "body_reference": item.get("body_reference"),
                    "external_message_id": item.get(
                        "external_message_id"
                    ),
                    "received_at": item.get("received_at"),
                    "has_attachments": bool(
                        item.get("has_attachments")
                    ),
                    "processing_status": processing_status,
                    "created_at": item.get("created_at"),
                    "file_path": "",
                }
            )

        self.documents = normalized
        self.sync_badge.setText("🟢 Ready")

        self.apply_filters()

    # ------------------------------------------------------------
    # FILTERS
    # ------------------------------------------------------------

    def apply_filters(self):
        search_query = self.search_input.text().strip().lower()
        filter_type = self.filter_combo.currentText()

        filtered: List[Any] = []

        for doc in self.documents:
            if isinstance(doc, DocumentModel):
                source = str(doc.source or "").lower()
                sender = str(doc.created_by or "").lower()
                title = str(doc.title or "").lower()
                mode = str(doc.mode or "").lower()
                att_cnt = doc.attachment_count or 0
            else:
                source = str(doc.get("source") or "").lower()
                sender = str(doc.get("created_by") or "").lower()
                title = str(doc.get("title") or "").lower()
                mode = str(doc.get("mode") or "").lower()
                att_cnt = doc.get("attachment_count") or 0

            if (
                filter_type == "With Attached Files"
                and att_cnt < 1
            ):
                continue

            if (
                filter_type == "Email Body / No Attachment"
                and att_cnt > 0
            ):
                continue

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
            self.table.setRowCount(0)
            self.table_stack.setCurrentWidget(self.empty_widget)
            self.process_button.setEnabled(False)
            return

        self.table_stack.setCurrentWidget(self.table)

        self.table.setRowCount(len(filtered))

        for row, doc in enumerate(filtered):
            if isinstance(doc, DocumentModel):
                source = doc.source or "External"
                sender = doc.created_by or source
                title = doc.title or ""
                mode = doc.mode or "Government Mail"
                fmt = doc.format or doc.file_type or "Email"
                att_cnt = doc.attachment_count or 0
                received = doc.date or "Today"
                status = doc.status or "NEW"
            else:
                source = doc.get("source") or "External"
                sender = (
                    doc.get("created_by")
                    or doc.get("sender_email")
                    or source
                )
                title = doc.get("title") or ""
                mode = doc.get("mode") or "Government Mail"
                fmt = (
                    doc.get("format")
                    or doc.get("file_type")
                    or "Email"
                )
                att_cnt = doc.get("attachment_count") or 0
                received = doc.get("date") or "Today"
                status = doc.get("status") or "NEW"

            if att_cnt > 1:
                att_str = f"📎 {att_cnt} attachments"
            elif att_cnt == 1:
                att_str = "📎 1 attachment"
            else:
                att_str = "No attachments"

            self.table.setItem(
                row,
                0,
                QTableWidgetItem(str(source)),
            )
            self.table.setItem(
                row,
                1,
                QTableWidgetItem(str(sender)),
            )
            self.table.setItem(
                row,
                2,
                QTableWidgetItem(str(title)),
            )
            self.table.setItem(
                row,
                3,
                QTableWidgetItem(str(mode)),
            )
            self.table.setItem(
                row,
                4,
                QTableWidgetItem(str(fmt)),
            )
            self.table.setItem(
                row,
                5,
                QTableWidgetItem(att_str),
            )
            self.table.setItem(
                row,
                6,
                QTableWidgetItem(str(received)),
            )

            status_item = QTableWidgetItem(str(status))
            status_item.setForeground(Qt.darkBlue)

            self.table.setItem(
                row,
                7,
                status_item,
            )

        self.process_button.setEnabled(
            self.table.currentRow() >= 0
        )

    def _clear_filters(self):
        self.search_input.clear()
        self.filter_combo.setCurrentIndex(0)

    # ------------------------------------------------------------
    # SELECTION / PROCESS
    # ------------------------------------------------------------

    def _on_selection_changed(self):
        self.process_button.setEnabled(
            self.table.currentRow() >= 0
        )

    def process_selected(self):
        row = self.table.currentRow()

        if row < 0 or row >= len(self._displayed_docs):
            QMessageBox.information(
                self,
                "No Document Selected",
                "Please select an incoming communication to process.",
            )
            return

        selected_item = self._displayed_docs[row]

        self.process_requested.emit(selected_item)

    # ------------------------------------------------------------
    # OUTLOOK AUTO SYNC
    # ------------------------------------------------------------

    def _background_autosync(self):
        try:
            from datetime import datetime

            repo = get_repository()
            result = repo.sync_outlook()

            status = result.get("status")
            now_str = datetime.now().strftime("%H:%M:%S")

            if status == "success":
                synced_cnt = result.get("synced_count", 0)

                if synced_cnt > 0:
                    self.sync_badge.setText(
                        f"🟢 Auto-Synced ({now_str}) • "
                        f"{synced_cnt} new mail(s)"
                    )
                    self.load_documents()
                else:
                    self.sync_badge.setText(
                        f"🟢 Auto-Synced ({now_str})"
                    )

            elif status == "not_configured":
                self.sync_badge.setText(
                    "⚪ Standby (Manual Mode)"
                )

        except Exception:
            pass

    def _sync_outlook(self):
        self.sync_outlook_btn.setEnabled(False)
        self.sync_outlook_btn.setText("⏳ Syncing...")

        try:
            from datetime import datetime

            repo = get_repository()
            result = repo.sync_outlook()

            status = result.get("status")
            message = result.get(
                "message",
                "Mailbox synchronization complete.",
            )

            now_str = datetime.now().strftime("%H:%M:%S")

            if status == "success":
                synced_cnt = result.get("synced_count", 0)

                self.sync_badge.setText(
                    f"🟢 Synced ({now_str}) • "
                    f"{synced_cnt} new mail(s)"
                )

                QMessageBox.information(
                    self,
                    "Outlook Synchronized",
                    message,
                )

            elif status == "not_configured":
                self.sync_badge.setText(
                    "⚪ Standby (Manual Mode)"
                )

                QMessageBox.information(
                    self,
                    "Outlook Notice",
                    f"{message}\n\n"
                    "Manual upload and existing intake "
                    "documents remain fully accessible.",
                )

            else:
                QMessageBox.warning(
                    self,
                    "Sync Issue",
                    message,
                )

            self.load_documents()

        except Exception as ex:
            QMessageBox.warning(
                self,
                "Sync Error",
                f"Could not complete Outlook sync:\n{ex}",
            )

        finally:
            self.sync_outlook_btn.setEnabled(True)
            self.sync_outlook_btn.setText("🔄 Sync Now")