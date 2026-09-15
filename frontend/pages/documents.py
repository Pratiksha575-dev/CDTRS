from datetime import datetime, timedelta
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from components.document_table import DocumentTable
from components.state_widgets import EmptyStateWidget
from models.document import DocumentModel
from models.enums import DocumentStatusEnum, PriorityEnum, RoleEnum
from services.document_service import document_service


class DocumentsPage(QWidget):
    """
    Central Registered Documents Management Page for CDTRS.

    Provides:
        - Document search
        - Status filtering
        - Priority filtering
        - Deadline filtering
        - Department filtering
        - Backend-powered department list
        - Document selection and viewing
        - DS action reminders

    Operational routing is NOT stored on DocumentModel through
    legacy fields such as current_stage, current_owner_id,
    target_department_id/name, or assigned_employee_id/name.

    Canonical routing/ownership is represented by:
        DocumentDepartmentRouting
            -> WorkAssignment
                -> ProgressUpdate
    """

    view_requested = Signal(object, str)

    def __init__(self, user_role: str = "DS"):
        super().__init__()

        self.user_role = RoleEnum.normalize(user_role)
        self.selected_document: Optional[DocumentModel] = None
        self.all_documents: List[DocumentModel] = []

        self.setup_ui()

        # Populate department dropdown from live backend.
        self._load_department_filter()

        self.load_documents()

        from services.event_bus import event_bus

        event_bus.data_changed.connect(self.load_documents)

    # =========================================================
    # LIFECYCLE
    # =========================================================

    def showEvent(self, event):
        super().showEvent(event)

        if not getattr(self, "_preserve_filters_once", False):
            self.load_documents()
        else:
            self._preserve_filters_once = False

    # =========================================================
    # UI
    # =========================================================

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(34, 28, 34, 30)
        main_layout.setSpacing(18)

        # Header
        header = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.setSpacing(4)

        title = QLabel("Registered Documents")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Search, monitor, and manage documents moving through the organisation's workflow."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)
        title_block.addWidget(title)
        title_block.addWidget(subtitle)

        self.document_count_label = QLabel("0 documents")
        self.document_count_label.setObjectName("documentCount")
        header.addLayout(title_block, 1)
        header.addWidget(self.document_count_label, 0, Qt.AlignTop)
        main_layout.addLayout(header)

        # Compact register status strip.
        # Documents is a management/listing workspace, so it intentionally
        # does not repeat the Dashboard's large operational KPI cards.
        register_strip = QFrame()
        register_strip.setObjectName("registerStrip")

        register_layout = QHBoxLayout(register_strip)
        register_layout.setContentsMargins(14, 9, 14, 9)
        register_layout.setSpacing(0)

        self.register_total_label = QLabel("0 documents")
        self.register_total_label.setObjectName("registerMetric")

        self.register_active_label = QLabel("0 active")
        self.register_active_label.setObjectName("registerMetric")

        self.register_high_label = QLabel("0 high priority")
        self.register_high_label.setObjectName("registerMetric")

        self.register_overdue_label = QLabel("0 overdue")
        self.register_overdue_label.setObjectName("registerMetric")

        for widget in (
            self.register_total_label,
            self.register_active_label,
            self.register_high_label,
            self.register_overdue_label,
        ):
            register_layout.addWidget(widget)
            register_layout.addSpacing(18)

        register_layout.addStretch()

        register_note = QLabel(
            "Double-click any row to open the document workflow"
        )
        register_note.setObjectName("registerNote")
        register_layout.addWidget(register_note)

        main_layout.addWidget(register_strip)

        # Filter panel
        filter_card = QFrame()
        filter_card.setObjectName("filterCard")
        filter_outer = QVBoxLayout(filter_card)
        filter_outer.setContentsMargins(16, 14, 16, 14)
        filter_outer.setSpacing(10)

        filter_heading = QHBoxLayout()
        filter_title = QLabel("Find a document")
        filter_title.setObjectName("filterTitle")
        filter_hint = QLabel("Use search and filters to narrow the list")
        filter_hint.setObjectName("filterHint")
        filter_heading.addWidget(filter_title)
        filter_heading.addWidget(filter_hint)
        filter_heading.addStretch()
        filter_outer.addLayout(filter_heading)

        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(9)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("documentSearch")
        self.search_input.setPlaceholderText("🔍  Search by title, reference number, or source...")
        self.search_input.setMinimumHeight(42)
        self.search_input.textChanged.connect(self.apply_filters)

        self.status_filter = self._create_filter_combo([
            "All Status",
            "Received",
            "Under Director Review",
            "Director Review Completed",
            "Returned to DS",
            "Under HOD Processing",
            "Assigned for Execution",
            "In Progress",
            "Progress Updated",
            "Closed",
        ])
        
        self.status_filter.currentIndexChanged.connect(self.apply_filters)
        self.priority_filter = self._create_filter_combo([
            "All Priorities", "High Priority", "Medium Priority", "Low Priority"
        ])
        self.priority_filter.currentIndexChanged.connect(self.apply_filters)
        self.deadline_filter = self._create_filter_combo([
            "All Deadlines", "Due Within 7 Days", "Overdue"
        ])
        self.deadline_filter.currentIndexChanged.connect(self.apply_filters)
        self.department_filter = self._create_filter_combo(["All Departments"])
        self.department_filter.currentIndexChanged.connect(self.apply_filters)

        clear_button = QPushButton("Reset")
        clear_button.setObjectName("secondaryButton")
        clear_button.setMinimumHeight(42)
        clear_button.setMinimumWidth(78)
        clear_button.clicked.connect(self.clear_filters)

        filter_layout.addWidget(self.search_input, 3)
        filter_layout.addWidget(self.status_filter, 1)
        filter_layout.addWidget(self.priority_filter, 1)
        filter_layout.addWidget(self.deadline_filter, 1)
        filter_layout.addWidget(self.department_filter, 1)
        filter_layout.addWidget(clear_button)
        filter_outer.addLayout(filter_layout)
        main_layout.addWidget(filter_card)

        # Table container
        table_card = QFrame()
        table_card.setObjectName("tableCard")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        table_header = QHBoxLayout()
        table_header.setContentsMargins(16, 12, 16, 10)
        table_title = QLabel("Document Register")
        table_title.setObjectName("tableTitle")
        self.result_label = QLabel("Showing 0 documents")
        self.result_label.setObjectName("resultLabel")
        table_header.addWidget(table_title)
        table_header.addStretch()
        table_header.addWidget(self.result_label)
        table_layout.addLayout(table_header)

        self.content_stack = QStackedWidget()
        self.table = DocumentTable()
        self.table.document_selected.connect(self.on_document_selected)
        # Double-click is intentionally available to every role.
        # view_document() delegates to MainWindow with the active role/context.
        self.table.doubleClicked.connect(self.view_document)
        self.empty_widget = EmptyStateWidget(
            title="No registered documents found",
            message="No documents match the current filters, or no dispatches have been registered yet."
        )
        self.content_stack.addWidget(self.table)
        self.content_stack.addWidget(self.empty_widget)
        table_layout.addWidget(self.content_stack, 1)
        main_layout.addWidget(table_card, 1)

        # Bottom actions
        action_card = QFrame()
        action_card.setObjectName("actionCard")
        action_layout = QHBoxLayout(action_card)
        action_layout.setContentsMargins(14, 10, 14, 10)
        action_hint = QLabel("Select a document to view its complete workflow details.")
        action_hint.setObjectName("actionHint")
        action_layout.addWidget(action_hint)
        action_layout.addStretch()

        if self.user_role in (RoleEnum.DS.value, "DS", "Master"):
            self.remind_button = QPushButton("⏰  Send Action Reminder")
            self.remind_button.setObjectName("secondaryButton")
            self.remind_button.setMinimumHeight(40)
            self.remind_button.clicked.connect(self.send_reminder)
            action_layout.addWidget(self.remind_button)

        self.view_button = QPushButton("View Document Details  →")
        self.view_button.setObjectName("primaryButton")
        self.view_button.setMinimumHeight(40)
        self.view_button.setMinimumWidth(190)
        self.view_button.setEnabled(False)
        self.view_button.clicked.connect(self.view_document)
        action_layout.addWidget(self.view_button)
        main_layout.addWidget(action_card)

        self.setLayout(main_layout)
        self.setStyleSheet(self.styleSheet() + """
            QLabel#documentCount {
                color: #334155;
                background: #FFFFFF;
                border: 1px solid #DCE3EC;
                border-radius: 16px;
                padding: 7px 13px;
                font-weight: 700;
            }

            QFrame#registerStrip {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }

            QLabel#registerMetric {
                color: #334155;
                font-size: 12px;
                font-weight: 700;
            }

            QLabel#registerNote {
                color: #94A3B8;
                font-size: 11px;
            }

            QFrame#filterCard {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 9px;
            }

            QFrame#tableCard {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 9px;
            }

            QFrame#actionCard {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 9px;
            }

            QLabel#filterTitle,
            QLabel#tableTitle {
                color: #0F172A;
                font-size: 14px;
                font-weight: 700;
            }

            QLabel#filterHint,
            QLabel#resultLabel,
            QLabel#actionHint {
                color: #64748B;
                font-size: 12px;
            }

            QLineEdit#documentSearch,
            QComboBox {
                min-height: 40px;
                background: #FFFFFF;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 7px;
                padding: 0 10px;
            }

            QLineEdit#documentSearch:focus,
            QComboBox:focus {
                border: 1px solid #64748B;
            }

            QPushButton#secondaryButton {
                background: #FFFFFF;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 7px;
                padding: 0 14px;
                font-weight: 600;
            }

            QPushButton#secondaryButton:hover {
                background: #F1F5F9;
            }

            QPushButton#primaryButton {
                background: #0F172A;
                color: #FFFFFF;
                border: 1px solid #0F172A;
                border-radius: 7px;
                padding: 0 16px;
                font-weight: 700;
            }

            QPushButton#primaryButton:hover {
                background: #1E293B;
            }

            QPushButton#primaryButton:disabled {
                background: #CBD5E1;
                border-color: #CBD5E1;
                color: #FFFFFF;
            }
        """)

    def _create_filter_combo(self, items):
        combo = QComboBox()
        combo.addItems(items)
        combo.setMinimumHeight(42)
        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return combo

    def _create_summary_card(self, label, value, hint):
        card = QFrame()
        card.setObjectName("summaryCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(2)
        label_widget = QLabel(label)
        label_widget.setStyleSheet("color:#64748B; font-size:10px; font-weight:700;")
        value_widget = QLabel(value)
        value_widget.setStyleSheet("color:#0F172A; font-size:22px; font-weight:800;")
        hint_widget = QLabel(hint)
        hint_widget.setStyleSheet("color:#94A3B8; font-size:10px;")
        hint_widget.setWordWrap(True)
        layout.addWidget(label_widget)
        layout.addWidget(value_widget)
        layout.addWidget(hint_widget)
        card._value_widget = value_widget
        return card

    def _refresh_summary(self, documents):
        """Refresh the compact register metrics."""
        total = len(documents)
        high = 0
        active = 0
        overdue = 0
        today = datetime.now().date()

        for document in documents:
            priority = str(
                getattr(document, "priority", "") or ""
            ).lower()
            status = str(
                getattr(document, "status", "") or ""
            ).lower()

            if priority in ("high", "red"):
                high += 1

            if status not in (
                "closed",
                "director review completed",
            ):
                active += 1

            deadline = getattr(document, "deadline", None)
            parsed = self._parse_date(deadline) if deadline else None

            if (
                parsed
                and parsed < today
                and status != "closed"
            ):
                overdue += 1

        self.register_total_label.setText(
            f"{total} document{'s' if total != 1 else ''}"
        )
        self.register_active_label.setText(f"{active} active")
        self.register_high_label.setText(f"{high} high priority")
        self.register_overdue_label.setText(f"{overdue} overdue")

        self.document_count_label.setText(
            f"{total} document{'s' if total != 1 else ''}"
        )

    # =========================================================
    # DOCUMENT LOADING
    # =========================================================

    def load_documents(self):
        try:
            self.all_documents = (
                document_service.get_documents()
            )
        except Exception as exc:
            self.all_documents = []

            QMessageBox.warning(
                self,
                "Unable to Load Documents",
                f"Could not load registered documents.\n\n{exc}",
            )

        self.apply_filters()

    # =========================================================
    # DEPARTMENT FILTER
    # =========================================================

    def _load_department_filter(self):
        """
        Populates the department filter from the live backend.
        """

        from repositories.provider import get_repository

        self.department_filter.blockSignals(True)

        current_text = (
            self.department_filter.currentText()
        )

        self.department_filter.clear()
        self.department_filter.addItem(
            "All Departments"
        )

        try:
            repo = get_repository()
            departments = repo.get_departments()

            for dept in departments:
                if dept.name:
                    self.department_filter.addItem(
                        dept.name
                    )

        except Exception:
            # Backend may be temporarily unavailable.
            # Keep the default "All Departments" option.
            pass

        idx = self.department_filter.findText(
            current_text
        )

        if idx >= 0:
            self.department_filter.setCurrentIndex(idx)
        else:
            self.department_filter.setCurrentIndex(0)

        self.department_filter.blockSignals(False)

    # =========================================================
    # CANONICAL ROUTING DISPLAY / FILTER HELPERS
    # =========================================================

    @staticmethod
    def _value(obj, *names, default=None):
        """Read a value from either a dict payload or model object."""
        for name in names:
            if isinstance(obj, dict):
                value = obj.get(name)
            else:
                value = getattr(obj, name, None)

            if value is not None and value != "":
                return value

        return default

    @classmethod
    def _active_branches(cls, document):
        branches = (
            cls._value(
                document,
                "department_routings",
                "routing_branches",
                "branches",
                default=[],
            )
            or []
        )

        if isinstance(branches, dict):
            branches = [branches]

        return [
            branch
            for branch in branches
            if cls._value(branch, "is_active", default=True) is not False
        ]

    @classmethod
    def _active_assignments(cls, document):
        assignments = cls._value(
            document,
            "work_assignments",
            default=[],
        ) or []

        if isinstance(assignments, dict):
            assignments = [assignments]

        return [
            assignment
            for assignment in assignments
            if cls._value(
                assignment,
                "is_active",
                default=True,
            ) is not False
        ]

    @classmethod
    def _routing_department_names(cls, document):
        names = []

        for branch in cls._active_branches(document):
            branch_type = str(
                cls._value(
                    branch,
                    "branch_type",
                    "route_type",
                    default="",
                )
            ).upper()

            if branch_type != "DEPARTMENT_HOD":
                continue

            department = cls._value(
                branch,
                "department_name",
                default=None,
            )

            if isinstance(department, dict):
                department = (
                    department.get("name")
                    or department.get("department_name")
                )

            if not department:
                department_obj = cls._value(
                    branch,
                    "department",
                    default=None,
                )
                if isinstance(department_obj, dict):
                    department = (
                        department_obj.get("name")
                        or department_obj.get("department_name")
                    )
                elif department_obj:
                    department = str(department_obj)

            if department and str(department) not in names:
                names.append(str(department))

        # WorkAssignment payloads can also carry the department.
        for assignment in cls._active_assignments(document):
            department = cls._value(
                assignment,
                "department_name",
                default=None,
            )

            if not department:
                department_obj = cls._value(
                    assignment,
                    "department",
                    default=None,
                )
                if isinstance(department_obj, dict):
                    department = (
                        department_obj.get("name")
                        or department_obj.get("department_name")
                    )
                elif department_obj:
                    department = str(department_obj)

            if department and str(department) not in names:
                names.append(str(department))

        return names

    @classmethod
    def _routing_search_text(cls, document):
        """Build searchable text from canonical routing/assignment data."""
        parts = []

        for branch in cls._active_branches(document):
            for key in (
                "branch_type",
                "route_type",
                "department_name",
                "target_user_name",
                "employee_name",
            ):
                value = cls._value(branch, key)
                if value:
                    if isinstance(value, dict):
                        value = (
                            value.get("name")
                            or value.get("department_name")
                            or value.get("full_name")
                        )
                    if value:
                        parts.append(str(value))

        for assignment in cls._active_assignments(document):
            for key in (
                "department_name",
                "assigned_to_name",
                "assigned_to_user_name",
                "employee_name",
                "team_name",
            ):
                value = cls._value(assignment, key)
                if value:
                    parts.append(str(value))

            members = cls._value(
                assignment,
                "members",
                default=[],
            ) or []

            if isinstance(members, dict):
                members = [members]

            for member in members:
                name = cls._value(
                    member,
                    "user_name",
                    "employee_name",
                    "name",
                    "full_name",
                )
                if name:
                    parts.append(str(name))

        return " ".join(parts).lower()

    # =========================================================
    # FILTERING
    # =========================================================

    def apply_filters(self):
        search_query = (
            self.search_input.text()
            .strip()
            .lower()
        )

        status_sel = (
            self.status_filter.currentText()
        )

        prio_sel = (
            self.priority_filter.currentText()
        )

        deadline_sel = (
            self.deadline_filter.currentText()
        )

        dept_sel = (
            self.department_filter.currentText()
        )

        filtered = list(self.all_documents)
        self._refresh_summary(self.all_documents)

        # --------------------------------
        # 1. SEARCH
        # --------------------------------

        if search_query:
            filtered = [
                document
                for document in filtered
                if search_query
                in (
                    str(
                        getattr(document, "title", "")
                        or getattr(document, "subject", "")
                        or ""
                    )
                ).lower()
                or search_query
                in str(
                    getattr(document, "reference", "")
                    or ""
                ).lower()
                or search_query
                in str(
                    getattr(document, "source", "")
                    or ""
                ).lower()
                or search_query
                in self._routing_search_text(document)
            ]

        # --------------------------------
        # 2. STATUS
        # --------------------------------

        if status_sel != "All Status":
            filtered = [
                document
                for document in filtered
                if (
                    document.status or ""
                ).lower()
                == status_sel.lower()
            ]

        # --------------------------------
        # 3. PRIORITY
        # --------------------------------

        if prio_sel == "High Priority":
            filtered = [
                document
                for document in filtered
                if (
                    document.priority or ""
                ).lower()
                in (
                    "high",
                    "red",
                )
            ]

        elif prio_sel == "Medium Priority":
            filtered = [
                document
                for document in filtered
                if (
                    document.priority or ""
                ).lower()
                in (
                    "medium",
                    "orange",
                    "yellow",
                )
            ]

        elif prio_sel == "Low Priority":
            filtered = [
                document
                for document in filtered
                if (
                    document.priority or ""
                ).lower()
                in (
                    "low",
                    "green",
                )
            ]

        # --------------------------------
        # 4. DEPARTMENT
        # --------------------------------
        #
        # Department is a document metadata/filter field.
        # It is NOT derived from the removed legacy
        # target_department_name field.
        #
        # Actual operational routing is represented by
        # document.work_assignments / routing branches.
        # --------------------------------

        if dept_sel != "All Departments":
            wanted_department = dept_sel.strip().lower()

            filtered = [
                document
                for document in filtered
                if any(
                    wanted_department == name.lower()
                    for name in self._routing_department_names(
                        document
                    )
                )
            ]

        # --------------------------------
        # 5. DEADLINE
        # --------------------------------

        if deadline_sel != "All Deadlines":

            today = datetime.now().date()

            due_soon_cutoff = (
                today + timedelta(days=7)
            )

            if deadline_sel == "Due Within 7 Days":

                filtered = [
                    document
                    for document in filtered
                    if (
                        document.deadline
                        and self._parse_date(
                            document.deadline
                        )
                        and today
                        <= self._parse_date(
                            document.deadline
                        )
                        <= due_soon_cutoff
                        and (
                            document.status or ""
                        ).lower()
                        != "closed"
                    )
                ]

            elif deadline_sel == "Overdue":

                filtered = [
                    document
                    for document in filtered
                    if (
                        document.deadline
                        and self._parse_date(
                            document.deadline
                        )
                        and self._parse_date(
                            document.deadline
                        )
                        < today
                        and (
                            document.status or ""
                        ).lower()
                        != "closed"
                    )
                ]

        # --------------------------------
        # UPDATE CONTENT
        # --------------------------------

        self.result_label.setText(f"Showing {len(filtered)} of {len(self.all_documents)}")

        if not filtered:

            self.content_stack.setCurrentWidget(
                self.empty_widget
            )

            self.selected_document = None
            self.view_button.setEnabled(False)

        else:

            self.content_stack.setCurrentWidget(
                self.table
            )

            self.table.load_documents(
                filtered
            )

            # Loading a list is not the same as selecting a document.
            # Keep the action disabled until a row is selected.
            self.selected_document = None
            self.view_button.setEnabled(False)

    # =========================================================
    # DATE PARSING
    # =========================================================

    def _parse_date(
        self,
        date_str: str,
    ):
        if not date_str:
            return None

        cleaned = (
            str(date_str)
            .strip()
            .split()[0]
        )

        formats = (
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
        )

        for fmt in formats:
            try:
                return datetime.strptime(
                    cleaned,
                    fmt,
                ).date()

            except Exception:
                pass

        return None

    # =========================================================
    # FILTER STATE
    # =========================================================

    def set_filters(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        deadline: Optional[str] = None,
        department: Optional[str] = None,
        search: Optional[str] = None,
    ):
        """
        Pre-selects filter dropdowns and applies filtering.
        """

        self._preserve_filters_once = True

        self.all_documents = (
            document_service.get_documents()
        )

        # --------------------------------
        # STATUS
        # --------------------------------

        if status:
            idx = self.status_filter.findText(
                status,
                Qt.MatchContains,
            )

            if idx >= 0:
                self.status_filter.setCurrentIndex(
                    idx
                )

        else:
            self.status_filter.setCurrentIndex(0)

        # --------------------------------
        # PRIORITY
        # --------------------------------

        if priority:
            idx = self.priority_filter.findText(
                priority,
                Qt.MatchContains,
            )

            if idx >= 0:
                self.priority_filter.setCurrentIndex(
                    idx
                )

        else:
            self.priority_filter.setCurrentIndex(0)

        # --------------------------------
        # DEADLINE
        # --------------------------------

        if deadline:
            idx = self.deadline_filter.findText(
                deadline,
                Qt.MatchContains,
            )

            if idx >= 0:
                self.deadline_filter.setCurrentIndex(
                    idx
                )

        else:
            self.deadline_filter.setCurrentIndex(0)

        # --------------------------------
        # DEPARTMENT
        # --------------------------------

        if department:
            idx = self.department_filter.findText(
                department,
                Qt.MatchContains,
            )

            if idx >= 0:
                self.department_filter.setCurrentIndex(
                    idx
                )

        else:
            self.department_filter.setCurrentIndex(0)

        # --------------------------------
        # SEARCH
        # --------------------------------

        if search is not None:
            self.search_input.setText(search)
        else:
            self.search_input.clear()

        self.apply_filters()

    def clear_filters(self):
        self.search_input.clear()

        self.status_filter.setCurrentIndex(0)
        self.priority_filter.setCurrentIndex(0)
        self.deadline_filter.setCurrentIndex(0)
        self.department_filter.setCurrentIndex(0)

        self.load_documents()

    # =========================================================
    # DOCUMENT SELECTION
    # =========================================================

    def on_document_selected(
        self,
        document,
    ):
        self.selected_document = document
        if hasattr(self, "view_button"):
            self.view_button.setEnabled(document is not None)

    def view_document(self, *args):
        """
        Open the selected document for the current user.

        This is intentionally role-agnostic.  The page emits the selected
        DocumentModel plus the active role/context to MainWindow, which remains
        responsible for opening the appropriate document-details workflow.

        ``*args`` is accepted because Qt's double-click signal can provide
        row/column information depending on the table implementation.
        """
        document = None

        # Prefer the table's canonical selection API.
        try:
            document = self.table.get_selected_document()
        except Exception:
            document = None

        # Fall back to the last selected document.
        if document is None:
            document = self.selected_document

        if document is None:
            QMessageBox.information(
                self,
                "No Document Selected",
                "Please select a document to open its details.",
            )
            return

        self.selected_document = document

        # Keep the action button state in sync.
        if hasattr(self, "view_button"):
            self.view_button.setEnabled(True)

        # MainWindow/navigation owns the actual role-specific details page.
        self.view_requested.emit(document, self.user_role)

    # =========================================================
    # ACTION REMINDER
    # =========================================================

    def send_reminder(self):
        document = (
            self.table.get_selected_document()
            or self.selected_document
        )

        if not document:
            QMessageBox.information(
                self,
                "No Selection",
                "Please select a document to send "
                "a deadline reminder.",
            )
            return

        if isinstance(
            document,
            DocumentModel,
        ):
            reference = (
                document.reference
                or "Document"
            )

            document_id = document.id

            status_str = (
                document.status or ""
            ).lower()

        else:
            reference = (
                document.get(
                    "reference",
                    "Document",
                )
            )

            document_id = document.get("id")

            status_str = (
                document.get(
                    "status",
                    "",
                )
                or ""
            ).lower()

        from services.notification_service import (
            notification_service,
        )

        recipient = (
            notification_service.send_action_reminder(
                document_id
            )
        )

        if not recipient:

            if status_str == "closed":

                QMessageBox.information(
                    self,
                    "Document Closed",
                    (
                        f"Document {reference} is finalized "
                        "and closed. Action reminders cannot "
                        "be sent for closed documents."
                    ),
                )

            else:

                QMessageBox.warning(
                    self,
                    "No Recipient Available",
                    (
                        f"No downstream reminder recipient "
                        f"is currently available for document "
                        f"{reference}. Please route the document "
                        "to a department or assign an employee first."
                    ),
                )

            return

        QMessageBox.information(
            self,
            "Action Reminder Dispatched",
            (
                "Official deadline reminder successfully "
                f"dispatched to {recipient['user_name']} "
                f"({recipient['role']}) for {reference}."
            ),
        )
        