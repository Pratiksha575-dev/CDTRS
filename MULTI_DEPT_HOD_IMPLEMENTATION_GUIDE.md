# CDTRS: Multi-Department HOD Support Implementation Guide (Option 1)

> **Purpose**: This document provides a complete, self-contained implementation plan and prompt. You can paste this entire prompt into Gemini or any AI coding assistant to implement multi-department management for HODs without breaking existing single-department setups.

---

## 📋 Prompt to Give to Gemini / AI Assistant

```markdown
# TASK: Implement Multi-Department HOD Support in CDTRS (Option 1: Junction Table)

You are working on the CDTRS (Centralised Document Tracking and Routing System) codebase.
Currently, a user with role `HOD` is linked to a single `department_id` on the `users` table.
We need to support scenarios where one HOD can manage multiple departments simultaneously (e.g. permanent HOD of Finance with additional charge of Technical) using an association/junction table approach.

Please implement the following changes step-by-step while maintaining backward compatibility with single-department users.

---

### Step 1: Backend Database Models (`backend/models.py`)

1. Add the `DepartmentHOD` model to `backend/models.py`:
```python
class DepartmentHOD(Base):
    __tablename__ = "department_hods"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    is_primary = Column(Boolean, default=False)
    assigned_at = Column(DateTime, default=datetime.now)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    department = relationship("Department", foreign_keys=[department_id])
```

2. Update the `User` model in `backend/models.py`:
   - Add relationship:
     ```python
     headed_departments = relationship("DepartmentHOD", foreign_keys=[DepartmentHOD.user_id], cascade="all, delete-orphan")
     ```
   - Add helper property:
     ```python
     @property
     def managed_department_ids(self) -> List[int]:
         ids = [dh.department_id for dh in self.headed_departments]
         if not ids and self.department_id:
             ids = [self.department_id]
         return ids
     ```

---

### Step 2: Backend Schemas (`backend/schemas.py`)

1. In `backend/schemas.py`, update `UserResponse`:
```python
class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: UserRole
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    managed_department_ids: List[int] = []
    managed_department_names: List[str] = []
    email: Optional[str] = None
    outlook_email: Optional[str] = None
    gov_email: Optional[str] = None
    
    class Config:
        from_attributes = True
```

---

### Step 3: Backend CRUD & Scoping (`backend/crud.py`)

1. Update `get_inbox(db, user)` for HOD role:
```python
elif user.role == UserRole.HOD:
    dept_ids = user.managed_department_ids
    if not dept_ids:
        return []
    
    return (
        db.query(models.Document)
        .filter(
            models.Document.target_department_id.in_(dept_ids),
            models.Document.current_stage.in_([WorkflowStage.HOD, WorkflowStage.EMPLOYEE, WorkflowStage.CLOSED])
        )
        .order_by(models.Document.created_at.desc())
        .all()
    )
```

2. Update `get_dashboard_stats(db, user)` for HOD role:
   - Calculate metrics (`total_documents`, `pending_action`) across all `user.managed_department_ids`.

3. Update `seed_data(db)` in `backend/crud.py`:
   - When seeding HOD users, check if they have multiple departments specified in `seed_data.json` and insert records into `DepartmentHOD`.

---

### Step 4: Seed Data JSON (`backend/data/seed_data.json`)

Allow HOD entries to specify either single or multiple departments:
```json
{
  "username": "hod_sharma",
  "role": "HOD",
  "full_name": "Dr. Sharma",
  "email": "sharma@cdtrs.gov.in",
  "departments": ["Finance", "Technical"],
  "designation": "Head of Finance & In-Charge (Technical)",
  "default_password": "cdtrs@hod"
}
```

---

### Step 5: Frontend HOD Inbox (`frontend/pages/hod_inbox.py`)

1. In `HODInboxPage.setup_ui()`:
   - If the logged-in HOD has multiple managed departments, add a **Department Filter Dropdown** right next to the category filter:
     `[All My Departments, Finance, Technical]`
2. In `HODInboxPage.apply_filter()`:
   - Filter rows where `doc.target_department_name == selected_department` (or show all if `"All My Departments"` is selected).

---

### Verification Checklist:
1. Run `python backend/seed.py --reset` to generate the new table and seed sample multi-dept HOD.
2. Login as the multi-dept HOD and verify:
   - Documents belonging to both departments appear in the HOD Inbox.
   - The department dropdown filters the inbox correctly.
   - Delegating staff assigns employees belonging to the specific document's target department.
```

---

## 🛠️ Summary of Files Modified When Running This Plan

| File | Changes Required |
|---|---|
| [`backend/models.py`](file:///c:/Users/Pratiksha/Downloads/CDTRS-main_final/CDTRS-main/CDTRS-main/backend/models.py) | Add `DepartmentHOD` model, link `headed_departments` and `managed_department_ids` to `User`. |
| [`backend/schemas.py`](file:///c:/Users/Pratiksha/Downloads/CDTRS-main_final/CDTRS-main/CDTRS-main/backend/schemas.py) | Add `managed_department_ids` & `managed_department_names` to `UserResponse`. |
| [`backend/crud.py`](file:///c:/Users/Pratiksha/Downloads/CDTRS-main_final/CDTRS-main/CDTRS-main/backend/crud.py) | Update `get_inbox` and `get_dashboard_stats` to query using `target_department_id.in_(dept_ids)`. |
| [`backend/data/seed_data.json`](file:///c:/Users/Pratiksha/Downloads/CDTRS-main_final/CDTRS-main/CDTRS-main/backend/data/seed_data.json) | Support list of departments for HOD accounts. |
| [`frontend/pages/hod_inbox.py`](file:///c:/Users/Pratiksha/Downloads/CDTRS-main_final/CDTRS-main/CDTRS-main/frontend/pages/hod_inbox.py) | Add department filter dropdown for HODs managing more than 1 department. |
