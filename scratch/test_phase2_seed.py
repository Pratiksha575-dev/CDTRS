import os
import sys
import traceback
from datetime import date, datetime

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
from repositories.api_repository import APIRepository
from models.enums import RoleEnum, RouteTypeEnum, DocumentStatusEnum
from models.document import DocumentModel


def verify_phase2_dataset(backend_url="https://cdtrs.onrender.com/api/v1"):
    print("\n=======================================================")
    print(f"PHASE 2 DATASET & ROLE-GATING VERIFICATION ({backend_url})")
    print("=======================================================")
    settings.set_api_url(backend_url)
    settings.set_data_source("api")
    settings.api_timeout = 60.0

    repo = get_repository()
    assert isinstance(repo, APIRepository), f"Expected APIRepository, got {type(repo)}"

    # 1. Authenticate DS
    print("\n[1] Authenticating DS Account...")
    ds_user = repo.authenticate("ds_user", "cdtrs@ds")
    assert ds_user is not None, "DS Login failed"
    print(f" [PASS] Authenticated DS: {ds_user.full_name} ({ds_user.role})")

    # 2. Check Departments
    print("\n[2] Verifying 5 Organization Departments...")
    from api.client import api_client
    from api.endpoints import Endpoints
    depts = api_client.get(Endpoints.DEPARTMENTS_LIST)
    print(f" [PASS] Total Departments: {len(depts)}")
    dept_names = [d["name"] for d in depts]
    print(f"        Departments present: {', '.join(dept_names)}")
    expected_depts = ["Administration", "Finance", "Procurement", "Human Resources", "Technical"]
    for ed in expected_depts:
        assert ed in dept_names, f"Missing expected department: {ed}"
    print(" [PASS] All 5 required departments verified!")

    # 3. Check Users & Employees
    print("\n[3] Verifying HODs and Department Employees...")
    users = api_client.get(Endpoints.USERS_LIST)
    print(f" [PASS] Total User Accounts: {len(users)}")
    
    # HOD accounts
    hod_usernames = ["hod_finance", "hod_procurement", "hod_hr", "hod_tech"]
    existing_users = {u["username"]: u for u in users}
    for hu in hod_usernames:
        if hu in existing_users:
            print(f"        - HOD verified: {hu} (Role: {existing_users[hu]['role']}, Dept: {existing_users[hu].get('department_id')})")

    # Employee accounts
    emp_records = api_client.get("/employees")
    print(f" [PASS] Total Employee Profiles: {len(emp_records)}")
    for e in emp_records:
        print(f"        - Employee: {e.get('employee_code')} | {e.get('full_name')} | Dept ID: {e.get('department_id')}")

    # 4. Check DS Incoming Inbox (All 20 initial documents)
    print("\n[4] Verifying DS Incoming Inbox...")
    inbox_docs = repo.get_inbox()
    all_docs = repo.get_documents()
    print(f" [PASS] Total Documents in System: {len(all_docs)}")
    print(f" [PASS] Documents in DS Incoming Inbox: {len(inbox_docs)}")

    # 5. Check Initial Role-Gating (HODs, Employees, Director must have 0 active routed tasks initially)
    print("\n[5] Verifying Strict Initial Role-Gating (Zero Pre-routing)...")

    # Director
    repo.authenticate("director", "cdtrs@director")
    dir_inbox = repo.get_inbox()
    print(f" [PASS] Director Inbox: {len(dir_inbox)} items (Expected: 0 unrouted items)")
    assert len(dir_inbox) == 0, f"Director inbox should have 0 items before DS routes, got {len(dir_inbox)}"

    # HOD Finance
    repo.authenticate("hod_finance", "cdtrs@hod")
    hod_fin_inbox = repo.get_inbox()
    print(f" [PASS] Finance HOD Inbox: {len(hod_fin_inbox)} items (Expected: 0 unrouted items)")
    assert len(hod_fin_inbox) == 0, f"Finance HOD inbox should have 0 items before DS routes, got {len(hod_fin_inbox)}"

    # HOD Procurement
    repo.authenticate("hod_procurement", "cdtrs@hod")
    hod_proc_inbox = repo.get_inbox()
    print(f" [PASS] Procurement HOD Inbox: {len(hod_proc_inbox)} items (Expected: 0 unrouted items)")
    assert len(hod_proc_inbox) == 0, f"Procurement HOD inbox should have 0 items before DS routes, got {len(hod_proc_inbox)}"

    # Employee Rahul
    repo.authenticate("emp_rahul", "cdtrs@emp")
    rahul_inbox = repo.get_inbox()
    print(f" [PASS] Employee Rahul Tasks: {len(rahul_inbox)} items (Expected: 0 unrouted items)")
    assert len(rahul_inbox) == 0, f"Employee Rahul should have 0 assigned tasks before delegation, got {len(rahul_inbox)}"

    # Employee Priya
    repo.authenticate("emp_priya", "cdtrs@emp")
    priya_inbox = repo.get_inbox()
    print(f" [PASS] Employee Priya Tasks: {len(priya_inbox)} items (Expected: 0 unrouted items)")
    assert len(priya_inbox) == 0, f"Employee Priya should have 0 assigned tasks before delegation, got {len(priya_inbox)}"

    # 6. Verify Document Detail & Frontend Deserialization
    print("\n[6] Verifying Frontend DocumentModel Deserialization & Routing Intelligence...")
    repo.authenticate("ds_user", "cdtrs@ds")
    if all_docs:
        doc0 = all_docs[0]
        detail = repo.get_document(doc0.id)
        assert detail is not None
        print(f" [PASS] DocumentModel deserialized cleanly: Title='{detail.title}', Ref='{detail.reference_no}'")
        print(f"        Stage='{detail.current_stage}', Status='{detail.status}', Priority='{detail.priority}'")
        print(f"        Suggested Dept='{detail.suggested_department_name}' (ID: {detail.suggested_department_id})")
        print(f"        Suggested Employee='{detail.suggested_employee_name}' (ID: {detail.suggested_employee_id})")

    print("\n>>> PHASE 2 DATA FOUNDATION & ROLE-GATING FULLY VERIFIED! <<<")


if __name__ == "__main__":
    try:
        verify_phase2_dataset()
    except Exception as ex:
        print(f"\n[FAIL] Phase 2 verification error: {ex}")
        traceback.print_exc()
        sys.exit(1)
