# ==============================================================================
# CDTRS V2 - Database Schema Migration Script
# Safely adds new tables and columns to existing PostgreSQL / SQLite database.
# ==============================================================================

import sys
from pathlib import Path
from sqlalchemy import text

# Ensure backend directory is in path
sys.path.insert(0, str(Path(__file__).parent))

from database import engine, Base
import models

def run_migration():
    print("==================================================")
    print("CDTRS V2 - Database Migration")
    print("==================================================")

    # 1. Create any missing tables (including document_assignments)
    print("\n[1/2] Creating new tables (Base.metadata.create_all)...")
    Base.metadata.create_all(bind=engine)
    print("  [OK] Tables created / verified.")

    # 2. Add columns to existing tables if they don't exist yet
    print("\n[2/2] Verifying columns on existing tables...")
    with engine.connect() as conn:
        dialect = engine.dialect.name
        
        # PostgreSQL vs SQLite ALTER TABLE
        if dialect == "postgresql":
            statements = [
                "ALTER TABLE work_assignments ADD COLUMN IF NOT EXISTS requires_hod_validation BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE progress_updates ADD COLUMN IF NOT EXISTS hod_validation_required BOOLEAN DEFAULT FALSE;",
                "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'prog_val_status_enum') THEN CREATE TYPE prog_val_status_enum AS ENUM ('DIRECT_TO_DS', 'PENDING_HOD_REVIEW', 'HOD_APPROVED', 'RETURNED_TO_EMPLOYEE'); END IF; END $$;",
                "ALTER TABLE progress_updates ADD COLUMN IF NOT EXISTS hod_validation_status VARCHAR(50) DEFAULT 'DIRECT_TO_DS';",
                "ALTER TABLE progress_updates ADD COLUMN IF NOT EXISTS hod_review_note TEXT;",
                "ALTER TABLE progress_updates ADD COLUMN IF NOT EXISTS hod_reviewed_by_user_id INTEGER REFERENCES users(id);",
                "ALTER TABLE progress_updates ADD COLUMN IF NOT EXISTS hod_reviewed_at TIMESTAMP;",
            ]
            for stmt in statements:
                try:
                    conn.execute(text(stmt))
                    conn.commit()
                except Exception as ex:
                    print(f"  Note: {ex}")
        else: # SQLite or other
            sqlite_cols = [
                ("work_assignments", "requires_hod_validation", "BOOLEAN DEFAULT 0"),
                ("progress_updates", "hod_validation_required", "BOOLEAN DEFAULT 0"),
                ("progress_updates", "hod_validation_status", "VARCHAR(50) DEFAULT 'DIRECT_TO_DS'"),
                ("progress_updates", "hod_review_note", "TEXT"),
                ("progress_updates", "hod_reviewed_by_user_id", "INTEGER"),
                ("progress_updates", "hod_reviewed_at", "DATETIME"),
            ]
            for tbl, col, col_type in sqlite_cols:
                try:
                    conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_type};"))
                    conn.commit()
                    print(f"  [OK] Added column {col} to {tbl}")
                except Exception:
                    # Column likely already exists
                    pass

    print("\n[OK] Migration completed successfully!")
    print("==================================================")

if __name__ == "__main__":
    run_migration()
