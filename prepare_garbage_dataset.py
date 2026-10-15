"""Prepare the supplied 12-class archive into deterministic, deduplicated splits."""
from __future__ import annotations

import argparse
import csv
import hashlib
import random
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath

LABELS = {
    "battery", "biological", "brown-glass", "cardboard", "clothes",
    "green-glass", "metal", "paper", "plastic", "shoes", "trash", "white-glass",
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True, help="Path to archive.zip")
    parser.add_argument("--output", type=Path, default=Path("data_garbage"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not args.archive.is_file():
        raise SystemExit(f"Dataset archive not found: {args.archive}")
    if args.output.exists():
        raise SystemExit(f"Output already exists: {args.output}; it will not be overwritten.")

    with zipfile.ZipFile(args.archive) as archive:
        grouped: dict[str, list[tuple[str, zipfile.ZipInfo]]] = defaultdict(list)
        skipped = 0
        for info in archive.infolist():
            if info.is_dir() or PurePosixPath(info.filename).suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            parts = PurePosixPath(info.filename).parts
            if len(parts) < 3 or parts[-2].lower() not in LABELS:
                skipped += 1
                continue
            label = parts[-2].lower()
            if info.file_size > 40_000_000:
                raise SystemExit(f"Refusing unusually large image member: {info.filename}")
            digest = hashlib.sha256(archive.read(info)).hexdigest()
            grouped[digest].append((label, info))

    by_label: dict[str, dict[str, zipfile.ZipInfo]] = defaultdict(dict)
    conflicting_duplicates = 0
    for digest, copies in grouped.items():
        labels = {label for label, _ in copies}
        if len(labels) > 1:
            conflicting_duplicates += 1
            continue
        label = next(iter(labels))
        by_label[label][digest] = copies[0][1]
    entries = [(label, digest, info) for label, images in by_label.items() for digest, info in images.items()]

    missing = sorted(LABELS - set(by_label))
    if missing:
        raise SystemExit(f"Archive is missing expected class folders: {', '.join(missing)}")

    rng = random.Random(args.seed)
    split_for: dict[tuple[str, str], str] = {}
    for label in sorted(by_label):
        hashes = sorted(by_label[label])
        rng.shuffle(hashes)
        if len(hashes) < 10:
            raise SystemExit(f"Class '{label}' has too few unique images ({len(hashes)}).")
        test_n = max(1, round(len(hashes) * 0.15))
        val_n = max(1, round(len(hashes) * 0.15))
        for index, digest in enumerate(hashes):
            split = "test" if index < test_n else "validation" if index < test_n + val_n else "train"
            split_for[(label, digest)] = split

    args.output.mkdir(parents=True)
    counts: dict[tuple[str, str], int] = defaultdict(int)
    with zipfile.ZipFile(args.archive) as archive, (args.output / "preparation_manifest.csv").open("w", newline="", encoding="utf-8") as manifest:
        writer = csv.writer(manifest)
        writer.writerow(["source_file", "class_label", "split", "sha256"])
        for label, digest, info in entries:
            split = split_for[(label, digest)]
            folder = args.output / split / label
            folder.mkdir(parents=True, exist_ok=True)
            suffix = PurePosixPath(info.filename).suffix.lower()
            destination = folder / f"{digest[:20]}{suffix}"
            destination.write_bytes(archive.read(info))
            writer.writerow([info.filename, label, split, digest])
            counts[(split, label)] += 1

    attribution = args.output / "DATASET_ATTRIBUTION.txt"
    attribution.write_text(
        "Dataset supplied by the user: Garbage Classification (12 classes), "
        "matching https://www.kaggle.com/datasets/mostafaabla/garbage-classification\n"
        "The ZIP did not include a license or attribution file. Confirm the dataset page's "
        "current terms before redistribution or public release. Educational use only as requested.\n",
        encoding="utf-8",
    )
    print(f"Prepared {sum(counts.values())} unique images at {args.output} ({skipped} unrelated files and {conflicting_duplicates} cross-label duplicate groups skipped).")
    for split in ("train", "validation", "test"):
        print(f"{split}:")
        for label in sorted(LABELS):
            print(f"  {label:14s} {counts[(split, label)]:5d}")
    print("Exact duplicate files were removed before the split; see preparation_manifest.csv for source traceability.")


if __name__ == "__main__":
    main()
