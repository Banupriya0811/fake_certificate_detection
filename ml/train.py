"""
DocVerify AI — Single-Command Dataset Preparation, Training & Evaluation
=======================================================================
One command handles the full ML workflow:
  1. Cleans, deduplicates, pre-resizes (224x224), and splits Dataset/ -> train/val/test
  2. Trains MobileNetV2 detector (Phase 1 head + Phase 2 fine-tuning) with fast caching
  3. Evaluates on the unseen test split and saves confusion matrix & training curves
  4. Syncs model.keras & class_info.json to backend/model/

Run:
    python ml/train.py
    python ml/train.py --image path/to/document.jpg
"""

import argparse
import hashlib
import json
import os
import random
import re
import shutil
import time
from collections import defaultdict

import matplotlib
import numpy as np
import tensorflow as tf
from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from tensorflow.keras import Input, Model, layers
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.callbacks import CSVLogger, EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config import (
    ALLOWED_EXTS,
    ARTIFACTS_DIR,
    BACKEND_MODEL_DIR,
    BATCH_SIZE,
    CLASS_INFO_PATH,
    CLASS_NAMES,
    CONFUSION_MATRIX_PATH,
    DETECTOR_MODEL_PATH,
    IMG_SIZE,
    PROCESSED_DIR,
    RAW_DATASET_DIR,
    SEED,
    TRAINING_CURVES_PATH,
    TRAINING_LOG_PATH,
)

tf.keras.utils.set_random_seed(SEED)


def _file_md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _group_key(filename: str) -> str:
    stem = os.path.splitext(filename)[0].lower()
    stem = re.sub(r"^(?:\d+_\d{9,12}_)+", "", stem)
    for suffix in ("_blur", "_noise", "_compressed", "_bw", "_bright", "_textedit", "_contrast", "_patch", "_1"):
        stem = stem.replace(suffix, "")
    return re.sub(r"[^a-z0-9]+", "_", stem).strip("_") or filename.lower()


def _collect_unique(folder: str, label: str) -> list[dict]:
    records, seen = [], set()
    for fname in sorted(os.listdir(folder)):
        if not fname.lower().endswith(ALLOWED_EXTS):
            continue
        path = os.path.join(folder, fname)
        try:
            with Image.open(path) as img:
                img.verify()
        except Exception:
            continue
        digest = _file_md5(path)
        if digest in seen:
            continue
        seen.add(digest)
        records.append({
            "filename": fname,
            "path": path,
            "md5": digest,
            "group": _group_key(fname),
            "label": label,
        })
    return records


def prepare_dataset(val_ratio: float = 0.15, test_ratio: float = 0.15) -> dict:
    """Deduplicate, remove cross-class leaks, group-split, and pre-resize to 224x224."""
    real_dir = os.path.join(RAW_DATASET_DIR, "real")
    fake_dir = os.path.join(RAW_DATASET_DIR, "fake")
    if not os.path.isdir(real_dir) or not os.path.isdir(fake_dir):
        raise FileNotFoundError(f"Missing '{real_dir}' or '{fake_dir}'.")

    real_recs = _collect_unique(real_dir, "real")
    real_hashes = {r["md5"] for r in real_recs}
    fake_recs = [r for r in _collect_unique(fake_dir, "fake") if r["md5"] not in real_hashes]

    groups = defaultdict(list)
    for rec in real_recs + fake_recs:
        groups[rec["group"]].append(rec)

    keys = sorted(groups.keys())
    random.Random(SEED).shuffle(keys)

    total = len(real_recs) + len(fake_recs)
    n_test = max(1, round(total * test_ratio))
    n_val = max(1, round(total * val_ratio))

    splits = {"train": [], "val": [], "test": []}
    for k in keys:
        if len(splits["test"]) < n_test:
            splits["test"].extend(groups[k])
        elif len(splits["val"]) < n_val:
            splits["val"].extend(groups[k])
        else:
            splits["train"].extend(groups[k])

    if os.path.exists(PROCESSED_DIR):
        shutil.rmtree(PROCESSED_DIR)

    counts = {}
    for split_name, items in splits.items():
        c = {"fake": 0, "real": 0}
        for idx, rec in enumerate(items):
            dest_dir = os.path.join(PROCESSED_DIR, split_name, rec["label"])
            os.makedirs(dest_dir, exist_ok=True)
            out_path = os.path.join(dest_dir, f"{rec['label']}_{idx:04d}.jpg")
            with Image.open(rec["path"]) as img:
                resized = img.convert("RGB").resize((IMG_SIZE, IMG_SIZE), Image.Resampling.BILINEAR)
                resized.save(out_path, format="JPEG", quality=95)
            c[rec["label"]] += 1
        counts[split_name] = c

    print(
        f"[1/3] Dataset ready -> "
        f"train(fake={counts['train']['fake']}, real={counts['train']['real']}), "
        f"val(fake={counts['val']['fake']}, real={counts['val']['real']}), "
        f"test(fake={counts['test']['fake']}, real={counts['test']['real']})"
    )
    return counts


def _make_dataset(split_name: str, augment: bool = False):
    split_dir = os.path.join(PROCESSED_DIR, split_name)
    ds = tf.keras.utils.image_dataset_from_directory(
        split_dir,
        labels="inferred",
        label_mode="binary",
        class_names=CLASS_NAMES,
        image_size=(IMG_SIZE, IMG_SIZE),
        batch_size=BATCH_SIZE,
        shuffle=augment,
        seed=SEED,
        verbose=0,
    )
    rescale = layers.Rescaling(1.0 / 255.0)
    ds = ds.map(lambda x, y: (rescale(x), y), num_parallel_calls=tf.data.AUTOTUNE).cache()

    if augment:
        aug = tf.keras.Sequential([
            layers.RandomFlip("horizontal"),
            layers.RandomRotation(0.03),
            layers.RandomZoom(0.05),
        ])
        ds = ds.map(lambda x, y: (aug(x, training=True), y), num_parallel_calls=tf.data.AUTOTUNE)

    return ds.prefetch(tf.data.AUTOTUNE)


def _build_model() -> Model:
    base = MobileNetV2(input_shape=(IMG_SIZE, IMG_SIZE, 3), include_top=False, weights="imagenet")
    base.trainable = False

    inputs = Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    x = layers.Rescaling(2.0, offset=-1.0)(inputs)
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.35)(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dropout(0.25)(x)
    outputs = layers.Dense(1, activation="sigmoid")(x)
    return Model(inputs, outputs, name="docverify_mobilenetv2")


def _save_curves(h1, h2) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    acc = h1.history.get("accuracy", []) + h2.history.get("accuracy", [])
    val_acc = h1.history.get("val_accuracy", []) + h2.history.get("val_accuracy", [])
    loss = h1.history.get("loss", []) + h2.history.get("loss", [])
    val_loss = h1.history.get("val_loss", []) + h2.history.get("val_loss", [])
    split_ep = len(h1.history.get("loss", [])) - 0.5

    axes[0].plot(acc, label="Train")
    axes[0].plot(val_acc, label="Val")
    axes[0].axvline(split_ep, color="gray", linestyle="--")
    axes[0].set_title("Accuracy")
    axes[0].legend()

    axes[1].plot(loss, label="Train")
    axes[1].plot(val_loss, label="Val")
    axes[1].axvline(split_ep, color="gray", linestyle="--")
    axes[1].set_title("Loss")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(TRAINING_CURVES_PATH, dpi=140)
    plt.close(fig)


def train_and_evaluate(epochs_head: int = 12, epochs_fine: int = 10) -> None:
    t0 = time.time()
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    os.makedirs(BACKEND_MODEL_DIR, exist_ok=True)

    counts = prepare_dataset()
    n_fake = counts["train"]["fake"]
    n_real = counts["train"]["real"]
    total = n_fake + n_real
    class_weight = {0: total / (2.0 * max(n_fake, 1)), 1: total / (2.0 * max(n_real, 1))}

    train_ds = _make_dataset("train", augment=True)
    val_ds = _make_dataset("val", augment=False)

    print("[2/3] Training MobileNetV2 detector...")
    model = _build_model()
    p1_ckpt = os.path.join(ARTIFACTS_DIR, "_p1.keras")
    p2_ckpt = os.path.join(ARTIFACTS_DIR, "_p2.keras")

    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss="binary_crossentropy",
        metrics=["accuracy", tf.keras.metrics.AUC(name="auc")],
    )
    h1 = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs_head,
        class_weight=class_weight,
        callbacks=[
            EarlyStopping("val_loss", patience=5, restore_best_weights=True, mode="min"),
            ModelCheckpoint(p1_ckpt, monitor="val_loss", save_best_only=True, mode="min"),
            ReduceLROnPlateau("val_loss", factor=0.5, patience=3, min_lr=1e-6),
            CSVLogger(TRAINING_LOG_PATH),
        ],
        verbose=1,
    )
    if os.path.exists(p1_ckpt):
        model = tf.keras.models.load_model(p1_ckpt)
    p1_loss = float(model.evaluate(val_ds, verbose=0)[0])

    base_layer = model.get_layer("mobilenetv2_1.00_224")
    base_layer.trainable = True
    for layer in base_layer.layers[:-20]:
        layer.trainable = False
    for layer in base_layer.layers[-20:]:
        if isinstance(layer, layers.BatchNormalization):
            layer.trainable = False

    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-5),
        loss="binary_crossentropy",
        metrics=["accuracy", tf.keras.metrics.AUC(name="auc")],
    )
    h2 = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs_fine,
        class_weight=class_weight,
        callbacks=[
            EarlyStopping("val_loss", patience=4, restore_best_weights=True, mode="min"),
            ModelCheckpoint(p2_ckpt, monitor="val_loss", save_best_only=True, mode="min"),
            CSVLogger(TRAINING_LOG_PATH, append=True),
        ],
        verbose=1,
    )
    if os.path.exists(p2_ckpt):
        p2_model = tf.keras.models.load_model(p2_ckpt)
        p2_loss = float(p2_model.evaluate(val_ds, verbose=0)[0])
    else:
        p2_model, p2_loss = model, float(model.evaluate(val_ds, verbose=0)[0])

    best_model = p2_model if p2_loss <= p1_loss else model
    best_model.save(DETECTOR_MODEL_PATH)
    for tmp in (p1_ckpt, p2_ckpt):
        if os.path.exists(tmp):
            os.remove(tmp)

    class_info = {
        "class_indices": {"fake": 0, "real": 1},
        "threshold": 0.5,
        "fake_class_is_0": True,
        "threshold_note": "output < 0.5 -> FAKE | output >= 0.5 -> REAL",
    }
    with open(CLASS_INFO_PATH, "w", encoding="utf-8") as f:
        json.dump(class_info, f, indent=2)

    _save_curves(h1, h2)
    shutil.copy2(DETECTOR_MODEL_PATH, os.path.join(BACKEND_MODEL_DIR, "model.keras"))
    shutil.copy2(CLASS_INFO_PATH, os.path.join(BACKEND_MODEL_DIR, "class_info.json"))

    # Step 3: Evaluate on unseen test split
    print("\n[3/3] Evaluating on unseen test split...")
    test_ds = _make_dataset("test", augment=False)
    y_true, y_prob = [], []
    for bx, by in test_ds:
        y_prob.extend(best_model.predict(bx, verbose=0).flatten().tolist())
        y_true.extend(by.numpy().flatten().astype(int).tolist())

    y_pred = [1 if p >= 0.5 else 0 for p in y_prob]
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    auc = roc_auc_score(y_true, y_prob) if len(set(y_true)) == 2 else 0.0
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])

    fig, ax = plt.subplots(figsize=(4.5, 4))
    ax.imshow(cm, cmap="Blues")
    ax.set(xticks=[0, 1], yticks=[0, 1], xticklabels=["Fake", "Real"], yticklabels=["Fake", "Real"],
           xlabel="Predicted", ylabel="Actual", title="Test Confusion Matrix")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(CONFUSION_MATRIX_PATH, dpi=140)
    plt.close(fig)

    with open(os.path.join(ARTIFACTS_DIR, "evaluation_report.json"), "w", encoding="utf-8") as f:
        json.dump({
            "samples": len(y_true),
            "accuracy": round(float(acc), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1": round(float(f1), 4),
            "roc_auc": round(float(auc), 4),
            "confusion_matrix": cm.tolist(),
        }, f, indent=2)

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s | Test Accuracy: {acc*100:.2f}% | ROC-AUC: {auc:.4f}")
    print(classification_report(y_true, y_pred, labels=[0, 1], target_names=["Fake", "Real"], zero_division=0))
    print(f"Synced model & class_info.json -> {BACKEND_MODEL_DIR}\n")


def predict_single(image_path: str) -> None:
    if not os.path.exists(DETECTOR_MODEL_PATH):
        raise FileNotFoundError("Model not trained yet. Run: python ml/train.py")
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    model = tf.keras.models.load_model(DETECTOR_MODEL_PATH, compile=False)
    with Image.open(image_path) as img:
        arr = np.asarray(img.convert("RGB").resize((IMG_SIZE, IMG_SIZE), Image.Resampling.BILINEAR), dtype="float32") / 255.0
    raw = float(model.predict(np.expand_dims(arr, 0), verbose=0)[0][0])
    is_fake = raw < 0.5
    conf = (1.0 - raw if is_fake else raw) * 100.0
    print(f"\nFile: {image_path}\nResult: {'Fake Document' if is_fake else 'Original Document'} ({conf:.2f}%)\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Single-command ML training & evaluation pipeline.")
    parser.add_argument("--image", type=str, default=None, help="Optional: classify a single image.")
    parser.add_argument("--epochs-head", type=int, default=12)
    parser.add_argument("--epochs-fine", type=int, default=10)
    args = parser.parse_args()

    if args.image:
        predict_single(args.image)
    else:
        train_and_evaluate(epochs_head=args.epochs_head, epochs_fine=args.epochs_fine)

