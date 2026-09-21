"""
=============================================================================
CDTRS OCR fineTune — utils/dataset.py
=============================================================================
PaddlePaddle Dataset class for handwritten OCR fine-tuning.

Dataset format (defined in dataset/README.md):
  dataset/images/image001.png
  dataset/labels/image001.txt   ← contains the ground-truth text (one line)

Split manifest files (in dataset/splits/) are plain text files:
  <relative_image_path>\t<label_text>

All operations are local — no internet required.
=============================================================================
"""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config as cfg

# preprocessing is only needed inside HandwrittenDataset (requires cv2/numpy)
# — imported lazily so vocab/split helpers work without cv2.
_preprocess_image = None

def _get_preprocess():
    global _preprocess_image
    if _preprocess_image is None:
        import numpy as np  # noqa: F401
        from utils.preprocessing import preprocess_image as _pi
        _preprocess_image = _pi
    return _preprocess_image

# Optional PaddlePaddle import — handled gracefully
try:
    import paddle
    from paddle.io import Dataset as PaddleDataset
    _PADDLE_AVAILABLE = True
except ImportError:
    _PADDLE_AVAILABLE = False
    PaddleDataset = object   # fallback base class


# ---------------------------------------------------------------------------
# Vocabulary helpers
# ---------------------------------------------------------------------------

def load_vocab(vocab_path: str | Path) -> dict[str, int]:
    """
    Load vocabulary from a vocab.txt file.
    Line 0 is BLANK_TOKEN (index 0), line 1 is UNKNOWN_TOKEN, then characters.

    Returns: {char: index}
    """
    path = Path(vocab_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Vocabulary file not found: {path}\n"
            "Run prepare_dataset.py first to generate the vocabulary."
        )
    vocab: dict[str, int] = {}
    with open(path, encoding="utf-8") as f:
        for idx, line in enumerate(f):
            char = line.rstrip("\n")
            vocab[char] = idx
    return vocab


def build_vocab(labels: list[str]) -> dict[str, int]:
    """
    Build a character vocabulary from a list of label strings.
    Index 0 = BLANK_TOKEN, 1 = UNKNOWN_TOKEN, then sorted unique chars.
    """
    chars = sorted(set("".join(labels)))
    vocab = {cfg.BLANK_TOKEN: 0, cfg.UNKNOWN_TOKEN: 1}
    for i, c in enumerate(chars, start=2):
        vocab[c] = i
    return vocab


def save_vocab(vocab: dict[str, int], vocab_path: str | Path) -> None:
    """Save vocabulary to vocab.txt (one token per line, ordered by index)."""
    path = Path(vocab_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(vocab.items(), key=lambda x: x[1])
    with open(path, "w", encoding="utf-8") as f:
        for char, _ in ordered:
            f.write(char + "\n")


def encode_label(text: str, vocab: dict[str, int]) -> list[int]:
    """Convert a label string to a list of integer indices."""
    unk_idx = vocab.get(cfg.UNKNOWN_TOKEN, 1)
    return [vocab.get(c, unk_idx) for c in text]


# ---------------------------------------------------------------------------
# Split manifest helpers
# ---------------------------------------------------------------------------

def load_split(split_file: str | Path) -> list[tuple[str, str]]:
    """
    Load a split manifest file.
    Each line: <image_path><TAB><label_text>
    Returns: [(image_path, label_text), ...]
    """
    path = Path(split_file)
    if not path.exists():
        raise FileNotFoundError(
            f"Split file not found: {path}\n"
            "Run prepare_dataset.py first."
        )
    samples = []
    with open(path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) != 2:
                print(f"  [WARN] Skipping malformed line {line_num} in {path.name}: {line!r}")
                continue
            samples.append((parts[0], parts[1]))
    return samples


# ---------------------------------------------------------------------------
# PaddlePaddle Dataset class
# ---------------------------------------------------------------------------

class HandwrittenDataset(PaddleDataset):
    """
    PaddlePaddle Dataset for handwritten OCR training.

    Parameters
    ----------
    split_file : path to train.txt / val.txt / test.txt
    vocab      : {char: index} mapping (from load_vocab / build_vocab)
    enhance    : whether to apply handwriting preprocessing
    """

    def __init__(
        self,
        split_file: str | Path,
        vocab: dict[str, int],
        enhance: bool = True,
    ):
        if not _PADDLE_AVAILABLE:
            raise ImportError(
                "paddlepaddle is not installed. "
                "Install it with: pip install paddlepaddle==2.6.2"
            )
        super().__init__()
        self.samples = load_split(split_file)
        self.vocab   = vocab
        self.enhance = enhance

        if not self.samples:
            raise ValueError(
                f"No valid samples found in {split_file}.\n"
                "Please add images and labels to dataset/images/ and dataset/labels/, "
                "then run prepare_dataset.py."
            )

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        image_path, label_text = self.samples[idx]

        # 1. Preprocess image → float32 (H, W, 3) normalised [0,1]
        preprocess_image = _get_preprocess()
        img = preprocess_image(image_path, enhance=self.enhance)

        # 2. Transpose to (C, H, W) — PaddlePaddle convention
        img_tensor = paddle.to_tensor(
            img.transpose(2, 0, 1),  # (3, H, W)
            dtype="float32",
        )

        # 3. Encode label
        label_ids = encode_label(label_text, self.vocab)
        label_tensor = paddle.to_tensor(label_ids, dtype="int32")

        # 4. Label length (needed for CTC loss)
        label_len = paddle.to_tensor([len(label_ids)], dtype="int32")

        return img_tensor, label_tensor, label_len
