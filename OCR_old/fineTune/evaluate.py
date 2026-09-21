"""
=============================================================================
CDTRS OCR fineTune — evaluate.py
=============================================================================
Evaluate fine-tuned or original OCR model on the test split.

Metrics:
  • Character Error Rate (CER)
  • Word Error Rate (WER)

Optionally compares fine-tuned model against original PaddleOCR baseline.

Usage:
    python evaluate.py                          # evaluate latest fine-tuned model
    python evaluate.py --model handwritten_v1   # evaluate specific version
    python evaluate.py --model original         # evaluate original PaddleOCR
    python evaluate.py --compare                # compare latest vs original

No internet connection required.
=============================================================================
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as cfg
from model_manager import resolve_model_dir, print_versions
from utils.dataset import load_vocab, load_split
from utils.metrics import evaluate_batch
from utils.preprocessing import preprocess_image


# ---------------------------------------------------------------------------
# Run fine-tuned CRNN model on test set
# ---------------------------------------------------------------------------

def _run_crnn_eval(model_version: str) -> dict:
    """Load and evaluate a CRNN fine-tuned model on the test split."""
    try:
        import paddle
        import numpy as np
    except ImportError:
        print("[ERROR] paddlepaddle not installed.")
        sys.exit(1)

    # Import train.py model builder without circular issues
    from train import _build_crnn, _ctc_greedy_decode
    from model_manager import load_model_weights

    test_split = cfg.SPLITS_DIR / "test.txt"
    vocab_path = cfg.SPLITS_DIR / cfg.VOCAB_FILENAME

    for p in [test_split, vocab_path]:
        if not p.exists():
            print(f"[ERROR] Missing: {p}\nRun prepare_dataset.py first.")
            sys.exit(1)

    vocab     = load_vocab(vocab_path)
    vocab_inv = {v: k for k, v in vocab.items()}
    samples   = load_split(test_split)

    if not samples:
        print("[ERROR] No test samples found. Run prepare_dataset.py first.")
        sys.exit(1)

    paddle.set_device(cfg.DEVICE)
    model = _build_crnn(len(vocab))
    load_model_weights(model, version=model_version)
    model.eval()

    predictions: list[str] = []
    labels:      list[str] = []

    with paddle.no_grad():
        for img_path, gt_label in samples:
            img = preprocess_image(img_path, enhance=True)       # (H, W, 3) float32
            img_t = paddle.to_tensor(
                img.transpose(2, 0, 1)[None],                    # (1, C, H, W)
                dtype="float32",
            )
            logits    = model(img_t)                             # (T, 1, C)
            logits_np = logits.numpy().transpose(1, 0, 2)        # (1, T, C)
            pred = _ctc_greedy_decode(logits_np, vocab_inv)[0]
            predictions.append(pred)
            labels.append(gt_label)

    return evaluate_batch(predictions, labels)


# ---------------------------------------------------------------------------
# Run original PaddleOCR baseline on test set
# ---------------------------------------------------------------------------

def _run_paddle_baseline() -> dict:
    """Run original PaddleOCR on test images and compute CER/WER."""
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        print("[ERROR] paddleocr not installed.")
        sys.exit(1)

    test_split = cfg.SPLITS_DIR / "test.txt"
    if not test_split.exists():
        print(f"[ERROR] Missing: {test_split}\nRun prepare_dataset.py first.")
        sys.exit(1)

    samples = load_split(test_split)
    if not samples:
        print("[ERROR] No test samples.")
        sys.exit(1)

    ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    predictions: list[str] = []
    labels:      list[str] = []

    for img_path, gt_label in samples:
        try:
            result = ocr.ocr(img_path, cls=True)
            texts = []
            if result:
                for page in result:
                    if page:
                        for box in page:
                            if isinstance(box, (list, tuple)) and len(box) == 2:
                                txt = box[1][0] if isinstance(box[1], (list, tuple)) else ""
                                texts.append(str(txt))
            predictions.append(" ".join(texts))
        except Exception as e:
            print(f"  [WARN] PaddleOCR failed on {Path(img_path).name}: {e}")
            predictions.append("")
        labels.append(gt_label)

    return evaluate_batch(predictions, labels)


# ---------------------------------------------------------------------------
# Main evaluation entry
# ---------------------------------------------------------------------------

def evaluate(model_version: str = "latest", compare: bool = False) -> None:
    print("\n" + "=" * 60)
    print("  CDTRS OCR fineTune — Evaluation")
    print("=" * 60)

    results: dict = {}

    if model_version == "original":
        print("\n  Evaluating: Original PaddleOCR baseline ...")
        results["original"] = _run_paddle_baseline()
        _print_result("Original PaddleOCR", results["original"])
    else:
        print(f"\n  Evaluating: Fine-tuned model ({model_version}) ...")
        results[model_version] = _run_crnn_eval(model_version)
        _print_result(model_version, results[model_version])

    if compare:
        print("\n  Evaluating: Original PaddleOCR baseline (for comparison) ...")
        results["original"] = _run_paddle_baseline()
        _print_result("Original PaddleOCR", results["original"])
        _print_comparison(results.get(model_version, {}), results["original"])

    # Save results
    output = {
        "evaluated_at": datetime.now().isoformat(),
        "model_version": model_version,
        "compare": compare,
        "results": results,
    }
    with open(cfg.EVAL_RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n  Full results saved → {cfg.EVAL_RESULTS_FILE}")
    print("=" * 60 + "\n")


def _print_result(label: str, metrics: dict) -> None:
    n   = metrics.get("num_samples", 0)
    cer = metrics.get("mean_cer", 0.0)
    wer = metrics.get("mean_wer", 0.0)
    print(f"\n  {label}")
    print(f"    Samples evaluated : {n}")
    print(f"    Mean CER          : {cer:.4f}  ({cer*100:.2f}%)")
    print(f"    Mean WER          : {wer:.4f}  ({wer*100:.2f}%)")


def _print_comparison(ft: dict, base: dict) -> None:
    print("\n  --- Comparison ---")
    ft_cer  = ft.get("mean_cer",  1.0)
    ft_wer  = ft.get("mean_wer",  1.0)
    b_cer   = base.get("mean_cer", 1.0)
    b_wer   = base.get("mean_wer", 1.0)
    delta_c = b_cer - ft_cer
    delta_w = b_wer - ft_wer
    sign_c  = "↓ improvement" if delta_c > 0 else ("↑ regression" if delta_c < 0 else "no change")
    sign_w  = "↓ improvement" if delta_w > 0 else ("↑ regression" if delta_w < 0 else "no change")
    print(f"    CER delta (base - fine-tuned): {delta_c:+.4f}  {sign_c}")
    print(f"    WER delta (base - fine-tuned): {delta_w:+.4f}  {sign_w}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate OCR model on test set.")
    parser.add_argument("--model",   default="latest",
                        help="Model version: 'latest'|'original'|'handwritten_vN'")
    parser.add_argument("--compare", action="store_true",
                        help="Also run original PaddleOCR for comparison")
    args = parser.parse_args()

    print("\n  Saved model versions:")
    print_versions()
    evaluate(model_version=args.model, compare=args.compare)
