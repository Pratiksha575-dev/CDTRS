import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from models import (
    AttachmentModel,
    DocumentModel,
    DocumentRouteModel,
    DocumentStatusEnum,
    NotificationModel,
    PriorityEnum,
    ProgressUpdateModel,
    RoleEnum,
    RouteTypeEnum,
    UserModel,
    WorkAssignmentModel,
    WorkflowEventModel,
    WorkflowStageEnum,
    IngestionModeEnum,
)
from models.department import DepartmentModel
from repositories.base import BaseRepository


class MockRepository(BaseRepository):
    """
    Self-contained in-memory development repository for CDTRS V2.
    Simulates complete V2 multi-department workflow lifecycle across 5 departments.
    All 5 canonical demonstration documents initially start in DS Inbox at stage=DS, status=RECEIVED.
    """

    def __init__(self):
        self._current_user: Optional[UserModel] = None
        self._next_doc_id = 5
        self._next_route_id = 1
        self._next_assign_id = 1
        self._next_progress_id = 1
        self._next_attach_id = 10
        self._next_event_id = 10
        self._next_notif_id = 1

        self._seed_users()
        self._seed_documents()
        self._seed_intake_inbox()

    # =========================================================
    # SEEDING INITIAL DEVELOPMENT DATA
    # =========================================================

    def _seed_users(self):
        self._departments = [
            {"id": 1, "name": "Finance"},
            {"id": 2, "name": "Procurement"},
            {"id": 3, "name": "Human Resources"},
            {"id": 4, "name": "Maintenance"},
            {"id": 5, "name": "IT"},
        ]

        self._users: Dict[str, UserModel] = {
            # Executive & Administrative Roles
            "master": UserModel(id=1, username="master", full_name="Director Secretary", role=RoleEnum.DIRECTOR_SECRETARY.value),
            "ds": UserModel(id=1, username="ds", full_name="Director Secretary", role=RoleEnum.DIRECTOR_SECRETARY.value),
            "director": UserModel(id=2, username="director", full_name="Dr. Director", role=RoleEnum.DIRECTOR.value),
            "admin": UserModel(id=8, username="admin", full_name="System Admin", role=RoleEnum.ADMINISTRATOR.value),
            "viewer": UserModel(id=9, username="viewer", full_name="Auditor Viewer", role=RoleEnum.READ_ONLY.value),

            # Department 1: Finance (HOD ID: 3, Employees: 101-105)
            "hod_finance": UserModel(id=3, username="hod_finance", full_name="Finance HOD", role=RoleEnum.HOD.value, department_id=1, department_name="Finance"),
            "emp_rahul": UserModel(id=101, username="emp_rahul", full_name="Rahul Sharma", role=RoleEnum.EMPLOYEE.value, department_id=1, department_name="Finance"),
            "emp_sneha": UserModel(id=102, username="emp_sneha", full_name="Sneha Patil", role=RoleEnum.EMPLOYEE.value, department_id=1, department_name="Finance"),
            "emp_amit": UserModel(id=103, username="emp_amit", full_name="Amit Joshi", role=RoleEnum.EMPLOYEE.value, department_id=1, department_name="Finance"),
            "emp_neha": UserModel(id=104, username="emp_neha", full_name="Neha Kulkarni", role=RoleEnum.EMPLOYEE.value, department_id=1, department_name="Finance"),
            "emp_rohan": UserModel(id=105, username="emp_rohan", full_name="Rohan Mehta", role=RoleEnum.EMPLOYEE.value, department_id=1, department_name="Finance"),

            # Department 2: Procurement (HOD ID: 4, Employees: 201-205)
            "hod_proc": UserModel(id=4, username="hod_proc", full_name="Procurement HOD", role=RoleEnum.HOD.value, department_id=2, department_name="Procurement"),
            "emp_priya": UserModel(id=201, username="emp_priya", full_name="Priya Verma", role=RoleEnum.EMPLOYEE.value, department_id=2, department_name="Procurement"),
            "emp_arjun": UserModel(id=202, username="emp_arjun", full_name="Arjun Shah", role=RoleEnum.EMPLOYEE.value, department_id=2, department_name="Procurement"),
            "emp_karan": UserModel(id=203, username="emp_karan", full_name="Karan Desai", role=RoleEnum.EMPLOYEE.value, department_id=2, department_name="Procurement"),
            "emp_pooja": UserModel(id=204, username="emp_pooja", full_name="Pooja Nair", role=RoleEnum.EMPLOYEE.value, department_id=2, department_name="Procurement"),
            "emp_vivek": UserModel(id=205, username="emp_vivek", full_name="Vivek More", role=RoleEnum.EMPLOYEE.value, department_id=2, department_name="Procurement"),

            # Department 3: Human Resources (HOD ID: 5, Employees: 301-305)
            "hod_hr": UserModel(id=5, username="hod_hr", full_name="HR HOD", role=RoleEnum.HOD.value, department_id=3, department_name="Human Resources"),
            "emp_anjali": UserModel(id=301, username="emp_anjali", full_name="Anjali Gupta", role=RoleEnum.EMPLOYEE.value, department_id=3, department_name="Human Resources"),
            "emp_rohit": UserModel(id=302, username="emp_rohit", full_name="Rohit Singh", role=RoleEnum.EMPLOYEE.value, department_id=3, department_name="Human Resources"),
            "emp_meera": UserModel(id=303, username="emp_meera", full_name="Meera Joshi", role=RoleEnum.EMPLOYEE.value, department_id=3, department_name="Human Resources"),
            "emp_tanvi": UserModel(id=304, username="emp_tanvi", full_name="Tanvi Shah", role=RoleEnum.EMPLOYEE.value, department_id=3, department_name="Human Resources"),
            "emp_akash": UserModel(id=305, username="emp_akash", full_name="Akash Patil", role=RoleEnum.EMPLOYEE.value, department_id=3, department_name="Human Resources"),

            # Department 4: Maintenance (HOD ID: 6, Employees: 401-405)
            "hod_maint": UserModel(id=6, username="hod_maint", full_name="Maintenance HOD", role=RoleEnum.HOD.value, department_id=4, department_name="Maintenance"),
            "emp_suresh": UserModel(id=401, username="emp_suresh", full_name="Suresh Pawar", role=RoleEnum.EMPLOYEE.value, department_id=4, department_name="Maintenance"),
            "emp_kavita": UserModel(id=402, username="emp_kavita", full_name="Kavita More", role=RoleEnum.EMPLOYEE.value, department_id=4, department_name="Maintenance"),
            "emp_nikhil": UserModel(id=403, username="emp_nikhil", full_name="Nikhil Patil", role=RoleEnum.EMPLOYEE.value, department_id=4, department_name="Maintenance"),
            "emp_snehal": UserModel(id=404, username="emp_snehal", full_name="Snehal Jadhav", role=RoleEnum.EMPLOYEE.value, department_id=4, department_name="Maintenance"),
            "emp_omkar": UserModel(id=405, username="emp_omkar", full_name="Omkar Shinde", role=RoleEnum.EMPLOYEE.value, department_id=4, department_name="Maintenance"),

            # Department 5: IT (HOD ID: 7, Employees: 501-505)
            "hod_it": UserModel(id=7, username="hod_it", full_name="IT HOD", role=RoleEnum.HOD.value, department_id=5, department_name="IT"),
            "emp_aditya": UserModel(id=501, username="emp_aditya", full_name="Aditya Kulkarni", role=RoleEnum.EMPLOYEE.value, department_id=5, department_name="IT"),
            "emp_riya": UserModel(id=502, username="emp_riya", full_name="Riya Shah", role=RoleEnum.EMPLOYEE.value, department_id=5, department_name="IT"),
            "emp_siddhant": UserModel(id=503, username="emp_siddhant", full_name="Siddhant Joshi", role=RoleEnum.EMPLOYEE.value, department_id=5, department_name="IT"),
            "emp_isha": UserModel(id=504, username="emp_isha", full_name="Isha Patil", role=RoleEnum.EMPLOYEE.value, department_id=5, department_name="IT"),
            "emp_yash": UserModel(id=505, username="emp_yash", full_name="Yash Deshmukh", role=RoleEnum.EMPLOYEE.value, department_id=5, department_name="IT"),
        }

        # Set default active session to DS for initial development
        self._current_user = self._users["ds"]

    def _seed_documents(self):
        """
        Initializes the canonical 5 demonstration documents in the active repository store.
        All 5 documents start in DS Inbox at stage=DS, status=RECEIVED, unassigned, and unrouted.
        Suggested department/employee metadata is present for demonstration intelligence.
        """
        now_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        now_day = datetime.now().strftime("%Y-%m-%d")
        deadline_7d = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        self._documents: List[DocumentModel] = [
            # --------------------------------------------------
            # DOCUMENT 1 — FRESH / NORMAL WORKFLOW
            # --------------------------------------------------
            DocumentModel(
                id=1,
                reference_no="CDTRS-2026-0001",
                title="National Higher Education Accreditation & Governance Compliance Directive",
                date=f"{now_day} 09:30 AM",
                mode="Outlook / Government Mail",
                source="Ministry of Higher Education",
                priority=PriorityEnum.MEDIUM.value,
                deadline=None,
                status=DocumentStatusEnum.RECEIVED.value,
                current_stage=WorkflowStageEnum.DS.value,
                current_owner_id=1,
                current_owner_name="Director Secretary",
                target_department_id=None,
                target_department_name=None,
                assigned_employee_id=None,
                assigned_employee_name=None,
                suggested_department_id=None,
                suggested_department_name=None,
                suggested_employee_id=None,
                suggested_employee_name=None,
                director_remark=None,
                hod_remark=None,
                has_prior_director_remark=False,
                has_director_routing_instruction=False,
                file_path="data/incoming/government_mail/accreditation_compliance_directive.pdf",
                file_type="PDF",
                format="PDF",
                attachment_count=1,
                attachments_list=["accreditation_compliance_directive.pdf"],
                created_by=1,
                created_at=now_date
            ),
            # --------------------------------------------------
            # DOCUMENT 2 — DEPARTMENT SUGGESTION
            # --------------------------------------------------
            DocumentModel(
                id=2,
                reference_no="CDTRS-2026-0002",
                title="Q3 Financial Audit & Capital Grant Disbursement Notice",
                date=f"{now_day} 09:45 AM",
                mode="Internet / Web Portal",
                source="State Audit Bureau",
                priority=PriorityEnum.HIGH.value,
                deadline=None,
                status=DocumentStatusEnum.RECEIVED.value,
                current_stage=WorkflowStageEnum.DS.value,
                current_owner_id=1,
                current_owner_name="Director Secretary",
                target_department_id=None,
                target_department_name=None,
                assigned_employee_id=None,
                assigned_employee_name=None,
                suggested_department_id=1,
                suggested_department_name="Finance",
                suggested_employee_id=None,
                suggested_employee_name=None,
                director_remark=None,
                hod_remark=None,
                has_prior_director_remark=False,
                has_director_routing_instruction=False,
                file_path="data/incoming/government_mail/audit_disbursement_notice.pdf",
                file_type="PDF",
                format="PDF",
                attachment_count=2,
                attachments_list=["audit_disbursement_notice.pdf", "capital_grant_schedule.xlsx"],
                created_by=1,
                created_at=now_date
            ),
            # --------------------------------------------------
            # DOCUMENT 3 — DEPARTMENT + EMPLOYEE SUGGESTION
            # --------------------------------------------------
            DocumentModel(
                id=3,
                reference_no="CDTRS-2026-0003",
                title="Statutory Vendor Tax Clearance & Procurement Verification",
                date=f"{now_day} 10:00 AM",
                mode="Fax",
                source="Central Board of Direct Taxes",
                priority=PriorityEnum.HIGH.value,
                deadline=None,
                status=DocumentStatusEnum.RECEIVED.value,
                current_stage=WorkflowStageEnum.DS.value,
                current_owner_id=1,
                current_owner_name="Director Secretary",
                target_department_id=None,
                target_department_name=None,
                assigned_employee_id=None,
                assigned_employee_name=None,
                suggested_department_id=1,
                suggested_department_name="Finance",
                suggested_employee_id=101,
                suggested_employee_name="Rahul Sharma",
                director_remark=None,
                hod_remark=None,
                has_prior_director_remark=False,
                has_director_routing_instruction=False,
                file_path="data/incoming/government_mail/vendor_tax_clearance.pdf",
                file_type="PDF",
                format="PDF",
                attachment_count=1,
                attachments_list=["vendor_tax_clearance.pdf"],
                created_by=1,
                created_at=now_date
            ),
            # --------------------------------------------------
            # DOCUMENT 4 — PRE-REVIEWED / DIRECTOR REMARK
            # --------------------------------------------------
            DocumentModel(
                id=4,
                reference_no="CDTRS-2026-0004",
                title="Urgent Campus Security Infrastructure Upgrade Order (Pre-Reviewed)",
                date=f"{now_day} 10:15 AM",
                mode="Physical / Scanned PDF",
                source="Office of the Director",
                priority=PriorityEnum.HIGH.value,
                deadline=None,
                status=DocumentStatusEnum.RECEIVED.value,
                current_stage=WorkflowStageEnum.DS.value,
                current_owner_id=1,
                current_owner_name="Director Secretary",
                target_department_id=None,
                target_department_name=None,
                assigned_employee_id=None,
                assigned_employee_name=None,
                suggested_department_id=1,
                suggested_department_name="Finance",
                suggested_employee_id=101,
                suggested_employee_name="Rahul Sharma",
                director_remark="Approved. Expedite procurement and assign to Rahul Sharma for immediate execution.",
                hod_remark=None,
                has_prior_director_remark=True,
                has_director_routing_instruction=True,
                director_routing_raw_text="Approved. Expedite procurement and assign to Rahul Sharma for immediate execution.",
                routing_instruction_confidence=96,
                file_path="data/incoming/scans/security_infrastructure_upgrade.pdf",
                file_type="Scanned PDF",
                format="PDF",
                attachment_count=1,
                attachments_list=["security_infrastructure_upgrade.pdf"],
                created_by=1,
                created_at=now_date
            ),
            # --------------------------------------------------
            # DOCUMENT 5 — URGENT / DEADLINE
            # --------------------------------------------------
            DocumentModel(
                id=5,
                reference_no="CDTRS-2026-0005",
                title="High-Priority Enterprise Server Maintenance & Firewall Compliance",
                date=f"{now_day} 10:30 AM",
                mode="Internet / Web Portal",
                source="Cyber Security Directorate",
                priority=PriorityEnum.HIGH.value,
                deadline=deadline_7d,
                status=DocumentStatusEnum.RECEIVED.value,
                current_stage=WorkflowStageEnum.DS.value,
                current_owner_id=1,
                current_owner_name="Director Secretary",
                target_department_id=None,
                target_department_name=None,
                assigned_employee_id=None,
                assigned_employee_name=None,
                suggested_department_id=5,
                suggested_department_name="IT",
                suggested_employee_id=None,
                suggested_employee_name=None,
                director_remark=None,
                hod_remark=None,
                has_prior_director_remark=False,
                has_director_routing_instruction=False,
                file_path="data/incoming/outlook/server_maintenance_compliance.pdf",
                file_type="PDF",
                format="PDF",
                attachment_count=2,
                attachments_list=["server_maintenance_compliance.pdf", "firewall_rules.xlsx"],
                created_by=1,
                created_at=now_date
            ),
        ]

        self._routes: List[DocumentRouteModel] = []
        self._assignments: List[WorkAssignmentModel] = []
        self._progress_updates: List[ProgressUpdateModel] = []
        self._notifications: List[NotificationModel] = []
        self._attachments: List[AttachmentModel] = []
        self._history: Dict[int, List[WorkflowEventModel]] = {}

        # Seed initial intake/received audit events (one per document)
        for doc in self._documents:
            remarks_text = f"Document {doc.reference_no} received and registered at DS stage."
            if doc.id == 4:
                remarks_text = f"Document {doc.reference_no} registered from physical intake with pre-existing Director directive."
            elif doc.id == 5:
                remarks_text = f"Document {doc.reference_no} received with priority deadline ({doc.deadline})."

            self._history[doc.id] = [
                WorkflowEventModel(
                    id=doc.id,
                    document_id=doc.id,
                    action="Document Ingested",
                    from_role="DS",
                    to_role="DS",
                    remarks=remarks_text,
                    performed_by=1,
                    performed_by_name="Director Secretary",
                    timestamp=doc.date or now_date
                )
            ]

            # Seed initial attachments
            if doc.attachments_list:
                for idx, fname in enumerate(doc.attachments_list, 1):
                    fext = fname.rsplit(".", 1)[-1].upper() if "." in fname else "PDF"
                    self._attachments.append(
                        AttachmentModel(
                            id=len(self._attachments) + 1,
                            document_id=doc.id,
                            progress_update_id=None,
                            file_name=fname,
                            file_path=doc.file_path or f"data/incoming/{fname}",
                            file_type=fext,
                            file_size=2048 * idx,
                            category="ORIGINAL",
                            source=doc.source or "Initial Intake",
                            uploaded_by=1,
                            uploaded_by_name="Director Secretary",
                            created_at=doc.date or now_date
                        )
                    )

    def _seed_intake_inbox(self):
        """
        Initializes the 5 canonical intake documents in the DS Incoming Queue.
        """
        now_day = datetime.now().strftime("%Y-%m-%d")
        deadline_7d = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        self._inbox_documents: List[DocumentModel] = [
            DocumentModel(
                id=1,
                title="National Higher Education Accreditation & Governance Compliance Directive",
                date=f"{now_day} 09:30 AM",
                mode="Outlook / Government Mail",
                source="Ministry of Higher Education",
                priority=PriorityEnum.MEDIUM.value,
                file_path="data/incoming/government_mail/accreditation_compliance_directive.pdf",
                file_type="PDF",
                format="PDF",
                attachment_count=1,
                attachments_list=["accreditation_compliance_directive.pdf"],
                status="Received"
            ),
            DocumentModel(
                id=2,
                title="Q3 Financial Audit & Capital Grant Disbursement Notice",
                date=f"{now_day} 09:45 AM",
                mode="Internet / Web Portal",
                source="State Audit Bureau",
                priority=PriorityEnum.HIGH.value,
                file_path="data/incoming/government_mail/audit_disbursement_notice.pdf",
                file_type="PDF",
                format="PDF",
                attachment_count=2,
                attachments_list=["audit_disbursement_notice.pdf", "capital_grant_schedule.xlsx"],
                suggested_department_name="Finance",
                suggested_department_id=1,
                status="Received"
            ),
            DocumentModel(
                id=3,
                title="Statutory Vendor Tax Clearance & Procurement Verification",
                date=f"{now_day} 10:00 AM",
                mode="Fax",
                source="Central Board of Direct Taxes",
                priority=PriorityEnum.HIGH.value,
                file_path="data/incoming/government_mail/vendor_tax_clearance.pdf",
                file_type="PDF",
                format="PDF",
                attachment_count=1,
                attachments_list=["vendor_tax_clearance.pdf"],
                suggested_department_name="Finance",
                suggested_department_id=1,
                suggested_employee_name="Rahul Sharma",
                suggested_employee_id=101,
                status="Received"
            ),
            DocumentModel(
                id=4,
                title="Urgent Campus Security Infrastructure Upgrade Order (Pre-Reviewed)",
                date=f"{now_day} 10:15 AM",
                mode="Physical / Scanned PDF",
                source="Office of the Director",
                priority=PriorityEnum.HIGH.value,
                file_path="data/incoming/scans/security_infrastructure_upgrade.pdf",
                file_type="Scanned PDF",
                format="PDF",
                attachment_count=1,
                attachments_list=["security_infrastructure_upgrade.pdf"],
                suggested_department_name="Finance",
                suggested_department_id=1,
                suggested_employee_name="Rahul Sharma",
                suggested_employee_id=101,
                director_remark="Approved. Expedite procurement and assign to Rahul Sharma for immediate execution.",
                has_prior_director_remark=True,
                status="Received"
            ),
            DocumentModel(
                id=5,
                title="High-Priority Enterprise Server Maintenance & Firewall Compliance",
                date=f"{now_day} 10:30 AM",
                mode="Internet / Web Portal",
                source="Cyber Security Directorate",
                priority=PriorityEnum.HIGH.value,
                deadline=deadline_7d,
                file_path="data/incoming/outlook/server_maintenance_compliance.pdf",
                file_type="PDF",
                format="PDF",
                attachment_count=2,
                attachments_list=["server_maintenance_compliance.pdf", "firewall_rules.xlsx"],
                suggested_department_name="Technical",
                suggested_department_id=5,
                status="Received"
            ),
        ]

    # =========================================================
    # AUTHENTICATION & USER SESSION
    # =========================================================

    def authenticate(self, username: str, password: str) -> Optional[UserModel]:
        u = username.strip().lower()
        alias_map = {
            "master": "ds",
            "hod": "hod_finance",
            "employee": "emp_rahul",
            "rahul": "emp_rahul",
            "employee2": "emp_priya",
            "priya": "emp_priya",
            "sneha": "emp_sneha",
            "amit": "emp_amit",
            "neha": "emp_neha",
            "rohan": "emp_rohan",
            "arjun": "emp_arjun",
            "karan": "emp_karan",
            "pooja": "emp_pooja",
            "vivek": "emp_vivek",
            "anjali": "emp_anjali",
            "rohit": "emp_rohit",
            "meera": "emp_meera",
            "tanvi": "emp_tanvi",
            "akash": "emp_akash",
            "suresh": "emp_suresh",
            "kavita": "emp_kavita",
            "nikhil": "emp_nikhil",
            "snehal": "emp_snehal",
            "omkar": "emp_omkar",
            "aditya": "emp_aditya",
            "riya": "emp_riya",
            "siddhant": "emp_siddhant",
            "isha": "emp_isha",
            "yash": "emp_yash",
        }
        if u in alias_map:
            u = alias_map[u]
        if u in self._users:
            self._current_user = self._users[u]
            return self._current_user
        return None

    def get_current_user(self) -> Optional[UserModel]:
        return self._current_user

    def logout(self) -> None:
        self._current_user = None

    def get_users(self, role: Optional[str] = None, department_id: Optional[int] = None) -> List[UserModel]:
        seen_ids = set()
        users = []
        for u in self._users.values():
            if u.id not in seen_ids:
                seen_ids.add(u.id)
                users.append(u)
        if role:
            users = [u for u in users if (u.role or "").lower() == role.lower()]
        if department_id:
            users = [u for u in users if u.department_id == department_id]
        return users

    def get_departments(self) -> List[DepartmentModel]:
        return [DepartmentModel.from_dict(d) for d in self._departments]

    # =========================================================
    # DOCUMENT LIFECYCLE & INBOX
    # =========================================================

    def get_inbox(self) -> List[DocumentModel]:
        return list(self._inbox_documents)

    def add_inbox_item(self, document: DocumentModel) -> DocumentModel:
        if document.id is None:
            self._next_doc_id += 1
            document.id = self._next_doc_id
        self._inbox_documents.append(document)
        from services.event_bus import event_bus
        event_bus.notify_inbox_updated()
        return document

    def remove_inbox_item(self, item_id: int) -> bool:
        """Removes an incoming intake item after it has been processed and registered."""
        initial_len = len(self._inbox_documents)
        self._inbox_documents = [d for d in self._inbox_documents if d.id != item_id]
        if len(self._inbox_documents) < initial_len:
            from services.event_bus import event_bus
            event_bus.notify_inbox_updated()
            return True
        return False

    def get_documents(
        self,
        status: Optional[str] = None,
        department: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[DocumentModel]:
        # Enforce canonical document identity: exactly one record per unique ID / reference
        seen_ids = set()
        unique_documents: List[DocumentModel] = []
        for d in self._documents:
            ident = d.id if d.id is not None else d.reference_no
            if ident not in seen_ids:
                seen_ids.add(ident)
                unique_documents.append(d)

        results = list(unique_documents)

        # 1. Enforce Strict Role-Based and Department-Based Scoping from Authenticated Session
        if self._current_user:
            role = (self._current_user.role or "").lower()
            if role in (RoleEnum.HOD.value.lower(), "hod"):
                dept_name = (self._current_user.department_name or "").lower()
                dept_id = self._current_user.department_id
                # HOD sees active documents belonging to their department that have been formally routed by DS
                results = [
                    d for d in results
                    if (
                        ((dept_name and (d.target_department_name or "").lower() == dept_name)
                         or (dept_id is not None and d.target_department_id == dept_id))
                        and d.current_stage in (WorkflowStageEnum.HOD.value, WorkflowStageEnum.EMPLOYEE.value, WorkflowStageEnum.CLOSED.value)
                        and d.current_stage not in (WorkflowStageEnum.DS.value, WorkflowStageEnum.DIRECTOR.value)
                    )
                ]
            elif role in (RoleEnum.EMPLOYEE.value.lower(), "employee"):
                emp_id = self._current_user.id
                # Employee sees tasks specifically assigned to them
                results = [
                    d for d in results
                    if d.assigned_employee_id == emp_id
                    and d.current_stage in (WorkflowStageEnum.EMPLOYEE.value, WorkflowStageEnum.CLOSED.value)
                    and d.current_stage not in (WorkflowStageEnum.DS.value, WorkflowStageEnum.DIRECTOR.value, WorkflowStageEnum.HOD.value)
                ]

        # 2. Query Filters
        if status and status != "All Status":
            results = [d for d in results if (d.status or "").lower() == status.lower()]
        if department and department != "All Departments":
            results = [d for d in results if (d.target_department_name or d.department or "").lower() == department.lower()]
        if source and source != "All Sources":
            results = [d for d in results if (d.source or "").lower() == source.lower()]
        if search:
            q = search.lower()
            results = [
                d for d in results
                if q in (d.title or "").lower()
                or q in (d.reference_no or "").lower()
                or q in (d.source or "").lower()
            ]
        return results

    def get_document(self, document_id: int) -> Optional[DocumentModel]:
        for d in self._documents:
            if d.id == document_id:
                return d
        for d in self._inbox_documents:
            if d.id == document_id:
                return d
        return None

    def create_document(self, document: DocumentModel, file_path: Optional[str] = None) -> DocumentModel:
        """
        Creates or updates a document in the registered collection.
        If a document with the same ID or reference number already exists, updates it in place
        to guarantee exactly one canonical record per document.
        """
        # 1. Check if document already exists by ID or by reference_no in _documents
        existing_doc = None
        if document.id is not None:
            existing_doc = next((d for d in self._documents if d.id == document.id), None)
        if not existing_doc and document.reference_no:
            existing_doc = next((d for d in self._documents if d.reference_no == document.reference_no), None)

        if existing_doc:
            # Update existing document record in place
            if document.title:
                existing_doc.title = document.title
            if document.date:
                existing_doc.date = document.date
            if document.mode:
                existing_doc.mode = document.mode
            if document.source:
                existing_doc.source = document.source
            if document.priority:
                existing_doc.priority = document.priority
            if document.deadline is not None:
                existing_doc.deadline = document.deadline
            if document.format:
                existing_doc.format = document.format
            if document.file_type:
                existing_doc.file_type = document.file_type
            if file_path or document.file_path:
                existing_doc.file_path = file_path or document.file_path
            if document.ocr_text:
                existing_doc.ocr_text = document.ocr_text
            if document.target_department_id is not None:
                existing_doc.target_department_id = document.target_department_id
            if document.target_department_name:
                existing_doc.target_department_name = document.target_department_name
            if document.assigned_employee_id is not None:
                existing_doc.assigned_employee_id = document.assigned_employee_id
            if document.assigned_employee_name:
                existing_doc.assigned_employee_name = document.assigned_employee_name
            if document.suggested_department_id is not None:
                existing_doc.suggested_department_id = document.suggested_department_id
            if document.suggested_department_name:
                existing_doc.suggested_department_name = document.suggested_department_name
            if document.suggested_employee_id is not None:
                existing_doc.suggested_employee_id = document.suggested_employee_id
            if document.suggested_employee_name:
                existing_doc.suggested_employee_name = document.suggested_employee_name
            if document.director_remark:
                existing_doc.director_remark = document.director_remark
            if document.has_prior_director_remark:
                existing_doc.has_prior_director_remark = document.has_prior_director_remark
            if document.has_director_routing_instruction:
                existing_doc.has_director_routing_instruction = document.has_director_routing_instruction
            if document.attachment_count:
                existing_doc.attachment_count = document.attachment_count
            if document.attachments_list:
                existing_doc.attachments_list = document.attachments_list
            existing_doc.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

            # Remove from incoming inbox queue if present
            if document.id is not None:
                self.remove_inbox_item(document.id)
            if existing_doc.id is not None and existing_doc.id != document.id:
                self.remove_inbox_item(existing_doc.id)

            from services.event_bus import event_bus
            event_bus.notify_document_updated(existing_doc)
            return existing_doc

        # 2. Brand new document registration
        if document.id is not None and not any(d.id == document.id for d in self._documents):
            doc_id = document.id
            if doc_id >= self._next_doc_id:
                self._next_doc_id = doc_id
        else:
            self._next_doc_id += 1
            doc_id = self._next_doc_id

        ref_no = document.reference_no or f"CDTRS-2026-{doc_id:04d}"

        new_doc = DocumentModel(
            id=doc_id,
            reference_no=ref_no,
            title=document.title,
            date=document.date or datetime.now().strftime("%Y-%m-%d"),
            mode=document.mode or IngestionModeEnum.GOVERNMENT_MAIL.value,
            source=document.source or "External",
            priority=document.priority or PriorityEnum.MEDIUM.value,
            deadline=document.deadline,
            status=document.status or DocumentStatusEnum.RECEIVED.value,
            current_stage=document.current_stage or WorkflowStageEnum.DS.value,
            director_remark=document.director_remark,
            hod_remark=document.hod_remark,
            target_department_id=document.target_department_id,
            target_department_name=document.target_department_name,
            assigned_employee_id=document.assigned_employee_id,
            assigned_employee_name=document.assigned_employee_name,
            suggested_department_id=document.suggested_department_id,
            suggested_department_name=document.suggested_department_name,
            suggested_employee_id=document.suggested_employee_id,
            suggested_employee_name=document.suggested_employee_name,
            has_director_routing_instruction=document.has_director_routing_instruction,
            has_prior_director_remark=document.has_prior_director_remark,
            file_path=file_path or document.file_path,
            file_type=document.file_type or "PDF",
            format=document.format or "PDF",
            attachment_count=document.attachment_count,
            attachments_list=document.attachments_list
        )
        self._documents.append(new_doc)
        self._log_event(doc_id, action="Document Ingested", from_role="DS", remarks=f"Document {ref_no} registered into repository.")

        # Create original source attachment if file exists
        if new_doc.file_path:
            self.upload_attachment(
                document_id=doc_id,
                file_path=new_doc.file_path,
                category="ORIGINAL",
                source=new_doc.source or "Initial Intake"
            )

        if document.id is not None:
            self.remove_inbox_item(document.id)

        from services.event_bus import event_bus
        event_bus.notify_document_created(new_doc)
        return new_doc

    def close_document(self, document_id: int, remarks: Optional[str] = None) -> DocumentModel:
        doc = self.get_document(document_id)
        if not doc:
            raise ValueError(f"Document #{document_id} not found.")

        doc.status = DocumentStatusEnum.CLOSED.value
        doc.current_stage = WorkflowStageEnum.CLOSED.value
        doc.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        self._log_event(
            document_id,
            action="Document Closed",
            from_role="DS",
            remarks=remarks or "Document finalized and closed by Director Secretary."
        )
        from services.event_bus import event_bus
        event_bus.notify_document_updated(doc)
        return doc

    # =========================================================
    # ROUTING (DS Decisions & Director Return)
    # =========================================================

    def route_document(
        self,
        document_id: int,
        route_type: str,
        to_user_id: Optional[int] = None,
        to_department_id: Optional[int] = None,
        remarks: Optional[str] = None
    ) -> DocumentModel:
        doc = self.get_document(document_id)
        if not doc:
            raise ValueError(f"Document #{document_id} not found.")

        # Ensure document is in registered collection _documents and not duplicate
        if not any(d.id == doc.id for d in self._documents):
            self._documents.append(doc)

        # Remove from incoming queue if it was an inbox item
        self.remove_inbox_item(document_id)

        self._next_route_id += 1
        route = DocumentRouteModel(
            id=self._next_route_id,
            document_id=document_id,
            route_type=route_type,
            from_user_id=self._current_user.id if self._current_user else 1,
            to_user_id=to_user_id,
            to_department_id=to_department_id,
            remarks=remarks,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
        )
        self._routes.append(route)

        if route_type == RouteTypeEnum.DS_TO_DIRECTOR.value:
            doc.current_stage = WorkflowStageEnum.DIRECTOR.value
            doc.status = DocumentStatusEnum.UNDER_DIRECTOR_REVIEW.value
            doc.current_owner_id = 2
            doc.current_owner_name = "Director"
            self._log_event(document_id, action="Routed to Director", from_role="DS", to_role="Director", remarks=remarks or "Forwarded for Executive Review")
            self._send_notification(user_id=2, document=doc, title="New Document for Review", message=f"DS routed {doc.reference} for your review.")

        elif route_type == RouteTypeEnum.DS_TO_HOD.value:
            doc.current_stage = WorkflowStageEnum.HOD.value
            doc.status = DocumentStatusEnum.UNDER_HOD_PROCESSING.value
            doc.target_department_id = to_department_id
            # Clear previous employee assignment on new department routing
            doc.assigned_employee_id = None
            doc.assigned_employee_name = None
            if to_department_id:
                for d in self._departments:
                    if d["id"] == to_department_id:
                        doc.target_department_name = d["name"]
                        break
            doc.has_director_routing_instruction = False
            self._log_event(document_id, action="Routed to HOD", from_role="DS", to_role="HOD", remarks=remarks or f"Destination: {doc.target_department_name or 'HOD'}")
            
            # Send notification to the specific department HOD
            matching_hod = next((u for u in self._users.values() if (u.role or "").lower() == "hod" and u.department_id == to_department_id), None)
            if matching_hod:
                self._send_notification(user_id=matching_hod.id, document=doc, title="Document Received for Department", message=f"DS routed {doc.reference} to {doc.target_department_name} HOD.")

        elif route_type == RouteTypeEnum.DS_TO_EMPLOYEE.value:
            doc.current_stage = WorkflowStageEnum.EMPLOYEE.value
            doc.status = DocumentStatusEnum.ASSIGNED_FOR_EXECUTION.value
            doc.assigned_employee_id = to_user_id
            if to_user_id:
                for u in self._users.values():
                    if u.id == to_user_id:
                        doc.assigned_employee_name = u.full_name
                        if u.department_name:
                            doc.target_department_name = u.department_name
                            doc.target_department_id = u.department_id
                        break
            doc.has_director_routing_instruction = False
            self._log_event(document_id, action="Directly Routed to Employee", from_role="DS", to_role="Employee", remarks=remarks or f"Employee: {doc.assigned_employee_name or 'Staff'}")
            if to_user_id:
                self._send_notification(user_id=to_user_id, document=doc, title="Direct Task Assigned", message=f"DS routed {doc.reference} directly to you.")

        elif route_type == RouteTypeEnum.DIRECTOR_TO_DS.value:
            doc.current_stage = WorkflowStageEnum.DS.value
            doc.status = DocumentStatusEnum.DIRECTOR_REVIEW_COMPLETED.value
            doc.current_owner_id = 1
            doc.current_owner_name = "Director Secretary"
            self._log_event(document_id, action="Returned to DS", from_role="Director", to_role="DS", remarks=remarks or "Returned to Director Secretary")
            self._send_notification(user_id=1, document=doc, title="Document Returned", message=f"Director returned {doc.reference} with remarks.")

        elif route_type == RouteTypeEnum.DS_TO_DIRECTOR_FOLLOWUP.value:
            doc.current_stage = WorkflowStageEnum.DIRECTOR.value
            doc.status = DocumentStatusEnum.UNDER_DIRECTOR_REVIEW.value
            self._log_event(document_id, action="Follow-up Forwarded to Director", from_role="DS", to_role="Director", remarks=remarks or "Progress follow-up forwarded to Director")
            self._send_notification(user_id=2, document=doc, title="Progress Follow-up", message=f"DS forwarded employee progress for {doc.reference}.")

        doc.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        from services.event_bus import event_bus
        event_bus.notify_document_updated(doc)
        return doc

    def save_director_remark(self, document_id: int, remark: str) -> DocumentModel:
        doc = self.get_document(document_id)
        if not doc:
            raise ValueError(f"Document #{document_id} not found.")

        doc.director_remark = remark
        doc.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Analyze remark for routing instructions (SUGGESTION ONLY - NEVER AUTO-ROUTE)
        from services.routing_service import routing_service
        analysis = routing_service.analyze_director_remark(remark)
        doc.has_director_routing_instruction = analysis["has_routing_instruction"]
        doc.director_routing_raw_text = remark
        doc.routing_instruction_confidence = analysis.get("confidence", 0)

        if analysis["has_routing_instruction"]:
            doc.suggested_department_name = analysis.get("suggested_department")
            doc.suggested_department_id = analysis.get("suggested_department_id")
            doc.suggested_employee_name = analysis.get("suggested_employee")
            doc.suggested_employee_id = analysis.get("suggested_employee_id")

        self._log_event(document_id, action="Director Remark Saved", from_role="Director", remarks=remark)
        from services.event_bus import event_bus
        event_bus.notify_document_updated(doc)
        return doc

    def return_to_ds(self, document_id: int, remarks: Optional[str] = None) -> DocumentModel:
        doc = self.get_document(document_id)
        if remarks and (not doc or not doc.director_remark):
            self.save_director_remark(document_id, remarks)
        return self.route_document(
            document_id=document_id,
            route_type=RouteTypeEnum.DIRECTOR_TO_DS.value,
            to_user_id=1,
            remarks=remarks
        )

    def save_hod_remark(self, document_id: int, remark: str) -> DocumentModel:
        doc = self.get_document(document_id)
        if not doc:
            raise ValueError(f"Document #{document_id} not found.")

        doc.hod_remark = remark
        doc.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._log_event(document_id, action="HOD Remark Saved", from_role="HOD", remarks=remark)
        from services.event_bus import event_bus
        event_bus.notify_document_updated(doc)
        return doc

    def forward_followup_to_director(self, document_id: int, remarks: Optional[str] = None) -> DocumentModel:
        return self.route_document(
            document_id=document_id,
            route_type=RouteTypeEnum.DS_TO_DIRECTOR_FOLLOWUP.value,
            to_user_id=2,
            remarks=remarks
        )

    # =========================================================
    # WORK ASSIGNMENT (HOD -> Employee Delegation)
    # =========================================================

    def assign_employee(
        self,
        document_id: int,
        assigned_to_id: int,
        instructions: Optional[str] = None
    ) -> WorkAssignmentModel:
        doc = self.get_document(document_id)
        if not doc:
            raise ValueError(f"Document #{document_id} not found.")

        assigned_user = next((u for u in self._users.values() if u.id == assigned_to_id), None)
        assigned_name = assigned_user.full_name if assigned_user else f"Employee #{assigned_to_id}"

        self._next_assign_id += 1
        assign = WorkAssignmentModel(
            id=self._next_assign_id,
            document_id=document_id,
            assigned_by_id=self._current_user.id if self._current_user else 3,
            assigned_to_id=assigned_to_id,
            assigned_to_name=assigned_name,
            instructions=instructions,
            is_active=True,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
        )
        self._assignments.append(assign)

        # Update Document state
        doc.status = DocumentStatusEnum.ASSIGNED_FOR_EXECUTION.value
        doc.current_stage = WorkflowStageEnum.EMPLOYEE.value
        doc.assigned_employee_id = assigned_to_id
        doc.assigned_employee_name = assigned_name
        doc.current_owner_id = assigned_to_id
        doc.current_owner_name = assigned_name
        doc.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        self._log_event(
            document_id,
            action="Employee Assigned",
            from_role="HOD",
            to_role="Employee",
            remarks=f"Assigned to {assigned_name}. Instructions: {instructions or 'None'}"
        )
        self._send_notification(
            user_id=assigned_to_id,
            document=doc,
            title="Task Assigned",
            message=f"HOD assigned {doc.reference}: {doc.title}"
        )
        from services.event_bus import event_bus
        event_bus.notify_document_updated(doc)
        return assign

    def get_assignments(self, document_id: int) -> List[WorkAssignmentModel]:
        return [a for a in self._assignments if a.document_id == document_id]

    # =========================================================
    # PROGRESS & ATTACHMENTS (Employee Reporting)
    # =========================================================

    def submit_progress(
        self,
        document_id: int,
        description: str,
        attachment_file_path: Optional[str] = None
    ) -> ProgressUpdateModel:
        doc = self.get_document(document_id)
        if not doc:
            raise ValueError(f"Document #{document_id} not found.")

        self._next_progress_id += 1
        user_id = self._current_user.id if self._current_user else 101
        user_name = self._current_user.full_name if self._current_user else "Rahul Sharma"

        progress = ProgressUpdateModel(
            id=self._next_progress_id,
            document_id=document_id,
            user_id=user_id,
            user_name=user_name,
            description=description,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            attachments=[]
        )

        if attachment_file_path:
            attach = self.upload_attachment(
                document_id=document_id,
                file_path=attachment_file_path,
                progress_update_id=progress.id,
                category="WORKFLOW",
                source="Employee Progress"
            )
            progress.attachments.append(attach)

        self._progress_updates.append(progress)

        # Update Document state
        doc.status = DocumentStatusEnum.PROGRESS_UPDATED.value
        doc.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        self._log_event(
            document_id,
            action="Progress Update Submitted",
            from_role="Employee",
            remarks=description
        )

        # Notify HOD and DS
        if doc.target_department_id:
            matching_hod = next((u for u in self._users.values() if (u.role or "").lower() == "hod" and u.department_id == doc.target_department_id), None)
            if matching_hod:
                self._send_notification(user_id=matching_hod.id, document=doc, title="Progress Updated", message=f"{user_name} updated progress for {doc.reference}.")
        self._send_notification(user_id=1, document=doc, title="Progress Updated", message=f"{user_name} updated progress for {doc.reference}.")

        from services.event_bus import event_bus
        event_bus.notify_document_updated(doc)
        return progress

    def get_progress_updates(self, document_id: int) -> List[ProgressUpdateModel]:
        return [p for p in self._progress_updates if p.document_id == document_id]

    def upload_attachment(
        self,
        document_id: int,
        file_path: str,
        progress_update_id: Optional[int] = None,
        category: str = "WORKFLOW",
        source: Optional[str] = None
    ) -> AttachmentModel:
        self._next_attach_id += 1
        user_id = self._current_user.id if self._current_user else 1
        user_name = self._current_user.full_name if self._current_user else "User"

        filename = os.path.basename(file_path) if file_path else "attachment"
        file_size = os.path.getsize(file_path) if (file_path and os.path.exists(file_path)) else 1024
        file_ext = filename.rsplit(".", 1)[-1].upper() if "." in filename else "PDF"

        attach = AttachmentModel(
            id=self._next_attach_id,
            document_id=document_id,
            progress_update_id=progress_update_id,
            file_name=filename,
            file_path=file_path,
            file_type=file_ext,
            file_size=file_size,
            category=category,
            source=source or "Upload",
            uploaded_by=user_id,
            uploaded_by_name=user_name,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
        )
        self._attachments.append(attach)

        # Update document attachment count
        doc = self.get_document(document_id)
        if doc:
            doc.attachment_count = len([a for a in self._attachments if a.document_id == document_id])

        self._log_event(
            document_id,
            action="Attachment Uploaded",
            from_role=self._current_user.role if self._current_user else "User",
            remarks=f"File: {filename} ({category})"
        )
        return attach

    def get_attachments(
        self,
        document_id: int,
        category: Optional[str] = None
    ) -> List[AttachmentModel]:
        results = [a for a in self._attachments if a.document_id == document_id]
        if category:
            results = [a for a in results if a.category.upper() == category.upper()]
        return results

    # =========================================================
    # WORKFLOW AUDIT & HISTORY
    # =========================================================

    def _log_event(
        self,
        document_id: int,
        action: str,
        from_role: Optional[str] = None,
        to_role: Optional[str] = None,
        remarks: Optional[str] = None
    ) -> WorkflowEventModel:
        self._next_event_id += 1
        user_id = self._current_user.id if self._current_user else 1
        user_name = self._current_user.full_name if self._current_user else from_role or "System"

        event = WorkflowEventModel(
            id=self._next_event_id,
            document_id=document_id,
            action=action,
            from_role=from_role,
            to_role=to_role,
            remarks=remarks,
            performed_by=user_id,
            performed_by_name=user_name,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M")
        )

        if document_id not in self._history:
            self._history[document_id] = []
        self._history[document_id].append(event)
        return event

    def get_workflow_history(self, document_id: int) -> List[WorkflowEventModel]:
        doc = self.get_document(document_id)
        if not doc:
            return []

        # Enforce Scoping
        if self._current_user:
            role = (self._current_user.role or "").lower()
            if role in (RoleEnum.HOD.value.lower(), "hod"):
                dept_name = (self._current_user.department_name or "").lower()
                dept_id = self._current_user.department_id
                if not ((dept_name and (doc.target_department_name or "").lower() == dept_name) or (dept_id is not None and doc.target_department_id == dept_id)):
                    return []
            elif role in (RoleEnum.EMPLOYEE.value.lower(), "employee"):
                if doc.assigned_employee_id != self._current_user.id:
                    return []

        return self._history.get(document_id, [])

    def get_all_audit_history(
        self,
        user: Optional[str] = None,
        action: Optional[str] = None
    ) -> List[WorkflowEventModel]:
        # Determine authorized document IDs based on active authenticated session
        authorized_doc_ids = None
        if self._current_user:
            role = (self._current_user.role or "").lower()
            if role in (RoleEnum.HOD.value.lower(), "hod"):
                dept_name = (self._current_user.department_name or "").lower()
                dept_id = self._current_user.department_id
                authorized_doc_ids = {
                    d.id for d in self._documents
                    if (dept_name and (d.target_department_name or "").lower() == dept_name)
                    or (dept_id is not None and d.target_department_id == dept_id)
                }
            elif role in (RoleEnum.EMPLOYEE.value.lower(), "employee"):
                emp_id = self._current_user.id
                authorized_doc_ids = {
                    d.id for d in self._documents
                    if d.assigned_employee_id == emp_id
                }

        all_events: List[WorkflowEventModel] = []
        for doc_id, events in self._history.items():
            if authorized_doc_ids is None or doc_id in authorized_doc_ids:
                all_events.extend(events)

        if user and user != "All Users":
            all_events = [e for e in all_events if (e.performed_by_name or e.from_role or "").lower() == user.lower()]
        if action and action != "All Actions":
            all_events = [e for e in all_events if (e.action or "").lower() == action.lower()]

        return all_events

    # =========================================================
    # NOTIFICATIONS
    # =========================================================

    def _send_notification(self, user_id: int, document: DocumentModel, title: str, message: str) -> None:
        self._next_notif_id += 1
        notif = NotificationModel(
            id=self._next_notif_id,
            user_id=user_id,
            document_id=document.id or 0,
            title=title,
            message=message,
            is_read=False,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
        )
        self._notifications.append(notif)
        from services.event_bus import event_bus
        event_bus.notify_notifications_updated()

    def get_notifications(
        self,
        user_id: Optional[int] = None,
        unread_only: bool = False
    ) -> List[NotificationModel]:
        target_uid = user_id or (self._current_user.id if self._current_user else 1)
        results = [n for n in self._notifications if n.user_id == target_uid]
        if unread_only:
            results = [n for n in results if not n.is_read]
        return results

    def mark_notification_read(self, notification_id: int) -> bool:
        for n in self._notifications:
            if n.id == notification_id:
                n.is_read = True
                from services.event_bus import event_bus
                event_bus.notify_notifications_updated()
                return True
        return False

    # =========================================================
    # METRICS & DASHBOARD
    # =========================================================

    def get_dashboard_summary(self, role: Optional[str] = None) -> Dict[str, Any]:
        target_role = role or (self._current_user.role if self._current_user else RoleEnum.DIRECTOR_SECRETARY.value)
        target_role_lower = (target_role or "").lower()

        docs = self.get_documents()
        total = len(docs)
        in_progress = len([d for d in docs if d.current_stage in (WorkflowStageEnum.HOD.value, WorkflowStageEnum.EMPLOYEE.value)])
        closed = len([d for d in docs if d.current_stage == WorkflowStageEnum.CLOSED.value])
        high_priority = len([d for d in docs if (d.priority or "").lower() == "high"])

        if target_role_lower in (RoleEnum.DIRECTOR.value.lower(), "director"):
            pending_review = len([d for d in self._documents if d.current_stage == WorkflowStageEnum.DIRECTOR.value])
            reviewed = len([d for d in self._documents if d.director_remark or d.status == DocumentStatusEnum.DIRECTOR_REVIEW_COMPLETED.value])
            return {
                "total_documents": total,
                "pending_review": pending_review,
                "reviewed_documents": reviewed,
                "high_priority": high_priority,
                "recent_documents": docs[:5]
            }
        elif target_role_lower in (RoleEnum.HOD.value.lower(), "hod"):
            unassigned = len([d for d in docs if not d.assigned_employee_name and d.current_stage == WorkflowStageEnum.HOD.value])
            progress_updated = len([d for d in docs if d.status == DocumentStatusEnum.PROGRESS_UPDATED.value])
            return {
                "total_documents": total,
                "unassigned_tasks": unassigned,
                "in_progress": in_progress,
                "progress_updated": progress_updated,
                "recent_documents": docs[:5]
            }
        elif target_role_lower in (RoleEnum.EMPLOYEE.value.lower(), "employee"):
            new_tasks = len([d for d in docs if d.status == DocumentStatusEnum.ASSIGNED_FOR_EXECUTION.value])
            return {
                "total_documents": total,
                "new_assignments": new_tasks,
                "in_progress": in_progress,
                "high_priority": high_priority,
                "recent_documents": docs[:5]
            }
        else:
            pending_ds = len([d for d in self._documents if d.current_stage == WorkflowStageEnum.DS.value])
            return {
                "total_documents": len(self._documents),
                "inbox_items": len(self._inbox_documents),
                "pending_ds": pending_ds,
                "in_progress": in_progress,
                "closed": closed,
                "high_priority": high_priority,
                "recent_documents": docs[:5]
            }

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_documents": len(self._documents),
            "pending_review": len([d for d in self._documents if d.current_stage == WorkflowStageEnum.DIRECTOR.value]),
            "in_progress": len([d for d in self._documents if d.current_stage in (WorkflowStageEnum.HOD.value, WorkflowStageEnum.EMPLOYEE.value)]),
            "closed": len([d for d in self._documents if d.current_stage == WorkflowStageEnum.CLOSED.value]),
            "high_priority": len([d for d in self._documents if (d.priority or "").lower() == "high"])
        }

    def get_department_metrics(self, department_id: int) -> Dict[str, Any]:
        dept_docs = [d for d in self._documents if d.target_department_id == department_id]
        return {
            "total": len(dept_docs),
            "unassigned": len([d for d in dept_docs if not d.assigned_employee_id and d.current_stage == WorkflowStageEnum.HOD.value]),
            "in_progress": len([d for d in dept_docs if d.current_stage == WorkflowStageEnum.EMPLOYEE.value and d.status != DocumentStatusEnum.PROGRESS_UPDATED.value]),
            "progress_updated": len([d for d in dept_docs if d.status == DocumentStatusEnum.PROGRESS_UPDATED.value])
        }
