"""
OCR Package for CDTRS
Exports DocumentOCR and rules configuration.
"""

from pathlib import Path
import sys

# Ensure this directory is in sys.path
_PKG_DIR = str(Path(__file__).resolve().parent)
if _PKG_DIR not in sys.path:
    sys.path.insert(0, _PKG_DIR)

# PZ_26/08: Safely import DocumentOCR with graceful fallback so rules can be imported without OpenCV/PaddleOCR
try:
    from .ocr import DocumentOCR
except ImportError:
    DocumentOCR = None

# PZ_26/08: Export standalone extract_fields and suggest_department helpers
from .rules import (
    FIELD_PATTERNS,
    DEPARTMENT_KEYWORDS,
    DEPARTMENT_SCORE_WEIGHTS,
    DOCUMENT_TYPE_CANONICAL,
    extract_fields,
    suggest_department,
)

__all__ = [
    "DocumentOCR",
    "FIELD_PATTERNS",
    "DEPARTMENT_KEYWORDS",
    "DEPARTMENT_SCORE_WEIGHTS",
    "DOCUMENT_TYPE_CANONICAL",
]
