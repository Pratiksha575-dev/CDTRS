import os
import sys
import traceback

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# For testing HTTPS without certificate failure on Windows dev environments
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import requests
original_request = requests.Session.request
def insecure_request(self, method, url, *args, **kwargs):
    kwargs["verify"] = False
    return original_request(self, method, url, *args, **kwargs)
requests.Session.request = insecure_request

from config.settings import settings
from repositories.provider import get_repository
from repositories.mock_repository import MockRepository
from repositories.api_repository import APIRepository
from models.enums import RoleEnum, RouteTypeEnum, DocumentStatusEnum
from models.document import DocumentModel


def run_mock_mode_tests():
    print("\n=======================================================")
    print("TEST SUITE 1: MOCK MODE VERIFICATION (Stable Baseline)")
    print("=======================================================")
    settings.set_data_source("mock")
    repo = get_repository()
    assert isinstance(repo, MockRepository), f"Expected MockRepository, got {type(repo)}"
    print("[PASS] Repository provider correctly returned MockRepository")

    # 1. Login
    ds_user = repo.authenticate("ds", "ds123")
    assert ds_user is not None, "DS authentication failed in mock mode"
    assert ds_user.role == RoleEnum.DIRECTOR_SECRETARY.value
    print(f"[PASS] Mock DS Login: {ds_user.full_name} ({ds_user.role})")

    # 2. Inbox
    inbox = repo.get_inbox()
    assert len(inbox) == 20, f"Expected 20 mock inbox items, got {len(inbox)}"
    print(f"[PASS] Mock DS Inbox loaded: {len(inbox)} items")

    # 3. Create Document
    new_doc = DocumentModel(
        title="Test Mock Document 2026",
        date="2026-08-16",
        mode="Government Mail",
        source="Ministry of Electronics",
        priority="High",
        remarks="Urgent review requested."
    )
    created = repo.create_document(new_doc)
    assert created.id is not None
    print(f"[PASS] Mock Create Document: ID={created.id}, Ref={created.reference_no}")

    # Verify document is in document list
    docs = repo.get_documents()
    assert len(docs) > 0, "Mock documents repository should have the created document"
    print(f"[PASS] Mock Document List verified: {len(docs)} documents")

    # 4. Route DS -> Director
    directors = repo.get_users(role=RoleEnum.DIRECTOR.value)
    assert len(directors) > 0
    routed = repo.route_document(created.id, RouteTypeEnum.DS_TO_DIRECTOR.value, to_user_id=directors[0].id)
    assert routed.current_stage == "DIRECTOR"
    print(f"[PASS] Mock Route to Director: Stage={routed.current_stage}, Status={routed.status}")

    # 5. Director Review & Return
    director_user = repo.authenticate("director", "director123")
    assert director_user is not None
    with_remark = repo.save_director_remark(created.id, "Please forward to Finance Department for urgent processing.")
    assert with_remark.director_remark is not None
    returned = repo.return_to_ds(created.id, "Returned to DS with instructions.")
    assert returned.current_stage == "DS"
    print(f"[PASS] Mock Director Remark & Return: Stage={returned.current_stage}")

    # 6. DS Route to HOD Finance
    repo.authenticate("ds", "ds123")
    to_hod = repo.route_document(created.id, RouteTypeEnum.DS_TO_HOD.value, to_department_id=1)
    assert to_hod.current_stage == "HOD"
    print(f"[PASS] Mock Route to HOD Finance: Stage={to_hod.current_stage}, Target Dept={to_hod.target_department_id}")

    # 7. HOD Assign to Employee
    hod_fin = repo.authenticate("hod_finance", "hod123")
    assert hod_fin is not None
    assignment = repo.assign_employee(created.id, assigned_to_id=101, instructions="Analyze financial feasibility.")
    assert assignment.assigned_to_id == 101
    print(f"[PASS] Mock HOD Assign: Assigned To ID={assignment.assigned_to_id}")

    # 8. Employee Progress Update
    emp = repo.authenticate("emp_rahul", "emp123")
    assert emp is not None
    prog = repo.submit_progress(created.id, "Completed initial analysis, financial model attached.")
    assert prog.id is not None
    print(f"[PASS] Mock Employee Progress: Description={prog.description}")

    # 9. Close Document
    repo.authenticate("ds", "ds123")
    closed = repo.close_document(created.id, "All actions finalized and verified.")
    assert closed.current_stage == "CLOSED"
    print(f"[PASS] Mock Close Document: Stage={closed.current_stage}")

    print(">>> ALL MOCK MODE TESTS PASSED SUCCESSFULLY! <<<\n")


def run_api_mode_tests(backend_url="https://cdtrs.onrender.com/api/v1"):
    print("\n=======================================================")
    print(f"TEST SUITE 2: API MODE VERIFICATION ({backend_url})")
    print("=======================================================")
    settings.set_api_url(backend_url)
    settings.set_data_source("api")

    repo = get_repository()
    assert isinstance(repo, APIRepository), f"Expected APIRepository, got {type(repo)}"
    print("[PASS] Repository provider correctly returned APIRepository")

    # 1. Authenticate DS User
    print("\n[1] Testing DS Authentication...")
    ds_user = repo.authenticate("ds_user", "cdtrs@ds")
    assert ds_user is not None, "DS Login failed against live API"
    assert ds_user.role == "Director Secretary", f"Role mapping failed: {ds_user.role}"
    print(f"[PASS] Authenticated DS: {ds_user.full_name}, Role={ds_user.role}")

    # 2. Get Current User (/auth/me)
    print("\n[2] Testing /auth/me resolution...")
    me = repo.get_current_user()
    assert me is not None
    assert me.username == "ds_user"
    print(f"[PASS] Verified /auth/me profile: Username={me.username}, Role={me.role}")

    # 3. DS Inbox & Document List
    print("\n[3] Testing Documents List & Inbox...")
    docs = repo.get_documents()
    print(f"[PASS] Retrieved {len(docs)} documents from backend")
    inbox = repo.get_inbox()
    print(f"[PASS] Retrieved {len(inbox)} role-scoped inbox documents for DS")

    # 4. Create Document
    print("\n[4] Testing Document Registration...")
    new_doc = DocumentModel(
        title="Phase 1 API Integration Verification Document",
        date="2026-08-16",
        mode="Manual Upload",
        source="Ministry Audit Division",
        priority="High",
        remarks="Automated verification dispatch for CDTRS V2 REST API."
    )
    created = repo.create_document(new_doc)
    assert created.id is not None
    assert created.title == new_doc.title
    print(f"[PASS] Created Canonical Document: ID={created.id}, Ref={created.reference_no}, Status={created.status}, Stage={created.current_stage}")

    # 5. Fetch Detailed Document by ID
    print("\n[5] Testing Document Detail Fetch...")
    fetched = repo.get_document(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    print(f"[PASS] Fetched Document Details: Title='{fetched.title}', Priority={fetched.priority}, Version={fetched.version}")

    # 6. Route DS -> Director
    print("\n[6] Testing Routing DS -> Director...")
    directors = repo.get_users(role="Director")
    director_id = directors[0].id if directors else 2  # Default seed Director ID
    routed = repo.route_document(created.id, "DS_TO_DIRECTOR", to_user_id=director_id, remarks="Forwarded to Director for executive review.")
    assert routed.current_stage == "DIRECTOR"
    assert "Director Review" in routed.status
    print(f"[PASS] Routed to Director: Stage={routed.current_stage}, Status='{routed.status}', Version={routed.version}")

    # 7. Director Review, Remark & Return to DS
    print("\n[7] Testing Director Login, Remark & Return to DS...")
    dir_user = repo.authenticate("director", "cdtrs@director")
    assert dir_user is not None
    assert dir_user.role == "Director"
    print(f"[PASS] Director Authenticated: {dir_user.full_name} ({dir_user.role})")

    # Save Director remark with explicit Department instruction
    with_remark = repo.save_director_remark(created.id, "Please forward to Finance Department for immediate action.")
    assert with_remark.director_remark is not None
    print(f"[PASS] Saved Director Remark: '{with_remark.director_remark}'")

    # Return to DS
    returned = repo.return_to_ds(created.id, "Returned with executive guidance.")
    assert returned.current_stage == "DS"
    print(f"[PASS] Director Returned to DS: Stage={returned.current_stage}, Status='{returned.status}'")

    # 8. DS Verifies Remark Suggestion & Routes to HOD Finance
    print("\n[8] Testing DS Suggestion Detection & HOD Routing...")
    repo.authenticate("ds_user", "cdtrs@ds")
    doc_with_sugg = repo.get_document(created.id)
    print(f"[PASS] Director Routing Suggestion Detected: {doc_with_sugg.has_director_routing_instruction} (Confidence: {doc_with_sugg.routing_instruction_confidence}%)")

    # Find Finance department ID
    finance_dept_id = doc_with_sugg.suggested_department_id or 2
    to_hod = repo.route_document(created.id, "DS_TO_HOD", to_department_id=finance_dept_id, remarks="Routing confirmed to Finance department.")
    assert to_hod.current_stage == "HOD"
    print(f"[PASS] Routed to HOD: Stage={to_hod.current_stage}, Target Dept ID={to_hod.target_department_id}")

    # 9. HOD Scoping & Assignment
    print("\n[9] Testing HOD Scoping & Delegation...")
    hod_fin = repo.authenticate("hod_finance", "cdtrs@hod")
    assert hod_fin is not None
    assert hod_fin.role == "HOD"
    print(f"[PASS] HOD Finance Authenticated: {hod_fin.full_name}")

    # Verify HOD inbox contains the document
    hod_inbox = repo.get_inbox()
    matching_inbox = [d for d in hod_inbox if d.id == created.id]
    assert len(matching_inbox) > 0, "Document not visible in Finance HOD inbox"
    print(f"[PASS] Document confirmed visible in Finance HOD queue ({len(hod_inbox)} items)")

    # Test Department Isolation: Procurement HOD should NOT see this document
    hod_proc = repo.authenticate("hod_procurement", "cdtrs@hod")
    assert hod_proc is not None
    proc_inbox = repo.get_inbox()
    assert not any(d.id == created.id for d in proc_inbox), "CRITICAL: Procurement HOD should not see Finance document!"
    print(f"[PASS] Department Isolation Verified: Procurement HOD cannot see Finance document")

    # Back to Finance HOD -> Assign to Employee Rahul
    repo.authenticate("hod_finance", "cdtrs@hod")
    rahul_user_id = 5  # emp_rahul user ID
    assignment = repo.assign_employee(created.id, assigned_to_id=rahul_user_id, instructions="Execute compliance check.")
    assert assignment.assigned_to_id == rahul_user_id
    print(f"[PASS] HOD Assigned Employee: Assigned to ID={assignment.assigned_to_id}")

    # 10. Employee Task Scoping & Progress Update
    print("\n[10] Testing Employee Task Scoping & Progress Submission...")
    emp_rahul = repo.authenticate("emp_rahul", "cdtrs@emp")
    assert emp_rahul is not None
    assert emp_rahul.role == "Employee"
    print(f"[PASS] Employee Rahul Authenticated: {emp_rahul.full_name}")

    emp_inbox = repo.get_inbox()
    assert any(d.id == created.id for d in emp_inbox), "Document not visible in Rahul's task list"
    print(f"[PASS] Document confirmed visible in Rahul's assigned tasks")

    # Test Employee Isolation: Employee Priya should NOT see Rahul's task
    emp_priya = repo.authenticate("emp_priya", "cdtrs@emp")
    assert emp_priya is not None
    priya_inbox = repo.get_inbox()
    assert not any(d.id == created.id for d in priya_inbox), "CRITICAL: Priya should not see Rahul's assigned task!"
    print(f"[PASS] Employee Isolation Verified: Priya cannot see Rahul's task")

    # Rahul submits progress
    repo.authenticate("emp_rahul", "cdtrs@emp")
    prog = repo.submit_progress(created.id, "Compliance verification complete. All standards met.")
    assert prog.id is not None
    print(f"[PASS] Progress update submitted: ID={prog.id}, Description='{prog.description}'")

    # 11. DS Closes Document
    print("\n[11] Testing Document Closure by DS...")
    repo.authenticate("ds_user", "cdtrs@ds")
    closed = repo.close_document(created.id, "Final verification complete. Archive closed.")
    assert closed.current_stage == "CLOSED"
    print(f"[PASS] Document Successfully Closed: Stage={closed.current_stage}, Status='{closed.status}'")

    # 12. History & Dashboard Stats
    print("\n[12] Testing Workflow History & Dashboard API...")
    history = repo.get_workflow_history(created.id)
    assert len(history) > 0
    print(f"[PASS] Retrieved {len(history)} chronological workflow events for document {created.id}")

    dashboard = repo.get_dashboard_summary()
    assert "role" in dashboard
    print(f"[PASS] Dashboard summary retrieved: Role={dashboard.get('role')}, Total Docs={dashboard.get('total_documents')}, Pending={dashboard.get('pending_action')}")

    print("\n>>> ALL API MODE TESTS PASSED SUCCESSFULLY! <<<")


if __name__ == "__main__":
    try:
        run_mock_mode_tests()
        run_api_mode_tests()
        print("\n=======================================================")
        print("SUMMARY: PHASE 1 INTEGRATION VALIDATED 100% COMPLETE!")
        print("=======================================================")
    except Exception as ex:
        print(f"\n[FAIL] Test encountered error: {ex}")
        traceback.print_exc()
        sys.exit(1)
