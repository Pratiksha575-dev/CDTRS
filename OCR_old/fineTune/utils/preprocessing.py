"""
=============================================================================
CDTRS OCR fineTune — utils/preprocessing.py
=============================================================================
Image preprocessing pipeline for handwritten OCR recognition.
Mirrors the preprocessing in OCR/ocr.py but adapted for fixed-height
CRNN input crops (IMG_HEIGHT x variable_width).

All operations are purely local — no internet required.
=============================================================================
"""

from __future__ import annotations
import sys
from pathlib import Path

# Ensure fineTune package is importable when run standalone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np
from PIL import Image

import config as cfg


def load_image(image_path: str | Path) -> np.ndarray:
    """
    Load any supported image file as a BGR numpy array.
    Fallback to PIL for exotic formats (TIFF, WEBP ...).
    """
    path = Path(image_path)
    img = cv2.imread(str(path))
    if img is None:
        pil = Image.open(path).convert("RGB")
        img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    return img


def enhance_for_handwriting(img: np.ndarray) -> np.ndarray:
    """
    Apply handwriting-specific enhancement to a BGR image:
      1. Grayscale
      2. CLAHE contrast enhancement
      3. Non-local means denoising
      4. Adaptive Gaussian thresholding (binarise)
      5. Auto-deskew
    Returns a BGR image suitable for PaddleOCR / CRNN input.
    """
    # 1. Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2. CLAHE contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray  = clahe.apply(gray)

    # 3. Denoise
    gray = cv2.fastNlMeansDenoising(gray, h=10)

    # 4. Adaptive thresholding
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=15, C=8,
    )

    # 5. Deskew
    binary = _deskew(binary)

    return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)


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
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        img, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def resize_for_crnn(img: np.ndarray,
                    target_height: int = cfg.IMG_HEIGHT,
                    max_width: int = cfg.IMG_MAX_WIDTH) -> np.ndarray:
    """
    Resize image to a fixed height while keeping aspect ratio,
    then pad to max_width with white (255) on the right.

    Returns a float32 numpy array normalised to [0, 1]
    of shape (target_height, max_width, 3).
    """
    h, w = img.shape[:2]
    scale = target_height / h
    new_w = min(int(w * scale), max_width)
    resized = cv2.resize(img, (new_w, target_height), interpolation=cv2.INTER_LINEAR)

    # Pad width to max_width
    padded = np.full((target_height, max_width, 3), 255, dtype=np.uint8)
    padded[:, :new_w, :] = resized

    # Normalise to [0, 1] float32
    return padded.astype(np.float32) / 255.0


def preprocess_image(image_path: str | Path,
                     enhance: bool = True) -> np.ndarray:
    """
    Full preprocessing pipeline for a single image:
      load → (optional) enhance → resize/normalise → float32 array

    Returns shape: (target_height, max_width, 3) float32 [0,1]
    """
    img = load_image(image_path)
    if enhance:
        img = enhance_for_handwriting(img)
    return resize_for_crnn(img)
