"""
CDTRS OCR fineTune — utils/__init__.py
Lazy imports so that vocab/dataset helpers work without cv2/paddle.
"""

def __getattr__(name):
    if name in ("preprocess_image", "load_image", "enhance_for_handwriting", "resize_for_crnn"):
        from .preprocessing import preprocess_image, load_image, enhance_for_handwriting, resize_for_crnn
        return locals()[name]
    if name in ("compute_cer", "compute_wer", "evaluate_batch"):
        from .metrics import compute_cer, compute_wer, evaluate_batch
        return locals()[name]
    if name in ("HandwrittenDataset", "load_vocab", "build_vocab", "save_vocab", "load_split"):
        from .dataset import HandwrittenDataset, load_vocab, build_vocab, save_vocab, load_split
        return locals()[name]
    raise AttributeError(f"module 'utils' has no attribute {name!r}")

# Eagerly export vocab helpers (no cv2/paddle needed)
from .metrics import compute_cer, compute_wer, evaluate_batch
from .dataset import load_vocab, build_vocab, save_vocab, load_split, encode_label

__all__ = [
    "preprocess_image", "load_image", "enhance_for_handwriting", "resize_for_crnn",
    "compute_cer", "compute_wer", "evaluate_batch",
    "HandwrittenDataset", "load_vocab", "build_vocab", "save_vocab", "load_split", "encode_label",
]
