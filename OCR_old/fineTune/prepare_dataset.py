"""
=============================================================================
CDTRS OCR fineTune — prepare_dataset.py
=============================================================================
Dataset preparation pipeline.

What it does:
  1. Discovers all images in dataset/images/
  2. Matches each image to a label in dataset/labels/
  3. Validates image readability and label content
  4. Reports missing images and missing labels
  5. Normalises label text (strip whitespace, NFC unicode)
  6. Builds or updates the character vocabulary
  7. Creates train / val / test split manifests in dataset/splits/
  8. Saves a dataset_manifest.json with statistics

Usage:
    python prepare_dataset.py [--enhance]

    --enhance   Apply handwriting preprocessing during validation (slower)

No internet connection required.
=============================================================================
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

# Ensure fineTune package root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as cfg
from utils.dataset import build_vocab, save_vocab, encode_label


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_image_readable(path: Path) -> bool:
    """Try loading the image with PIL; return False if it fails."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            im.verify()
        return True
    except Exception:
        return False


def _normalise_label(text: str) -> str:
    """Strip whitespace and apply NFC Unicode normalisation."""
    return unicodedata.normalize("NFC", text.strip())


def _split_list(items: list, train_r: float, val_r: float, seed: int):
    """Randomly split a list into (train, val, test) partitions."""
    rng = random.Random(seed)
    shuffled = items[:]
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = int(n * train_r)
    n_val   = int(n * val_r)
    return (
        shuffled[:n_train],
        shuffled[n_train:n_train + n_val],
        shuffled[n_train + n_val:],
    )


def _write_split(samples: list[tuple[str, str]], split_path: Path) -> None:
    """Write a split manifest file (TSV: image_path<TAB>label)."""
    split_path.parent.mkdir(parents=True, exist_ok=True)
    with open(split_path, "w", encoding="utf-8") as f:
        for img_path, label in samples:
            f.write(f"{img_path}\t{label}\n")


# ---------------------------------------------------------------------------
# Main preparation pipeline
# ---------------------------------------------------------------------------

def prepare_dataset(validate_images: bool = False, convert_pdfs: bool = True) -> None:
    print("\n" + "=" * 60)
    print("  CDTRS OCR fineTune -- Dataset Preparation")
    print("=" * 60)

    # Ensure directories exist
    cfg.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    cfg.LABELS_DIR.mkdir(parents=True, exist_ok=True)
    cfg.SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    cfg.PDFS_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 0. Auto-convert any PDFs in dataset/pdfs/ to images
    # ------------------------------------------------------------------
    if convert_pdfs:
        pdf_files = sorted(cfg.PDFS_DIR.glob("*.pdf")) + sorted(cfg.PDFS_DIR.glob("*.PDF"))
        if pdf_files:
            print(f"\n  Found {len(pdf_files)} PDF(s) in {cfg.PDFS_DIR}")
            print("  Auto-converting PDFs to images ...")
            from pdf_to_images import convert_all_pdfs
            summary = convert_all_pdfs(
                pdfs_dir=cfg.PDFS_DIR,
                images_dir=cfg.IMAGES_DIR,
                overwrite=False,
            )
            print(f"  PDF conversion done: {summary['images_created']} image(s) ready")
        else:
            pass  # No PDFs present — fine, images may already be there


    # ------------------------------------------------------------------
    # 1. Discover images
    # ------------------------------------------------------------------
    image_files = sorted(
        p for p in cfg.IMAGES_DIR.iterdir()
        if p.suffix.lower() in cfg.SUPPORTED_IMAGE_EXTS
    )

    if not image_files:
        print(
            "\n  [WARNING] No image files found in:\n"
            f"    {cfg.IMAGES_DIR}\n\n"
            "  Add your handwritten images (.png/.jpg/.jpeg/.bmp/.tiff) there,\n"
            "  and a matching .txt label file in:\n"
            f"    {cfg.LABELS_DIR}\n\n"
            "  Example:\n"
            "    dataset/images/page001.png\n"
            "    dataset/labels/page001.txt  (contains the handwritten text)\n"
        )
        sys.exit(0)

    print(f"\n  Found {len(image_files)} image(s) in {cfg.IMAGES_DIR}")

    # ------------------------------------------------------------------
    # 2. Match images → labels; validate
    # ------------------------------------------------------------------
    valid_samples:   list[tuple[str, str]] = []
    missing_labels:  list[str]             = []
    missing_images:  list[str]             = []
    invalid_images:  list[str]             = []
    invalid_labels:  list[str]             = []

    for img_path in image_files:
        stem       = img_path.stem
        label_path = cfg.LABELS_DIR / (stem + ".txt")

        # Check label exists
        if not label_path.exists():
            missing_labels.append(img_path.name)
            continue

        # Read and validate label
        label_text = label_path.read_text(encoding="utf-8")
        label_text = _normalise_label(label_text)

        if len(label_text) < cfg.MIN_LABEL_LENGTH:
            invalid_labels.append(img_path.name + " (label empty/too short)")
            continue

        if len(label_text) > cfg.MAX_LABEL_LENGTH:
            invalid_labels.append(img_path.name + f" (label length {len(label_text)} > {cfg.MAX_LABEL_LENGTH})")
            continue

        # Optionally validate image readability
        if validate_images:
            if not _is_image_readable(img_path):
                invalid_images.append(img_path.name)
                continue

        valid_samples.append((str(img_path), label_text))

    # Check for orphan labels (labels without images)
    label_stems = {p.stem for p in cfg.LABELS_DIR.glob("*.txt")}
    image_stems = {p.stem for p in image_files}
    for stem in sorted(label_stems - image_stems):
        missing_images.append(stem + ".txt")

    # ------------------------------------------------------------------
    # 3. Report
    # ------------------------------------------------------------------
    print(f"\n  Valid samples          : {len(valid_samples)}")
    print(f"  Missing labels         : {len(missing_labels)}")
    print(f"  Orphan labels (no img) : {len(missing_images)}")
    print(f"  Unreadable images      : {len(invalid_images)}")
    print(f"  Invalid labels         : {len(invalid_labels)}")

    if missing_labels:
        print("\n  [WARN] Images missing a label file:")
        for name in missing_labels[:10]:
            print(f"    - {name}")
        if len(missing_labels) > 10:
            print(f"    ... and {len(missing_labels) - 10} more")

    if invalid_labels:
        print("\n  [WARN] Skipped samples (invalid labels):")
        for name in invalid_labels[:10]:
            print(f"    - {name}")

    if not valid_samples:
        print(
            "\n  [ERROR] No valid samples after validation.\n"
            "  Please check that:\n"
            "    * Images exist in dataset/images/\n"
            "    * Each image has a matching .txt label in dataset/labels/\n"
            "    * Label files are not empty\n"
        )
        sys.exit(1)

    # ------------------------------------------------------------------
    # 4. Build / update vocabulary
    # ------------------------------------------------------------------
    all_labels = [label for _, label in valid_samples]
    vocab      = build_vocab(all_labels)
    vocab_path = cfg.SPLITS_DIR / cfg.VOCAB_FILENAME
    save_vocab(vocab, vocab_path)
    print(f"\n  Vocabulary size        : {len(vocab)} characters")
    print(f"  Vocabulary saved to    : {vocab_path}")

    # ------------------------------------------------------------------
    # 5. Create splits
    # ------------------------------------------------------------------
    train, val, test = _split_list(
        valid_samples,
        cfg.TRAIN_RATIO,
        cfg.VAL_RATIO,
        cfg.SPLIT_SEED,
    )

    _write_split(train, cfg.SPLITS_DIR / "train.txt")
    _write_split(val,   cfg.SPLITS_DIR / "val.txt")
    _write_split(test,  cfg.SPLITS_DIR / "test.txt")

    print(f"\n  Train split            : {len(train)} samples → {cfg.SPLITS_DIR / 'train.txt'}")
    print(f"  Val split              : {len(val)} samples   → {cfg.SPLITS_DIR / 'val.txt'}")
    print(f"  Test split             : {len(test)} samples  → {cfg.SPLITS_DIR / 'test.txt'}")

    # ------------------------------------------------------------------
    # 6. Save manifest
    # ------------------------------------------------------------------
    manifest = {
        "prepared_at":       datetime.now().isoformat(),
        "total_valid":       len(valid_samples),
        "train_samples":     len(train),
        "val_samples":       len(val),
        "test_samples":      len(test),
        "vocab_size":        len(vocab),
        "missing_labels":    missing_labels,
        "missing_images":    missing_images,
        "invalid_labels":    invalid_labels,
        "invalid_images":    invalid_images,
        "config": {
            "train_ratio":   cfg.TRAIN_RATIO,
            "val_ratio":     cfg.VAL_RATIO,
            "test_ratio":    cfg.TEST_RATIO,
            "split_seed":    cfg.SPLIT_SEED,
            "min_label_len": cfg.MIN_LABEL_LENGTH,
            "max_label_len": cfg.MAX_LABEL_LENGTH,
        },
    }
    manifest_path = cfg.DATASET_DIR / "dataset_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n  Manifest saved         : {manifest_path}")
    print("\n  Dataset preparation complete.")
    print("  Next step: python train.py")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Prepare handwritten OCR dataset for fine-tuning."
    )
    parser.add_argument(
        "--validate-images", action="store_true",
        help="Validate each image is readable (slower but thorough)"
    )
    parser.add_argument(
        "--no-convert-pdfs", action="store_true",
        help="Skip auto-conversion of PDFs in dataset/pdfs/ (default: convert automatically)"
    )
    args = parser.parse_args()
    prepare_dataset(
        validate_images=args.validate_images,
        convert_pdfs=not args.no_convert_pdfs,
    )

