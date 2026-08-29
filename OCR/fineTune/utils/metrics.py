"""
=============================================================================
CDTRS OCR fineTune — utils/metrics.py
=============================================================================
Offline evaluation metrics: Character Error Rate (CER) and Word Error Rate (WER).
No external dependencies beyond Python stdlib.
=============================================================================
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Edit-distance helper
# ---------------------------------------------------------------------------

def _edit_distance(a: str, b: str) -> int:
    """Standard Levenshtein edit distance between two strings."""
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


# ---------------------------------------------------------------------------
# CER
# ---------------------------------------------------------------------------

def compute_cer(predicted: str, ground_truth: str) -> float:
    """
    Character Error Rate = edit_distance(pred, gt) / len(gt)

    Returns 0.0 if ground_truth is empty.
    Returns 1.0 if ground_truth is empty but predicted is not.
    """
    pred = predicted.strip()
    gt   = ground_truth.strip()
    if not gt:
        return 0.0 if not pred else 1.0
    return _edit_distance(pred, gt) / len(gt)


# ---------------------------------------------------------------------------
# WER
# ---------------------------------------------------------------------------

def compute_wer(predicted: str, ground_truth: str) -> float:
    """
    Word Error Rate = edit_distance(pred_words, gt_words) / len(gt_words)

    Returns 0.0 if ground_truth is empty.
    Returns 1.0 if ground_truth is empty but predicted is not.
    """
    pred_words = predicted.strip().split()
    gt_words   = ground_truth.strip().split()
    if not gt_words:
        return 0.0 if not pred_words else 1.0
    return _edit_distance(pred_words, gt_words) / len(gt_words)


# ---------------------------------------------------------------------------
# Batch evaluation
# ---------------------------------------------------------------------------

def evaluate_batch(
    predictions: list[str],
    labels: list[str],
) -> dict:
    """
    Compute mean CER and WER over a list of (prediction, label) pairs.

    Returns:
        {
          "num_samples": int,
          "mean_cer":    float,
          "mean_wer":    float,
          "per_sample":  [ {"predicted": str, "label": str, "cer": float, "wer": float}, ... ]
        }
    """
    if len(predictions) != len(labels):
        raise ValueError(
            f"predictions ({len(predictions)}) and labels ({len(labels)}) must have the same length"
        )

    per_sample = []
    total_cer  = 0.0
    total_wer  = 0.0

    for pred, gt in zip(predictions, labels):
        cer = compute_cer(pred, gt)
        wer = compute_wer(pred, gt)
        total_cer += cer
        total_wer += wer
        per_sample.append({
            "predicted": pred,
            "label":     gt,
            "cer":       round(cer, 4),
            "wer":       round(wer, 4),
        })

    n = len(predictions)
    return {
        "num_samples": n,
        "mean_cer":    round(total_cer / n, 4) if n else 0.0,
        "mean_wer":    round(total_wer / n, 4) if n else 0.0,
        "per_sample":  per_sample,
    }
