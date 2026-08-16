# Canonical Departments Specification

This document defines the exact organizational structure and department hierarchy in the CDTRS system.

---

## 1. Department Hierarchy & Headcount

| Dept ID | Department Name | Short Code | Designated HOD (User ID) | Employee Count | Employee ID Range | Primary Operational Function |
|:---:|:---|:---:|:---|:---:|:---:|:---|
| **1** | **Finance** | `FIN` | Finance HOD (ID: 3) | 5 | 101 – 105 | Budgeting, grants, disbursements, financial audits |
| **2** | **Procurement** | `PROC` | Procurement HOD (ID: 4) | 5 | 201 – 205 | Vendor management, purchases, tender compliance |
| **3** | **Human Resources** | `HR` | HR HOD (ID: 5) | 5 | 301 – 305 | Staffing, establishment, service rules, training |
| **4** | **Maintenance** | `MAINT` | Maintenance HOD (ID: 6) | 5 | 401 – 405 | Estate management, electrical/civil works, facilities |
| **5** | **IT** *(Technical)* | `IT` | IT HOD (ID: 7) | 5 | 501 – 505 | Infrastructure, servers, security, firewalls, software |

---

## 2. Detailed Roster per Department

### Department 1: Finance (`FIN`)
- **Department ID**: `1`
- **HOD**: `Finance HOD` (`hod_finance`, User ID: 3)
- **Employees**:
  1. `Rahul Sharma` (ID: 101, `emp_rahul`, Senior Accounts Officer)
  2. `Sneha Patil` (ID: 102, `emp_sneha`, Accounts Officer)
  3. `Amit Joshi` (ID: 103, `emp_amit`, Financial Analyst)
  4. `Neha Kulkarni` (ID: 104, `emp_neha`, Junior Accountant)
  5. `Rohan Mehta` (ID: 105, `emp_rohan`, Audit Assistant)

### Department 2: Procurement (`PROC`)
- **Department ID**: `2`
- **HOD**: `Procurement HOD` (`hod_proc`, User ID: 4)
- **Employees**:
  1. `Priya Verma` (ID: 201, `emp_priya`, Procurement Specialist)
  2. `Arjun Shah` (ID: 202, `emp_arjun`, Purchase Officer)
  3. `Karan Desai` (ID: 203, `emp_karan`, Contracts Administrator)
  4. `Pooja Nair` (ID: 204, `emp_pooja`, Vendor Coordinator)
  5. `Vivek More` (ID: 205, `emp_vivek`, Inventory Assistant)

### Department 3: Human Resources (`HR`)
- **Department ID**: `3`
- **HOD**: `HR HOD` (`hod_hr`, User ID: 5)
- **Employees**:
  1. `Anjali Gupta` (ID: 301, `emp_anjali`, HR Executive)
  2. `Rohit Singh` (ID: 302, `emp_rohit`, Recruitment Specialist)
  3. `Meera Joshi` (ID: 303, `emp_meera`, Payroll Officer)
  4. `Tanvi Shah` (ID: 304, `emp_tanvi`, Training Coordinator)
  5. `Akash Patil` (ID: 305, `emp_akash`, HR Assistant)

### Department 4: Maintenance (`MAINT`)
- **Department ID**: `4`
- **HOD**: `Maintenance HOD` (`hod_maint`, User ID: 6)
- **Employees**:
  1. `Suresh Pawar` (ID: 401, `emp_suresh`, Estate Officer)
  2. `Kavita More` (ID: 402, `emp_kavita`, Facilities Supervisor)
  3. `Nikhil Patil` (ID: 403, `emp_nikhil`, Electrical Engineer)
  4. `Snehal Jadhav` (ID: 404, `emp_snehal`, Civil Supervisor)
  5. `Omkar Shinde` (ID: 405, `emp_omkar`, Maintenance Technician)

### Department 5: IT (`IT`)
- **Department ID**: `5`
- **HOD**: `IT HOD` (`hod_it`, User ID: 7)
- **Employees**:
  1. `Aditya Kulkarni` (ID: 501, `emp_aditya`, Systems Administrator)
  2. `Riya Shah` (ID: 502, `emp_riya`, Network Engineer)
  3. `Siddhant Joshi` (ID: 503, `emp_siddhant`, Database Administrator)
  4. `Isha Patil` (ID: 504, `emp_isha`, Security Analyst)
  5. `Yash Deshmukh` (ID: 505, `emp_yash`, IT Support Specialist)

---

## 3. Department Aliases & Lookup Rules
- When the frontend searches or routes by department, the following aliases map to the same `department_id`:
  - `"Finance"` / `"FIN"` → Department ID `1`
  - `"Procurement"` / `"PROC"` → Department ID `2`
  - `"Human Resources"` / `"HR"` → Department ID `3`
  - `"Maintenance"` / `"MAINT"` → Department ID `4`
  - `"IT"` / `"Technical"` / `"IT Cell"` → Department ID `5`
