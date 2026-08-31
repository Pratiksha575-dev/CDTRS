from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from components.state_widgets import EmptyStateWidget
from models.document import DocumentModel
from models.enums import DocumentStatusEnum, RoleEnum, WorkflowStageEnum
from services.auth_service import auth_service
from services.dashboard_service import dashboard_service
from services.document_service import document_service
from repositories.provider import get_repository


class DashboardPage(QWidget):
    """
    Role-specialized Dashboard for CDTRS.
    Provides customized operational KPI cards and actionable summaries for:
    - Director Secretary (operational overview and compact action cards)
    - Director (executive document reviews and progress follow-ups)
    - HOD (departmental workload, task delegation, and progress oversight)
    - Employee (task assignments, active work items, and progress submissions)
    """

    view_requested = Signal(object, str)
    navigate_requested = Signal(str, object)  # Emits target page name (e.g. "Inbox", "Documents") and filter dictionary

    def __init__(self, role: str = "Director Secretary"):
        super().__init__()
        self.role = RoleEnum.normalize(role)
        self.documents: List[DocumentModel] = []
        self.setup_ui()
        self.refresh()
        from services.event_bus import event_bus
        event_bus.data_changed.connect(self.refresh)
        event_bus.inbox_updated.connect(self.refresh)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 25, 30, 30)
        main_layout.setSpacing(18)

        # --------------------------------
        # HEADER
        # --------------------------------
        header_layout = QHBoxLayout()
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)

        if self.role == RoleEnum.DIRECTOR.value:
            title_text = "Director Executive Dashboard"
            sub_text = "Executive overview of incoming policy documents, initial reviews, and progress follow-ups."
        elif self.role in (RoleEnum.HOD.value, "HOD"):
            title_text = "Department Head (HOD) Dashboard"
            sub_text = "Departmental workload oversight, employee delegation, and execution progress tracking."
        elif self.role in (RoleEnum.EMPLOYEE.value, "Employee"):
            title_text = "Employee Task Dashboard"
            sub_text = "Active task assignments, deliverables, and progress submission overview."
        else:
            title_text = "Director Secretary Dashboard"
            sub_text = "Operational intake overview, review routing, and lifecycle monitoring."

        title = QLabel(title_text)
        title.setObjectName("pageTitle")

        subtitle = QLabel(sub_text)
        subtitle.setObjectName("pageSubtitle")

        title_vbox.addWidget(title)
        title_vbox.addWidget(subtitle)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # --------------------------------
        # KPI SUMMARY CARDS
        # --------------------------------
        self.kpi_grid = QGridLayout()
        self.kpi_grid.setSpacing(12)

        if self.role == RoleEnum.DIRECTOR.value:
            self.card_dir_new = self._create_kpi_card(
                "Awaiting Initial Review", "0", "#0F172A",
                callback=lambda: self.navigate_requested.emit("Inbox", {"category": "Initial Reviews"})
            )
            self.card_dir_followup = self._create_kpi_card(
                "Progress Follow-ups", "0", "#0284C7",
                callback=lambda: self.navigate_requested.emit("Inbox", {"category": "Progress Follow-ups"})
            )
            self.card_dir_reviewed = self._create_kpi_card(
                "Total Reviewed / Returned", "0", "#059669",
                callback=lambda: self.navigate_requested.emit("Inbox", {"category": "Reviewed & Returned to DS"})
            )
            self.card_dir_critical = self._create_kpi_card(
                "Critical / High Priority", "0", "#E11D48",
                callback=lambda: self.navigate_requested.emit("Inbox", {"priority": "High"})
            )


            self.kpi_grid.addWidget(self.card_dir_new["frame"], 0, 0)
            self.kpi_grid.addWidget(self.card_dir_followup["frame"], 0, 1)
            self.kpi_grid.addWidget(self.card_dir_reviewed["frame"], 0, 2)
            self.kpi_grid.addWidget(self.card_dir_critical["frame"], 0, 3)

        elif self.role in (RoleEnum.HOD.value, "HOD"):
            self.card_hod_unassigned = self._create_kpi_card(
                "Awaiting Employee Assignment", "0", "#D97706",
                callback=lambda: self.navigate_requested.emit("Inbox", {})
            )
            self.card_hod_assigned = self._create_kpi_card(
                "Assigned / In Progress", "0", "#0284C7",
                callback=lambda: self.navigate_requested.emit("Inbox", {})
            )
            self.card_hod_progress = self._create_kpi_card(
                "Progress Updates Received", "0", "#059669",
                callback=lambda: self.navigate_requested.emit("Inbox", {})
            )
            self.card_hod_critical = self._create_kpi_card(
                "Critical / High Priority", "0", "#E11D48",
                callback=lambda: self.navigate_requested.emit("Documents", {"priority": "High Priority"})
            )

            self.kpi_grid.addWidget(self.card_hod_unassigned["frame"], 0, 0)
            self.kpi_grid.addWidget(self.card_hod_assigned["frame"], 0, 1)
            self.kpi_grid.addWidget(self.card_hod_progress["frame"], 0, 2)
            self.kpi_grid.addWidget(self.card_hod_critical["frame"], 0, 3)

        elif self.role in (RoleEnum.EMPLOYEE.value, "Employee"):
            self.card_emp_active = self._create_kpi_card(
                "Active Assigned Tasks", "0", "#0F172A",
                callback=lambda: self.navigate_requested.emit("Inbox", {})
            )
            self.card_emp_pending = self._create_kpi_card(
                "New / Pending Progress", "0", "#D97706",
                callback=lambda: self.navigate_requested.emit("Inbox", {})
            )
            self.card_emp_progress = self._create_kpi_card(
                "Progress Updates Submitted", "0", "#059669",
                callback=lambda: self.navigate_requested.emit("Inbox", {})
            )
            self.card_emp_critical = self._create_kpi_card(
                "Critical / High Priority", "0", "#E11D48",
                callback=lambda: self.navigate_requested.emit("Inbox", {})
            )

            self.kpi_grid.addWidget(self.card_emp_active["frame"], 0, 0)
            self.kpi_grid.addWidget(self.card_emp_pending["frame"], 0, 1)
            self.kpi_grid.addWidget(self.card_emp_progress["frame"], 0, 2)
            self.kpi_grid.addWidget(self.card_emp_critical["frame"], 0, 3)

        else:
            self.card_intake = self._create_kpi_card(
                "New Incoming", "0", "#0284C7"
            )
            self.card_director_rev = self._create_kpi_card(
                "Awaiting Director Review", "0", "#6366F1"
            )
            self.card_director_done = self._create_kpi_card(
                "Returned by Director", "0", "#D97706"
            )
            self.card_hod = self._create_kpi_card(
                "Under HOD Processing", "0", "#0D9488"
            )
            self.card_progress = self._create_kpi_card(
                "Progress Updates", "0", "#2563EB"
            )
            self.card_closed = self._create_kpi_card(
                "Closed Documents", "0", "#059669"
            )

            self.kpi_grid.addWidget(self.card_intake["frame"], 0, 0)
            self.kpi_grid.addWidget(self.card_director_rev["frame"], 0, 1)
            self.kpi_grid.addWidget(self.card_director_done["frame"], 0, 2)
            self.kpi_grid.addWidget(self.card_hod["frame"], 1, 0)
            self.kpi_grid.addWidget(self.card_progress["frame"], 1, 1)
            self.kpi_grid.addWidget(self.card_closed["frame"], 1, 2)

        main_layout.addLayout(self.kpi_grid)

        # --------------------------------
        # ROLE-SPECIFIC CONTENT
        # --------------------------------
        if self.role == RoleEnum.DIRECTOR_SECRETARY.value or self.role == "Director Secretary":
            self._setup_ds_actionable_cards(main_layout)
        else:
            self._setup_standard_queue_table(main_layout)

        self.setLayout(main_layout)

    def _setup_ds_actionable_cards(self, main_layout: QVBoxLayout):
        """Sets up clean operational Action Required navigation sections for DS."""
        action_title = QLabel("Operational Action Required")
        action_title.setObjectName("sectionTitle")
        main_layout.addWidget(action_title)

        action_grid = QGridLayout()
        action_grid.setSpacing(14)

        # Action Card 1: Incoming Dispatches
        self.act_card_intake = self._create_action_card(
            "New Incoming Documents",
            "0 documents awaiting processing",
            "View Inbox →",
            lambda: self.navigate_requested.emit("Inbox", {}),
            accent_color="#0284C7"
        )
        # Action Card 2: Returned by Director
        self.act_card_dir = self._create_action_card(
            "Documents Returned by Director",
            "0 documents requiring routing",
            "View Documents →",
            lambda: self.navigate_requested.emit("Documents", {"status": "Director Review Completed"}),
            accent_color="#D97706"
        )
        # Action Card 3: Progress Follow-up
        self.act_card_prog = self._create_action_card(
            "Progress / Follow-up Requiring Attention",
            "0 updates requiring attention",
            "View Documents →",
            lambda: self.navigate_requested.emit("Documents", {"status": "Progress Updated"}),
            accent_color="#2563EB"
        )
        # Action Card 4: Upcoming Deadlines
        self.act_card_deadlines = self._create_action_card(
            "Upcoming Deadlines",
            "0 active documents registered",
            "View Documents →",
            lambda: self.navigate_requested.emit("Documents", {"deadline": "Due Within 7 Days"}),
            accent_color="#059669"
        )

        action_grid.addWidget(self.act_card_intake["frame"], 0, 0)
        action_grid.addWidget(self.act_card_dir["frame"], 0, 1)
        action_grid.addWidget(self.act_card_prog["frame"], 1, 0)
        action_grid.addWidget(self.act_card_deadlines["frame"], 1, 1)
        main_layout.addLayout(action_grid)
        main_layout.addStretch()

    def _setup_standard_queue_table(self, main_layout: QVBoxLayout):
        """Sets up document action queue table for Director, HOD, and Employee."""
        if self.role == RoleEnum.DIRECTOR.value:
            queue_title = "Executive Review Queue"
            btn_text = "Review Selected Document"
        elif self.role in (RoleEnum.HOD.value, "HOD"):
            queue_title = "Departmental Action Queue"
            btn_text = "Open Document / Assign"
        elif self.role in (RoleEnum.EMPLOYEE.value, "Employee"):
            queue_title = "My Active Tasks Queue"
            btn_text = "Open Task / Submit Progress"
        else:
            queue_title = "Actionable Documents Queue"
            btn_text = "View Selected Document"

        section_lbl = QLabel(queue_title)
        section_lbl.setObjectName("sectionTitle")
        main_layout.addWidget(section_lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Reference", "Title", "Priority", "Department / Origin", "Status", "Stage"
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

        main_layout.addWidget(self.table, 1)

        btn_bar = QHBoxLayout()
        btn_bar.addStretch()
        self.view_btn = QPushButton(btn_text)
        self.view_btn.setStyleSheet("background-color: #0F172A; color: white; font-weight: 600; padding: 7px 18px; border-radius: 5px;")
        self.view_btn.clicked.connect(self._handle_view_selected)
        btn_bar.addWidget(self.view_btn)
        main_layout.addLayout(btn_bar)

    def _create_kpi_card(self, title: str, value: str, accent_color: str, callback=None) -> dict:
        frame = QFrame()
        frame.setObjectName("contentCard")
        frame.setStyleSheet(f"QFrame#contentCard {{ border-left: 4px solid {accent_color}; background-color: #FFFFFF; border-radius: 6px; border-top: 1px solid #E2E8F0; border-right: 1px solid #E2E8F0; border-bottom: 1px solid #E2E8F0; }}")

        if callback:
            frame.setCursor(Qt.PointingHandCursor)
            frame.mousePressEvent = lambda event: callback()

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        t_lbl = QLabel(title)
        t_lbl.setWordWrap(True)
        t_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600; text-transform: uppercase;")

        v_lbl = QLabel(value)
        v_lbl.setStyleSheet("color: #0F172A; font-size: 22px; font-weight: bold;")

        layout.addWidget(t_lbl)
        layout.addWidget(v_lbl)

        return {"frame": frame, "value_label": v_lbl}

    def _create_action_card(self, title: str, subtitle: str, btn_text: str, callback, accent_color: str = "#0F172A") -> dict:
        frame = QFrame()
        frame.setObjectName("contentCard")
        frame.setStyleSheet(f"QFrame#contentCard {{ background-color: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid {accent_color}; border-radius: 6px; }}")

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        vbox = QVBoxLayout()
        vbox.setSpacing(3)
        t_lbl = QLabel(title)
        t_lbl.setWordWrap(True)
        t_lbl.setStyleSheet("font-weight: 700; color: #0F172A; font-size: 13px;")

        s_lbl = QLabel(subtitle)
        s_lbl.setWordWrap(True)
        s_lbl.setStyleSheet("color: #64748B; font-size: 12px;")

        vbox.addWidget(t_lbl)
        vbox.addWidget(s_lbl)
        layout.addLayout(vbox, 1)

        btn = QPushButton(btn_text)
        btn.setStyleSheet("background-color: #F8FAFC; border: 1px solid #CBD5E1; color: #0F172A; font-weight: 600; padding: 7px 14px; border-radius: 5px;")
        btn.clicked.connect(callback)
        layout.addWidget(btn)

        return {"frame": frame, "title_label": t_lbl, "sub_label": s_lbl, "btn": btn}

    def refresh(self):
        """Loads live KPI metrics and recent documents dynamically from services."""
        self.documents = document_service.get_documents()

        if self.role == RoleEnum.DIRECTOR.value:
            dir_docs = [d for d in self.documents if d.current_stage == WorkflowStageEnum.DIRECTOR.value or d.status == DocumentStatusEnum.UNDER_DIRECTOR_REVIEW.value]

            # Use in-memory attribute checks — no per-document network calls (avoids UI freeze)
            initial_count = 0
            followup_count = 0
            for d in dir_docs:
                has_progress = (
                    d.status == DocumentStatusEnum.PROGRESS_UPDATED.value
                    or getattr(d, "has_progress_updates", False)
                )
                if has_progress:
                    followup_count += 1
                else:
                    initial_count += 1

            reviewed_count = sum(
                1 for d in self.documents
                if (bool(d.director_remark) or d.status == "Director Review Completed")
                and d.current_stage != "DIRECTOR"
            )
            critical_count = sum(1 for d in dir_docs if (d.priority or "").lower() in ("high", "red"))

            self.card_dir_new["value_label"].setText(str(initial_count))
            self.card_dir_followup["value_label"].setText(str(followup_count))
            self.card_dir_reviewed["value_label"].setText(str(reviewed_count))
            self.card_dir_critical["value_label"].setText(str(critical_count))

            display_list = dir_docs
            if hasattr(self, "table"):
                self._populate_table(display_list)

        elif self.role in (RoleEnum.HOD.value, "HOD"):
            current_user = auth_service.get_current_user()
            user_dept_name = current_user.department_name if current_user else None
            user_dept_id = current_user.department_id if current_user else None

            hod_docs = [
                d for d in self.documents
                if (user_dept_name is None or (d.target_department_name or d.department or "").lower() == user_dept_name.lower() or d.target_department_id == user_dept_id)
                and (
                    d.current_stage in (WorkflowStageEnum.HOD.value, WorkflowStageEnum.EMPLOYEE.value)
                    or d.status in (
                        DocumentStatusEnum.UNDER_HOD_PROCESSING.value,
                        DocumentStatusEnum.ASSIGNED_FOR_EXECUTION.value,
                        DocumentStatusEnum.IN_PROGRESS.value,
                        DocumentStatusEnum.PROGRESS_UPDATED.value
                    )
                )
            ]

            unassigned_count = sum(1 for d in hod_docs if d.current_stage == WorkflowStageEnum.HOD.value and not d.assigned_employee_name)
            assigned_count = sum(1 for d in hod_docs if d.current_stage == WorkflowStageEnum.EMPLOYEE.value or bool(d.assigned_employee_name))
            progress_count = sum(1 for d in hod_docs if d.status == DocumentStatusEnum.PROGRESS_UPDATED.value)
            critical_count = sum(1 for d in hod_docs if (d.priority or "").lower() in ("high", "red"))

            self.card_hod_unassigned["value_label"].setText(str(unassigned_count))
            self.card_hod_assigned["value_label"].setText(str(assigned_count))
            self.card_hod_progress["value_label"].setText(str(progress_count))
            self.card_hod_critical["value_label"].setText(str(critical_count))

            display_list = hod_docs
            if hasattr(self, "table"):
                self._populate_table(display_list)

        elif self.role in (RoleEnum.EMPLOYEE.value, "Employee"):
            current_user = auth_service.get_current_user()
            emp_id = current_user.id if current_user else None

            if emp_id is None:
                emp_docs = []
            else:
                emp_docs = [
                    d for d in self.documents
                    if d.assigned_employee_id == emp_id
                    or (d.current_owner_id == emp_id and d.current_stage == WorkflowStageEnum.EMPLOYEE.value)
                ]

            active_count = len(emp_docs)
            progress_count = sum(1 for d in emp_docs if d.status == DocumentStatusEnum.PROGRESS_UPDATED.value or getattr(d, "has_progress_updates", False))
            pending_count = active_count - progress_count
            critical_count = sum(1 for d in emp_docs if (d.priority or "").lower() in ("high", "urgent"))

            self.card_emp_active["value_label"].setText(str(active_count))
            self.card_emp_pending["value_label"].setText(str(pending_count))
            self.card_emp_progress["value_label"].setText(str(progress_count))
            self.card_emp_critical["value_label"].setText(str(critical_count))

            display_list = emp_docs
            if hasattr(self, "table"):
                self._populate_table(display_list)

        else:
            # Director Secretary KPI calculations - strictly count unregistered intake items
            repo = get_repository()
            try:
                unregistered_items = repo.get_incoming_messages(status="PENDING") or []
                intake_cnt = len(unregistered_items)
            except Exception:
                intake_cnt = 0

            dir_rev_cnt = sum(1 for d in self.documents if d.status == DocumentStatusEnum.UNDER_DIRECTOR_REVIEW.value or d.current_stage == "DIRECTOR")
            dir_done_cnt = sum(1 for d in self.documents if d.status == DocumentStatusEnum.DIRECTOR_REVIEW_COMPLETED.value or (d.director_remark and d.current_stage == "DS"))
            hod_cnt = sum(1 for d in self.documents if d.status == DocumentStatusEnum.UNDER_HOD_PROCESSING.value or d.current_stage == "HOD")
            prog_cnt = sum(1 for d in self.documents if d.status == DocumentStatusEnum.PROGRESS_UPDATED.value)
            closed_cnt = sum(1 for d in self.documents if d.status == DocumentStatusEnum.CLOSED.value)

            self.card_intake["value_label"].setText(str(intake_cnt))
            self.card_director_rev["value_label"].setText(str(dir_rev_cnt))
            self.card_director_done["value_label"].setText(str(dir_done_cnt))
            self.card_hod["value_label"].setText(str(hod_cnt))
            self.card_progress["value_label"].setText(str(prog_cnt))
            self.card_closed["value_label"].setText(str(closed_cnt))

            # Update DS Actionable Cards
            if hasattr(self, "act_card_intake"):
                self.act_card_intake["sub_label"].setText(f"{intake_cnt} documents awaiting processing")
                self.act_card_dir["sub_label"].setText(f"{dir_done_cnt} documents requiring routing")
                self.act_card_prog["sub_label"].setText(f"{prog_cnt} updates requiring attention")

                today = datetime.now().date()
                due_soon_cutoff = today + timedelta(days=7)
                upcoming_active_cnt = sum(
                    1 for d in self.documents
                    if d.deadline
                    and self._parse_date(d.deadline)
                    and today <= self._parse_date(d.deadline) <= due_soon_cutoff
                    and d.current_stage not in (WorkflowStageEnum.CLOSED.value, "Closed", "CLOSED")
                    and (d.status or "").lower() != "closed"
                )
                self.act_card_deadlines["sub_label"].setText(f"{upcoming_active_cnt} active documents due within 7 days")

    def _parse_date(self, date_str: str):
        if not date_str:
            return None
        cleaned = str(date_str).strip().split()[0]
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y", "%m-%d-%Y"):
            try:
                return datetime.strptime(cleaned, fmt).date()
            except Exception:
                pass
        return None

    def _populate_table(self, display_list: List[DocumentModel]):
        self.table.setRowCount(len(display_list))
        self._displayed_docs = display_list
        for row, doc in enumerate(display_list):
            self.table.setItem(row, 0, QTableWidgetItem(doc.reference or "-"))
            self.table.setItem(row, 1, QTableWidgetItem(doc.title or "Untitled"))
            self.table.setItem(row, 2, QTableWidgetItem(doc.priority or "-"))
            self.table.setItem(row, 3, QTableWidgetItem(doc.department or doc.source or "-"))
            self.table.setItem(row, 4, QTableWidgetItem(doc.status or "-"))
            self.table.setItem(row, 5, QTableWidgetItem(doc.current_stage or "-"))

    def _handle_view_selected(self):
        if hasattr(self, "table"):
            row = self.table.currentRow()
            if row >= 0 and row < len(getattr(self, "_displayed_docs", [])):
                selected_doc = self._displayed_docs[row]
                self.view_requested.emit(selected_doc, self.role)
