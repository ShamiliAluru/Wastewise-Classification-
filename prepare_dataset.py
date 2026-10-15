"""Restructure NexTech14 into fine-grained folders without split leakage."""
from __future__ import annotations

import argparse
import csv
import hashlib
import random
import re
import zipfile
from collections import defaultdict
from pathlib import Path

SOURCE_LABELS = {
    "battery": "batteries",
    "e-waste": "electronics",
    "food-waste": "food_scraps",
    "garden-waste": "yard_waste",
    "other-organic": "other_organic",
    "glass": "glass",
    "metal": "metal",
    "paper": "paper",
    "plastic": "plastic",
    "textile_fabric": "textile",
    "trash": "general_waste",
}
SPLIT_MAP = {"train": "train", "val": "validation", "test": "test"}


def parse_member(name: str):
    """Return split, fine label, family key, and augmentation flag for a ZIP member."""
    path = Path(name)
    parts = path.parts
    if len(parts) < 4 or parts[-3] not in SPLIT_MAP:
        return None
    split, broad_group, filename = parts[-3], parts[-2], path.name
    if broad_group not in {"hazardous", "organic", "recyclable"}:
        return None
    stem = path.stem
    is_augmented = re.search(r"_aug\d+$", stem, re.IGNORECASE) is not None
    base = re.sub(r"_aug\d+$", "", stem, flags=re.IGNORECASE)
    match = re.fullmatch(r"(.+)-(\d+)", base)
    if not match:
        raise ValueError(f"Unexpected image filename format: {filename}")
    source_label = match.group(1).lower()
    if source_label not in SOURCE_LABELS:
        raise ValueError(f"Unrecognized image label '{source_label}' in {filename}")
    label = SOURCE_LABELS[source_label]
    return split, label, f"{label}/{base}", is_augmented, filename


def allocate_groups(groups_by_class, seed: int):
    """Assign complete source-image families to train/validation/test."""
    rng = random.Random(seed)
    assignment = {}
    for label, families in sorted(groups_by_class.items()):
        families = sorted(families)
        rng.shuffle(families)
        count = len(families)
        if count < 3:
            raise ValueError(f"Class '{label}' has only {count} original image families; need at least 3.")
        test_count = max(1, round(count * 0.15))
        val_count = max(1, round(count * 0.15))
        while test_count + val_count >= count:
            if test_count >= val_count:
                test_count -= 1
            else:
                val_count -= 1
        for index, family in enumerate(families):
            if index < test_count:
                split = "test"
            elif index < test_count + val_count:
                split = "validation"
            else:
                split = "train"
            assignment[family] = split
    return assignment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True, help="Path to NexTech14_Waste_Dataset.zip")
    parser.add_argument("--output", type=Path, default=Path("data"), help="Output dataset directory (must not already exist)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not args.archive.is_file():
        raise SystemExit(f"ZIP file not found: {args.archive}")
    if args.output.exists():
        raise SystemExit(f"Output already exists: {args.output}. Move or rename it first; this script will not overwrite data.")

    with zipfile.ZipFile(args.archive) as archive:
        members = []
        groups_by_class = defaultdict(set)
        for info in archive.infolist():
            if info.is_dir() or Path(info.filename).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                continue
            parsed = parse_member(info.filename)
            if parsed is None:
                continue
            split, label, family, augmented, filename = parsed
            members.append((info, split, label, family, augmented, filename))
            groups_by_class[label].add(family)
        if not members:
            raise SystemExit("No labeled image files found. Check that this is the NexTech14 dataset ZIP.")
        assignment = allocate_groups(groups_by_class, args.seed)

        args.output.mkdir(parents=True)
        manifest_path = args.output / "preparation_manifest.csv"
        seen_hashes = set()
        counts = defaultdict(int)
        with manifest_path.open("w", newline="", encoding="utf-8") as manifest_file:
            writer = csv.writer(manifest_file)
            writer.writerow(["source_file", "original_split", "new_split", "fine_label", "source_family", "was_augmented"])
            for info, original_split, label, family, augmented, filename in members:
                new_split = assignment[family]
                # Keep augmented variants for training only. Validation and test
                # contain one original photo per held-out source family.
                if new_split != "train" and augmented:
                    continue
                with archive.open(info) as source:
                    content = source.read()
                digest = hashlib.sha256(content).hexdigest()
                identity = digest
                if identity in seen_hashes:
                    continue
                seen_hashes.add(identity)
                destination_dir = args.output / new_split / label
                destination_dir.mkdir(parents=True, exist_ok=True)
                destination = destination_dir / filename
                if destination.exists():
                    destination = destination_dir / f"{Path(filename).stem}_{digest[:8]}{Path(filename).suffix}"
                destination.write_bytes(content)
                writer.writerow([info.filename, original_split, new_split, label, family, augmented])
                counts[(new_split, label)] += 1

    print(f"Prepared {sum(counts.values())} images from {len(assignment)} original-image families at: {args.output}")
    print("Counts by split and item label:")
    for (split, label), count in sorted(counts.items()):
        print(f"  {split:10s} {label:16s} {count:5d}")
    print("Source train/val/test directories were regrouped because augmented siblings cross those splits.")
    print("Augmented copies are kept for training only; validation and test use held-out original photos.")


if __name__ == "__main__":
    main()
