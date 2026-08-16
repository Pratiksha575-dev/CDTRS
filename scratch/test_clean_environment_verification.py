import os
import sys

# Ensure project root is the only path in sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

print("=" * 70)
print(f"CLEAN VIRTUAL ENVIRONMENT VERIFICATION")
print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version}")
print("=" * 70)

# Verify we are running inside _temp_test_venv
assert "_temp_test_venv" in sys.executable, "Must run strictly inside _temp_test_venv!"

# 1. VERIFY ALL RUNTIME IMPORTS
print("\n[1/7] Testing Third-Party Runtime Imports...")
import PySide6
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QApplication, QWidget, QMainWindow, QFrame, QLabel, QPushButton
import requests
import pip_system_certs
import dotenv
import fastapi
import uvicorn
import pydantic
import sqlalchemy
import jose
import passlib
import bcrypt
import multipart
print("  [OK] PySide6 (GUI framework) loaded successfully.")
print("  [OK] requests & pip_system_certs (Networking & SSL) loaded successfully.")
print("  [OK] fastapi, uvicorn, pydantic, sqlalchemy, jose, bcrypt (Backend stack) loaded successfully.")

# 2. VERIFY SETTINGS & CONFIGURATION RESOLUTION
print("\n[2/7] Testing Configuration Resolution in config/settings.py...")
from config.settings import settings
print(f"  [OK] settings.api_url = {settings.api_url}")
print(f"  [OK] settings.data_source = {settings.data_source}")
assert settings.api_url == "https://cdtrs.onrender.com/api/v1", "API URL must resolve to Render backend"
print("  [OK] Render Backend URL verification passed: https://cdtrs.onrender.com/api/v1")

# 3. VERIFY MOCK REPOSITORY 5 CANONICAL DOCUMENTS
print("\n[3/7] Testing MockRepository & Canonical Demonstration Dataset...")
from repositories.mock_repository import MockRepository
mock_repo = MockRepository()
docs = mock_repo.get_documents()
assert len(docs) == 5, f"MockRepository must contain exactly 5 canonical documents! Found: {len(docs)}"
for d in docs:
    assert d.current_stage == "DS", f"Doc #{d.id} must be in DS stage initially"
    assert d.status == "Received", f"Doc #{d.id} must have status Received initially"
print(f"  [OK] MockRepository initialized with exactly 5 canonical documents all in DS Inbox.")

# 4. VERIFY REPOSITORY PROVIDER RESOLUTION
print("\n[4/7] Testing Repository Provider Resolution (Mock & API modes)...")
from repositories.provider import get_repository
from repositories.api_repository import APIRepository

settings.set_data_source("mock")
repo_mock = get_repository()
assert isinstance(repo_mock, MockRepository), "get_repository() must return MockRepository in mock mode"

settings.set_data_source("api")
repo_api = get_repository()
assert isinstance(repo_api, APIRepository), "get_repository() must return APIRepository in api mode"
print("  [OK] Repository Provider seamlessly switches between MockRepository and APIRepository.")

# Reset to mock for UI initialization tests
settings.set_data_source("mock")

# 5. VERIFY UI WINDOW INITIALIZATION (LoginWindow & MainWindow)
print("\n[5/7] Testing UI Initialization (LoginWindow, MainWindow, Sidebar, DocumentViewer)...")
app = QApplication.instance() or QApplication(sys.argv)

with open(os.path.join(ROOT_DIR, "styles", "theme.qss"), "r", encoding="utf-8") as f:
    app.setStyleSheet(f.read())

from ui.login import LoginWindow
from ui.main_window import MainWindow
from ui.sidebar import Sidebar
from components.document_viewer import DocumentViewer

login_win = LoginWindow()
assert login_win is not None
print("  [OK] LoginWindow created and themed successfully.")

main_win_ds = MainWindow(username="ds_user", role="Director Secretary")
assert main_win_ds is not None
assert main_win_ds.dashboard_page is not None
assert main_win_ds.inbox_page is not None
assert main_win_ds.documents_page is not None
assert main_win_ds.history_page is not None
print("  [OK] MainWindow for Director Secretary initialized successfully.")

main_win_dir = MainWindow(username="director", role="Director")
assert main_win_dir is not None
assert main_win_dir.director_inbox_page is not None
assert main_win_dir.director_reviewed_page is not None
print("  [OK] MainWindow for Director initialized successfully.")

main_win_hod = MainWindow(username="hod_finance", role="HOD")
assert main_win_hod is not None
assert main_win_hod.hod_inbox_page is not None
print("  [OK] MainWindow for HOD initialized successfully.")

main_win_emp = MainWindow(username="emp_rahul", role="Employee")
assert main_win_emp is not None
assert main_win_emp.employee_tasks_page is not None
print("  [OK] MainWindow for Employee initialized successfully.")

# 6. VERIFY MAIN.PY ENTRY POINT INTEGRITY
print("\n[6/7] Testing main.py Entry Point Syntax & Structure...")
with open(os.path.join(ROOT_DIR, "main.py"), "r", encoding="utf-8") as f:
    main_code = f.read()
import ast
ast.parse(main_code, filename="main.py")
print("  [OK] main.py parsed and verified as valid application entry point.")

# 7. CLEAN UP UI OBJECTS
login_win.deleteLater()
main_win_ds.deleteLater()
main_win_dir.deleteLater()
main_win_hod.deleteLater()
main_win_emp.deleteLater()

print("\n" + "=" * 70)
print("ALL CLEAN VIRTUAL ENVIRONMENT VERIFICATIONS PASSED SUCCESSFULLY! (100%)")
print("=" * 70)
