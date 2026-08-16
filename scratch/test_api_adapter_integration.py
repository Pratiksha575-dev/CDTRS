import os
import sys
import subprocess
import time
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

# Configure isolated environment for backend process
TEST_DB_PATH = os.path.join(ROOT_DIR, "scratch", "test_integration.db")
if os.path.exists(TEST_DB_PATH):
    try:
        os.remove(TEST_DB_PATH)
    except Exception:
        pass

backend_env = os.environ.copy()
backend_env["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
backend_env["UPLOAD_DIR"] = os.path.join(ROOT_DIR, "scratch", "test_uploads")
backend_env["SEED_DB"] = "true"

# Spawn backend server in subprocess
backend_dir = os.path.join(ROOT_DIR, "backend")
server_proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8899", "--log-level", "error"],
    cwd=backend_dir,
    env=backend_env
)

# Wait for backend server to boot up with healthcheck
import urllib.request
server_ready = False
for _ in range(30):
    try:
        with urllib.request.urlopen("http://127.0.0.1:8899/health", timeout=1.0) as resp:
            if resp.status == 200:
                server_ready = True
                break
    except Exception:
        time.sleep(0.3)

if not server_ready:
    print("Failed to connect to test backend server.")
    server_proc.terminate()
    sys.exit(1)

from config.settings import settings
settings.set_api_url("http://127.0.0.1:8899/api/v1")
settings.set_data_source("api")

from repositories.api_repository import APIRepository
from models import DocumentModel, UserModel
from models.enums import RouteTypeEnum, PriorityEnum
from api.client import api_client

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

results = []

def record_test(name, endpoint, method, req_shape, resp_shape, model_conversion, status_code, passed, error_msg=None):
    results.append({
        "name": name,
        "endpoint": endpoint,
        "method": method,
        "req_shape": req_shape,
        "resp_shape": resp_shape,
        "model_conversion": model_conversion,
        "status_code": status_code,
        "passed": passed,
        "error": error_msg
    })
    status_icon = "[PASS]" if passed else "[FAIL]"
    print(f"{status_icon:<7} | {name:<32} | {method} {endpoint:<40} | Status: {status_code}")
    if error_msg:
        print(f"        Error: {error_msg}")

print("=" * 90)
print("CDTRS API ADAPTER INTEGRATION TEST SUITE (22 OPERATIONS)")
print("=" * 90)

repo = APIRepository()

try:
    # 1. Login with DS
    try:
        user = repo.authenticate("ds_user", "cdtrs@ds")
        passed = user is not None and user.role == "Director Secretary" and user.username == "ds_user"
        record_test("1. Login DS", "/api/v1/auth/login", "POST", "{username, password}", "{access_token, user}", "UserModel (role: Director Secretary)", 200, passed)
    except Exception as e:
        record_test("1. Login DS", "/api/v1/auth/login", "POST", "{username, password}", "-", "-", 500, False, str(e))

    # 2. Login with Director
    try:
        user = repo.authenticate("director", "cdtrs@director")
        passed = user is not None and user.role == "Director" and user.username == "director"
        record_test("2. Login Director", "/api/v1/auth/login", "POST", "{username, password}", "{access_token, user}", "UserModel (role: Director)", 200, passed)
    except Exception as e:
        record_test("2. Login Director", "/api/v1/auth/login", "POST", "{username, password}", "-", "-", 500, False, str(e))

    # 3. Login with HOD (Finance)
    try:
        user = repo.authenticate("hod_finance", "cdtrs@hod")
        passed = user is not None and user.role == "HOD" and user.username == "hod_finance"
        record_test("3. Login HOD", "/api/v1/auth/login", "POST", "{username, password}", "{access_token, user}", "UserModel (role: HOD)", 200, passed)
    except Exception as e:
        record_test("3. Login HOD", "/api/v1/auth/login", "POST", "{username, password}", "-", "-", 500, False, str(e))

    # 4. Login with Employee (Rahul)
    try:
        user = repo.authenticate("emp_rahul", "cdtrs@emp")
        passed = user is not None and user.role == "Employee" and user.username == "emp_rahul"
        record_test("4. Login Employee", "/api/v1/auth/login", "POST", "{username, password}", "{access_token, user}", "UserModel (role: Employee)", 200, passed)
    except Exception as e:
        record_test("4. Login Employee", "/api/v1/auth/login", "POST", "{username, password}", "-", "-", 500, False, str(e))

    # 5. Wrong password (clean error, no traceback)
    try:
        wrong_user = repo.authenticate("ds_user", "wrong_password")
        passed = wrong_user is None
        record_test("5. Wrong Password", "/api/v1/auth/login", "POST", "{username, password}", "{detail: Invalid ...}", "Returns None cleanly (no traceback)", 401, passed)
    except Exception as e:
        record_test("5. Wrong Password", "/api/v1/auth/login", "POST", "{username, password}", "-", "-", 500, False, str(e))

    # Re-authenticate as DS for document creation & management
    repo.authenticate("ds_user", "cdtrs@ds")

    # 22. Manual document upload (Multipart)
    created_doc_id = None
    try:
        temp_file = os.path.join(ROOT_DIR, "scratch", "test_dispatch.pdf")
        os.makedirs(os.path.dirname(temp_file), exist_ok=True)
        with open(temp_file, "w") as f:
            f.write("%PDF-1.4 Mock PDF content for manual upload testing")

        doc_to_create = DocumentModel(
            title="Annual Budget Allocation Circular",
            date=datetime.now().strftime("%Y-%m-%d"),
            mode="Manual Upload",
            priority="High",
            source="Ministry of Finance",
            remarks="Urgent financial review and compliance requested."
        )
        new_doc = repo.create_document(doc_to_create, file_path=temp_file)
        created_doc_id = new_doc.id
        passed = new_doc is not None and new_doc.id is not None and new_doc.title == "Annual Budget Allocation Circular" and new_doc.status == "Received" and new_doc.priority == "High"
        record_test("22. Manual Document Upload", "/api/v1/intake/manual-upload", "POST", "Multipart (Form + File)", "DocumentResponse", "DocumentModel (doc_id->id, received_date->date)", 201, passed)
    except Exception as e:
        record_test("22. Manual Document Upload", "/api/v1/intake/manual-upload", "POST", "Multipart", "-", "-", 500, False, str(e))

    # 6. Get DS inbox
    try:
        inbox = repo.get_inbox()
        passed = isinstance(inbox, list) and len(inbox) >= 1
        record_test("6. Get DS Inbox", "/api/v1/documents/inbox", "GET", "-", "List[DocumentListResponse]", "List[DocumentModel]", 200, passed)
    except Exception as e:
        record_test("6. Get DS Inbox", "/api/v1/documents/inbox", "GET", "-", "-", "-", 500, False, str(e))

    # 10. Get document detail
    try:
        doc = repo.get_document(created_doc_id)
        passed = doc is not None and doc.id == created_doc_id and doc.title == "Annual Budget Allocation Circular"
        record_test("10. Get Document Detail", f"/api/v1/documents/{created_doc_id}", "GET", "-", "DocumentResponse", "DocumentModel (doc_id->id, title, date)", 200, passed)
    except Exception as e:
        record_test("10. Get Document Detail", f"/api/v1/documents/{created_doc_id}", "GET", "-", "-", "-", 500, False, str(e))

    # 11. Route DS -> Director
    try:
        routed_doc = repo.route_document(
            document_id=created_doc_id,
            route_type=RouteTypeEnum.DS_TO_DIRECTOR.value,
            to_user_id=2,  # Director user ID
            remarks="Submitting for Director executive review."
        )
        passed = routed_doc is not None and routed_doc.status == "Under Director Review" and routed_doc.current_stage == "DIRECTOR"
        record_test("11. Route DS -> Director", f"/api/v1/documents/{created_doc_id}/route", "POST", "{route_type: INITIAL_DIRECTOR_REVIEW, to_user_id}", "DocumentResponse", "DocumentModel (status: Under Director Review)", 200, passed)
    except Exception as e:
        record_test("11. Route DS -> Director", f"/api/v1/documents/{created_doc_id}/route", "POST", "-", "-", "-", 500, False, str(e))

    # 7. Get Director inbox
    try:
        repo.authenticate("director", "cdtrs@director")
        dir_inbox = repo.get_inbox()
        passed = isinstance(dir_inbox, list) and any(d.id == created_doc_id for d in dir_inbox)
        record_test("7. Get Director Inbox", "/api/v1/documents/inbox", "GET", "-", "List[DocumentListResponse]", "List[DocumentModel] (scoped to Director)", 200, passed)
    except Exception as e:
        record_test("7. Get Director Inbox", "/api/v1/documents/inbox", "GET", "-", "-", "-", 500, False, str(e))

    # 12. Save Director remark
    try:
        remark_doc = repo.save_director_remark(
            document_id=created_doc_id,
            remark="Approved in principle. Route to Finance Department for implementation."
        )
        passed = remark_doc is not None and "Approved in principle" in (remark_doc.director_remark or "")
        record_test("12. Save Director Remark", f"/api/v1/documents/{created_doc_id}/director-remark", "PUT", "{director_remark}", "DocumentResponse", "DocumentModel (director_remark updated)", 200, passed)
    except Exception as e:
        record_test("12. Save Director Remark", f"/api/v1/documents/{created_doc_id}/director-remark", "PUT", "-", "-", "-", 500, False, str(e))

    # 13. Return Director -> DS
    try:
        returned_doc = repo.return_to_ds(
            document_id=created_doc_id,
            remarks="Review completed with instructions."
        )
        passed = returned_doc is not None and returned_doc.status == "Director Review Completed" and returned_doc.current_stage == "DS"
        record_test("13. Return Director -> DS", f"/api/v1/documents/{created_doc_id}/return-to-ds", "POST", "{remarks}", "DocumentResponse", "DocumentModel (status: Director Review Completed)", 200, passed)
    except Exception as e:
        record_test("13. Return Director -> DS", f"/api/v1/documents/{created_doc_id}/return-to-ds", "POST", "-", "-", "-", 500, False, str(e))

    # 14. Route DS -> HOD (Finance)
    try:
        repo.authenticate("ds_user", "cdtrs@ds")
        hod_routed_doc = repo.route_document(
            document_id=created_doc_id,
            route_type=RouteTypeEnum.DS_TO_HOD.value,
            to_user_id=3,  # Finance HOD
            to_department_id=2, # Finance Department
            remarks="Routed to Finance HOD as per Director instruction."
        )
        passed = hod_routed_doc is not None and hod_routed_doc.status == "Under HOD Processing" and hod_routed_doc.current_stage == "HOD"
        record_test("14. Route DS -> HOD", f"/api/v1/documents/{created_doc_id}/route", "POST", "{route_type: POST_REVIEW_TO_HOD, to_department_id}", "DocumentResponse", "DocumentModel (status: Under HOD Processing)", 200, passed)
    except Exception as e:
        record_test("14. Route DS -> HOD", f"/api/v1/documents/{created_doc_id}/route", "POST", "-", "-", "-", 500, False, str(e))

    # 8. Get HOD inbox
    try:
        repo.authenticate("hod_finance", "cdtrs@hod")
        hod_inbox = repo.get_inbox()
        passed = isinstance(hod_inbox, list) and any(d.id == created_doc_id for d in hod_inbox)
        record_test("8. Get HOD Inbox", "/api/v1/documents/inbox", "GET", "-", "List[DocumentListResponse]", "List[DocumentModel] (scoped to Finance)", 200, passed)
    except Exception as e:
        record_test("8. Get HOD Inbox", "/api/v1/documents/inbox", "GET", "-", "-", "-", 500, False, str(e))

    # 15. Assign HOD -> Employee (Rahul)
    try:
        assignment = repo.assign_employee(
            document_id=created_doc_id,
            assigned_to_id=5,  # emp_rahul user_id
            instructions="Please prepare the budget utilization report."
        )
        passed = assignment is not None and assignment.assigned_to_id == 5 and assignment.instructions == "Please prepare the budget utilization report."
        record_test("15. Assign HOD -> Employee", f"/api/v1/documents/{created_doc_id}/assign", "POST", "{assigned_to_user_id, instructions}", "AssignmentResponse", "WorkAssignmentModel (assigned_to_user_id->assigned_to_id)", 201, passed)
    except Exception as e:
        record_test("15. Assign HOD -> Employee", f"/api/v1/documents/{created_doc_id}/assign", "POST", "-", "-", "-", 500, False, str(e))

    # 9. Get Employee tasks
    try:
        repo.authenticate("emp_rahul", "cdtrs@emp")
        emp_tasks = repo.get_inbox()
        passed = isinstance(emp_tasks, list) and any(d.id == created_doc_id for d in emp_tasks)
        record_test("9. Get Employee Tasks", "/api/v1/documents/inbox", "GET", "-", "List[DocumentListResponse]", "List[DocumentModel] (scoped to emp_rahul)", 200, passed)
    except Exception as e:
        record_test("9. Get Employee Tasks", "/api/v1/documents/inbox", "GET", "-", "-", "-", 500, False, str(e))

    # 16. Submit Employee progress
    progress_obj = None
    try:
        progress_obj = repo.submit_progress(
            document_id=created_doc_id,
            description="Budget figures verified and draft variance report completed."
        )
        passed = progress_obj is not None and progress_obj.id is not None and "draft variance report" in progress_obj.description
        record_test("16. Submit Progress", f"/api/v1/documents/{created_doc_id}/progress", "POST", "{description}", "ProgressResponse", "ProgressUpdateModel (submitted_by_user_id->user_id)", 201, passed)
    except Exception as e:
        record_test("16. Submit Progress", f"/api/v1/documents/{created_doc_id}/progress", "POST", "-", "-", "-", 500, False, str(e))

    # 17. Upload progress attachment
    try:
        att_file = os.path.join(ROOT_DIR, "scratch", "draft_variance_report.pdf")
        with open(att_file, "w") as f:
            f.write("%PDF-1.4 Draft Variance Report Test Content")

        att = repo.upload_attachment(
            document_id=created_doc_id,
            file_path=att_file,
            progress_update_id=progress_obj.id if progress_obj else None,
            category="WORKFLOW"
        )
        passed = att is not None and att.id is not None and att.category == "WORKFLOW" and att.file_name == "draft_variance_report.pdf"
        record_test("17. Upload Progress Attachment", f"/api/v1/documents/{created_doc_id}/attachments", "POST", "Multipart (file, attachment_type, progress_update_id)", "AttachmentResponse", "AttachmentModel (uploaded_by_user_id->uploaded_by)", 201, passed)
    except Exception as e:
        record_test("17. Upload Progress Attachment", f"/api/v1/documents/{created_doc_id}/attachments", "POST", "-", "-", "-", 500, False, str(e))

    # 18. Get workflow history
    try:
        history = repo.get_workflow_history(created_doc_id)
        passed = isinstance(history, list) and len(history) >= 3
        record_test("18. Get Workflow History", f"/api/v1/documents/{created_doc_id}/history", "GET", "-", "List[WorkflowHistoryResponse]", "List[WorkflowEventModel] (performed_by_user_id->performed_by)", 200, passed)
    except Exception as e:
        record_test("18. Get Workflow History", f"/api/v1/documents/{created_doc_id}/history", "GET", "-", "-", "-", 500, False, str(e))

    # 19. Notifications
    try:
        notifs = repo.get_notifications()
        passed = isinstance(notifs, list)
        record_test("19. Notifications", "/api/v1/notifications", "GET", "-", "List[NotificationResponse]", "List[NotificationModel]", 200, passed)
    except Exception as e:
        record_test("19. Notifications", "/api/v1/notifications", "GET", "-", "-", "-", 500, False, str(e))

    # 20. Reminders
    try:
        reminders = api_client.get("/reminders")
        passed = isinstance(reminders, list)
        record_test("20. Reminders", "/api/v1/reminders", "GET", "-", "List[ReminderResponse]", "Reminder list", 200, passed)
    except Exception as e:
        record_test("20. Reminders", "/api/v1/reminders", "GET", "-", "-", "-", 500, False, str(e))

    # 21. Dashboard
    try:
        dash = repo.get_dashboard_summary()
        passed = isinstance(dash, dict) and "total_documents" in dash and "role" in dash
        record_test("21. Dashboard", "/api/v1/dashboard", "GET", "-", "DashboardResponse", "Dict[str, Any] with role & metrics", 200, passed)
    except Exception as e:
        record_test("21. Dashboard", "/api/v1/dashboard", "GET", "-", "-", "-", 500, False, str(e))

finally:
    # Terminate backend subprocess
    server_proc.terminate()
    server_proc.wait(timeout=3)

print("=" * 90)
total_tests = len(results)
passed_tests = sum(1 for r in results if r["passed"])
failed_tests = total_tests - passed_tests
print(f"FINAL RESULT: {passed_tests}/{total_tests} OPERATIONS PASSED ({failed_tests} failed)")
print("=" * 90)

if failed_tests > 0:
    sys.exit(1)
else:
    sys.exit(0)
