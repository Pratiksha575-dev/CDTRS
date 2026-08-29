import os
import sys

# Ensure backend folder is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import models
from database import engine, SessionLocal

def clear_all_documents():
    print("=" * 60)
    print("CDTRS Local Database: Clearing Documents for Clean Workflow Test")
    print("=" * 60)

    db = SessionLocal()
    try:
        # Delete all child records referencing documents
        db.query(models.Notification).delete()
        db.query(models.WorkflowHistory).delete()
        db.query(models.Reminder).delete()
        db.query(models.RoutingSuggestion).delete()
        db.query(models.DocumentExtractedField).delete()
        db.query(models.DocumentOCR).delete()
        db.query(models.ProgressUpdate).delete()
        db.query(models.DocumentRemark).delete()
        db.query(models.WorkAssignment).delete()
        db.query(models.DocumentRoute).delete()
        db.query(models.Attachment).delete()
        deleted_docs = db.query(models.Document).delete()

        db.commit()

        print(f"[OK] Successfully deleted all documents ({deleted_docs} removed).")
        print("[OK] All child tables (OCR, history, remarks, assignments, attachments, notifications) cleared.")
        print("[OK] All user accounts, departments, and employees preserved.")
        print("\nYour database is now completely clean and ready for manual intake & upload testing!")
        print("=" * 60)
    except Exception as e:
        db.rollback()
        print(f"Error clearing documents: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clear_all_documents()
