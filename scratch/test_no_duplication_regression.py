import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from PySide6.QtWidgets import QApplication, QMessageBox
app = QApplication.instance() or QApplication(sys.argv)
QMessageBox.information = lambda *args, **kwargs: None
QMessageBox.warning = lambda *args, **kwargs: None
QMessageBox.critical = lambda *args, **kwargs: None

from config.settings import settings
settings.set_data_source("mock")

from repositories.provider import get_repository
from repositories.mock_repository import MockRepository
import repositories.provider as prov
from services.auth_service import auth_service
from services.document_service import document_service
from services.routing_service import routing_service
from services.assignment_service import assignment_service
from services.progress_service import progress_service
from pages.documents import DocumentsPage
from pages.document_intake import DocumentIntakePage
from models.enums import RoleEnum, DocumentStatusEnum, WorkflowStageEnum

print("======================================================================")
print("TESTING STRICT DATA IDENTITY & ZERO DUPLICATION INVARIANT")
print("======================================================================")

# Initialize fresh MockRepository
repo = MockRepository()
prov._mock_repo_instance = repo
auth_service.login("ds", "1234")
docs_page = DocumentsPage(user_role="Director Secretary")

def verify_document_counts(step_name: str, expected_stage: str = None, doc_id: int = 1):
    docs = repo.get_documents()
    refs = [d.reference_no for d in docs]
    unique_refs = set(refs)
    
    docs_page.load_documents()
    ui_rows = docs_page.table.rowCount()
    
    print(f"\n--- STEP: {step_name} ---")
    print(f"  Repo documents count: {len(docs)}")
    print(f"  Unique references: {len(unique_refs)} -> {sorted(list(unique_refs))}")
    print(f"  DocumentsPage UI rows: {ui_rows}")
    
    assert len(docs) == 5, f"[{step_name}] Expected exactly 5 registered documents, got {len(docs)}"
    assert len(unique_refs) == 5, f"[{step_name}] Expected exactly 5 unique references, got {len(unique_refs)} ({refs})"
    assert ui_rows == 5, f"[{step_name}] Expected DocumentsPage to display exactly 5 rows, got {ui_rows}"
    
    if expected_stage:
        target_doc = repo.get_document(doc_id)
        assert target_doc is not None, f"Document {doc_id} must exist"
        assert target_doc.current_stage == expected_stage, f"Document {doc_id} expected stage {expected_stage}, got {target_doc.current_stage}"
        # Ensure no other document has the same reference
        matching = [d for d in docs if d.reference_no == target_doc.reference_no]
        assert len(matching) == 1, f"Found multiple documents with reference {target_doc.reference_no}: {matching}"
        print(f"  [OK] Document {doc_id} ({target_doc.reference_no}) is in stage {target_doc.current_stage}, status {target_doc.status} with EXACTLY ONE record.")

# 1. INITIAL STATE
verify_document_counts("1. Initial Application State", expected_stage=WorkflowStageEnum.DS.value)

# 2. DOCUMENT 1: INTAKE VIA DOCUMENT INTAKE PAGE
print("\n--- Testing Document Intake processing on Document 1 ---")
intake_page = DocumentIntakePage()
intake_page.load_document(repo.get_document(1))
intake_page.save_and_confirm_routing()
verify_document_counts("2. Document 1 Registered & Routed to Director via Intake Page", expected_stage=WorkflowStageEnum.DIRECTOR.value)

# 3. DOCUMENT 1: DIRECTOR -> DS
auth_service.login("director", "1234")
routing_service.save_director_remark(1, "Accreditation directive approved. Proceed with compliance.")
routing_service.return_to_ds(1, remarks="Returned to DS")
auth_service.login("ds", "1234")
verify_document_counts("3. Document 1 Returned by Director to DS", expected_stage=WorkflowStageEnum.DS.value)

# 4. DOCUMENT 1: DS -> HOD
routing_service.route_to_hod(1, department_id=2, remarks="Route to Procurement HOD")
verify_document_counts("4. Document 1 Routed by DS to Procurement HOD", expected_stage=WorkflowStageEnum.HOD.value)

# 5. DOCUMENT 1: HOD -> EMPLOYEE
auth_service.login("hod_proc", "1234")
assignment_service.assign_employee(1, assigned_to_id=201, instructions="Execute compliance verification")
auth_service.login("ds", "1234")
verify_document_counts("5. Document 1 Assigned by HOD to Priya Verma", expected_stage=WorkflowStageEnum.EMPLOYEE.value)

# 6. DOCUMENT 1: EMPLOYEE PROGRESS
auth_service.login("emp_priya", "1234")
progress_service.submit_progress(1, description="Audit completed, certificate ready.")
auth_service.login("ds", "1234")
verify_document_counts("6. Document 1 Progress Submitted by Priya Verma", expected_stage=WorkflowStageEnum.EMPLOYEE.value)

# 7. DOCUMENT 1: FOLLOW-UP TO DIRECTOR
routing_service.forward_followup_to_director(1, remarks="Forwarding progress update")
verify_document_counts("7. Document 1 Forwarded as Follow-up to Director", expected_stage=WorkflowStageEnum.DIRECTOR.value)

# 8. DOCUMENT 1: DIRECTOR ENDORSES & RETURNS
auth_service.login("director", "1234")
routing_service.return_to_ds(1, remarks="Follow-up endorsed")
auth_service.login("ds", "1234")
verify_document_counts("8. Document 1 Returned to DS after Follow-up Review", expected_stage=WorkflowStageEnum.DS.value)

# 9. DOCUMENT 1: DS CLOSES DOCUMENT
document_service.close_document(1, remarks="Finalized and closed")
verify_document_counts("9. Document 1 Finalized and Closed", expected_stage=WorkflowStageEnum.CLOSED.value)

# 10. DOCUMENT 4: PRE-REVIEWED INTAKE & DIRECT ROUTE BYPASS
print("\n--- Testing Document 4 (Pre-Reviewed) Intake & Direct Route Bypass ---")
intake_page.load_document(repo.get_document(4))
intake_page.save_and_confirm_routing()
verify_document_counts("10. Document 4 Pre-Reviewed Direct Route Bypass to Rahul Sharma", expected_stage=WorkflowStageEnum.EMPLOYEE.value, doc_id=4)

# 11. DOCUMENT 5: URGENT / DEADLINE INTAKE & ROUTE TO IT HOD
print("\n--- Testing Document 5 Urgent / Deadline Intake & Route to IT HOD ---")
intake_page.load_document(repo.get_document(5))
intake_page.save_and_confirm_routing()
verify_document_counts("11. Document 5 Intake Registered & Sent to Director", expected_stage=WorkflowStageEnum.DIRECTOR.value, doc_id=5)

auth_service.login("director", "1234")
routing_service.save_director_remark(5, "Approved for urgent server patching. Assign to IT Cell.")
routing_service.return_to_ds(5, remarks="Returned to DS for IT execution")
auth_service.login("ds", "1234")
routing_service.route_to_hod(5, department_id=5, remarks="Route to IT HOD")
verify_document_counts("12. Document 5 Routed to IT HOD", expected_stage=WorkflowStageEnum.HOD.value, doc_id=5)

print("\n======================================================================")
print("ALL 11 WORKFLOW & DATA IDENTITY INVARIANT TESTS PASSED WITH ZERO DUPLICATES! (100%)")
print("======================================================================")
