import os
import sys

# Ensure backend folder is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import models
import crud
from database import engine, SessionLocal

def main():
    print("=" * 60)
    print("CDTRS Local Database Seeding & User Setup")
    print("=" * 60)

    # 1. Ensure all tables exist in database
    print("\n1. Creating database tables...")
    models.Base.metadata.create_all(bind=engine)
    print("[OK] All database tables created.")

    # 2. Seed departments, employees, and test user accounts
    print("\n2. Seeding initial test data...")
    db = SessionLocal()
    try:
        crud.seed_data(db)
        print("[OK] Seed data inserted / verified successfully.")

        # 3. Print list of available accounts
        users = crud.get_users(db)
        print("\n" + "=" * 60)
        print("AVAILABLE LOCAL TEST ACCOUNTS (API MODE)")
        print("=" * 60)
        print(f"{'Username':<18} | {'Role':<18} | {'Default Password'}")
        print("-" * 60)
        
        passwords = {
            "ds_user": "cdtrs@ds",
            "director": "cdtrs@director",
            "hod_finance": "cdtrs@hod",
            "hod_procurement": "cdtrs@hod",
            "emp_rahul": "cdtrs@emp",
            "emp_priya": "cdtrs@emp"
        }
        for u in users:
            pwd = passwords.get(u.username, "cdtrs@emp")
            role_val = u.role.value if hasattr(u.role, "value") else str(u.role)
            print(f"{u.username:<18} | {role_val:<18} | {pwd}")
        print("=" * 60)
    except Exception as e:
        print(f"[ERROR] Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
