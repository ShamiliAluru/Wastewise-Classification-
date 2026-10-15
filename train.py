"""Train Wastewise with transfer learning from a folder-based image dataset."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import tensorflow as tf
from src.catalog import FOLDER_TO_CATEGORY

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"), help="Directory containing train/validation/test class folders")
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--fine-tune-epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--output", type=Path, default=Path("models"))
    args = parser.parse_args()
    size = (224, 224)
    folders = {part: args.data / part for part in ("train", "validation", "test")}
    for folder in folders.values():
        if not folder.is_dir():
            raise SystemExit(f"Missing {folder}. See README.md for the required folder layout.")
    train_ds = tf.keras.utils.image_dataset_from_directory(folders["train"], image_size=size, batch_size=args.batch_size, label_mode="categorical", seed=42)
    val_ds = tf.keras.utils.image_dataset_from_directory(folders["validation"], image_size=size, batch_size=args.batch_size, label_mode="categorical", shuffle=False)
    test_ds = tf.keras.utils.image_dataset_from_directory(folders["test"], image_size=size, batch_size=args.batch_size, label_mode="categorical", shuffle=False)
    class_names = train_ds.class_names
    if val_ds.class_names != class_names or test_ds.class_names != class_names:
        raise SystemExit("Train, validation, and test folders must contain the same class subfolders.")
    unknown = sorted(set(class_names) - set(FOLDER_TO_CATEGORY))
    if unknown:
        raise SystemExit(f"Unknown class folder(s): {', '.join(unknown)}. Use class names documented in README.md.")
    if len(class_names) < 3:
        raise SystemExit("Add at least three waste classes so the classifier can learn useful distinctions.")
    autotune = tf.data.AUTOTUNE
    train_ds = train_ds.shuffle(800, seed=42).prefetch(autotune)
    val_ds = val_ds.prefetch(autotune)
    test_ds = test_ds.prefetch(autotune)
    train_dir = folders["train"]
    train_counts = {name: sum(1 for item in (train_dir / name).iterdir() if item.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}) for name in class_names}
    total_train = sum(train_counts.values())
    class_weights = {index: total_train / (len(class_names) * train_counts[name]) for index, name in enumerate(class_names) if train_counts[name]}

    augment = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(0.06),
        tf.keras.layers.RandomZoom(0.08),
    ], name="light_augmentation")
    base = tf.keras.applications.MobileNetV2(input_shape=(*size, 3), include_top=False, weights="imagenet")
    base.trainable = False
    inputs = tf.keras.Input(shape=(*size, 3), name="photo_rgb")
    x = augment(inputs)
    x = tf.keras.layers.Rescaling(1.0 / 127.5, offset=-1)(x)
    x = base(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.25)(x)
    outputs = tf.keras.layers.Dense(len(class_names), activation="softmax", name="waste_class")(x)
    model = tf.keras.Model(inputs, outputs, name="wastewise_classifier")
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3), loss="categorical_crossentropy", metrics=["accuracy"])
    args.output.mkdir(parents=True, exist_ok=True)
    model_path = args.output / "wastewise.keras"
    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(model_path, monitor="val_accuracy", mode="max", save_best_only=True),
        tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=4, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.3, patience=2, min_lr=1e-6),
    ]
    model.fit(train_ds, validation_data=val_ds, epochs=args.epochs, callbacks=callbacks, class_weight=class_weights)
    if args.fine_tune_epochs > 0:
        base.trainable = True
        for layer in base.layers[:-30]:
            layer.trainable = False
        model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5), loss="categorical_crossentropy", metrics=["accuracy"])
        model.fit(train_ds, validation_data=val_ds, epochs=args.fine_tune_epochs, callbacks=callbacks, class_weight=class_weights)
    best_model = tf.keras.models.load_model(model_path)
    loss, accuracy = best_model.evaluate(test_ds, verbose=0)
    import numpy as np
    true_indices = np.concatenate([np.argmax(labels.numpy(), axis=1) for _, labels in test_ds])
    predicted_indices = np.argmax(best_model.predict(test_ds, verbose=0), axis=1)
    confusion = tf.math.confusion_matrix(true_indices, predicted_indices, num_classes=len(class_names)).numpy()
    per_class = {}
    for index, name in enumerate(class_names):
        true_positive = int(confusion[index, index])
        precision_denominator = int(confusion[:, index].sum())
        recall_denominator = int(confusion[index, :].sum())
        precision = true_positive / precision_denominator if precision_denominator else 0.0
        recall = true_positive / recall_denominator if recall_denominator else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[name] = {"precision": precision, "recall": recall, "f1": f1, "support": recall_denominator}
    metadata = {"model": "MobileNetV2 transfer learning", "image_size": list(size), "class_names": class_names,
                "class_categories": {name: FOLDER_TO_CATEGORY[name] for name in class_names}, "test_accuracy": float(accuracy),
                "test_loss": float(loss), "test_confusion_matrix": confusion.tolist(), "test_per_class": per_class}
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Saved model: {model_path}")
    print(f"Held-out test accuracy: {accuracy:.1%}")
    print("Per-class test metrics (precision / recall / F1):")
    for name in class_names:
        metrics = per_class[name]
        print(f"  {name:14s} {metrics['precision']:.1%} / {metrics['recall']:.1%} / {metrics['f1']:.1%}  (n={metrics['support']})")
    print("Record this score with your dataset/source; it is not a guarantee for real-world photos.")

if __name__ == "__main__":
    main()
