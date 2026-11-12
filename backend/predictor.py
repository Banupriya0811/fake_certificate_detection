"""Document authenticity predictor backed by the trained Keras CNN model."""

import json
import os
import random
import numpy as np
from PIL import Image


class DocumentPredictor:
    """Loads the trained CNN classifier and runs inference on document images."""

    def __init__(self, model_path: str, class_info_path: str, image_size=(224, 224)):
        self.model_path = model_path
        self.class_info_path = class_info_path
        self.image_size = image_size
        self.model = None
        self.fake_class_is_0 = True
        self.threshold = 0.5
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.class_info_path):
            with open(self.class_info_path, "r", encoding="utf-8") as f:
                info = json.load(f)
            self.fake_class_is_0 = info.get("fake_class_is_0", True)
            self.threshold = float(info.get("threshold", 0.5))

        if not os.path.exists(self.model_path):
            print(f"[Predictor] Model not found at {self.model_path} — running in DEMO mode.")
            return

        try:
            from tensorflow.keras.models import load_model

            self.model = load_model(self.model_path, compile=False)
            print(f"[Predictor] Loaded model from {self.model_path}")
        except Exception as exc:
            print(f"[Predictor] Failed to load model ({exc}) — running in DEMO mode.")
            self.model = None

    @property
    def is_loaded(self) -> bool:
        return self.model is not None

    def _preprocess(self, filepath: str) -> np.ndarray:
        with Image.open(filepath) as img:
            rgb = img.convert("RGB").resize(self.image_size, Image.Resampling.BILINEAR)
            arr = np.asarray(rgb, dtype="float32") / 255.0
        return np.expand_dims(arr, axis=0)

    def predict(self, filepath: str) -> dict:
        """Return verdict, confidence (0-100), raw score, and inference mode."""
        if self.model is None:
            raw = random.uniform(0.1, 0.9)
            mode = "demo"
        else:
            batch = self._preprocess(filepath)
            raw = float(self.model.predict(batch, verbose=0)[0][0])
            mode = "model"

        if self.fake_class_is_0:
            is_fake = raw < self.threshold
            fake_prob = 1.0 - raw
            real_prob = raw
        else:
            is_fake = raw >= self.threshold
            fake_prob = raw
            real_prob = 1.0 - raw

        confidence = round((fake_prob if is_fake else real_prob) * 100.0, 2)
        result = "Fake Document" if is_fake else "Original Document"

        return {
            "result": result,
            "is_fake": is_fake,
            "confidence": confidence,
            "raw_score": round(raw, 4),
            "fake_probability": round(fake_prob * 100.0, 2),
            "real_probability": round(real_prob * 100.0, 2),
            "mode": mode,
        }

