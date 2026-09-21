"""
=============================================================================
CDTRS OCR fineTune — model_manager.py
=============================================================================
Versioned local model management.

Responsibilities:
  - Discover existing model versions inside models/
  - Determine the next version name (handwritten_v1, v2, v3 ...)
  - Save model weights + metadata JSON
  - Load model weights from a named version
  - List all saved versions

No internet connection is used. All paths stay inside OCR/fineTune/models/.
=============================================================================
"""

from __future__ import annotations
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg


# ---------------------------------------------------------------------------
# Version discovery
# ---------------------------------------------------------------------------

def _version_dirs() -> list[Path]:
    """Return all handwritten_vN directories sorted by N ascending."""
    pattern = re.compile(r"^handwritten_v(\d+)$")
    dirs = []
    for p in cfg.TRAINED_MODELS_DIR.iterdir():
        if p.is_dir():
            m = pattern.match(p.name)
            if m:
                dirs.append((int(m.group(1)), p))
    dirs.sort(key=lambda x: x[0])
    return [d for _, d in dirs]


def list_versions() -> list[dict]:
    """
    Return a list of dicts describing each saved fine-tuned model version.
    Each dict contains the fields from model_metadata.json plus 'version_dir'.
    """
    result = []
    for vdir in _version_dirs():
        meta_path = vdir / "model_metadata.json"
        if meta_path.exists():
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
        else:
            meta = {"version": vdir.name, "note": "metadata missing"}
        meta["version_dir"] = str(vdir)
        result.append(meta)
    return result


def get_latest_version() -> Path | None:
    """Return the path to the most recently fine-tuned model dir, or None."""
    dirs = _version_dirs()
    return dirs[-1] if dirs else None


def get_next_version_name() -> str:
    """Return the next version name, e.g. 'handwritten_v3'."""
    dirs = _version_dirs()
    if not dirs:
        return "handwritten_v1"
    last = dirs[-1].name  # e.g. handwritten_v2
    n = int(re.search(r"(\d+)$", last).group(1))
    return f"handwritten_v{n + 1}"


def resolve_model_dir(version: str = "latest") -> Path:
    """
    Resolve a model directory by version name.

    Parameters
    ----------
    version : "latest" | "original" | "handwritten_vN"

    Raises FileNotFoundError with a helpful message if the directory or
    model weights are missing.
    """
    if version == "original":
        d = cfg.ORIGINAL_MODEL_DIR
        if not d.exists() or not any(d.iterdir()):
            raise FileNotFoundError(
                f"Original model directory is empty or missing: {d}\n"
                "Run download_models.py once to fetch the PP-OCRv3 weights locally."
            )
        return d

    if version == "latest":
        d = get_latest_version()
        if d is None:
            # Fall back to original
            return resolve_model_dir("original")
        return d

    # Explicit version name
    d = cfg.TRAINED_MODELS_DIR / version
    if not d.exists():
        raise FileNotFoundError(
            f"Model version '{version}' not found at: {d}\n"
            f"Available versions: {[v['version'] for v in list_versions()] or ['(none yet)']}"
        )
    return d


# ---------------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------------

def save_model(model: Any, version_name: str, metadata: dict) -> Path:
    """
    Save PaddlePaddle model parameters and metadata JSON.

    Parameters
    ----------
    model        : paddle.nn.Layer
    version_name : e.g. "handwritten_v1"
    metadata     : dict with training details

    Returns the version directory path.
    """
    try:
        import paddle
    except ImportError as e:
        raise ImportError("paddlepaddle is not installed.") from e

    version_dir = cfg.TRAINED_MODELS_DIR / version_name
    version_dir.mkdir(parents=True, exist_ok=True)

    # Save weights
    weights_path = str(version_dir / cfg.MODEL_FILENAME)
    paddle.save(model.state_dict(), weights_path)
    print(f"  [ModelManager] Saved weights → {weights_path}")

    # Save metadata
    save_metadata(version_dir, metadata)
    return version_dir


def load_model_weights(model: Any, version: str = "latest") -> Path:
    """
    Load saved PaddlePaddle parameters into *model* in-place.

    Parameters
    ----------
    model   : paddle.nn.Layer (must be already constructed)
    version : "latest" | "original" | "handwritten_vN"

    Returns the version directory that was loaded.
    """
    try:
        import paddle
    except ImportError as e:
        raise ImportError("paddlepaddle is not installed.") from e

    version_dir  = resolve_model_dir(version)
    weights_path = version_dir / cfg.MODEL_FILENAME

    if not weights_path.exists():
        raise FileNotFoundError(
            f"Model weights not found at: {weights_path}\n"
            f"Version directory exists but weights file '{cfg.MODEL_FILENAME}' is missing."
        )

    state_dict = paddle.load(str(weights_path))
    model.set_state_dict(state_dict)
    print(f"  [ModelManager] Loaded weights from {weights_path}")
    return version_dir


def save_metadata(version_dir: Path, metadata: dict) -> None:
    """Write model_metadata.json into *version_dir*."""
    meta_path = version_dir / "model_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"  [ModelManager] Metadata saved → {meta_path}")


# ---------------------------------------------------------------------------
# Print summary
# ---------------------------------------------------------------------------

def print_versions() -> None:
    """Pretty-print all available model versions."""
    versions = list_versions()
    if not versions:
        print("  No fine-tuned models found. Run train.py to create the first one.")
        return
    print(f"\n  {'VERSION':<20} {'TRAINED ON':<22} {'MEAN CER':<12} {'MEAN WER':<12}")
    print("  " + "-" * 70)
    for v in versions:
        name    = v.get("version", "?")
        trained = v.get("trained_at", "?")[:19]
        cer     = v.get("val_cer", v.get("mean_cer", "?"))
        wer     = v.get("val_wer", v.get("mean_wer", "?"))
        if isinstance(cer, float):
            cer = f"{cer:.4f}"
        if isinstance(wer, float):
            wer = f"{wer:.4f}"
        print(f"  {name:<20} {trained:<22} {cer:<12} {wer:<12}")
    print()


if __name__ == "__main__":
    print("\n=== Saved Model Versions ===")
    print_versions()
    latest = get_latest_version()
    print(f"Latest version : {latest.name if latest else '(none — run train.py first)'}")
    print(f"Next version   : {get_next_version_name()}")
