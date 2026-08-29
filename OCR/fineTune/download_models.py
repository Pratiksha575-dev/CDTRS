"""
=============================================================================
CDTRS OCR fineTune — download_models.py
=============================================================================
ONE-TIME OFFLINE SETUP HELPER

This script downloads the PP-OCRv3 recognition model weights from
PaddleOCR's official CDN and saves them into:
    OCR/fineTune/models/original/

After running this once, NO INTERNET connection is ever needed again
for training, evaluation, or inference.

Usage:
    python download_models.py

What it downloads (~12 MB):
  • PP-OCRv3 text recognition model (en_PP-OCRv3_rec)
    Source: https://paddleocr.bj.bcebos.com/ (PaddlePaddle official CDN)

IMPORTANT:
  This is the ONLY script in the fineTune system that uses the internet.
  All other scripts (train.py, evaluate.py, inference.py) work offline.
=============================================================================
"""

from __future__ import annotations

import hashlib
import os
import sys
import tarfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg

# ---------------------------------------------------------------------------
# PP-OCRv3 English recognition model (inference weights, not training source)
# ---------------------------------------------------------------------------
MODELS_TO_DOWNLOAD = [
    {
        "name":     "PP-OCRv3 English Recognition",
        "url":      "https://paddleocr.bj.bcebos.com/PP-OCRv3/english/en_PP-OCRv3_rec_infer.tar",
        "filename": "en_PP-OCRv3_rec_infer.tar",
        "dest_dir": cfg.ORIGINAL_MODEL_DIR,
        "md5":      None,   # Set to the expected MD5 if you want strict verification
    }
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: Path) -> None:
    """Download *url* to *dest* with a simple progress indicator."""
    print(f"  Downloading {url}")
    print(f"  → {dest}")
    os.makedirs(dest.parent, exist_ok=True)

    def _reporthook(count, block_size, total_size):
        if total_size > 0:
            pct = min(100, int(count * block_size * 100 / total_size))
            mb  = count * block_size / 1_000_000
            print(f"\r  Progress: {pct}%  ({mb:.1f} MB downloaded)", end="", flush=True)

    urllib.request.urlretrieve(url, str(dest), reporthook=_reporthook)
    print()  # newline after progress


def _extract_tar(tar_path: Path, dest_dir: Path) -> None:
    """Extract a .tar file into *dest_dir*."""
    print(f"  Extracting {tar_path.name} ...")
    with tarfile.open(tar_path, "r") as tar:
        tar.extractall(str(dest_dir))
    print(f"  Extracted to {dest_dir}")


def _already_downloaded(dest_dir: Path) -> bool:
    """Check if model files already exist in dest_dir."""
    if not dest_dir.exists():
        return False
    files = list(dest_dir.iterdir())
    # Expect at least 2 files (model weights + config)
    return len(files) >= 2


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def download_models() -> None:
    print("\n" + "=" * 60)
    print("  CDTRS OCR fineTune — One-Time Model Download")
    print("=" * 60)
    print("  This script downloads PP-OCRv3 weights once.")
    print("  After this, no internet is required for training/inference.")
    print()

    all_ok = True
    for spec in MODELS_TO_DOWNLOAD:
        dest_dir: Path = spec["dest_dir"]
        tar_path: Path = dest_dir.parent / spec["filename"]

        # Already present?
        if _already_downloaded(dest_dir):
            print(f"  [OK] {spec['name']} already exists at:\n       {dest_dir}")
            continue

        try:
            # Download
            _download(spec["url"], tar_path)

            # Optional MD5 check
            if spec.get("md5"):
                actual = _md5(tar_path)
                if actual != spec["md5"]:
                    print(f"  [WARN] MD5 mismatch! Expected {spec['md5']}, got {actual}")

            # Extract
            dest_dir.mkdir(parents=True, exist_ok=True)
            _extract_tar(tar_path, dest_dir)

            # Clean up tar
            tar_path.unlink()
            print(f"  [OK] {spec['name']} saved to {dest_dir}\n")

        except Exception as e:
            print(f"  [ERROR] Failed to download {spec['name']}: {e}")
            all_ok = False

    if all_ok:
        print("  All models downloaded successfully!")
        print(f"  Original model location: {cfg.ORIGINAL_MODEL_DIR}")
        print("\n  You can now train offline:")
        print("    python prepare_dataset.py")
        print("    python train.py")
    else:
        print("\n  Some downloads failed. Check your internet connection and retry.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    download_models()
