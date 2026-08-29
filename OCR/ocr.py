"""
=============================================================================
CDTRS OCR Engine  —  ocr.py
=============================================================================
Core OCR class that wraps PaddleOCR (v3.x) to process any document:
  • Images   : PNG, JPG, JPEG, TIFF, BMP, WEBP
  • PDFs     : rendered page-by-page via PyMuPDF (fitz)
  • Handwriting: adaptive image pre-processing + lowered confidence thresholds

All regex patterns and department keywords live in rules.py — edit that
file to add/change extraction logic without touching this engine.

Usage (standalone):
    from ocr import DocumentOCR
    engine = DocumentOCR()
    result = engine.process("path/to/document.pdf")
    import json; print(json.dumps(result, indent=2))
=============================================================================
"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Any

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    from PIL import Image
except ImportError:
    Image = None

# Lazy-cached PaddleOCR instances (one for print, one for handwriting)
_paddle_print: Any | None = None
_paddle_hw:    Any | None = None

# Load our rules (all editable in rules.py)
try:
    from rules import (
        FIELD_PATTERNS,
        DEPARTMENT_KEYWORDS,
        DEPARTMENT_SCORE_WEIGHTS,
        DOCUMENT_TYPE_CANONICAL,
        PRINT_CONFIG,
        HANDWRITING_CONFIG,
        HANDWRITING_CONFIDENCE_THRESHOLD,
        MIN_TEXT_LENGTH_FOR_EXTRACTION,
    )
except ImportError:
    from OCR.rules import (
        FIELD_PATTERNS,
        DEPARTMENT_KEYWORDS,
        DEPARTMENT_SCORE_WEIGHTS,
        DOCUMENT_TYPE_CANONICAL,
        PRINT_CONFIG,
        HANDWRITING_CONFIG,
        HANDWRITING_CONFIDENCE_THRESHOLD,
        MIN_TEXT_LENGTH_FOR_EXTRACTION,
    )


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported file types
# ---------------------------------------------------------------------------
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}
PDF_EXTENSIONS   = {".pdf"}
ALL_EXTENSIONS   = IMAGE_EXTENSIONS | PDF_EXTENSIONS


# ===========================================================================
# Internal: lazy PaddleOCR factory (v3.x compatible)
# ===========================================================================

def _get_ocr(handwriting: bool = False) -> Any:
    """Return a cached PaddleOCR instance tuned for print or handwriting."""
    global _paddle_print, _paddle_hw

    try:
        from paddleocr import PaddleOCR
    except (ImportError, AttributeError, Exception) as exc:
        raise ImportError(
            f"PaddleOCR is not available ({exc}).\n"
            "Using PyMuPDF / pypdf digital text extraction."
        ) from exc

    if handwriting:
        if _paddle_hw is None:
            try:
                cfg = {
                    k: v for k, v in HANDWRITING_CONFIG.items()
                    if not k.startswith("preprocess_")
                }
                cfg = _map_config_to_v3(cfg)
                _paddle_hw = PaddleOCR(**cfg)
            except Exception:
                try:
                    _paddle_hw = PaddleOCR(use_angle_cls=True, lang="en")
                except Exception:
                    _paddle_hw = PaddleOCR()
        return _paddle_hw
    else:
        if _paddle_print is None:
            try:
                cfg = _map_config_to_v3(PRINT_CONFIG)
                _paddle_print = PaddleOCR(**cfg)
            except Exception:
                try:
                    _paddle_print = PaddleOCR(use_angle_cls=True, lang="en")
                except Exception:
                    _paddle_print = PaddleOCR()
        return _paddle_print


def _map_config_to_v3(cfg: dict) -> dict:
    """
    Translate PaddleOCR v2 config keys to v3 equivalents.
    Keys not accepted by v3 are silently dropped.
    """
    RENAME = {
        "det_db_thresh":       "text_det_thresh",
        "det_db_box_thresh":   "text_det_box_thresh",
        "rec_score_thresh":    "text_rec_score_thresh",
        "use_angle_cls":       "use_textline_orientation",
    }
    # Keys accepted by PaddleOCR v3 __init__
    ACCEPTED = {
        "lang", "text_det_thresh", "text_det_box_thresh",
        "text_rec_score_thresh", "use_textline_orientation",
        "use_doc_orientation_classify", "use_doc_unwarping",
        "text_detection_model_name", "text_recognition_model_name",
        "ocr_version", "use_angle_cls",
    }
    out = {}
    for k, v in cfg.items():
        new_k = RENAME.get(k, k)
        if new_k in ACCEPTED or k in ACCEPTED:
            out[k] = v
    return out


# ===========================================================================
# Internal: parse PaddleOCR results (Supports both .ocr() and .predict())
# ===========================================================================

def _parse_ocr_result(result: Any) -> tuple[list[str], list[float]]:
    """
    Extract (texts, scores) from any PaddleOCR result format:
    1. Standard list of boxes/tuples: [ [box, (text, score)], ... ]
    2. Flat list: [ (text, score), ... ]
    3. Dict format (v3/Paddlex): {'rec_texts': [...], 'rec_scores': [...]}
    """
    texts:  list[str]   = []
    scores: list[float] = []

    if not result:
        return texts, scores

    try:
        # Case 1: Dict output
        if isinstance(result, dict):
            rec_texts  = result.get("rec_texts",  []) or []
            rec_scores = result.get("rec_scores", []) or []
            for t, s in zip(rec_texts, rec_scores):
                if t and str(t).strip():
                    texts.append(str(t).strip())
                    scores.append(float(s))
        # Case 2: List output
        elif isinstance(result, list):
            for item in result:
                if not item:
                    continue
                # item can be [box, (text, score)]
                if isinstance(item, (list, tuple)) and len(item) == 2 and isinstance(item[1], (tuple, list)):
                    txt = item[1][0]
                    sc = float(item[1][1]) if len(item[1]) > 1 else 0.9
                    if txt and str(txt).strip():
                        texts.append(str(txt).strip())
                        scores.append(sc)
                # item can be a nested page list
                elif isinstance(item, list):
                    sub_texts, sub_scores = _parse_ocr_result(item)
                    texts.extend(sub_texts)
                    scores.extend(sub_scores)
                # item can be (text, score)
                elif isinstance(item, (tuple, list)) and len(item) >= 2 and isinstance(item[0], str):
                    texts.append(str(item[0]).strip())
                    scores.append(float(item[1]))
    except Exception as e:
        logger.warning("Could not parse OCR result: %s", e)

    return texts, scores


# ===========================================================================
# DocumentOCR  — public engine class
# ===========================================================================

class DocumentOCR:
    """
    Process any supported document and return structured extraction results.

    Parameters
    ----------
    use_gpu : bool
        Enable GPU acceleration (requires paddlepaddle-gpu).
    force_handwriting : bool
        Always use handwriting-optimised mode, skip auto-detection.
    """

    def __init__(self, use_gpu: bool = False, force_handwriting: bool = False):
        self.use_gpu           = use_gpu
        self.force_handwriting = force_handwriting

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def process(self, file_path: str | Path) -> dict[str, Any]:
        """
        Run OCR on *file_path* and return:

        {
          "file":                 str,
          "file_type":            "pdf" | "image",
          "page_count":           int,
          "raw_text":             str,
          "confidence":           float,       # 0–1 average
          "is_handwritten":       bool,
          "fields":               { ... },     # regex-extracted fields
          "department_suggestion":{ ... }      # scored department
        }
        """
        path   = Path(file_path)
        suffix = path.suffix.lower()

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if suffix not in ALL_EXTENSIONS:
            raise ValueError(
                f"Unsupported extension '{suffix}'. "
                f"Supported: {sorted(ALL_EXTENSIONS)}"
            )

        file_type   = "pdf" if suffix in PDF_EXTENSIONS else "image"
        print(f"\n[OCR ENGINE] Processing: {path.name} ({file_type.upper()})", flush=True)
        pages_data  = self._extract_pages(path, handwriting=self.force_handwriting)

        # Aggregate
        raw_text, avg_conf = self._aggregate(pages_data)

        # Auto-detect handwriting based on confidence
        is_handwritten = self.force_handwriting or (
            avg_conf < HANDWRITING_CONFIDENCE_THRESHOLD
        )

        # If auto-detected as handwriting, re-run with HW settings
        if is_handwritten and not self.force_handwriting:
            logger.info(
                "Low confidence %.2f — re-processing in handwriting mode.", avg_conf
            )
            print(f"[OCR ENGINE] Low confidence ({avg_conf*100:.1f}%) — re-running with handwriting model...", flush=True)
            pages_data = self._extract_pages(path, handwriting=True)
            raw_text, avg_conf = self._aggregate(pages_data)

        fields = self._extract_fields(raw_text)
        dept   = self._suggest_department(raw_text)

        print(f"[OCR ENGINE] Done: {len(pages_data)} page(s) | Confidence: {avg_conf*100:.1f}% | Raw Text: {len(raw_text)} chars", flush=True)

        return {
            "file":                  str(path.resolve()),
            "file_type":             file_type,
            "page_count":            len(pages_data),
            "raw_text":              raw_text,
            "confidence":            round(avg_conf, 4),
            "is_handwritten":        is_handwritten,
            "fields":                fields,
            "department_suggestion": dept,
        }

    # -----------------------------------------------------------------------
    # Page extraction dispatcher
    # -----------------------------------------------------------------------

    def _extract_pages(
        self, path: Path, handwriting: bool = False
    ) -> list[dict]:
        if path.suffix.lower() in PDF_EXTENSIONS:
            return self._process_pdf(path, handwriting=handwriting)
        return self._process_image(path, handwriting=handwriting)

    # -----------------------------------------------------------------------
    # PDF processing  (PyMuPDF)
    # -----------------------------------------------------------------------

    def _process_pdf(self, path: Path, handwriting: bool = False) -> list[dict]:
        try:
            import fitz
        except ImportError as exc:
            raise ImportError(
                "PyMuPDF is not installed. Run: pip install PyMuPDF\n"
            ) from exc

        results = []
        doc     = fitz.open(str(path))

        for page_num, page in enumerate(doc):
            # Check if this page contains embedded digital text
            digital_text = page.get_text().strip()
            if len(digital_text) >= 40 and not handwriting:
                # Digital PDF Page -> extract directly via PyMuPDF
                results.append({
                    "text":        digital_text,
                    "confidences": [0.98] * max(1, len(digital_text.splitlines())),
                    "page":        page_num + 1,
                })
                continue

            # Scanned / Image Page -> Rasterize at 300 DPI and run PaddleOCR
            mat      = fitz.Matrix(300 / 72, 300 / 72)   # 300 DPI
            pix      = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            img_arr  = np.frombuffer(pix.samples, dtype=np.uint8)
            img_cv   = img_arr.reshape(pix.height, pix.width, 3)
            img_cv   = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)

            if handwriting:
                img_cv = self._preprocess_for_handwriting(img_cv)

            page_res           = self._run_paddle(img_cv, handwriting=handwriting)
            page_res["page"]   = page_num + 1
            results.append(page_res)

        doc.close()
        return results

    # -----------------------------------------------------------------------
    # Image processing
    # -----------------------------------------------------------------------

    def _process_image(self, path: Path, handwriting: bool = False) -> list[dict]:
        img_cv = cv2.imread(str(path))
        if img_cv is None:
            # Fallback for exotic formats (TIFF, WEBP …)
            pil  = Image.open(path).convert("RGB")
            img_cv = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

        if handwriting:
            img_cv = self._preprocess_for_handwriting(img_cv)

        page_res         = self._run_paddle(img_cv, handwriting=handwriting)
        page_res["page"] = 1
        return [page_res]

    # -----------------------------------------------------------------------
    # PaddleOCR v3 inference
    # -----------------------------------------------------------------------

    def _run_paddle(
        self, img_cv: np.ndarray, handwriting: bool = False
    ) -> dict:
        """Pass a BGR numpy image to PaddleOCR; return text + confidence list."""
        ocr = _get_ocr(handwriting=handwriting)
        results = None

        # Standard PaddleOCR uses .ocr(img, cls=True)
        if hasattr(ocr, "ocr"):
            try:
                results = ocr.ocr(img_cv, cls=True)
            except TypeError:
                results = ocr.ocr(img_cv)
            except Exception as ex:
                logger.warning("PaddleOCR.ocr execution error: %s", ex)
                results = None
        elif hasattr(ocr, "predict"):
            results = ocr.predict(img_cv)
        elif callable(ocr):
            results = ocr(img_cv)

        all_texts:  list[str]   = []
        all_scores: list[float] = []

        if results:
            # If results is a list of pages (standard for .ocr()), parse each item
            if isinstance(results, list):
                for res in results:
                    texts, scores = _parse_ocr_result(res)
                    all_texts.extend(texts)
                    all_scores.extend(scores)
            else:
                texts, scores = _parse_ocr_result(results)
                all_texts.extend(texts)
                all_scores.extend(scores)

        return {
            "text":        "\n".join(all_texts),
            "confidences": all_scores,
        }

    # -----------------------------------------------------------------------
    # Text aggregation
    # -----------------------------------------------------------------------

    @staticmethod
    def _aggregate(pages: list[dict]) -> tuple[str, float]:
        all_parts  = [p["text"] for p in pages]
        all_scores = [s for p in pages for s in p["confidences"]]
        raw_text   = "\n".join(all_parts).strip()
        avg_conf   = float(np.mean(all_scores)) if all_scores else 0.0
        return raw_text, avg_conf

    # -----------------------------------------------------------------------
    # Handwriting image pre-processing
    # -----------------------------------------------------------------------

    def _preprocess_for_handwriting(self, img: np.ndarray) -> np.ndarray:
        """
        Enhance image quality for handwriting OCR:
          1. Grayscale
          2. CLAHE contrast enhancement
          3. Non-local means denoising
          4. Adaptive thresholding (binarise)
          5. Auto-deskew
        """
        # 1. Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 2. Contrast  — Contrast Limited Adaptive Histogram Equalisation
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray  = clahe.apply(gray)

        # 3. Denoise
        gray = cv2.fastNlMeansDenoising(gray, h=10)

        # 4. Adaptive threshold (binarise)
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=15, C=8,
        )

        # 5. Deskew
        binary = self._deskew(binary)

        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    @staticmethod
    def _deskew(img: np.ndarray) -> np.ndarray:
        """Auto-rotate a binary image to correct tilt using minAreaRect."""
        coords = np.column_stack(np.where(img > 0))
        if coords.shape[0] < 5:
            return img
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M      = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            img, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

    # -----------------------------------------------------------------------
    # Field extraction  (rules.py FIELD_PATTERNS)
    # -----------------------------------------------------------------------

    def _extract_fields(self, text: str) -> dict[str, Any]:
        """Apply all FIELD_PATTERNS from rules.py to *text*."""
        if len(text) < MIN_TEXT_LENGTH_FOR_EXTRACTION:
            return {}

        extracted: dict[str, Any] = {}

        for field, patterns in FIELD_PATTERNS.items():
            if field == "designation":
                # Collect ALL designation matches
                found: list[str] = []
                for pat in patterns:
                    for m in re.finditer(pat, text, re.IGNORECASE):
                        val = m.group("val").strip()
                        if val and val not in found:
                            found.append(val)
                if found:
                    extracted[field] = found
            else:
                # First match wins
                for pat in patterns:
                    try:
                        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
                    except re.error as e:
                        logger.warning("Bad regex pattern in rules.py [%s]: %s", field, e)
                        continue
                    if m:
                        try:
                            val = m.group("val").strip()
                        except IndexError:
                            val = m.group(0).strip()
                        if val:
                            extracted[field] = val
                            break

        # Normalise document_type
        if "document_type" in extracted:
            raw = extracted["document_type"].lower().strip()
            for key, canonical in DOCUMENT_TYPE_CANONICAL.items():
                if key in raw:
                    extracted["document_type"] = canonical
                    break

        return extracted

    # -----------------------------------------------------------------------
    # Department suggestion  (rules.py DEPARTMENT_KEYWORDS)
    # -----------------------------------------------------------------------

    def _suggest_department(self, text: str) -> dict[str, Any]:
        """Score each department against *text* using keyword + weight rules."""
        if len(text) < MIN_TEXT_LENGTH_FOR_EXTRACTION:
            return {"suggested": None, "confidence": 0.0, "scores": {}}

        text_lower = text.lower()
        scores: dict[str, float] = {}

        for dept, keywords in DEPARTMENT_KEYWORDS.items():
            dept_score = 0.0
            for kw in keywords:
                count = len(re.findall(re.escape(kw), text_lower))
                if count:
                    weight      = DEPARTMENT_SCORE_WEIGHTS.get(kw, 1.0)
                    dept_score += count * weight
            if dept_score > 0:
                scores[dept] = round(dept_score, 2)

        if not scores:
            return {"suggested": None, "confidence": 0.0, "scores": {}}

        sorted_scores = dict(
            sorted(scores.items(), key=lambda x: x[1], reverse=True)
        )
        top_dept   = next(iter(sorted_scores))
        top_score  = sorted_scores[top_dept]
        total      = sum(sorted_scores.values())
        confidence = round(top_score / total, 4) if total else 0.0

        return {
            "suggested":  top_dept,
            "confidence": confidence,
            "scores":     sorted_scores,
        }
