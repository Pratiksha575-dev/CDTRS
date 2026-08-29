# CDTRS OCR fineTune — Offline Handwritten OCR Fine-Tuning System

## Overview

OCR/fineTune/ is a **fully offline** handwritten OCR fine-tuning system built
on top of the existing CDTRS PaddleOCR engine.

It lets you:
- Add your own handwritten document images + ground-truth labels
- Fine-tune a CRNN recognition model on those images — completely offline
- Add more data later and fine-tune again without losing previous models
- Run offline inference using either the fine-tuned model or the original PaddleOCR

---

## Current OCR Model

The existing CDTRS project uses:

| Component | Detail |
|---|---|
| Engine | PaddleOCR v3.x |
| Package | paddleocr==2.8.1 + paddlepaddle==2.6.2 |
| Core class | OCR/ocr.py → DocumentOCR |
| Handwriting detection | Auto-detects via confidence threshold (0.72); re-runs in HW mode |
| Preprocessing | CLAHE → Denoise → Adaptive Threshold → Deskew |

The existing OCR/ocr.py, OCR/rules.py, OCR/main.py, and OCR/__init__.py
are **completely untouched** by this system.

---

## Architecture

`
OCR/
├── ocr.py          ← EXISTING engine (unchanged)
├── rules.py        ← EXISTING rules (unchanged)
└── fineTune/
    ├── config.py          ← all configuration
    ├── prepare_dataset.py ← validate + split dataset
    ├── train.py           ← fine-tune CRNN model
    ├── evaluate.py        ← CER / WER evaluation
    ├── inference.py       ← offline inference CLI
    ├── model_manager.py   ← versioned local model management
    ├── download_models.py ← ONE-TIME internet setup only
    ├── utils/
    │   ├── preprocessing.py  ← image enhancement pipeline
    │   ├── metrics.py        ← CER / WER calculation
    │   └── dataset.py        ← PaddlePaddle Dataset class
    ├── dataset/
    │   ├── images/           ← your handwritten images go here
    │   ├── labels/           ← matching .txt ground-truth labels
    │   └── splits/           ← auto-generated train/val/test splits
    └── models/
        ├── original/         ← PP-OCRv3 base weights (downloaded once)
        ├── handwritten_v1/   ← first fine-tuned checkpoint
        ├── handwritten_v2/   ← second fine-tuned checkpoint
        └── ...
`

### Fine-Tuning Architecture

`
PP-OCRv3 Detection (finds text boxes)
          +
  Fine-tuned CRNN Recognition
  (MobileNet CNN → BiLSTM → CTC)
          +
    CTC Greedy Decoder
          ↓
  Recognized handwritten text
`

The **detection** model (finding where text is on the page) stays as the
original PP-OCRv3 det model. Only the **recognition** component (reading what
the text says) is fine-tuned — this is where handwriting accuracy improves.

---

## Offline Requirement

After the one-time download_models.py step, **no internet connection is needed**.

All of the following work completely offline:
- Adding handwritten datasets
- Dataset validation and splitting
- Training and fine-tuning
- Evaluation (CER/WER)
- Model saving and loading
- OCR inference

The CRNN model architecture is implemented entirely in PaddlePaddle —
no Hugging Face, no cloud API, no remote model repository.

---

## Dataset Format

See dataset/README.md for complete details.

**Quick summary:**

`
dataset/
├── images/
│   ├── page001.png      ← handwritten image
│   ├── page002.jpg
│   └── ...
└── labels/
    ├── page001.txt      ← ground-truth text for page001.png
    ├── page002.txt      ← ground-truth text for page002.jpg
    └── ...
`

Each .txt label file contains the exact handwritten text from the image
(UTF-8, plain text, no special formatting required).

---

## Step-by-Step Workflow

### First-Time Setup (internet needed once)

`ash
cd OCR/fineTune

# Download PP-OCRv3 base model weights (one-time, ~12 MB)
python download_models.py
`

### Adding Handwritten Data

`
1. Copy your handwritten images to:   dataset/images/
2. Create matching label files in:    dataset/labels/
   (same filename stem, .txt extension, contains the handwritten text)
`

### Dataset Preparation

`ash
python prepare_dataset.py
`

This will:
- Discover all images and labels
- Validate them
- Build the character vocabulary
- Create train/val/test split files in dataset/splits/
- Save dataset/dataset_manifest.json with statistics

### Fine-Tuning

`ash
python train.py
`

First run: starts from models/original/ (PP-OCRv3 base weights)
Later runs: auto-detects the latest fine-tuned model and continues from it

To override:
`ash
python train.py --base original        # force start from original
python train.py --base handwritten_v1  # start from a specific version
python train.py --epochs 30            # change epoch count
`

### Evaluation

`ash
python evaluate.py                     # evaluate latest fine-tuned model
python evaluate.py --model handwritten_v1  # evaluate specific version
python evaluate.py --compare           # compare fine-tuned vs original
`

Saves results to evaluation_results.json.

### Inference

`ash
python inference.py --input path/to/handwritten_image.png
python inference.py --input scan.pdf --model original
python inference.py --input note.jpg --model latest
python inference.py --input note.jpg --model handwritten_v2 --verbose
python inference.py --list-models     # show all saved versions
`

---

## Adding New Data Later (Incremental Fine-Tuning)

This is the core design of the system. You can add new data at any time,
while completely offline, and fine-tune again:

`
STEP 1: Add new images + labels
  dataset/images/new_page_001.png
  dataset/labels/new_page_001.txt

STEP 2: Re-run dataset preparation (discovers all data, new + old)
  python prepare_dataset.py

STEP 3: Fine-tune again (auto-continues from latest model)
  python train.py
  → Saves models/handwritten_v2/

STEP 4: Evaluate the new model
  python evaluate.py

STEP 5: Use for inference
  python inference.py --input your_image.png --model latest
`

---

## Model Versioning

Models are stored locally in models/:

`
models/
├── original/               ← PP-OCRv3 base weights (never overwritten)
│   └── (PaddleOCR files)
├── handwritten_v1/         ← first fine-tuning run
│   ├── handwritten_rec.pdparams
│   ├── vocab.txt
│   └── model_metadata.json
├── handwritten_v2/         ← second fine-tuning run (new data added)
│   ├── handwritten_rec.pdparams
│   ├── vocab.txt
│   └── model_metadata.json
└── ...
`

Each model_metadata.json records:
- Version name
- Base model used for this training
- Training date and time
- Number of epochs
- Val CER and Val WER at best epoch
- Number of training/validation samples
- Vocabulary size
- All training hyperparameters
- Full per-epoch history

To list all saved versions:
`ash
python model_manager.py
`

---

## Re-Training / Fine-Tuning Strategy

**Scenario A: New data only (incremental)**
`
handwritten_v1  +  new_data  →  train.py  →  handwritten_v2
`
Auto-detected. Just run python train.py.

**Scenario B: Retrain from original (if v1 degraded)**
`
original  +  all_data  →  train.py --base original  →  handwritten_v2
`

**Scenario C: Restart from a specific version**
`
handwritten_v1  +  all_data  →  train.py --base handwritten_v1  →  handwritten_v2
`

---

## Catastrophic Forgetting

The fine-tuned model only replaces the **recognition** component.
The original **detection** model is always used.

To prevent degradation on printed text:
- Mix printed document images into your dataset/images/ folder
- The model will learn both printed and handwritten text
- Previous fine-tuned checkpoints are always preserved — you can roll back

---

## Offline Dependencies

Everything required after download_models.py:

| Package | Purpose | Already in requirements.txt? |
|---|---|---|
| paddlepaddle==2.6.2 | Training framework | YES |
| paddleocr==2.8.1 | Detection model | YES |
| opencv-python==4.10.0.84 | Image processing | YES |
| Pillow==10.4.0 | Image loading | YES |
| 
umpy==1.26.4 | Array operations | YES |
| scikit-image==0.24.0 | Image utilities | YES |

No additional packages need to be installed.

---

## Configuration

All settings are in config.py. Key parameters:

| Setting | Default | Description |
|---|---|---|
| DEVICE | "cpu" | "cpu" or "gpu" |
| EPOCHS | 50 | Training epochs |
| BATCH_SIZE | 16 | Reduce to 8 if RAM is limited |
| LEARNING_RATE |  .0005 | Initial learning rate |
| TRAIN_RATIO |  .70 | 70% of data for training |
| VAL_RATIO |  .15 | 15% for validation |
| TEST_RATIO |  .15 | 15% for evaluation |
| IMG_HEIGHT | 32 | CRNN input height (px) |
| IMG_MAX_WIDTH | 320 | Max padded width (px) |

---

## Limitations

1. **Single-line recognition**: The CRNN model recognizes one text line at a time.
   Multi-line pages use PaddleOCR's detector to split into lines first.

2. **Language**: Currently configured for English (lang="en"). For other
   languages, update PRINT_CONFIG and HANDWRITING_CONFIG in OCR/rules.py
   and set lang accordingly in config.py.

3. **First run**: download_models.py requires a one-time internet connection.
   After that, everything is offline.

4. **GPU**: GPU training requires paddlepaddle-gpu instead of paddlepaddle.
   CPU training works with the existing equirements.txt.
   Change DEVICE = "gpu" in config.py if you have a CUDA GPU.

5. **Minimum dataset size**: At least a few dozen image-label pairs are needed
   for meaningful fine-tuning. More data = better accuracy.
