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
        """DS routes document to Director for review."""
        repo = get_repository()
        return repo.route_document(
            document_id=document_id,
            route_type=RouteTypeEnum.DS_TO_DIRECTOR.value,
            to_user_id=2,
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
            dept_map = {"Finance": 1, "Procurement": 2, "Human Resources": 3, "HR": 3, "Maintenance": 4, "IT": 5}
            department_id = dept_map.get(department_name, 1)
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
        """
        t = f" {(remark or '').lower().strip()} "
        dept = None
        dept_id = None
        emp = None
        emp_id = None

        # Employee detection across all 5 departments
        emp_database = [
            # Finance (1)
            ("rahul sharma", "Rahul Sharma", 101, "Finance", 1),
            ("rahul", "Rahul Sharma", 101, "Finance", 1),
            ("sneha patil", "Sneha Patil", 102, "Finance", 1),
            ("sneha", "Sneha Patil", 102, "Finance", 1),
            ("amit joshi", "Amit Joshi", 103, "Finance", 1),
            ("amit", "Amit Joshi", 103, "Finance", 1),
            ("neha kulkarni", "Neha Kulkarni", 104, "Finance", 1),
            ("neha", "Neha Kulkarni", 104, "Finance", 1),
            ("rohan mehta", "Rohan Mehta", 105, "Finance", 1),
            ("rohan", "Rohan Mehta", 105, "Finance", 1),
            # Procurement (2)
            ("priya verma", "Priya Verma", 201, "Procurement", 2),
            ("priya", "Priya Verma", 201, "Procurement", 2),
            ("arjun shah", "Arjun Shah", 202, "Procurement", 2),
            ("arjun", "Arjun Shah", 202, "Procurement", 2),
            ("karan desai", "Karan Desai", 203, "Procurement", 2),
            ("karan", "Karan Desai", 203, "Procurement", 2),
            ("pooja nair", "Pooja Nair", 204, "Procurement", 2),
            ("pooja", "Pooja Nair", 204, "Procurement", 2),
            ("vivek more", "Vivek More", 205, "Procurement", 2),
            ("vivek", "Vivek More", 205, "Procurement", 2),
            # HR (3)
            ("anjali gupta", "Anjali Gupta", 301, "Human Resources", 3),
            ("anjali", "Anjali Gupta", 301, "Human Resources", 3),
            ("rohit singh", "Rohit Singh", 302, "Human Resources", 3),
            ("rohit", "Rohit Singh", 302, "Human Resources", 3),
            ("meera joshi", "Meera Joshi", 303, "Human Resources", 3),
            ("meera", "Meera Joshi", 303, "Human Resources", 3),
            ("tanvi shah", "Tanvi Shah", 304, "Human Resources", 3),
            ("tanvi", "Tanvi Shah", 304, "Human Resources", 3),
            ("akash patil", "Akash Patil", 305, "Human Resources", 3),
            ("akash", "Akash Patil", 305, "Human Resources", 3),
            # Maintenance (4)
            ("suresh pawar", "Suresh Pawar", 401, "Maintenance", 4),
            ("suresh", "Suresh Pawar", 401, "Maintenance", 4),
            ("kavita more", "Kavita More", 402, "Maintenance", 4),
            ("kavita", "Kavita More", 402, "Maintenance", 4),
            ("nikhil patil", "Nikhil Patil", 403, "Maintenance", 4),
            ("nikhil", "Nikhil Patil", 403, "Maintenance", 4),
            ("snehal jadhav", "Snehal Jadhav", 404, "Maintenance", 4),
            ("snehal", "Snehal Jadhav", 404, "Maintenance", 4),
            ("omkar shinde", "Omkar Shinde", 405, "Maintenance", 4),
            ("omkar", "Omkar Shinde", 405, "Maintenance", 4),
            # IT (5)
            ("aditya kulkarni", "Aditya Kulkarni", 501, "IT", 5),
            ("aditya", "Aditya Kulkarni", 501, "IT", 5),
            ("riya shah", "Riya Shah", 502, "IT", 5),
            ("riya", "Riya Shah", 502, "IT", 5),
            ("siddhant joshi", "Siddhant Joshi", 503, "IT", 5),
            ("siddhant", "Siddhant Joshi", 503, "IT", 5),
            ("isha patil", "Isha Patil", 504, "IT", 5),
            ("isha", "Isha Patil", 504, "IT", 5),
            ("yash deshmukh", "Yash Deshmukh", 505, "IT", 5),
            ("yash", "Yash Deshmukh", 505, "IT", 5),
        ]

        # 1. Check for specific individual employee name
        for token, full_name, e_id, d_name, d_id in emp_database:
            if f" {token} " in t or f" {token}," in t or f" {token}." in t or f" {token}:" in t:
                emp = full_name
                emp_id = e_id
                dept = d_name
                dept_id = d_id
                break

        # 2. Check for explicit routing/assignment action intent
        routing_action_markers = (
            "assign", "route", "send", "forward", "refer", "hand over",
            "action by", "directed to", "to be handled by", "delegate",
            "task", "expedite", "for action", "for implementation", "for audit"
        )
        has_routing_intent = any(marker in t for marker in routing_action_markers) or (emp is not None)

        # 3. Department detection (only if routing intent is present or explicit department instruction)
        if has_routing_intent and not dept:
            if "procurement" in t or "purchase" in t or "tender" in t:
                dept = "Procurement"
                dept_id = 2
            elif "finance" in t or "accounts" in t:
                dept = "Finance"
                dept_id = 1
            elif "human resource" in t or " hr " in t or "hr department" in t or "hr dept" in t:
                dept = "Human Resources"
                dept_id = 3
            elif "maintenance" in t or "facility" in t:
                dept = "Maintenance"
                dept_id = 4
            elif "it department" in t or "it dept" in t or "it cell" in t or "information technology" in t or "tech department" in t:
                dept = "IT"
                dept_id = 5

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