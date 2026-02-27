import os
import json
import math
import time
import copy
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms

import timm
from tqdm import tqdm

from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    classification_report
)

import matplotlib.pyplot as plt


# =========================
# Config
# =========================
ROOT_DIR = r"C:\Users\Nouran\Desktop\PR2\SDPS\Deeplearning Model\Patterned Data Set"   # dataset root
SPLITS = {"train": "Training", "test": "Testing", "val": "Evaluating"}  # map to folder names

MODEL_NAME = "tf_efficientnetv2_s"   # EfficientNetV2-S in timm
IMG_SIZE = 224
BATCH_SIZE = 16
NUM_EPOCHS = 5
LR = 3e-4
WEIGHT_DECAY = 1e-4

NUM_WORKERS = 4
PIN_MEMORY = True

SEED = 42
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MIXED_PRECISION = True  # AMP

# checkpointing
OUT_DIR = "Effnetv2s Training"
SAVE_EVERY = 5  # epochs
BEST_METRIC = "f1_macro"  # choose: f1_macro or f1_weighted

# For x-rays: keep grayscale,while EfficientNet expects 3 channels; replicate 1->3
USE_GRAYSCALE = True

# =========================
# Reproducibility
# =========================
def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = False
    torch.backends.cudnn.benchmark = True

set_seed(SEED)


# =========================
# Dataset
# =========================
VALID_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

def build_class_map(root_dir: Path, train_folder: str) -> Tuple[List[str], Dict[str, int]]:
    """
    Stable mapping from folder names in training split.
    """
    train_dir = root_dir / train_folder
    class_names = sorted([p.name for p in train_dir.iterdir() if p.is_dir()])
    label_map = {name: i for i, name in enumerate(class_names)}
    return class_names, label_map

def collect_samples(split_dir: Path, label_map: Dict[str, int], recursive=True) -> List[Tuple[str, int]]:
    """
    Returns list of (filepath, label).
    """
    samples = []
    for class_name, label in label_map.items():
        class_dir = split_dir / class_name
        if not class_dir.exists():
            raise FileNotFoundError(f"Missing class folder: {class_dir}")

        iterator = class_dir.rglob("*") if recursive else class_dir.iterdir()
        for p in iterator:
            if p.is_file() and p.suffix.lower() in VALID_EXTS:
                samples.append((str(p), label))
    return samples

class LungFolderDataset(Dataset):
    def __init__(self, samples: List[Tuple[str, int]], transform=None, grayscale=True):
        self.samples = samples
        self.transform = transform
        self.grayscale = grayscale

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, y = self.samples[idx]
        with Image.open(path) as im:
            if self.grayscale:
                im = im.convert("L")  # 1 channel
            else:
                im = im.convert("RGB")

            if self.transform is not None:
                x = self.transform(im)
            else:
                x = transforms.ToTensor()(im)

        return x, y, path

def to_3ch(t):
    # t: (C,H,W)
   # t is a Tensor (C,H,W). If grayscale -> C=1, replicate to C=3
    return t.repeat(3, 1, 1) if (t.ndim == 3 and t.shape[0] == 1) else t
# =========================
# Transforms (X-ray friendly)
# =========================
def get_transforms(img_size=224, train=True, force_3ch=True):

    # For medical imaging, I avoid aggressive color jitter/hue.
    # I use mild geometric augmentation and slight contrast/brightness changes.
    if train:
        ops = [
            transforms.Resize((img_size, img_size)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(degrees=7),
            transforms.RandomAffine(degrees=0, translate=(0.02, 0.02), scale=(0.95, 1.05)),
            transforms.ToTensor(),
        ]
    else:
        ops = [
            transforms.Resize((img_size, img_size)),
            transforms.ToTensor(),
        ]

    if force_3ch:
        ops.append(transforms.Lambda(to_3ch))

    ops.append(
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    )

    return transforms.Compose(ops)


# =========================
# Metrics + Plots
# =========================
def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int):
    acc = accuracy_score(y_true, y_pred)

    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    p_weighted, r_weighted, f1_weighted, _ = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )

    return {
        "acc": float(acc),
        "precision_macro": float(p_macro),
        "recall_macro": float(r_macro),
        "f1_macro": float(f1_macro),
        "precision_weighted": float(p_weighted),
        "recall_weighted": float(r_weighted),
        "f1_weighted": float(f1_weighted),
    }

def save_confusion_heatmap(cm: np.ndarray, class_names: List[str], out_path: str, title: str):
    plt.figure(figsize=(8, 7))
    plt.imshow(cm, interpolation="nearest")
    plt.title(title)
    plt.colorbar()
    tick_marks = np.arange(len(class_names))
    plt.xticks(tick_marks, class_names, rotation=45, ha="right")
    plt.yticks(tick_marks, class_names)

    # annotate
    thresh = cm.max() * 0.6 if cm.max() > 0 else 0.5
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            plt.text(j, i, str(cm[i, j]),
                     horizontalalignment="center",
                     color="white" if cm[i, j] > thresh else "black")

    plt.ylabel("True label")
    plt.xlabel("Predicted label")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


# =========================
# Calibration: Temperature Scaling + ECE
# =========================
def softmax_np(logits: np.ndarray) -> np.ndarray:
    logits = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(logits)
    return exp / exp.sum(axis=1, keepdims=True)

def expected_calibration_error(probs: np.ndarray, y_true: np.ndarray, n_bins: int = 15) -> float:
    """
    probs: (N, C) predicted probabilities
    y_true: (N,) int labels
    """
    confidences = probs.max(axis=1)
    predictions = probs.argmax(axis=1)
    accuracies = (predictions == y_true).astype(np.float32)

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    N = len(y_true)

    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        mask = (confidences > lo) & (confidences <= hi)
        if mask.sum() == 0:
            continue
        bin_acc = accuracies[mask].mean()
        bin_conf = confidences[mask].mean()
        ece += (mask.sum() / N) * abs(bin_acc - bin_conf)
    return float(ece)

class TemperatureScaler(nn.Module):
    """
    Learn a single scalar temperature T > 0 minimizing NLL on validation set.
    """
    def __init__(self):
        super().__init__()
        self.log_t = nn.Parameter(torch.zeros(1))  # T = exp(log_t)

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        t = torch.exp(self.log_t).clamp(min=1e-6)
        return logits / t

    def temperature(self) -> float:
        return float(torch.exp(self.log_t).detach().cpu().item())

def fit_temperature(logits: np.ndarray, y_true: np.ndarray, device: str = "cpu") -> Tuple[float, float]:
    """
    Fit temperature on validation logits and return (temperature, ece_after).
    """
    scaler = TemperatureScaler().to(device)
    criterion = nn.CrossEntropyLoss()

    logits_t = torch.tensor(logits, dtype=torch.float32, device=device)
    y_t = torch.tensor(y_true, dtype=torch.long, device=device)

    optimizer = optim.LBFGS([scaler.log_t], lr=0.1, max_iter=50)

    def closure():
        optimizer.zero_grad()
        loss = criterion(scaler(logits_t), y_t)
        loss.backward()
        return loss

    optimizer.step(closure)

    # ECE after temperature scaling
    with torch.no_grad():
        calibrated_logits = scaler(logits_t).cpu().numpy()
        probs = softmax_np(calibrated_logits)
        ece = expected_calibration_error(probs, y_true, n_bins=15)

    return scaler.temperature(), float(ece)


# =========================
# Train/Eval loops
# =========================
@torch.no_grad()
def run_inference(model, loader, device):
    model.eval()
    all_logits, all_y, all_paths = [], [], []
    for x, y, paths in tqdm(loader, desc="Infer", leave=False):
        x = x.to(device, non_blocking=True)
        logits = model(x)
        all_logits.append(logits.detach().cpu())
        all_y.append(y)
        all_paths.extend(list(paths))
    all_logits = torch.cat(all_logits, dim=0).numpy()
    all_y = torch.cat(all_y, dim=0).numpy()
    return all_logits, all_y, all_paths

def train_one_epoch(model, loader, optimizer, scaler_amp, device):
    model.train()
    criterion = nn.CrossEntropyLoss()
    running_loss = 0.0
    n = 0

    for x, y, _ in tqdm(loader, desc="Train", leave=False):
        x = x.to(device, non_blocking=True)
        y = y.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)

        if MIXED_PRECISION and device.startswith("cuda"):
            use_cuda = (DEVICE.startswith("cuda") and torch.cuda.is_available())
            amp_enabled = MIXED_PRECISION and use_cuda
            with torch.amp.autocast(device_type="cuda", enabled=amp_enabled):
                logits = model(x)
                loss = criterion(logits, y)
            scaler_amp.scale(loss).backward()
            scaler_amp.step(optimizer)
            scaler_amp.update()
        else:
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()

        bs = x.size(0)
        running_loss += loss.item() * bs
        n += bs

    return running_loss / max(1, n)


# =========================
# Checkpointing
# =========================
def save_checkpoint(path, state: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    torch.save(state, path)

def get_score(metrics: dict, key: str) -> float:
    if key == "acc":
        return metrics["acc"]
    if key == "f1_macro":
        return metrics["f1_macro"]
    if key == "f1_weighted":
        return metrics["f1_weighted"]
    raise ValueError(f"Unknown BEST_METRIC: {key}")


# =========================
# Main
# =========================
def main():
    out_dir = Path(OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    root = Path(ROOT_DIR)
    for k, folder in SPLITS.items():
        if not (root / folder).exists():
            raise FileNotFoundError(f"Missing split folder: {root / folder}")

    # Build class map from training folder names
    class_names, label_map = build_class_map(root, SPLITS["train"])
    num_classes = len(class_names)

    # Save metadata
    meta = {
        "root_dir": str(root),
        "splits": SPLITS,
        "class_names": class_names,
        "label_map": label_map,
        "model": MODEL_NAME,
        "img_size": IMG_SIZE,
        "batch_size": BATCH_SIZE,
        "epochs": NUM_EPOCHS,
        "lr": LR,
        "weight_decay": WEIGHT_DECAY,
        "seed": SEED,
        "device": DEVICE,
        "best_metric": BEST_METRIC,
    }
    with open(out_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    # Samples
    train_samples = collect_samples(root / SPLITS["train"], label_map, recursive=True)
    val_samples   = collect_samples(root / SPLITS["val"],   label_map, recursive=True)
    test_samples  = collect_samples(root / SPLITS["test"],  label_map, recursive=True)

    print(f"Classes ({num_classes}): {class_names}")
    print(f"Train: {len(train_samples)} | Val: {len(val_samples)} | Test: {len(test_samples)}")

    # Datasets/Loaders
    train_tf = get_transforms(IMG_SIZE, train=True,  force_3ch=True)
    eval_tf  = get_transforms(IMG_SIZE, train=False, force_3ch=True)


    ds_train = LungFolderDataset(train_samples, transform=train_tf, grayscale=USE_GRAYSCALE)
    ds_val   = LungFolderDataset(val_samples,   transform=eval_tf,  grayscale=USE_GRAYSCALE)
    ds_test  = LungFolderDataset(test_samples,  transform=eval_tf,  grayscale=USE_GRAYSCALE)

    dl_train = DataLoader(ds_train, batch_size=BATCH_SIZE, shuffle=True,
                          num_workers=NUM_WORKERS, pin_memory=PIN_MEMORY)
    dl_val   = DataLoader(ds_val, batch_size=BATCH_SIZE, shuffle=False,
                          num_workers=NUM_WORKERS, pin_memory=PIN_MEMORY)
    dl_test  = DataLoader(ds_test, batch_size=BATCH_SIZE, shuffle=False,
                          num_workers=NUM_WORKERS, pin_memory=PIN_MEMORY)

    # Model
    model = timm.create_model(MODEL_NAME, pretrained=True, num_classes=num_classes)
    model.to(DEVICE)

    # Optimizer + Scheduler
    optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)

    # cosine schedule
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=NUM_EPOCHS)

    use_cuda = (DEVICE.startswith("cuda") and torch.cuda.is_available())
    amp_enabled = MIXED_PRECISION and use_cuda

    scaler_amp = torch.amp.GradScaler("cuda", enabled=amp_enabled)

    best_score = -1.0
    best_state = None

    history = []

    for epoch in range(1, NUM_EPOCHS + 1):
        start = time.time()

        train_loss = train_one_epoch(model, dl_train, optimizer, scaler_amp, DEVICE)

        # Validate
        val_logits, val_y, _ = run_inference(model, dl_val, DEVICE)
        val_pred = val_logits.argmax(axis=1)

        metrics = compute_metrics(val_y, val_pred, num_classes=num_classes)

        # Calibration on validation set (temperature scaling)
        # Compute ECE before and after
        val_probs_before = softmax_np(val_logits)
        ece_before = expected_calibration_error(val_probs_before, val_y, n_bins=15)

        temperature, ece_after = fit_temperature(val_logits, val_y, device=DEVICE)

        # Confusion matrix + heatmap
        cm = confusion_matrix(val_y, val_pred, labels=list(range(num_classes)))
        heatmap_path = out_dir / f"cm_heatmap_val_epoch_{epoch}.png"
        save_confusion_heatmap(cm, class_names, str(heatmap_path), title=f"Val Confusion Matrix - Epoch {epoch}")

        # Classification report
        report = classification_report(val_y, val_pred, target_names=class_names, zero_division=0)

        # Log record
        record = {
            "epoch": epoch,
            "train_loss": float(train_loss),
            "lr": float(optimizer.param_groups[0]["lr"]),
            **metrics,
            "ece_before": float(ece_before),
            "temperature": float(temperature),
            "ece_after": float(ece_after),
            "heatmap_path": str(heatmap_path),
            "seconds": float(time.time() - start),
        }
        history.append(record)

        # Save history every epoch
        with open(out_dir / "history.json", "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

        # Save report text
        with open(out_dir / f"classification_report_val_epoch_{epoch}.txt", "w", encoding="utf-8") as f:
            f.write(report)

        # Determine best
        score = get_score(metrics, BEST_METRIC)

        is_best = score > best_score
        if is_best:
            best_score = score
            best_state = copy.deepcopy(model.state_dict())

        # Build checkpoint payload (includes calibration)
        ckpt = {
            "epoch": epoch,
            "model_name": MODEL_NAME,
            "model_state": model.state_dict(),
            "optimizer_state": optimizer.state_dict(),
            "scheduler_state": scheduler.state_dict(),
            "amp_scaler_state": scaler_amp.state_dict() if scaler_amp is not None else None,
            "class_names": class_names,
            "label_map": label_map,
            "metrics_val": metrics,
            "train_loss": float(train_loss),
            "calibration": {
                "ece_before": float(ece_before),
                "temperature": float(temperature),
                "ece_after": float(ece_after),
            },
            "seed": SEED,
            "img_size": IMG_SIZE,
        }

        # Save periodic checkpoint
        if epoch % SAVE_EVERY == 0:
            save_checkpoint(str(out_dir / f"checkpoint_epoch_{epoch}.pt"), ckpt)

        # Save best checkpoint
        if is_best:
            save_checkpoint(str(out_dir / "checkpoint_best.pt"), ckpt)

        # Save last checkpoint each epoch (cheap and safe)
        save_checkpoint(str(out_dir / "checkpoint_last.pt"), ckpt)

        # Step scheduler
        scheduler.step()

        # Console summary
        print(
            f"Epoch {epoch}/{NUM_EPOCHS} | loss={train_loss:.4f} | "
            f"val_acc={metrics['acc']:.4f} | val_f1_macro={metrics['f1_macro']:.4f} | "
            f"ECE {ece_before:.4f}->{ece_after:.4f} (T={temperature:.3f}) | "
            f"saved: {heatmap_path.name}"
        )

    # -----------------------
    # Final test evaluation using BEST model
    # -----------------------
    if best_state is not None:
        model.load_state_dict(best_state)

    test_logits, test_y, _ = run_inference(model, dl_test, DEVICE)
    test_pred = test_logits.argmax(axis=1)

    test_metrics = compute_metrics(test_y, test_pred, num_classes=num_classes)
    test_probs_before = softmax_np(test_logits)
    test_ece_before = expected_calibration_error(test_probs_before, test_y, n_bins=15)

    # Fit temperature on validation again and apply to test
    # reuse last fitted temperature from best epoch would be ideal, but for simplicity I fit on validation set once more using the best model:
    val_logits_best, val_y_best, _ = run_inference(model, dl_val, DEVICE)
    temperature, _ = fit_temperature(val_logits_best, val_y_best, device=DEVICE)

    # Apply temperature to test logits
    test_logits_cal = test_logits / max(1e-6, temperature)
    test_probs_cal = softmax_np(test_logits_cal)
    test_ece_after = expected_calibration_error(test_probs_cal, test_y, n_bins=15)

    cm_test = confusion_matrix(test_y, test_pred, labels=list(range(num_classes)))
    heatmap_test_path = Path(OUT_DIR) / "cm_heatmap_test.png"
    save_confusion_heatmap(cm_test, class_names, str(heatmap_test_path), title="Test Confusion Matrix")

    report_test = classification_report(test_y, test_pred, target_names=class_names, zero_division=0)
    with open(Path(OUT_DIR) / "classification_report_test.txt", "w", encoding="utf-8") as f:
        f.write(report_test)

    summary = {
        "best_metric": BEST_METRIC,
        "best_score": float(best_score),
        "test_metrics": test_metrics,
        "test_ece_before": float(test_ece_before),
        "test_temperature_used": float(temperature),
        "test_ece_after": float(test_ece_after),
        "test_heatmap_path": str(heatmap_test_path),
    }
    with open(Path(OUT_DIR) / "test_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n=== TEST SUMMARY (Best model) ===")
    print(json.dumps(summary, indent=2))
    print(f"Saved outputs to: {Path(OUT_DIR).resolve()}")


if __name__ == "__main__":
    main()
