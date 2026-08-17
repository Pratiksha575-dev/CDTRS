from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from components.state_widgets import EmptyStateWidget
from models.document import DocumentModel
from models.workflow_event import WorkflowEventModel
from services.document_service import document_service
from services.workflow_service import workflow_service


def get_action_badge_colors(action: str) -> tuple:
    """Returns (background_color, text_color, border_color) for the action badge."""
    act = (action or "").lower()
    if "ingested" in act or "received" in act or "registered" in act:
        return "#ECFDF5", "#047857", "#A7F3D0"  # Emerald
    elif "closed" in act:
        return "#F1F5F9", "#334155", "#CBD5E1"  # Slate Dark
    elif "director" in act or "returned" in act or "executive" in act:
        return "#EEF2FF", "#4338CA", "#C7D2FE"  # Indigo
    elif "department" in act or "hod" in act:
        return "#E0F2FE", "#0369A1", "#BAE6FD"  # Sky Blue
    elif "staff" in act or "employee" in act or "assigned" in act:
        return "#F0FDF4", "#15803D", "#BBF7D0"  # Green
    elif "progress" in act or "update" in act or "follow-up" in act:
        return "#FEF3C7", "#B45309", "#FDE68A"  # Amber
    elif "attachment" in act or "file" in act:
        return "#F8FAFC", "#475569", "#E2E8F0"  # Slate
    else:
        return "#F1F5F9", "#1E293B", "#E2E8F0"  # Neutral


class DocumentAuditCard(QFrame):
    """
    Expandable document-centric audit card displaying the chronological timeline of events.
    """

    def __init__(self, doc: DocumentModel, events: List[WorkflowEventModel]):
        super().__init__()
        self.doc = doc
        self.events = events
        self.is_expanded = True
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("contentCard")
        self.setStyleSheet("""
            QFrame#contentCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        # Header bar
        header = QHBoxLayout()
        header.setSpacing(12)

        ref_lbl = QLabel(self.doc.reference or "-")
        ref_lbl.setStyleSheet("font-weight: bold; color: #0F172A; font-size: 14px;")

        title_lbl = QLabel(self.doc.title or "Untitled")
        title_lbl.setStyleSheet("color: #334155; font-size: 13px;")

        dept_lbl = QLabel(f"• {self.doc.department or self.doc.target_department_name or 'General'}")
        dept_lbl.setStyleSheet("color: #64748B; font-size: 12px;")

        stage_lbl = QLabel(f"[{self.doc.current_stage or 'DS'}]")
        stage_lbl.setStyleSheet("color: #2563EB; font-weight: 600; font-size: 11px;")

        header.addWidget(ref_lbl)
        header.addWidget(title_lbl)
        header.addWidget(dept_lbl)
        header.addWidget(stage_lbl)
        header.addStretch()

        self.toggle_btn = QPushButton(f"▲ Collapse ({len(self.events)} events)")
        self.toggle_btn.setStyleSheet("background-color: #F1F5F9; border: 1px solid #CBD5E1; color: #0F172A; font-weight: 600; font-size: 11px; padding: 4px 10px; border-radius: 4px;")
        self.toggle_btn.clicked.connect(self.toggle_expand)
        header.addWidget(self.toggle_btn)

        layout.addLayout(header)

        # Timeline container
        self.timeline_frame = QFrame()
        timeline_layout = QVBoxLayout(self.timeline_frame)
        timeline_layout.setContentsMargins(12, 8, 12, 8)
        timeline_layout.setSpacing(8)

        for ev in self.events:
            ev_row = QHBoxLayout()
            ev_row.setSpacing(12)

            time_lbl = QLabel(ev.timestamp or "-")
            time_lbl.setMinimumWidth(110)
            time_lbl.setMaximumWidth(140)
            time_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-family: monospace;")

            actor_lbl = QLabel(ev.performed_by_name or "System")
            actor_lbl.setMinimumWidth(150)
            actor_lbl.setMaximumWidth(220)
            actor_lbl.setWordWrap(True)
            actor_lbl.setStyleSheet("color: #0F172A; font-weight: 600; font-size: 12px;")

            action_lbl = QLabel(ev.action or "-")
            action_lbl.setMinimumWidth(160)
            action_lbl.setMaximumWidth(240)
            action_lbl.setWordWrap(True)
            action_lbl.setStyleSheet("color: #1E293B; font-weight: bold; font-size: 12px;")

            details_lbl = QLabel(ev.remarks or "-")
            details_lbl.setStyleSheet("color: #475569; font-size: 12px;")
            details_lbl.setWordWrap(True)

            ev_row.addWidget(time_lbl)
            ev_row.addWidget(actor_lbl)
            ev_row.addWidget(action_lbl)
            ev_row.addWidget(details_lbl, 1)

            timeline_layout.addLayout(ev_row)

        layout.addWidget(self.timeline_frame)

    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.timeline_frame.setVisible(self.is_expanded)
        if self.is_expanded:
            self.toggle_btn.setText(f"▲ Collapse ({len(self.events)} events)")
        else:
            self.toggle_btn.setText(f"▼ Expand ({len(self.events)} events)")


class HistoryPage(QWidget):
    """
    Document-Centric System History & Audit Trail.
    Presents chronological audit events organized by canonical registered document cards
    with expandable timeline streams and live reactive event updates.
    """

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.load_history()
        from services.event_bus import event_bus
        event_bus.data_changed.connect(self.load_history)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_history()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 25, 30, 30)
        main_layout.setSpacing(15)

        # --------------------------------
        # HEADER
        # --------------------------------
        title = QLabel("System History & Document Audit Trail")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Document-centric audit log tracking intake, executive reviews, departmental delegation, execution progress, and closures.")
        subtitle.setObjectName("pageSubtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # --------------------------------
        # FILTER BAR
        # --------------------------------
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Filter by title, reference #, or keyword...")
        self.search_input.textChanged.connect(self.load_history)

        self.role_filter = QComboBox()
        self.role_filter.addItems([
            "All Roles",
            "Director Secretary (DS)",
            "Director",
            "HOD",
            "Employee"
        ])
        self.role_filter.currentIndexChanged.connect(self.load_history)

        self.clear_button = QPushButton("✕ Clear Filters")
        self.clear_button.setStyleSheet("background-color: #FEF2F2; color: #DC2626; border: 1px solid #FCA5A5; padding: 5px 14px; border-radius: 4px; font-weight: 600;")
        self.clear_button.clicked.connect(self.clear_filters)
        self.clear_button.setVisible(False)

        filter_layout.addWidget(self.search_input, 2)
        filter_layout.addWidget(self.role_filter, 1)
        filter_layout.addWidget(self.clear_button)
        filter_layout.addStretch()

        main_layout.addLayout(filter_layout)

        # --------------------------------
        # CONTENT STACK & SCROLL AREA
        # --------------------------------
        self.content_stack = QStackedWidget()

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(12)
        self.cards_layout.addStretch()
        self.scroll_area.setWidget(self.cards_container)

        self.empty_widget = EmptyStateWidget(
            title="No workflow activity yet",
            message="Audit timeline events will appear here as documents are registered and progress through the system."
        )

        self.content_stack.addWidget(self.scroll_area)
        self.content_stack.addWidget(self.empty_widget)
        main_layout.addWidget(self.content_stack, 1)

        # --------------------------------
        # FOOTER
        # --------------------------------
        footer_layout = QHBoxLayout()
        self.count_label = QLabel("0 documents with audit activity")
        self.count_label.setObjectName("pageSubtitle")
        footer_layout.addWidget(self.count_label)
        footer_layout.addStretch()

        main_layout.addLayout(footer_layout)
        self.setLayout(main_layout)

    def load_history(self):
        # Clear existing cards
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        all_docs = document_service.get_documents()
        all_events = workflow_service.get_all_audit_history()

        # Update clear button visibility
        is_filtered = bool(self.search_input.text().strip()) or self.role_filter.currentIndex() > 0
        self.clear_button.setVisible(is_filtered)

        if not all_docs and not all_events:
            self.content_stack.setCurrentWidget(self.empty_widget)
            self.count_label.setText("0 documents with audit activity")
            return

        # Group events by document_id
        events_by_doc: Dict[int, List[WorkflowEventModel]] = {}
        for ev in all_events:
            events_by_doc.setdefault(ev.document_id, []).append(ev)

        search_query = self.search_input.text().strip().lower()
        role_sel = self.role_filter.currentText()

        card_count = 0
        total_events = 0

        for doc in all_docs:
            doc_evs = events_by_doc.get(doc.id, [])
            if not doc_evs:
                continue

            # Ensure strict chronological order (first event that occurred is first)
            doc_evs.sort(key=lambda e: (str(e.timestamp or ""), e.id or 0))

            # Role filter
            if role_sel != "All Roles":
                target_f = role_sel.lower()
                def _matches_role(event: WorkflowEventModel) -> bool:
                    fr = (event.from_role or "").strip().lower()
                    actor = (event.performed_by_name or "").strip().lower()
                    if "director secretary" in target_f or "ds" in target_f:
                        return fr in ("ds", "director secretary", "master") or "secretary" in actor or "ds" in actor
                    elif "director" in target_f:
                        return fr in ("director", "the director") and fr not in ("ds", "director secretary", "master")
                    elif "hod" in target_f:
                        return fr in ("hod", "head of department") or "hod" in actor
                    elif "employee" in target_f:
                        return fr in ("employee", "staff") or "emp" in actor or "rahul" in actor or "priya" in actor
                    return fr == target_f

                doc_evs = [e for e in doc_evs if _matches_role(e)]
                if not doc_evs:
                    continue

            # Search filter
            if search_query:
                matches_doc = (
                    search_query in (doc.title or "").lower()
                    or search_query in (doc.reference or "").lower()
                    or any(search_query in (e.remarks or "").lower() or search_query in (e.action or "").lower() for e in doc_evs)
                )
                if not matches_doc:
                    continue

            card = DocumentAuditCard(doc, doc_evs)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
            card_count += 1
            total_events += len(doc_evs)

        if card_count == 0:
            self.content_stack.setCurrentWidget(self.empty_widget)
            self.count_label.setText("0 documents matching filter")
        else:
            self.content_stack.setCurrentWidget(self.scroll_area)
            self.count_label.setText(f"{card_count} active document(s) with {total_events} chronological audit events")

    def clear_filters(self):
        self.search_input.clear()
        self.role_filter.setCurrentIndex(0)
        self.load_history()
