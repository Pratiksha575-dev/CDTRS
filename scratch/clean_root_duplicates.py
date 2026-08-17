import os
import shutil
import stat

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def remove_readonly(func, path, excinfo):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

dirs_to_delete = [
    "api",
    "assets",
    "components",
    "config",
    "data",
    "models",
    "pages",
    "repositories",
    "services",
    "styles",
    "ui"
]

for d in dirs_to_delete:
    target = os.path.join(ROOT_DIR, d)
    if os.path.exists(target) and os.path.isdir(target):
        try:
            shutil.rmtree(target, onerror=remove_readonly)
            print(f"[DELETED] Root directory: {d}")
        except Exception as e:
            print(f"[ERROR] Failed to delete {d}: {e}")

print("Root cleanup complete!")
