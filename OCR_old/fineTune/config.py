"""
=============================================================================
CDTRS OCR fineTune — config.py
=============================================================================
All paths and training hyperparameters are defined here.
Edit this file to change dataset locations, model paths, or training settings.

OFFLINE: No internet connection is needed after the initial model download.
         If DEVICE = "gpu", requires paddlepaddle-gpu; CPU works out of the box.
=============================================================================
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Base paths  (all relative to this file — stay inside OCR/fineTune/)
# ---------------------------------------------------------------------------

FINETUNE_DIR  = Path(__file__).resolve().parent          # OCR/fineTune/
DATASET_DIR   = FINETUNE_DIR / "dataset"
MODELS_DIR    = FINETUNE_DIR / "models"
SPLITS_DIR    = DATASET_DIR  / "splits"
IMAGES_DIR    = DATASET_DIR  / "images"
LABELS_DIR    = DATASET_DIR  / "labels"

# PDF source folder — put handwritten PDF files here for auto-conversion
PDFS_DIR      = DATASET_DIR  / "pdfs"

# DPI used when rendering PDF pages to images (higher = better quality, larger files)
PDF_RENDER_DPI = 300

# ---------------------------------------------------------------------------
# Model paths
# ---------------------------------------------------------------------------

# Original (pre-trained) PP-OCRv3 recognition model — downloaded once offline
ORIGINAL_MODEL_DIR = MODELS_DIR / "original"

# Where fine-tuned models are saved (versioned automatically)
TRAINED_MODELS_DIR = MODELS_DIR   # handwritten_v1, handwritten_v2, ...

# Model filename prefix used inside each version folder
MODEL_FILENAME = "handwritten_rec.pdparams"   # PaddlePaddle params file
VOCAB_FILENAME = "vocab.txt"                  # character vocabulary

# ---------------------------------------------------------------------------
# Dataset configuration
# ---------------------------------------------------------------------------

# Supported image extensions (lower-case)
SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}

# Train / Validation / Test split ratios (must sum to 1.0)
TRAIN_RATIO = 0.70
VAL_RATIO   = 0.15
TEST_RATIO  = 0.15

# Minimum label length to accept a sample (reject blank labels)
MIN_LABEL_LENGTH = 1

# Maximum label length (samples with longer labels are skipped)
MAX_LABEL_LENGTH = 100

# Random seed for reproducible splits
SPLIT_SEED = 42

# ---------------------------------------------------------------------------
# Image preprocessing for recognition (CRNN input)
# ---------------------------------------------------------------------------

# Height all images are resized to (PP-OCRv3 rec uses 32px height crops)
IMG_HEIGHT = 32

# Maximum width for padded batches
IMG_MAX_WIDTH = 320

# ---------------------------------------------------------------------------
# Training hyperparameters
# ---------------------------------------------------------------------------

# "cpu" or "gpu"  (gpu requires paddlepaddle-gpu)
DEVICE = "cpu"

# Number of training epochs
EPOCHS = 50

# Mini-batch size (reduce to 8 if running on CPU with limited RAM)
BATCH_SIZE = 16

# Initial learning rate
LEARNING_RATE = 0.0005

# Learning rate decay factor applied every LR_DECAY_EPOCHS epochs
LR_DECAY_FACTOR = 0.5
LR_DECAY_EPOCHS = 20

# DataLoader workers (0 = main thread; safest on Windows)
NUM_WORKERS = 0

# Save checkpoint every N epochs (in addition to best-val checkpoint)
CHECKPOINT_EVERY_N_EPOCHS = 10

# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

# Where evaluation results JSON is saved
EVAL_RESULTS_FILE = FINETUNE_DIR / "evaluation_results.json"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_FILE = FINETUNE_DIR / "training.log"

# ---------------------------------------------------------------------------
# Character vocabulary
# ---------------------------------------------------------------------------
# Built from training labels at prepare_dataset time.
# Saved to SPLITS_DIR/vocab.txt; loaded during training/inference.

BLANK_TOKEN   = "<blank>"   # CTC blank (index 0)
UNKNOWN_TOKEN = "<unk>"     # Unknown character

# ---------------------------------------------------------------------------
# Model architecture (CRNN)
# ---------------------------------------------------------------------------

# Backbone: "mobilenet" (faster, lighter) or "resnet" (more accurate, heavier)
BACKBONE = "mobilenet"

# RNN hidden size
RNN_HIDDEN = 256

# Number of RNN layers
RNN_LAYERS = 2
