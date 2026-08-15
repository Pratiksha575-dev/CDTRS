import sys
import os

# Point to project root
sys.path.insert(0, r"c:\Users\Pratiksha\OneDrive\Desktop\CDTRS")

print("======================================================================")
print("TESTING PHASE 9G: SENDER ACTION REMINDER LOGIC & VIEWER GLITCH FIX")
print("======================================================================")

from PySide6.QtWidgets import QApplication, QMessageBox, QFrame
app = QApplication.instance() or QApplication(sys.argv)

# Mock QMessageBox dialogs for automated testing
QMessageBox.information = lambda *args, **kwargs: None
QMessageBox.warning = lambda *args, **kwargs: None
QMessageBox.critical = lambda *args, **kwargs: None

from repositories.provider import get_repository
from services.auth_service import auth_service
from services.document_service import document_service
from services.assignment_service import assignment_service
from services.routing_service import routing_service
from services.notification_service import notification_service
from services.event_bus import event_bus
from models.document import DocumentModel
from models.enums import RoleEnum, DocumentStatusEnum, WorkflowStageEnum
from components.document_viewer import DocumentViewer

# Setup active session as DS
auth_service.login("ds", "1234")

# ----------------------------------------------------------------------
# TEST 1: FINANCE + RAHUL ASSIGNED -> RAHUL RECEIVES REMINDER
# ----------------------------------------------------------------------
print("\n--- TEST 1: Finance + Rahul Assigned ---")
doc_601 = document_service.create_document(
    DocumentModel(
        id=601,
        reference_no="CDTRS-2026-601",
        title="Q4 Balance Sheet Audit",
        source="Finance Dept",
        target_department_name="Finance",
        target_department_id=1,
        assigned_employee_id=5,
        assigned_employee_name="Rahul Sharma",
        current_stage=WorkflowStageEnum.EMPLOYEE.value,
        status=DocumentStatusEnum.ASSIGNED_FOR_EXECUTION.value
    )
)
rec_1 = notification_service.resolve_reminder_recipient(doc_601)
assert rec_1 is not None, "Recipient must be resolved"
assert rec_1["user_id"] == 5, f"Expected Rahul Sharma (ID 5), got {rec_1['user_id']}"
assert rec_1["user_name"] == "Rahul Sharma"
assert rec_1["recipient_type"] == "EMPLOYEE"

disp_1 = notification_service.send_action_reminder(601)
assert disp_1["user_id"] == 5
print("[PASS] TEST 1: Finance document with Rahul assigned directs reminder exclusively to Rahul Sharma.")

# ----------------------------------------------------------------------
# TEST 2: FINANCE + NO EMPLOYEE -> FINANCE HOD RECEIVES REMINDER
# ----------------------------------------------------------------------
print("\n--- TEST 2: Finance + No Employee ---")
doc_602 = document_service.create_document(
    DocumentModel(
        id=602,
        reference_no="CDTRS-2026-602",
        title="Annual Budget Allocations",
        source="Ministry of Finance",
        target_department_name="Finance",
        target_department_id=1,
        assigned_employee_id=None,
        assigned_employee_name=None,
        current_stage=WorkflowStageEnum.HOD.value,
        status=DocumentStatusEnum.UNDER_HOD_PROCESSING.value
    )
)
rec_2 = notification_service.resolve_reminder_recipient(doc_602)
assert rec_2 is not None, "Finance HOD recipient must be resolved"
assert rec_2["user_id"] == 3, f"Expected Finance HOD (ID 3), got {rec_2['user_id']}"
assert rec_2["user_name"] == "Head of Finance"
assert rec_2["role"] == "HOD"

disp_2 = notification_service.send_action_reminder(602)
assert disp_2["user_id"] == 3
print("[PASS] TEST 2: Finance document with no employee assigned directs reminder to Finance HOD.")

# ----------------------------------------------------------------------
# TEST 3: PROCUREMENT + NO EMPLOYEE -> PROCUREMENT HOD RECEIVES REMINDER
# ----------------------------------------------------------------------
print("\n--- TEST 3: Procurement + No Employee ---")
doc_603 = document_service.create_document(
    DocumentModel(
        id=603,
        reference_no="CDTRS-2026-603",
        title="Server Racks Tender RFP",
        source="Vendor Portal",
        target_department_name="Procurement",
        target_department_id=2,
        assigned_employee_id=None,
        assigned_employee_name=None,
        current_stage=WorkflowStageEnum.HOD.value,
        status=DocumentStatusEnum.UNDER_HOD_PROCESSING.value
    )
)
rec_3 = notification_service.resolve_reminder_recipient(doc_603)
assert rec_3 is not None, "Procurement HOD recipient must be resolved"
assert rec_3["user_id"] == 9, f"Expected Procurement HOD (ID 9), got {rec_3['user_id']}"
assert rec_3["user_name"] == "Head of Procurement"
assert rec_3["role"] == "HOD"

disp_3 = notification_service.send_action_reminder(603)
assert disp_3["user_id"] == 9
print("[PASS] TEST 3: Procurement document with no employee assigned directs reminder to Procurement HOD.")

# ----------------------------------------------------------------------
# TEST 4: PROCUREMENT + PRIYA ASSIGNED -> PRIYA RECEIVES REMINDER (NOT HOD)
# ----------------------------------------------------------------------
print("\n--- TEST 4: Procurement + Priya Assigned ---")
doc_604 = document_service.create_document(
    DocumentModel(
        id=604,
        reference_no="CDTRS-2026-604",
        title="Office Furniture Bids",
        source="General Admin",
        target_department_name="Procurement",
        target_department_id=2,
        assigned_employee_id=8,
        assigned_employee_name="Priya Verma",
        current_stage=WorkflowStageEnum.EMPLOYEE.value,
        status=DocumentStatusEnum.ASSIGNED_FOR_EXECUTION.value
    )
)
rec_4 = notification_service.resolve_reminder_recipient(doc_604)
assert rec_4 is not None, "Priya recipient must be resolved"
assert rec_4["user_id"] == 8, f"Expected Priya Verma (ID 8), got {rec_4['user_id']}"
assert rec_4["user_name"] == "Priya Verma"
assert rec_4["role"] == "Employee"

disp_4 = notification_service.send_action_reminder(604)
assert disp_4["user_id"] == 8
print("[PASS] TEST 4: Procurement document with Priya assigned directs reminder to Priya Verma, NOT Procurement HOD.")

# ----------------------------------------------------------------------
# TEST 5: NO DEPARTMENT + NO EMPLOYEE -> NO DOWNSTREAM RECIPIENT
# ----------------------------------------------------------------------
print("\n--- TEST 5: No Department + No Employee ---")
doc_605 = document_service.create_document(
    DocumentModel(
        id=605,
        reference_no="CDTRS-2026-605",
        title="Unrouted General Grievance",
        source="Public Portal",
        target_department_name=None,
        target_department_id=None,
        assigned_employee_id=None,
        assigned_employee_name=None,
        current_stage=WorkflowStageEnum.DS.value,
        status=DocumentStatusEnum.RECEIVED.value
    )
)
rec_5 = notification_service.resolve_reminder_recipient(doc_605)
assert rec_5 is None, "Unrouted document must return None (no downstream recipient)"

disp_5 = notification_service.send_action_reminder(605)
assert disp_5 is None
print("[PASS] TEST 5: Unrouted document correctly resolved to None (no arbitrary recipient).")

# ----------------------------------------------------------------------
# TEST 6: CLOSED DOCUMENT -> NO REMINDER
# ----------------------------------------------------------------------
print("\n--- TEST 6: Closed Document ---")
doc_606 = document_service.create_document(
    DocumentModel(
        id=606,
        reference_no="CDTRS-2026-606",
        title="Completed Equipment Audit",
        source="Internal",
        target_department_name="Finance",
        target_department_id=1,
        assigned_employee_id=5,
        assigned_employee_name="Rahul Sharma",
        current_stage=WorkflowStageEnum.CLOSED.value,
        status=DocumentStatusEnum.CLOSED.value
    )
)
rec_6 = notification_service.resolve_reminder_recipient(doc_606)
assert rec_6 is None, "Closed document must return None (no reminders for finalized documents)"

disp_6 = notification_service.send_action_reminder(606)
assert disp_6 is None
print("[PASS] TEST 6: Closed document correctly yields no reminder.")

# ----------------------------------------------------------------------
# TEST 7: DYNAMIC TRANSITION: HOD -> ASSIGN RAHUL -> NEXT GOES TO RAHUL
# ----------------------------------------------------------------------
print("\n--- TEST 7: Dynamic Assignment Transition ---")
doc_607 = document_service.create_document(
    DocumentModel(
        id=607,
        reference_no="CDTRS-2026-607",
        title="Dynamic Workflow Document",
        source="External",
        target_department_name="Finance",
        target_department_id=1,
        assigned_employee_id=None,
        assigned_employee_name=None,
        current_stage=WorkflowStageEnum.HOD.value,
        status=DocumentStatusEnum.UNDER_HOD_PROCESSING.value
    )
)
# Step 1: No employee -> Finance HOD
first_rec = notification_service.resolve_reminder_recipient(doc_607)
assert first_rec["user_id"] == 3, f"Expected Finance HOD (3), got {first_rec['user_id']}"

# Step 2: HOD assigns Rahul Sharma
assignment_service.assign_employee(607, assigned_to_id=5, instructions="Audit immediately.")

# Step 3: Next reminder must dynamically go to Rahul Sharma
updated_doc_607 = document_service.get_document(607)
second_rec = notification_service.resolve_reminder_recipient(updated_doc_607)
assert second_rec["user_id"] == 5, f"Expected Rahul Sharma (5), got {second_rec['user_id']}"
assert second_rec["user_name"] == "Rahul Sharma"
print("[PASS] TEST 7: Reminder recipient dynamically transitions from HOD to assigned employee upon delegation.")

# ----------------------------------------------------------------------
# TEST 8: SEND ALL DUE FOLLOWS EXACT SAME RULES
# ----------------------------------------------------------------------
print("\n--- TEST 8: Send All Due Logic ---")
all_due = notification_service.send_all_due_reminders()
assert len(all_due) > 0, "Due documents must be processed"
for item in all_due:
    d = item["document"]
    r = item["recipient"]
    assert (d.status or "").lower() != "closed", "Closed document must never be included in send all due"
    if d.assigned_employee_id is not None:
        assert r["user_id"] == d.assigned_employee_id, "Assigned employee must be the recipient"
    elif d.target_department_name:
        assert r["role"] == "HOD", "Department without employee must direct reminder to HOD"
print("[PASS] TEST 8: Send All Due reminders strictly enforce the centralized recipient resolution rules.")

# ----------------------------------------------------------------------
# TEST 9: DOCUMENT VIEWER GLITCH FIX & CLEAN IN-PLACE RERENDERING
# ----------------------------------------------------------------------
print("\n--- TEST 9: Document Viewer Clean In-Place Re-render on Remark Save ---")
auth_service.login("director", "1234")
doc_608 = document_service.create_document(
    DocumentModel(
        id=608,
        reference_no="CDTRS-2026-608",
        title="GLITCH-TEST-DOC: Executive Directive Review",
        source="Strategic Office",
        format="PDF",
        current_stage=WorkflowStageEnum.DIRECTOR.value,
        status=DocumentStatusEnum.UNDER_DIRECTOR_REVIEW.value
    )
)

viewer = DocumentViewer(doc_608, role="Director")
app.processEvents()
initial_child_count = len(viewer.findChildren(QFrame))

# Director saves remark 1
new_dir_remark = "Reviewed and authorized. Route to Finance immediately."
routing_service.save_director_remark(608, remark=new_dir_remark)
app.processEvents()

# Viewer must update in place without crashing or multiplying widgets
assert viewer.document.director_remark == new_dir_remark
after_child_count = len(viewer.findChildren(QFrame))

# Director saves remark 2
routing_service.save_director_remark(608, remark="Updated directive: urgent action.")
app.processEvents()
after_child_count_2 = len(viewer.findChildren(QFrame))

# Verify widget count remains constant across repeated updates (zero stacking)
assert initial_child_count == after_child_count == after_child_count_2, f"Widget count must be constant: {initial_child_count}, {after_child_count}, {after_child_count_2}"
print(f"[PASS] TEST 9: DocumentViewer rendered cleanly in-place on remark save (frames constant: {initial_child_count} -> {after_child_count} -> {after_child_count_2}).")

# ----------------------------------------------------------------------
# TEST 10: DOCUMENT VIEWER SIZING & RESPONSIVENESS
# ----------------------------------------------------------------------
print("\n--- TEST 10: Document Viewer Layout Sizing ---")
viewer.resize(800, 600)
assert viewer.scroll_area.widgetResizable() is True
assert viewer.preview.preview_area.minimumHeight() <= 300
assert viewer.info.fields["Reference"].text() == "CDTRS-2026-608"

# Test maximized geometry
viewer.resize(1920, 1080)
assert viewer.width() == 1920
print("[PASS] TEST 10: DocumentViewer adapts cleanly across compact (800x600) and large (1920x1080) window sizes.")

print("\n======================================================================")
print("ALL 10 PHASE 9G TESTS PASSED 100%!")
print("======================================================================")
