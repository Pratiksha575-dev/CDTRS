"""
=============================================================================
CDTRS OCR fineTune -- pdf_to_images.py
=============================================================================
Converts handwritten PDF files into individual page images for OCR training.

Standalone usage:
    python pdf_to_images.py                  # convert all PDFs in dataset/pdfs/
    python pdf_to_images.py --dpi 200        # lower DPI (faster, smaller)
    python pdf_to_images.py --dpi 400        # higher DPI (better quality)
    python pdf_to_images.py --overwrite      # re-render already existing images

Workflow
--------
INPUT : dataset/pdfs/my_handwritten_notes.pdf   (you put it here)
OUTPUT: dataset/images/my_handwritten_notes_page1.png
        dataset/images/my_handwritten_notes_page2.png
        ...

Then create matching label files:
    dataset/labels/my_handwritten_notes_page1.txt
    dataset/labels/my_handwritten_notes_page2.txt

If only some pages are handwritten, only add labels for those pages.
Unlabelled images are automatically skipped by prepare_dataset.py.

No internet required -- uses PyMuPDF (fitz), already in requirements.txt.
=============================================================================
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg


def convert_pdf_to_images(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = cfg.PDF_RENDER_DPI,
    overwrite: bool = False,
) -> list[Path]:
    """
    Render every page of pdf_path to a PNG image in output_dir.
    Returns list of created/existing image paths.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError(
            "PyMuPDF is not installed. It is in requirements.txt.\n"
            "Install: pip install PyMuPDF==1.24.9"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    stem    = pdf_path.stem
    created: list[Path] = []
    doc     = fitz.open(str(pdf_path))
    n_pages = len(doc)

    for page_num, page in enumerate(doc, start=1):
        suffix   = f"_page{page_num}" if n_pages > 1 else ""
        out_name = f"{stem}{suffix}.png"
        out_path = output_dir / out_name

        if out_path.exists() and not overwrite:
            print(f"  [SKIP] Already exists: {out_name}")
            created.append(out_path)
            continue

        # Render at specified DPI (PyMuPDF default is 72 dpi)
        scale  = dpi / 72.0
        matrix = fitz.Matrix(scale, scale)
        pix    = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB)
        pix.save(str(out_path))
        print(f"  [OK] page {page_num}/{n_pages}: {out_name}  ({pix.width}x{pix.height} px)")
        created.append(out_path)

    doc.close()
    return created


def convert_all_pdfs(
    pdfs_dir: Path   = cfg.PDFS_DIR,
    images_dir: Path = cfg.IMAGES_DIR,
    dpi: int         = cfg.PDF_RENDER_DPI,
    overwrite: bool  = False,
) -> dict:
    """Convert all PDFs in pdfs_dir to PNG images in images_dir."""
    pdfs_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(pdfs_dir.glob("*.pdf")) + sorted(pdfs_dir.glob("*.PDF"))

    if not pdf_files:
        print(
            f"\n  [INFO] No PDF files found in: {pdfs_dir}\n\n"
            "  Steps to use PDFs as training data:\n"
            "    1. Copy handwritten PDFs to that folder.\n"
            "    2. Run: python pdf_to_images.py\n"
            "    3. For each generated image, create a label .txt file in dataset/labels/\n"
            "    4. Run: python prepare_dataset.py\n"
        )
        return {"pdfs_found": 0, "images_created": 0}

    total   = 0
    ok_pdfs = 0
    for pdf_path in pdf_files:
        print(f"\n  Converting: {pdf_path.name}")
        try:
            imgs    = convert_pdf_to_images(pdf_path, images_dir, dpi=dpi, overwrite=overwrite)
            total  += len(imgs)
            ok_pdfs += 1
        except Exception as e:
            print(f"  [ERROR] {pdf_path.name}: {e}")

    return {
        "pdfs_found":     len(pdf_files),
        "pdfs_converted": ok_pdfs,
        "images_created": total,
    }


def print_label_instructions(images_dir: Path, labels_dir: Path) -> None:
    """Print a reminder listing images that still need a label file."""
    label_stems = {p.stem for p in labels_dir.glob("*.txt")}
    unlabelled  = [p for p in sorted(images_dir.glob("*.png")) if p.stem not in label_stems]

    if not unlabelled:
        print("\n  All images already have matching label files.")
        return

    print(f"\n  {len(unlabelled)} image(s) still need a label file:")
    for p in unlabelled[:10]:
        print(f"    dataset/labels/{p.stem}.txt")
    if len(unlabelled) > 10:
        print(f"    ... and {len(unlabelled) - 10} more")
    print("\n  Each .txt file must contain the exact handwritten text shown in that image.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert handwritten PDFs to PNG images for OCR fine-tuning."
    )
    parser.add_argument(
        "--dpi", type=int, default=cfg.PDF_RENDER_DPI,
        help=f"Render DPI (default: {cfg.PDF_RENDER_DPI})"
    )
    parser.add_argument(
        "--overwrite", action="store_true",
        help="Re-render images that already exist"
    )
    parser.add_argument(
        "--pdfs-dir", type=Path, default=cfg.PDFS_DIR,
        help="Directory containing PDF files"
    )
    parser.add_argument(
        "--images-dir", type=Path, default=cfg.IMAGES_DIR,
        help="Output directory for PNG images"
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  CDTRS OCR fineTune -- PDF to Images Converter")
    print("=" * 60)
    print(f"  PDFs dir   : {args.pdfs_dir}")
    print(f"  Images dir : {args.images_dir}")
    print(f"  DPI        : {args.dpi}")

    s = convert_all_pdfs(
        pdfs_dir=args.pdfs_dir,
        images_dir=args.images_dir,
        dpi=args.dpi,
        overwrite=args.overwrite,
    )

    if s["pdfs_found"] > 0:
        print(f"\n  PDFs found    : {s['pdfs_found']}")
        print(f"  PDFs converted: {s.get('pdfs_converted', 0)}")
        print(f"  Images created: {s['images_created']}")
        print_label_instructions(args.images_dir, cfg.LABELS_DIR)
        print("\n  Next step: add label .txt files, then run:")
        print("    python prepare_dataset.py")

    print("=" * 60 + "\n")
