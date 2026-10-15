"""Optional Keras image-model loading and image prediction."""
from __future__ import annotations

import io
import json
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "wastewise.keras"
METADATA_PATH = ROOT / "models" / "metadata.json"
CONFIDENCE_THRESHOLD = 0.62
CONFIDENCE_MARGIN = 0.14
_MODEL = None
_METADATA = None

def get_model_status() -> dict:
    return {"ready": MODEL_PATH.is_file() and METADATA_PATH.is_file()}

def _load_model():
    global _MODEL, _METADATA
    if _MODEL is None:
        if not get_model_status()["ready"]:
            return None, None
        try:
            import tensorflow as tf
            _MODEL = tf.keras.models.load_model(MODEL_PATH)
            _METADATA = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        except Exception:
            _MODEL, _METADATA = None, None
            return None, None
    return _MODEL, _METADATA

def classify_image(image_bytes: bytes) -> dict:
    try:
        with Image.open(io.BytesIO(image_bytes)) as check:
            check.verify()
        with Image.open(io.BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB").resize((224, 224))
    except (UnidentifiedImageError, OSError, ValueError):
        return {"status": "invalid", "detail": "Please upload a valid JPG, PNG, or WebP image."}
    model, metadata = _load_model()
    if model is None:
        return {"status": "unavailable"}
    import numpy as np
    scores = model.predict(np.expand_dims(np.asarray(image, dtype="float32"), axis=0), verbose=0)[0]
    ranked = np.argsort(scores)[::-1]
    index = int(ranked[0])
    confidence = float(scores[index])
    labels = metadata["class_names"]
    label = labels[index]
    from src.catalog import FOLDER_TO_CATEGORY, FOLDER_TO_ITEM
    category = FOLDER_TO_CATEGORY.get(label)
    item = FOLDER_TO_ITEM.get(label, label.replace("_", " "))
    second_score = float(scores[ranked[1]]) if len(ranked) > 1 else 0.0
    candidates = []
    for candidate_index in ranked[:3]:
        candidate_label = labels[int(candidate_index)]
        candidate_category = FOLDER_TO_CATEGORY.get(candidate_label)
        if candidate_category:
            candidates.append({
                "label": candidate_label,
                "item": FOLDER_TO_ITEM.get(candidate_label, candidate_label.replace("_", " ")),
                "category": candidate_category,
                "confidence": float(scores[int(candidate_index)]),
            })
    if confidence < CONFIDENCE_THRESHOLD or confidence - second_score < CONFIDENCE_MARGIN or category is None:
        return {"status": "unknown", "category": category, "item": item, "confidence": confidence, "candidates": candidates}
    return {"status": "ready", "category": category, "item": item, "confidence": confidence}
