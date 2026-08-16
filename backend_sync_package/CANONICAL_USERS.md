# Canonical Users Specification

This document defines the complete directory of canonical users in the CDTRS system.

---

## 1. Executive & Administrative Roles

| User ID | Username | Full Name | Role | Department ID | Department Name | Designation | Demo Password |
|:---:|:---|:---|:---|:---:|:---|:---|:---|
| **1** | `ds` *(alias: `master`)* | Director Secretary | `Director Secretary` | *None* | *Executive Office* | Secretary to Director | `1234` |
| **2** | `director` | Dr. Director | `Director` | *None* | *Directorate* | Director / Executive Head | `1234` |
| **8** | `admin` | System Admin | `Administrator` | *None* | *IT / Administration* | System Administrator | `1234` |
| **9** | `viewer` | Auditor Viewer | `Read-only User` | *None* | *Audit & Compliance* | External Auditor | `1234` |

---

## 2. Department Heads (HODs)

| User ID | Username | Full Name | Role | Department ID | Department Name | Designation | Demo Password |
|:---:|:---|:---|:---|:---:|:---|:---|:---|
| **3** | `hod_finance` *(alias: `hod`)* | Finance HOD | `HOD` | **1** | Finance | Head of Department (Finance) | `1234` |
| **4** | `hod_proc` | Procurement HOD | `HOD` | **2** | Procurement | Head of Department (Procurement) | `1234` |
| **5** | `hod_hr` | HR HOD | `HOD` | **3** | Human Resources | Head of Department (HR) | `1234` |
| **6** | `hod_maint` | Maintenance HOD | `HOD` | **4** | Maintenance | Head of Department (Maintenance) | `1234` |
| **7** | `hod_it` | IT HOD | `HOD` | **5** | IT | Head of Department (IT) | `1234` |

---

## 3. Department Employees

### Department 1: Finance (Dept ID: 1, Managed by HOD ID: 3)
| User / Employee ID | Username | Full Name | Role | Department ID | Designation | Demo Password |
|:---:|:---|:---|:---|:---:|:---|:---|
| **101** | `emp_rahul` *(alias: `employee`, `rahul`)* | Rahul Sharma | `Employee` | 1 | Senior Accounts Officer | `1234` |
| **102** | `emp_sneha` | Sneha Patil | `Employee` | 1 | Accounts Officer | `1234` |
| **103** | `emp_amit` | Amit Joshi | `Employee` | 1 | Financial Analyst | `1234` |
| **104** | `emp_neha` | Neha Kulkarni | `Employee` | 1 | Junior Accountant | `1234` |
| **105** | `emp_rohan` | Rohan Mehta | `Employee` | 1 | Audit Assistant | `1234` |

### Department 2: Procurement (Dept ID: 2, Managed by HOD ID: 4)
| User / Employee ID | Username | Full Name | Role | Department ID | Designation | Demo Password |
|:---:|:---|:---|:---|:---:|:---|:---|
| **201** | `emp_priya` *(alias: `priya`)* | Priya Verma | `Employee` | 2 | Procurement Specialist | `1234` |
| **202** | `emp_arjun` | Arjun Shah | `Employee` | 2 | Purchase Officer | `1234` |
| **203** | `emp_karan` | Karan Desai | `Employee` | 2 | Contracts Administrator | `1234` |
| **204** | `emp_pooja` | Pooja Nair | `Employee` | 2 | Vendor Coordinator | `1234` |
| **205** | `emp_vivek` | Vivek More | `Employee` | 2 | Inventory Assistant | `1234` |

### Department 3: Human Resources (Dept ID: 3, Managed by HOD ID: 5)
| User / Employee ID | Username | Full Name | Role | Department ID | Designation | Demo Password |
|:---:|:---|:---|:---|:---:|:---|:---|
| **301** | `emp_anjali` | Anjali Gupta | `Employee` | 3 | HR Executive | `1234` |
| **302** | `emp_rohit` | Rohit Singh | `Employee` | 3 | Recruitment Specialist | `1234` |
| **303** | `emp_meera` | Meera Joshi | `Employee` | 3 | Payroll Officer | `1234` |
| **304** | `emp_tanvi` | Tanvi Shah | `Employee` | 3 | Training Coordinator | `1234` |
| **305** | `emp_akash` | Akash Patil | `Employee` | 3 | HR Assistant | `1234` |

### Department 4: Maintenance (Dept ID: 4, Managed by HOD ID: 6)
| User / Employee ID | Username | Full Name | Role | Department ID | Designation | Demo Password |
|:---:|:---|:---|:---|:---:|:---|:---|
| **401** | `emp_suresh` | Suresh Pawar | `Employee` | 4 | Estate Officer | `1234` |
| **402** | `emp_kavita` | Kavita More | `Employee` | 4 | Facilities Supervisor | `1234` |
| **403** | `emp_nikhil` | Nikhil Patil | `Employee` | 4 | Electrical Engineer | `1234` |
| **404** | `emp_snehal` | Snehal Jadhav | `Employee` | 4 | Civil Supervisor | `1234` |
| **405** | `emp_omkar` | Omkar Shinde | `Employee` | 4 | Maintenance Technician | `1234` |

### Department 5: IT / Technical (Dept ID: 5, Managed by HOD ID: 7)
| User / Employee ID | Username | Full Name | Role | Department ID | Designation | Demo Password |
|:---:|:---|:---|:---|:---:|:---|:---|
| **501** | `emp_aditya` | Aditya Kulkarni | `Employee` | 5 | Systems Administrator | `1234` |
| **502** | `emp_riya` | Riya Shah | `Employee` | 5 | Network Engineer | `1234` |
| **503** | `emp_siddhant` | Siddhant Joshi | `Employee` | 5 | Database Administrator | `1234` |
| **504** | `emp_isha` | Isha Patil | `Employee` | 5 | Security Analyst | `1234` |
| **505** | `emp_yash` | Yash Deshmukh | `Employee` | 5 | IT Support Specialist | `1234` |

---

## 4. Authentication & Quick-Login Aliases

For seamless testing and backward compatibility with the frontend quick-login bar:
- `master` → logs in as User ID 1 (`ds`)
- `hod` → logs in as User ID 3 (`hod_finance`)
- `employee` or `rahul` → logs in as User ID 101 (`emp_rahul`)
- `priya` → logs in as User ID 201 (`emp_priya`)
- Passwords accepted for all accounts during demo: `1234`, `password`, `admin123`.
