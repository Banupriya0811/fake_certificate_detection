"""Shared configuration for the DocVerify AI ML pipeline."""

import os

ML_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(ML_DIR)

# Source dataset (contains real/ and fake/)
RAW_DATASET_DIR = os.path.join(ROOT_DIR, "Dataset")

# Clean deduplicated & split dataset output
PROCESSED_DIR = os.path.join(ML_DIR, "data", "processed")

# Training outputs & saved models
ARTIFACTS_DIR = os.path.join(ML_DIR, "artifacts")
GAN_MODEL_PATH = os.path.join(ARTIFACTS_DIR, "gan_generator.keras")
GAN_SAMPLES_DIR = os.path.join(ARTIFACTS_DIR, "gan_samples")
GENERATED_FAKES_DIR = os.path.join(ARTIFACTS_DIR, "generated_fakes")

DETECTOR_MODEL_PATH = os.path.join(ARTIFACTS_DIR, "model.keras")
CLASS_INFO_PATH = os.path.join(ARTIFACTS_DIR, "class_info.json")
TRAINING_LOG_PATH = os.path.join(ARTIFACTS_DIR, "training_log.csv")
TRAINING_CURVES_PATH = os.path.join(ARTIFACTS_DIR, "training_curves.png")
CONFUSION_MATRIX_PATH = os.path.join(ARTIFACTS_DIR, "confusion_matrix.png")

# Backend model directory (auto-synced after training)
BACKEND_MODEL_DIR = os.path.join(ROOT_DIR, "backend", "model")

# Model & training hyperparameters
IMG_SIZE = 224
BATCH_SIZE = 16
SEED = 42
LATENT_DIM = 128

# Explicit alphabetical class mapping: fake = 0, real = 1
CLASS_NAMES = ["fake", "real"]
ALLOWED_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp")

