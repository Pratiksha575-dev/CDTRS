import os
import shutil

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

os.makedirs(FRONTEND_DIR, exist_ok=True)

dirs_to_copy = ["api", "assets", "components", "config", "data", "models", "pages", "repositories", "services", "styles", "ui"]
files_to_copy = ["main.py", "requirements.txt"]

for d in dirs_to_copy:
    src = os.path.join(ROOT_DIR, d)
    dst = os.path.join(FRONTEND_DIR, d)
    if os.path.exists(src):
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print(f"Copied directory: {d} -> frontend/{d}")

for f in files_to_copy:
    src = os.path.join(ROOT_DIR, f)
    dst = os.path.join(FRONTEND_DIR, f)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"Copied file: {f} -> frontend/{f}")

print("Frontend folder population complete!")
