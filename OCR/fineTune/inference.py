"""
=============================================================================
CDTRS OCR fineTune — inference.py
=============================================================================
Standalone offline inference CLI.

Supports three modes:
  • original   — uses PaddleOCR (existing OCR/ocr.py engine) for full doc OCR
  • latest     — loads latest fine-tuned CRNN model
  • handwritten_vN — loads a specific fine-tuned version

Usage:
    python inference.py --input path/to/image.png
    python inference.py --input scan.pdf --model original
    python inference.py --input hw.png   --model latest
    python inference.py --input hw.jpg   --model handwritten_v2

No internet connection is required.
=============================================================================
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as cfg
from model_manager import resolve_model_dir, get_latest_version, print_versions


# ---------------------------------------------------------------------------
# Mode: original — delegate to existing DocumentOCR in OCR/ocr.py
# ---------------------------------------------------------------------------

def _run_original(file_path: Path) -> str:
    """Use the unmodified OCR/ocr.py DocumentOCR engine."""
    # Add OCR package directory to path
    ocr_pkg = Path(__file__).resolve().parent.parent  # OCR/
    sys.path.insert(0, str(ocr_pkg))
    try:
        from ocr import DocumentOCR
    except ImportError as e:
        print(f"[ERROR] Cannot import DocumentOCR from OCR/ocr.py: {e}")
        sys.exit(1)

    engine = DocumentOCR()
    result = engine.process(file_path)
    return result.get("raw_text", "")


# ---------------------------------------------------------------------------
# Mode: fine-tuned CRNN
# ---------------------------------------------------------------------------

def _run_finetuned(file_path: Path, model_version: str) -> str:
    """Use the fine-tuned CRNN model for recognition."""
    try:
        import paddle
        import numpy as np
    except ImportError:
        print("[ERROR] paddlepaddle not installed.")
        sys.exit(1)

    from train import _build_crnn, _ctc_greedy_decode
    from model_manager import load_model_weights
    from utils.dataset import load_vocab
    from utils.preprocessing import preprocess_image, load_image, enhance_for_handwriting

    # Load vocabulary from the model version dir first, then fallback to splits/
    version_dir = resolve_model_dir(model_version)
    vocab_candidates = [
        version_dir / cfg.VOCAB_FILENAME,
        cfg.SPLITS_DIR / cfg.VOCAB_FILENAME,
    ]
    vocab_path = next((p for p in vocab_candidates if p.exists()), None)
    if vocab_path is None:
        print(
            "[ERROR] vocab.txt not found. Run prepare_dataset.py first, "
            "or make sure the model version directory contains vocab.txt."
        )
        sys.exit(1)

    vocab     = load_vocab(vocab_path)
    vocab_inv = {v: k for k, v in vocab.items()}

    paddle.set_device(cfg.DEVICE)
    model = _build_crnn(len(vocab))
    load_model_weights(model, version=model_version)
    model.eval()

    # Detection: still use PaddleOCR detection to find text regions
    # Recognition: use fine-tuned CRNN on each cropped region
    try:
        from paddleocr import PaddleOCR
        det_ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        det_result = det_ocr.ocr(str(file_path), cls=True, rec=False)
    except Exception:
        det_result = None

    import cv2
    img_bgr = None
    if det_result and any(det_result):
        # Crop each detected region and run fine-tuned recognition
        img_bgr = load_image(file_path)
        all_texts: list[str] = []

        for page in det_result:
            if not page:
                continue
            for box_item in page:
                # box_item: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] or similar
                try:
                    box = np.array(box_item, dtype=np.int32)
                    x_min = max(0, int(box[:, 0].min()))
                    y_min = max(0, int(box[:, 1].min()))
                    x_max = min(img_bgr.shape[1], int(box[:, 0].max()))
                    y_max = min(img_bgr.shape[0], int(box[:, 1].max()))
                    crop  = img_bgr[y_min:y_max, x_min:x_max]
                    if crop.size == 0:
                        continue
                    # Preprocess crop
                    crop_enhanced = enhance_for_handwriting(crop)
                    from utils.preprocessing import resize_for_crnn
                    crop_resized = resize_for_crnn(crop_enhanced)
                    img_t = paddle.to_tensor(
                        crop_resized.transpose(2, 0, 1)[None],
                        dtype="float32",
                    )
                    with paddle.no_grad():
                        logits    = model(img_t)
                        logits_np = logits.numpy().transpose(1, 0, 2)
                    pred = _ctc_greedy_decode(logits_np, vocab_inv)[0]
                    if pred:
                        all_texts.append(pred)
                except Exception:
                    continue
        return "\n".join(all_texts)

    # Fallback: treat whole image as one crop
    img_proc = preprocess_image(file_path, enhance=True)
    img_t = paddle.to_tensor(
        img_proc.transpose(2, 0, 1)[None],
        dtype="float32",
    )
    with paddle.no_grad():
        logits    = model(img_t)
        logits_np = logits.numpy().transpose(1, 0, 2)
    return _ctc_greedy_decode(logits_np, vocab_inv)[0]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_inference(file_path: Path, model_version: str, verbose: bool) -> None:
    print("\n" + "=" * 60)
    print("  CDTRS OCR fineTune — Inference")
    print("=" * 60)
    print(f"  File  : {file_path}")
    print(f"  Model : {model_version}")

    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        sys.exit(1)

    if model_version == "original":
        print("\n  Using original PaddleOCR engine (OCR/ocr.py)...")
        text = _run_original(file_path)
    else:
        print(f"\n  Using fine-tuned CRNN model ({model_version})...")
        text = _run_finetuned(file_path, model_version)

    print("\n" + "-" * 60)
    print("  RECOGNIZED TEXT:")
    print("-" * 60)
    if text:
        print(text)
    else:
        print("  (no text recognized)")
    print("-" * 60 + "\n")

    if verbose:
        print(f"  Characters : {len(text)}")
        print(f"  Words      : {len(text.split())}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run offline OCR inference on an image or PDF."
    )
    parser.add_argument("--input",   required=True, type=Path,
                        help="Path to image (.png/.jpg/...) or PDF file")
    parser.add_argument("--model",   default="latest",
                        help="Model: 'latest'|'original'|'handwritten_vN' (default: latest)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print additional stats (character/word count)")
    parser.add_argument("--list-models", action="store_true",
                        help="List all saved model versions and exit")
    args = parser.parse_args()

    if args.list_models:
        print("\n  Saved model versions:")
        print_versions()
        sys.exit(0)

    run_inference(args.input, args.model, args.verbose)
