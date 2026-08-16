import os
import sys
from datetime import datetime, timedelta

# Point to project root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

print("======================================================================")
print("TESTING CANONICAL 5-DOCUMENT DATASET & FULL WORKFLOW LIFECYCLES")
print("======================================================================")

from PySide6.QtWidgets import QApplication, QMessageBox
app = QApplication.instance() or QApplication(sys.argv)

# Mock QMessageBox
QMessageBox.information = lambda *args, **kwargs: None
QMessageBox.warning = lambda *args, **kwargs: None
QMessageBox.critical = lambda *args, **kwargs: None

from config.settings import settings
settings.set_data_source("mock")

from repositories.provider import get_repository
from repositories.mock_repository import MockRepository
from services.auth_service import auth_service
from services.document_service import document_service
from services.assignment_service import assignment_service
from services.routing_service import routing_service
from services.notification_service import notification_service
from services.progress_service import progress_service
from services.workflow_service import workflow_service
from services.ocr_service import ocr_service
from models.enums import RoleEnum, DocumentStatusEnum, WorkflowStageEnum, PriorityEnum

# ----------------------------------------------------------------------
# 1. INITIAL STATE VERIFICATION
# ----------------------------------------------------------------------
print("\n--- 1. INITIAL STATE VERIFICATION ---")
repo = MockRepository()
# Override provider instance for testing
import repositories.provider as prov
prov._mock_repo_instance = repo

# Login as DS
auth_service.login("ds", "1234")
docs = repo.get_documents()
assert len(docs) == 5, f"Expected exactly 5 documents, found {len(docs)}"
print(f"[PASS] Total registered documents in MockRepository: {len(docs)}")

# Verify all 5 start in DS Inbox at stage=DS, status=Received, unassigned, unrouted
for doc in docs:
    assert doc.current_stage == WorkflowStageEnum.DS.value, f"Doc {doc.reference} stage expected DS, got {doc.current_stage}"
    assert doc.status == DocumentStatusEnum.RECEIVED.value, f"Doc {doc.reference} status expected Received, got {doc.status}"
    assert doc.current_owner_id == 1, f"Doc {doc.reference} owner_id expected 1, got {doc.current_owner_id}"
    assert doc.assigned_employee_id is None, f"Doc {doc.reference} assigned_employee_id must be None"
    assert doc.target_department_id is None, f"Doc {doc.reference} target_department_id must be None"
print("[PASS] All 5 documents initially start in DS Inbox at stage=DS, status=Received, unassigned, unrouted.")

# Verify specific metadata for each document
doc1 = repo.get_document(1)
assert doc1.title == "National Higher Education Accreditation & Governance Compliance Directive"
assert doc1.reference_no == "CDTRS-2026-0001"
assert doc1.priority == PriorityEnum.MEDIUM.value
assert doc1.suggested_department_name is None
assert doc1.suggested_employee_name is None
assert doc1.director_remark is None
assert doc1.deadline is None
print("[PASS] Document 1 metadata verified (Blank-slate fresh normal workflow).")

doc2 = repo.get_document(2)
assert doc2.title == "Q3 Financial Audit & Capital Grant Disbursement Notice"
assert doc2.reference_no == "CDTRS-2026-0002"
assert doc2.priority == PriorityEnum.HIGH.value
assert doc2.suggested_department_name == "Finance"
assert doc2.suggested_employee_name is None
assert doc2.director_remark is None
assert doc2.target_department_id is None, "Finance must ONLY be a suggested department at initial state"
print("[PASS] Document 2 metadata verified (Finance department suggestion).")

doc3 = repo.get_document(3)
assert doc3.title == "Statutory Vendor Tax Clearance & Procurement Verification"
assert doc3.reference_no == "CDTRS-2026-0003"
assert doc3.priority == PriorityEnum.HIGH.value
assert doc3.suggested_department_name == "Finance"
assert doc3.suggested_employee_name == "Rahul Sharma"
assert doc3.assigned_employee_id is None, "Rahul Sharma must ONLY be a suggested employee at initial state"
print("[PASS] Document 3 metadata verified (Finance + Rahul Sharma suggestion).")

doc4 = repo.get_document(4)
assert doc4.title == "Urgent Campus Security Infrastructure Upgrade Order (Pre-Reviewed)"
assert doc4.reference_no == "CDTRS-2026-0004"
assert doc4.priority == PriorityEnum.HIGH.value
assert doc4.suggested_department_name == "Finance"
assert doc4.suggested_employee_name == "Rahul Sharma"
assert doc4.director_remark == "Approved. Expedite procurement and assign to Rahul Sharma for immediate execution."
assert doc4.has_prior_director_remark is True
print("[PASS] Document 4 metadata verified (Pre-reviewed Director Remark present).")

doc5 = repo.get_document(5)
assert doc5.title == "High-Priority Enterprise Server Maintenance & Firewall Compliance"
assert doc5.reference_no == "CDTRS-2026-0005"
assert doc5.priority == PriorityEnum.HIGH.value
assert doc5.deadline is not None
assert doc5.suggested_department_name in ("Technical", "IT")
print(f"[PASS] Document 5 metadata verified (Urgent priority with 7-day deadline: {doc5.deadline}).")

# Verify each document has exactly 1 initial audit event
for doc_id in [1, 2, 3, 4, 5]:
    history = repo.get_workflow_history(doc_id)
    assert len(history) == 1, f"Expected 1 initial event for Doc {doc_id}, found {len(history)}"
    assert history[0].action == "Document Ingested"
print("[PASS] Clean initial audit history verified: exactly 1 'Document Ingested' event per document.")

# Verify role inboxes are initially empty
auth_service.login("director", "1234")
dir_docs = [d for d in repo.get_documents() if d.current_stage == WorkflowStageEnum.DIRECTOR.value]
assert len(dir_docs) == 0, f"Director Inbox must be initially empty, found {len(dir_docs)}"
dir_reviewed = [d for d in repo.get_documents() if d.director_remark is not None and d.current_stage != "DIRECTOR" and d.current_stage != "DS"]
print("[PASS] Director Inbox is initially empty (0 pending reviews).")

auth_service.login("hod_finance", "1234")
hod_docs = repo.get_documents()
assert len(hod_docs) == 0, f"HOD Inbox must be initially empty, found {len(hod_docs)}"
print("[PASS] HOD Inbox is initially empty (0 documents).")

auth_service.login("emp_rahul", "1234")
emp_docs = repo.get_documents()
assert len(emp_docs) == 0, f"Employee Tasks must be initially empty, found {len(emp_docs)}"
print("[PASS] Employee Tasks is initially empty (0 tasks).")


# ----------------------------------------------------------------------
# 2. DOCUMENT 1: COMPLETE NORMAL WORKFLOW DEMONSTRATION
# ----------------------------------------------------------------------
print("\n--- 2. DOCUMENT 1: NORMAL WORKFLOW EXECUTION ---")
auth_service.login("ds", "1234")

# Step 1: DS sends to Director
routing_service.route_to_director(1, remarks="Forwarded for Executive Review")
doc1 = repo.get_document(1)
assert doc1.current_stage == WorkflowStageEnum.DIRECTOR.value
assert doc1.status == DocumentStatusEnum.UNDER_DIRECTOR_REVIEW.value
print("  [OK] DS routed Document 1 to Director.")

# Step 2: Director reviews, adds remark, and returns to DS
auth_service.login("director", "1234")
routing_service.save_director_remark(1, "Accreditation review completed. Comply with statutory guidelines.")
routing_service.return_to_ds(1, remarks="Returned to DS after executive review")
doc1 = repo.get_document(1)
assert doc1.current_stage == WorkflowStageEnum.DS.value
assert doc1.status == DocumentStatusEnum.DIRECTOR_REVIEW_COMPLETED.value
assert doc1.director_remark == "Accreditation review completed. Comply with statutory guidelines."
print("  [OK] Director added remark and returned Document 1 to DS.")

# Step 3: DS routes to Procurement HOD
auth_service.login("ds", "1234")
routing_service.route_to_hod(1, department_id=2, remarks="Route to Procurement for statutory compliance")
doc1 = repo.get_document(1)
assert doc1.current_stage == WorkflowStageEnum.HOD.value
assert doc1.target_department_id == 2
assert doc1.target_department_name == "Procurement"
assert doc1.status == DocumentStatusEnum.UNDER_HOD_PROCESSING.value
print("  [OK] DS routed Document 1 to Procurement HOD.")

# Step 4: Procurement HOD assigns Priya Verma (emp_priya, ID 201)
auth_service.login("hod_proc", "1234")
assignment_service.assign_employee(1, assigned_to_id=201, instructions="Prepare accreditation compliance schedule")
doc1 = repo.get_document(1)
assert doc1.current_stage == WorkflowStageEnum.EMPLOYEE.value
assert doc1.assigned_employee_id == 201
assert doc1.assigned_employee_name == "Priya Verma"
assert doc1.status == DocumentStatusEnum.ASSIGNED_FOR_EXECUTION.value
print("  [OK] Procurement HOD assigned Document 1 to Priya Verma.")

# Step 5: Priya Verma submits execution progress
auth_service.login("emp_priya", "1234")
progress_service.submit_progress(1, description="Accreditation compliance audit completed and documented.")
doc1 = repo.get_document(1)
assert doc1.status == DocumentStatusEnum.PROGRESS_UPDATED.value
print("  [OK] Priya Verma submitted progress update.")

# Step 6: DS forwards follow-up to Director
auth_service.login("ds", "1234")
routing_service.forward_followup_to_director(1, remarks="Forwarding progress update for Director review")
doc1 = repo.get_document(1)
assert doc1.current_stage == WorkflowStageEnum.DIRECTOR.value
print("  [OK] DS forwarded follow-up to Director.")

# Step 7: Director returns to DS
auth_service.login("director", "1234")
routing_service.return_to_ds(1, remarks="Follow-up noted and endorsed.")
doc1 = repo.get_document(1)
assert doc1.current_stage == WorkflowStageEnum.DS.value
print("  [OK] Director reviewed follow-up and returned to DS.")

# Step 8: DS closes document
auth_service.login("ds", "1234")
document_service.close_document(1, remarks="Accreditation compliance verified and closed.")
doc1 = repo.get_document(1)
assert doc1.current_stage == WorkflowStageEnum.CLOSED.value
assert doc1.status == DocumentStatusEnum.CLOSED.value
print("  [OK] DS closed Document 1 successfully.")
print("[PASS] DOCUMENT 1: Complete 8-step normal workflow successfully executed.")


# ----------------------------------------------------------------------
# 3. DOCUMENT 2: DEPARTMENT SUGGESTION WORKFLOW
# ----------------------------------------------------------------------
print("\n--- 3. DOCUMENT 2: DEPARTMENT SUGGESTION WORKFLOW ---")
auth_service.login("ds", "1234")
doc2 = repo.get_document(2)
assert doc2.suggested_department_name == "Finance"

# DS chooses Route to Finance HOD
routing_service.route_to_hod(2, department_id=1, remarks="Routing to Finance based on suggestion")
doc2 = repo.get_document(2)
assert doc2.current_stage == WorkflowStageEnum.HOD.value
assert doc2.target_department_id == 1
assert doc2.target_department_name == "Finance"
assert doc2.status == DocumentStatusEnum.UNDER_HOD_PROCESSING.value
print("  [OK] DS routed Document 2 to Finance HOD based on suggestion.")

# Finance HOD assigns Rahul Sharma
auth_service.login("hod_finance", "1234")
assignment_service.assign_employee(2, assigned_to_id=101, instructions="Conduct reconciliation of Q3 capital grant")
doc2 = repo.get_document(2)
assert doc2.current_stage == WorkflowStageEnum.EMPLOYEE.value
assert doc2.assigned_employee_id == 101
assert doc2.assigned_employee_name == "Rahul Sharma"
print("  [OK] Finance HOD assigned Document 2 to Rahul Sharma.")
print("[PASS] DOCUMENT 2: Department suggestion workflow successfully executed.")


# ----------------------------------------------------------------------
# 4. DOCUMENT 3: DEPARTMENT + EMPLOYEE DIRECT ROUTING & REMINDER
# ----------------------------------------------------------------------
print("\n--- 4. DOCUMENT 3: DIRECT EMPLOYEE ROUTING & REMINDERS ---")
auth_service.login("ds", "1234")
doc3 = repo.get_document(3)
assert doc3.suggested_department_name == "Finance"
assert doc3.suggested_employee_name == "Rahul Sharma"

# DS routes directly to Rahul Sharma
routing_service.route_to_employee(3, employee_id=101, remarks="Direct routing to identified staff Rahul Sharma")
doc3 = repo.get_document(3)
assert doc3.current_stage == WorkflowStageEnum.EMPLOYEE.value
assert doc3.assigned_employee_id == 101
assert doc3.assigned_employee_name == "Rahul Sharma"
assert doc3.target_department_id == 1
assert doc3.target_department_name == "Finance"
assert doc3.status == DocumentStatusEnum.ASSIGNED_FOR_EXECUTION.value
print("  [OK] DS routed Document 3 directly to Rahul Sharma.")

# Rahul Sharma sees task
auth_service.login("emp_rahul", "1234")
rahul_tasks = repo.get_documents()
assert any(t.id == 3 for t in rahul_tasks), "Rahul must see Document 3 in tasks"
print("  [OK] Rahul Sharma sees task in My Tasks queue.")

# DS dispatches action reminder
auth_service.login("ds", "1234")
rec_3 = notification_service.resolve_reminder_recipient(3)
assert rec_3 is not None
assert rec_3["user_id"] == 101
assert rec_3["user_name"] == "Rahul Sharma"
assert rec_3["role"] == "Employee"

disp_3 = notification_service.send_action_reminder(3)
assert disp_3["user_id"] == 101
print("  [OK] DS dispatched action reminder directly to Rahul Sharma.")

# Rahul checks notifications
auth_service.login("emp_rahul", "1234")
notifs = notification_service.get_notifications(user_id=101)
assert len(notifs) > 0
assert any(n.document_id == 3 for n in notifs)
print("  [OK] Rahul Sharma received action reminder notification.")
print("[PASS] DOCUMENT 3: Direct employee routing & reminder workflow successfully executed.")


# ----------------------------------------------------------------------
# 5. DOCUMENT 4: PRE-REVIEWED DIRECTOR REMARK & DIRECT ROUTE BYPASS
# ----------------------------------------------------------------------
print("\n--- 5. DOCUMENT 4: PRE-REVIEWED DIRECTOR REMARK & BYPASS ---")
auth_service.login("ds", "1234")
doc4 = repo.get_document(4)
assert doc4.has_prior_director_remark is True
assert doc4.director_remark == "Approved. Expedite procurement and assign to Rahul Sharma for immediate execution."

# DS executes direct route bypass to Rahul Sharma
routing_service.route_to_employee(4, employee_id=101, remarks="Direct route to Rahul Sharma (Director review bypassed)")
doc4 = repo.get_document(4)
assert doc4.current_stage == WorkflowStageEnum.EMPLOYEE.value
assert doc4.assigned_employee_id == 101
assert doc4.assigned_employee_name == "Rahul Sharma"
assert doc4.target_department_name == "Finance"
assert doc4.director_remark == "Approved. Expedite procurement and assign to Rahul Sharma for immediate execution."
print("  [OK] DS bypassed Director review and routed directly to Rahul Sharma.")

# Verify Director sees Document 4 in Reviewed Documents archive
auth_service.login("director", "1234")
all_docs_dir = document_service.get_documents()
reviewed_archive = [d for d in all_docs_dir if d.director_remark is not None and d.current_stage != "DIRECTOR"]
assert any(d.id == 4 for d in reviewed_archive), "Document 4 must be visible in Director's Reviewed Documents archive"
print("  [OK] Document 4 is visible in Director's Reviewed Documents archive.")
print("[PASS] DOCUMENT 4: Pre-reviewed Director Remark bypass workflow successfully executed.")


# ----------------------------------------------------------------------
# 6. DOCUMENT 5: URGENT PRIORITY, DEADLINE TRACKING & TECHNICAL ROUTING
# ----------------------------------------------------------------------
print("\n--- 6. DOCUMENT 5: URGENT PRIORITY, DEADLINE & TECHNICAL ROUTING ---")
auth_service.login("ds", "1234")
doc5 = repo.get_document(5)
assert doc5.priority == PriorityEnum.HIGH.value
assert doc5.deadline is not None
print(f"  [OK] Document 5 has priority {doc5.priority} and deadline {doc5.deadline}.")

# Route to IT / Technical HOD
routing_service.route_to_hod(5, department_id=5, remarks="Urgent routing to IT Cell for firewall compliance")
doc5 = repo.get_document(5)
assert doc5.current_stage == WorkflowStageEnum.HOD.value
assert doc5.target_department_id == 5
assert doc5.target_department_name == "IT"
print("  [OK] DS routed Document 5 to IT / Technical HOD.")

# HOD Reminder resolution
rec_5 = notification_service.resolve_reminder_recipient(5)
assert rec_5 is not None
assert rec_5["role"] == "HOD"
assert rec_5["department_name"] == "IT"
disp_5 = notification_service.send_action_reminder(5)
assert disp_5["role"] == "HOD"
print(f"  [OK] Action reminder dispatched to IT HOD ({rec_5['user_name']}).")
print("[PASS] DOCUMENT 5: Urgent priority, deadline tracking & Technical routing successfully executed.")


# ----------------------------------------------------------------------
# 7. OCR SERVICE VERIFICATION ON CANONICAL DATASET
# ----------------------------------------------------------------------
print("\n--- 7. OCR SERVICE METADATA VERIFICATION ---")
ocr1 = ocr_service.process_incoming_document("", {"title": "National Higher Education Accreditation & Governance Compliance Directive", "source": "Ministry of Higher Education"})
assert ocr1["suggested_department"] == "Not Specified"
assert ocr1["has_prior_director_remark"] is False
print("  [OK] OCR Document 1: blank slate verified.")

ocr2 = ocr_service.process_incoming_document("", {"title": "Q3 Financial Audit & Capital Grant Disbursement Notice", "source": "State Audit Bureau"})
assert ocr2["suggested_department"] == "Finance"
assert ocr2["priority"] == "High"
print("  [OK] OCR Document 2: Finance suggestion verified.")

ocr3 = ocr_service.process_incoming_document("", {"title": "Statutory Vendor Tax Clearance & Procurement Verification", "source": "Central Board of Direct Taxes"})
assert ocr3["suggested_department"] == "Finance"
assert ocr3["suggested_employee"] == "Rahul Sharma"
print("  [OK] OCR Document 3: Finance + Rahul Sharma suggestion verified.")

ocr4 = ocr_service.process_incoming_document("", {"title": "Urgent Campus Security Infrastructure Upgrade Order (Pre-Reviewed)", "source": "Office of the Director"})
assert ocr4["has_prior_director_remark"] is True
assert "Approved" in ocr4["director_remark"]
assert ocr4["suggested_department"] == "Finance"
assert ocr4["suggested_employee"] == "Rahul Sharma"
print("  [OK] OCR Document 4: Pre-reviewed Director Remark detected verified.")

ocr5 = ocr_service.process_incoming_document("", {"title": "High-Priority Enterprise Server Maintenance & Firewall Compliance", "source": "Cyber Security Directorate"})
assert ocr5["suggested_department"] == "Technical"
assert ocr5["priority"] == "High"
assert ocr5["deadline"] != ""
print("  [OK] OCR Document 5: Technical + Urgent + Deadline verified.")
print("[PASS] OCR Service extracts and infers correct metadata for all 5 canonical documents.")

print("\n======================================================================")
print("ALL CANONICAL 5-DOCUMENT TESTS & WORKFLOWS PASSED SUCCESSFULLY! (100%)")
print("======================================================================")
