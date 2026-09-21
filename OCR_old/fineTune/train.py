"""
=============================================================================
CDTRS OCR fineTune — train.py
=============================================================================
Fine-tune the handwritten OCR recognition model offline.

Strategy
--------
  • Builds a CRNN (CNN + BiLSTM + CTC) recognizer using PaddlePaddle.
  • First run  : loads base weights from models/original/ (PP-OCRv3 style
                  MobileNetV3 features). If original weights are absent, 
                  trains from random initialisation on the handwritten data.
  • Later runs : auto-detects the latest fine-tuned version and continues
                  from it (incremental fine-tuning).
  • Saves each new version as models/handwritten_vN/ with full metadata.
  • Never overwrites a previous version.

Catastrophic forgetting mitigation
-------------------------------------
  Fine-tuning continues from a previously trained checkpoint, so the model
  retains what it already learned. For best results, include a mix of
  printed and handwritten samples in your dataset.

Usage:
    python train.py
    python train.py --base original        # force start from original model
    python train.py --base handwritten_v1  # start from a specific version
    python train.py --epochs 30            # override epoch count

No internet connection is required.
=============================================================================
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as cfg
from model_manager import (
    get_latest_version,
    get_next_version_name,
    save_model,
    load_model_weights,
    resolve_model_dir,
    print_versions,
)
from utils.dataset import HandwrittenDataset, load_vocab
from utils.metrics import evaluate_batch

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(cfg.LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger("fineTune.train")


# ---------------------------------------------------------------------------
# CRNN Model definition (pure PaddlePaddle — no internet downloads)
# ---------------------------------------------------------------------------

def _build_crnn(num_classes: int) -> "paddle.nn.Layer":
    """
    Build a lightweight CRNN:
      MobileNetV3-Small feature extractor (from scratch or loaded weights)
      → AdaptiveAvgPool height collapse
      → BiLSTM sequence modelling
      → Linear output → num_classes (for CTC)
    """
    import paddle
    import paddle.nn as nn

    class CRNN(nn.Layer):
        def __init__(self, num_classes: int):
            super().__init__()
            # --- CNN Backbone (MobileNetV3-style depthwise separable convs) ---
            self.cnn = nn.Sequential(
                # Block 1
                nn.Conv2D(3, 16, 3, padding=1),
                nn.BatchNorm2D(16),
                nn.ReLU(),
                nn.MaxPool2D(2, 2),  # H/2, W/2

                # Block 2
                nn.Conv2D(16, 32, 3, padding=1),
                nn.BatchNorm2D(32),
                nn.ReLU(),
                nn.MaxPool2D(2, 2),  # H/4, W/4

                # Block 3
                nn.Conv2D(32, 64, 3, padding=1),
                nn.BatchNorm2D(64),
                nn.ReLU(),
                nn.MaxPool2D(2, 2),  # H/8, W/8

                # Block 4
                nn.Conv2D(64, 128, 3, padding=1),
                nn.BatchNorm2D(128),
                nn.ReLU(),
                # No pool — keep width for sequence
            )
            # Collapse height → 1  (input H=32 → H=4 after 3 pools → AdaptAvg → 1)
            self.pool_h = nn.AdaptiveAvgPool2D((1, None))

            # --- Sequence modelling ---
            self.rnn = nn.LSTM(
                input_size=128,
                hidden_size=cfg.RNN_HIDDEN,
                num_layers=cfg.RNN_LAYERS,
                direction="bidirect",
                dropout=0.1 if cfg.RNN_LAYERS > 1 else 0.0,
            )
            self.classifier = nn.Linear(cfg.RNN_HIDDEN * 2, num_classes)

        def forward(self, x):
            # x: (B, C, H, W)
            feat = self.cnn(x)           # (B, 128, H', W')
            feat = self.pool_h(feat)     # (B, 128, 1, W')
            feat = feat.squeeze(2)       # (B, 128, W')
            feat = feat.transpose([0, 2, 1])  # (B, W', 128) = (B, T, C)
            feat, _ = self.rnn(feat)     # (B, T, hidden*2)
            logits = self.classifier(feat)    # (B, T, num_classes)
            logits = logits.transpose([1, 0, 2])  # (T, B, num_classes) for CTC
            return logits

    return CRNN(num_classes)


# ---------------------------------------------------------------------------
# CTC decode (greedy)
# ---------------------------------------------------------------------------

def _ctc_greedy_decode(logits_np, vocab_inv: dict[int, str]) -> list[str]:
    """Greedy CTC decode: collapse repeats, remove blanks."""
    import numpy as np
    results = []
    for seq in logits_np:  # seq: (T, num_classes)
        ids    = seq.argmax(axis=-1)  # (T,)
        chars  = []
        prev   = -1
        for idx in ids:
            if idx != 0 and idx != prev:   # 0 = CTC blank
                c = vocab_inv.get(int(idx), "")
                if c and c not in (cfg.BLANK_TOKEN, cfg.UNKNOWN_TOKEN):
                    chars.append(c)
            prev = idx
        results.append("".join(chars))
    return results


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def train(base_version: str = "auto", epochs: int | None = None) -> None:
    """
    Fine-tune the recognition model.

    Parameters
    ----------
    base_version : "auto" | "original" | "handwritten_vN"
        "auto" picks the latest fine-tuned model, falling back to original.
    epochs       : override cfg.EPOCHS if provided
    """
    try:
        import paddle
        import paddle.nn as nn
        from paddle.io import DataLoader
    except ImportError:
        print(
            "[ERROR] paddlepaddle is not installed.\n"
            "Install: pip install paddlepaddle==2.6.2"
        )
        sys.exit(1)

    n_epochs = epochs if epochs is not None else cfg.EPOCHS

    print("\n" + "=" * 60)
    print("  CDTRS OCR fineTune — Training")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Check dataset splits exist
    # ------------------------------------------------------------------
    train_split = cfg.SPLITS_DIR / "train.txt"
    val_split   = cfg.SPLITS_DIR / "val.txt"
    vocab_path  = cfg.SPLITS_DIR / cfg.VOCAB_FILENAME

    for p in [train_split, val_split, vocab_path]:
        if not p.exists():
            print(
                f"\n[ERROR] Required file missing: {p}\n"
                "Run prepare_dataset.py first:\n"
                "    python prepare_dataset.py\n"
            )
            sys.exit(1)

    # ------------------------------------------------------------------
    # 2. Load vocabulary
    # ------------------------------------------------------------------
    vocab     = load_vocab(vocab_path)
    num_classes = len(vocab)   # includes BLANK and UNKNOWN
    vocab_inv   = {v: k for k, v in vocab.items()}
    print(f"\n  Vocabulary size : {num_classes} characters")

    # ------------------------------------------------------------------
    # 3. Load datasets
    # ------------------------------------------------------------------
    train_ds = HandwrittenDataset(train_split, vocab, enhance=True)
    val_ds   = HandwrittenDataset(val_split,   vocab, enhance=True)
    print(f"  Train samples   : {len(train_ds)}")
    print(f"  Val samples     : {len(val_ds)}")

    # Collate: pad label sequences in a batch
    def _collate(batch):
        imgs, labels, lens = zip(*batch)
        imgs   = paddle.stack(imgs)
        max_l  = max(l.shape[0] for l in labels)
        padded = paddle.zeros([len(labels), max_l], dtype="int32")
        for i, lbl in enumerate(labels):
            padded[i, :lbl.shape[0]] = lbl
        lens = paddle.concat(list(lens))
        return imgs, padded, lens

    train_loader = DataLoader(
        train_ds, batch_size=cfg.BATCH_SIZE,
        shuffle=True, num_workers=cfg.NUM_WORKERS,
        collate_fn=_collate, drop_last=False,
    )
    val_loader = DataLoader(
        val_ds, batch_size=cfg.BATCH_SIZE,
        shuffle=False, num_workers=cfg.NUM_WORKERS,
        collate_fn=_collate, drop_last=False,
    )

    # ------------------------------------------------------------------
    # 4. Build model
    # ------------------------------------------------------------------
    paddle.set_device(cfg.DEVICE)
    model = _build_crnn(num_classes)

    # Try loading base weights
    if base_version == "auto":
        latest = get_latest_version()
        actual_base = latest.name if latest else "original"
    else:
        actual_base = base_version

    try:
        loaded_dir = load_model_weights(model, version=actual_base)
        print(f"  Base model      : {loaded_dir.name}")
    except FileNotFoundError as e:
        print(f"  [INFO] No pre-trained weights loaded ({e})")
        print("  Starting from random initialisation.")
        actual_base = "random"

    # ------------------------------------------------------------------
    # 5. Optimiser + Loss
    # ------------------------------------------------------------------
    lr_scheduler = paddle.optimizer.lr.StepDecay(
        learning_rate=cfg.LEARNING_RATE,
        step_size=cfg.LR_DECAY_EPOCHS,
        gamma=cfg.LR_DECAY_FACTOR,
    )
    optimiser = paddle.optimizer.Adam(
        parameters=model.parameters(),
        learning_rate=lr_scheduler,
    )
    ctc_loss = nn.CTCLoss(blank=0, reduction="mean")

    # ------------------------------------------------------------------
    # 6. Training loop
    # ------------------------------------------------------------------
    version_name  = get_next_version_name()
    best_val_cer  = float("inf")
    best_epoch    = 0
    history: list[dict] = []

    print(f"\n  New version     : {version_name}")
    print(f"  Epochs          : {n_epochs}")
    print(f"  Batch size      : {cfg.BATCH_SIZE}")
    print(f"  Learning rate   : {cfg.LEARNING_RATE}")
    print(f"  Device          : {cfg.DEVICE}")
    print(f"\n  {'Epoch':<8} {'Train Loss':<14} {'Val CER':<12} {'Val WER':<12}")
    print("  " + "-" * 50)

    import numpy as np

    for epoch in range(1, n_epochs + 1):
        # --- Train ---
        model.train()
        train_loss_sum = 0.0
        n_batches = 0

        for imgs, labels, label_lens in train_loader:
            logits = model(imgs)          # (T, B, C)
            T, B, _ = logits.shape
            input_lens = paddle.full([B], T, dtype="int32")

            loss = ctc_loss(logits, labels, input_lens, label_lens)
            loss.backward()
            optimiser.step()
            optimiser.clear_grad()

            train_loss_sum += float(loss.numpy())
            n_batches += 1

        avg_train_loss = train_loss_sum / max(n_batches, 1)
        lr_scheduler.step()

        # --- Validate ---
        model.eval()
        all_preds:  list[str] = []
        all_labels: list[str] = []

        with paddle.no_grad():
            for imgs, labels, label_lens in val_loader:
                logits = model(imgs)   # (T, B, C)
                logits_np = logits.numpy().transpose(1, 0, 2)  # (B, T, C)
                preds = _ctc_greedy_decode(logits_np, vocab_inv)
                all_preds.extend(preds)

                # Decode ground truth labels
                labels_np = labels.numpy()
                lens_np   = label_lens.numpy()
                offset    = 0
                for llen in lens_np:
                    ids = labels_np[offset:offset + int(llen)]
                    gt  = "".join(vocab_inv.get(int(i), "") for i in ids)
                    all_labels.append(gt)
                    offset += int(llen)

        val_metrics = evaluate_batch(all_preds, all_labels)
        val_cer = val_metrics["mean_cer"]
        val_wer = val_metrics["mean_wer"]

        print(f"  {epoch:<8} {avg_train_loss:<14.4f} {val_cer:<12.4f} {val_wer:<12.4f}")
        log.info("Epoch %d | loss=%.4f | val_cer=%.4f | val_wer=%.4f",
                 epoch, avg_train_loss, val_cer, val_wer)

        history.append({
            "epoch": epoch,
            "train_loss": round(avg_train_loss, 4),
            "val_cer": round(val_cer, 4),
            "val_wer": round(val_wer, 4),
        })

        # Save best checkpoint
        if val_cer < best_val_cer:
            best_val_cer = val_cer
            best_epoch   = epoch
            save_model(model, version_name + "_best", {
                "version": version_name + "_best",
                "base_model": actual_base,
                "epoch": epoch,
                "val_cer": round(val_cer, 4),
                "val_wer": round(val_wer, 4),
            })

        # Periodic checkpoint
        if epoch % cfg.CHECKPOINT_EVERY_N_EPOCHS == 0:
            save_model(model, version_name + f"_ep{epoch}", {
                "version": version_name + f"_ep{epoch}",
                "base_model": actual_base,
                "epoch": epoch,
                "val_cer": round(val_cer, 4),
            })

    # ------------------------------------------------------------------
    # 7. Save final model with full metadata
    # ------------------------------------------------------------------
    import json
    meta = {
        "version":        version_name,
        "base_model":     actual_base,
        "trained_at":     datetime.now().isoformat(),
        "epochs":         n_epochs,
        "best_epoch":     best_epoch,
        "val_cer":        round(best_val_cer, 4),
        "val_wer":        round(val_wer, 4),
        "train_samples":  len(train_ds),
        "val_samples":    len(val_ds),
        "vocab_size":     num_classes,
        "config": {
            "batch_size":    cfg.BATCH_SIZE,
            "learning_rate": cfg.LEARNING_RATE,
            "device":        cfg.DEVICE,
            "img_height":    cfg.IMG_HEIGHT,
            "img_max_width": cfg.IMG_MAX_WIDTH,
        },
        "history": history,
    }
    save_model(model, version_name, meta)

    # Copy vocab into the final version dir
    import shutil
    vocab_dest = cfg.TRAINED_MODELS_DIR / version_name / cfg.VOCAB_FILENAME
    shutil.copy(vocab_path, vocab_dest)

    print(f"\n  Training complete!")
    print(f"  Best epoch      : {best_epoch} (val CER = {best_val_cer:.4f})")
    print(f"  Final model     : {cfg.TRAINED_MODELS_DIR / version_name}")
    print(f"\n  Next steps:")
    print(f"    Evaluate : python evaluate.py")
    print(f"    Inference: python inference.py --input path/to/image.png")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune handwritten OCR.")
    parser.add_argument("--base",   default="auto",
                        help="Base model: 'auto'|'original'|'handwritten_vN'")
    parser.add_argument("--epochs", type=int, default=None,
                        help=f"Number of training epochs (default: {cfg.EPOCHS})")
    args = parser.parse_args()

    print("\n  Current model versions:")
    print_versions()
    train(base_version=args.base, epochs=args.epochs)
