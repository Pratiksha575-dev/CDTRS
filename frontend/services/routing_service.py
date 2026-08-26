from typing import Any, Dict, Optional

from models.document import DocumentModel
from models.enums import RouteTypeEnum
from repositories.provider import get_repository


class RoutingService:
    """
    Client service managing Director Secretary (DS) routing decisions,
    Director returns, workflow remark persistence, and Director remark routing extraction.
    """

    def __init__(self):
        pass

    def route_to_director(self, document_id: int, remarks: Optional[str] = None) -> DocumentModel:
        """DS routes document to Director for review.
        Backend resolves routing to the Director role — no hardcoded user ID required.
        """
        repo = get_repository()
        return repo.route_document(
            document_id=document_id,
            route_type=RouteTypeEnum.DS_TO_DIRECTOR.value,
            remarks=remarks or "Forwarded for Director Review"
        )

    def route_to_hod(
        self,
        document_id: int,
        department_id: Optional[int] = None,
        remarks: Optional[str] = None,
        department_name: Optional[str] = None
    ) -> DocumentModel:
        """DS routes document to HOD for departmental processing."""
        repo = get_repository()
        if department_id is None and department_name:
            # Look up real department ID from the backend
            try:
                departments = repo.get_departments()
                for dept in departments:
                    if dept.name.lower() == department_name.lower() or (
                        dept.name.lower() in department_name.lower()
                        or department_name.lower() in dept.name.lower()
                    ):
                        department_id = dept.id
                        break
            except Exception:
                pass
        if department_id is None:
            raise ValueError(
                f"Cannot route to HOD: department ID is unknown for '{department_name}'. "
                "Ensure the backend is connected and departments are registered."
            )
        return repo.route_document(
            document_id=document_id,
            route_type=RouteTypeEnum.DS_TO_HOD.value,
            to_department_id=department_id,
            remarks=remarks
        )

    def route_to_employee(
        self,
        document_id: int,
        employee_id: int,
        remarks: Optional[str] = None,
        employee_name: Optional[str] = None
    ) -> DocumentModel:
        """DS directly routes document to identified Employee."""
        repo = get_repository()
        return repo.route_document(
            document_id=document_id,
            route_type=RouteTypeEnum.DS_TO_EMPLOYEE.value,
            to_user_id=employee_id,
            remarks=remarks
        )

    def return_to_ds(self, document_id: int, remarks: Optional[str] = None) -> DocumentModel:
        """Director returns reviewed document back to DS."""
        repo = get_repository()
        return repo.return_to_ds(document_id=document_id, remarks=remarks)

    def forward_followup_to_director(self, document_id: int, remarks: Optional[str] = None) -> DocumentModel:
        """DS forwards employee progress update to Director as follow-up."""
        repo = get_repository()
        return repo.forward_followup_to_director(document_id=document_id, remarks=remarks)

    def save_director_remark(self, document_id: int, remark: str) -> DocumentModel:
        """Director saves remark on document without returning it."""
        repo = get_repository()
        return repo.save_director_remark(document_id=document_id, remark=remark)

    def save_hod_remark(self, document_id: int, remark: str) -> DocumentModel:
        """HOD saves remark on document without delegating assignment."""
        repo = get_repository()
        return repo.save_hod_remark(document_id=document_id, remark=remark)

    def analyze_director_remark(self, remark: str) -> Dict[str, Any]:
        """
        Analyzes Director remark text for explicit routing/assignment instructions.
        Strictly differentiates between a general review comment (e.g. 'Reviewed', 'Please check')
        and an explicit delegation/assignment directive (e.g. 'Route to Finance', 'Assign to Rahul Sharma').
        Employee names are matched against the live backend user list — not a hardcoded table.
        """
        t = f" {(remark or '').lower().strip()} "
        dept = None
        dept_id = None
        emp = None
        emp_id = None

        # 1. Check for specific individual employee name against live backend users
        try:
            repo = get_repository()
            live_users = repo.get_users(role="Employee")
            for user in live_users:
                name_lower = user.full_name.lower()
                first_name = name_lower.split()[0] if name_lower.split() else ""
                if (
                    f" {name_lower} " in t
                    or f" {first_name} " in t
                    or f" {first_name}," in t
                    or f" {first_name}." in t
                    or f" {first_name}:" in t
                ):
                    emp = user.full_name
                    emp_id = user.id
                    dept = user.department_name
                    dept_id = user.department_id
                    break
        except Exception:
            # If backend unreachable during remark analysis, proceed without employee match
            pass

        # 2. Check for explicit routing/assignment action intent
        routing_action_markers = (
            "assign", "route", "send", "forward", "refer", "hand over",
            "action by", "directed to", "to be handled by", "delegate",
            "task", "expedite", "for action", "for implementation", "for audit"
        )
        has_routing_intent = any(marker in t for marker in routing_action_markers) or (emp is not None)

        # 3. Department detection via keyword matching (text pattern only — ID resolved from backend)
        if has_routing_intent and not dept:
            dept_keywords = [
                ("procurement", "Procurement"),
                ("purchase", "Procurement"),
                ("tender", "Procurement"),
                ("finance", "Finance"),
                ("accounts", "Finance"),
                ("human resource", "Human Resources"),
                (" hr ", "Human Resources"),
                ("hr department", "Human Resources"),
                ("hr dept", "Human Resources"),
                ("maintenance", "Maintenance"),
                ("facility", "Maintenance"),
                ("it department", "IT"),
                ("it dept", "IT"),
                ("it cell", "IT"),
                ("information technology", "IT"),
                ("tech department", "IT"),
            ]
            for keyword, dept_name in dept_keywords:
                if keyword in t:
                    dept = dept_name
                    # Resolve dept_id from backend
                    try:
                        repo = get_repository()
                        for bd in repo.get_departments():
                            if bd.name.lower() == dept_name.lower():
                                dept_id = bd.id
                                break
                    except Exception:
                        pass
                    break

        # Must have both routing intent AND an identified department or employee
        has_instruction = bool(has_routing_intent and (dept or emp))
        conf = 96 if (dept and emp) else (92 if (dept or emp) else 0)
        return {
            "has_routing_instruction": has_instruction,
            "suggested_department": dept if has_instruction else None,
            "suggested_department_id": dept_id if has_instruction else None,
            "suggested_employee": emp if has_instruction else None,
            "suggested_employee_id": emp_id if has_instruction else None,
            "confidence": conf,
            "source": "Director Remark" if has_instruction else None
        }


# Global singleton service instance
routing_service = RoutingService()