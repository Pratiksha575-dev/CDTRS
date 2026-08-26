"""
=============================================================================
CDTRS OCR — Command-Line Runner / Demo  (main.py)
=============================================================================
Standalone CLI to test the OCR engine against any file or folder.

Usage examples:
  python main.py --file path/to/document.pdf
  python main.py --file path/to/scan.jpg --handwriting
  python main.py --folder path/to/docs/
  python main.py --file doc.pdf --save               # saves JSON to output/
  python main.py --file doc.pdf --quiet              # suppress banner
  python main.py --file doc.pdf --gpu                # enable GPU
=============================================================================
"""

import argparse
import json
import os
import sys
import textwrap
from pathlib import Path

# ---- Make sure the OCR folder is on the path when run directly ----------
sys.path.insert(0, str(Path(__file__).parent))

from ocr import DocumentOCR, IMAGE_EXTENSIONS, PDF_EXTENSIONS

SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS

# ANSI colour helpers (gracefully degraded on Windows)
def _supports_colour() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

BOLD    = "\033[1m"  if _supports_colour() else ""
GREEN   = "\033[92m" if _supports_colour() else ""
YELLOW  = "\033[93m" if _supports_colour() else ""
CYAN    = "\033[96m" if _supports_colour() else ""
RED     = "\033[91m" if _supports_colour() else ""
DIM     = "\033[2m"  if _supports_colour() else ""
RESET   = "\033[0m"  if _supports_colour() else ""

BANNER = f"""{CYAN}{BOLD}
╔══════════════════════════════════════════════════════╗
║          CDTRS Document OCR Engine v1.0              ║
║  PaddleOCR · PyMuPDF · Handwriting Detection · Regex ║
╚══════════════════════════════════════════════════════╝
{RESET}"""


# ===========================================================================
# Pretty-print result
# ===========================================================================

def print_result(result: dict, quiet: bool = False) -> None:
    """Pretty-print OCR result to stdout."""
    sep  = f"{DIM}{'─' * 58}{RESET}"

    print(sep)
    print(f"{BOLD}File      :{RESET} {result['file']}")
    print(f"{BOLD}Type      :{RESET} {result['file_type'].upper()}  "
          f"({result['page_count']} page(s))")
    conf_colour = GREEN if result["confidence"] >= 0.75 else (
        YELLOW if result["confidence"] >= 0.50 else RED
    )
    print(f"{BOLD}Confidence:{RESET} {conf_colour}{result['confidence']:.1%}{RESET}")
    hw_label = f"{YELLOW}YES (handwriting mode){RESET}" if result["is_handwritten"] else "No"
    print(f"{BOLD}Handwritten:{RESET} {hw_label}")
    print(sep)

    # ---- Extracted Fields -----------------------------------------------
    fields = result.get("fields", {})
    if fields:
        print(f"\n{BOLD}{CYAN}EXTRACTED FIELDS{RESET}")
        for k, v in fields.items():
            label = k.replace("_", " ").title()
            if isinstance(v, list):
                v_str = ", ".join(v)
            else:
                v_str = str(v)
            # Wrap long values
            wrapped = textwrap.fill(v_str, width=50, subsequent_indent="              ")
            print(f"  {BOLD}{label:<16}{RESET}: {wrapped}")
    else:
        print(f"\n{DIM}No structured fields extracted.{RESET}")

    # ---- Department Suggestion ------------------------------------------
    dept = result.get("department_suggestion", {})
    print(f"\n{BOLD}{CYAN}DEPARTMENT SUGGESTION{RESET}")
    if dept.get("suggested"):
        conf_pct = f"{dept['confidence']:.1%}"
        print(f"  {BOLD}Suggested  :{RESET} {GREEN}{dept['suggested']}{RESET}  "
              f"(confidence {GREEN}{conf_pct}{RESET})")
        top_scores = list(dept["scores"].items())[:5]  # top 5
        print(f"  {BOLD}Top scores :{RESET}")
        for d, s in top_scores:
            bar = "█" * min(int(s), 20)
            print(f"    {d:<24} {s:>5.1f}  {DIM}{bar}{RESET}")
    else:
        print(f"  {DIM}Could not determine department (insufficient text).{RESET}")

    # ---- Raw Text Preview -----------------------------------------------
    if not quiet:
        raw = result.get("raw_text", "")
        preview = raw[:600].replace("\n", " ↵ ") if raw else "(empty)"
        print(f"\n{BOLD}{CYAN}RAW TEXT PREVIEW{RESET} (first 600 chars)")
        print(f"{DIM}{preview}{RESET}")

    print(f"\n{sep}\n")


# ===========================================================================
# Save result to JSON
# ===========================================================================

def save_result(result: dict, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem     = Path(result["file"]).stem
    out_path = output_dir / f"{stem}_ocr_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    return out_path


# ===========================================================================
# Process a single file
# ===========================================================================

def process_file(
    file_path: Path,
    engine: DocumentOCR,
    save: bool,
    quiet: bool,
    output_dir: Path,
) -> dict | None:
    print(f"{BOLD}Processing:{RESET} {file_path.name}")
    try:
        result = engine.process(file_path)
        print_result(result, quiet=quiet)
        if save:
            saved = save_result(result, output_dir)
            print(f"{GREEN}✔  Saved → {saved}{RESET}\n")
        return result
    except Exception as exc:
        print(f"{RED}✘  Error processing {file_path.name}: {exc}{RESET}\n")
        return None


# ===========================================================================
# Main entry point
# ===========================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="CDTRS OCR",
        description="Process documents with PaddleOCR — extracts fields and suggests department.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python main.py --file invoice.pdf
              python main.py --file handwritten_note.jpg --handwriting
              python main.py --folder ./documents/ --save
              python main.py --file doc.pdf --save --quiet
        """),
    )

    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--file",   type=Path, metavar="PATH",
                     help="Path to a single document file")
    src.add_argument("--folder", type=Path, metavar="DIR",
                     help="Path to a folder; all supported files are processed")

    parser.add_argument("--handwriting", action="store_true",
                        help="Force handwriting recognition mode for all pages")
    parser.add_argument("--gpu",         action="store_true",
                        help="Enable GPU acceleration (requires paddlepaddle-gpu)")
    parser.add_argument("--save",        action="store_true",
                        help="Save OCR result(s) as JSON in the output/ folder")
    parser.add_argument("--quiet",       action="store_true",
                        help="Suppress raw text preview in output")
    parser.add_argument("--output-dir",  type=Path, default=Path("output"),
                        metavar="DIR",
                        help="Directory to save JSON results (default: ./output)")

    args = parser.parse_args()

    print(BANNER)

    engine = DocumentOCR(use_gpu=args.gpu, force_handwriting=args.handwriting)

    if args.file:
        # Single file mode
        if not args.file.exists():
            print(f"{RED}Error: File not found: {args.file}{RESET}")
            sys.exit(1)
        if args.file.suffix.lower() not in SUPPORTED_EXTENSIONS:
            print(
                f"{RED}Error: Unsupported file type '{args.file.suffix}'. "
                f"Supported: {sorted(SUPPORTED_EXTENSIONS)}{RESET}"
            )
            sys.exit(1)
        process_file(args.file, engine, args.save, args.quiet, args.output_dir)

    elif args.folder:
        # Folder mode
        if not args.folder.is_dir():
            print(f"{RED}Error: Not a directory: {args.folder}{RESET}")
            sys.exit(1)

        files = sorted(
            f for f in args.folder.rglob("*")
            if f.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        if not files:
            print(f"{YELLOW}No supported files found in {args.folder}{RESET}")
            sys.exit(0)

        print(f"{BOLD}Found {len(files)} document(s) in {args.folder}{RESET}\n")
        ok, fail = 0, 0
        for fp in files:
            r = process_file(fp, engine, args.save, args.quiet, args.output_dir)
            if r is not None:
                ok += 1
            else:
                fail += 1

        print(f"{sep if (sep := '─' * 58) else ''}")
        print(f"{GREEN}✔  {ok} succeeded{RESET}  "
              f"{(RED + '✘  ' + str(fail) + ' failed' + RESET) if fail else ''}")


if __name__ == "__main__":
    main()
