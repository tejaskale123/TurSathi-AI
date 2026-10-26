#!/usr/bin/env python3
"""
TurSathi AI - Dataset Integrity Analysis, Conflict Quarantine & Clean Split Generator
Phase B Implementation:
1. Cryptographically hashes (SHA-256 and MD5) all images in datasets/pigeonpea_disease_final/.
2. Identifies all cross-class duplicate conflicts and cross-split duplicates.
3. Generates a structured duplicate/conflict audit CSV and JSON report in reports/.
4. Constructs a clean, leak-free, conflict-free stratified split manifest (70% train / 15% val / 15% test).
5. Quarantines ambiguous conflicting image hashes without deleting or moving any source files.
"""

import os
import csv
import json
import hashlib
import random
from pathlib import Path
from collections import defaultdict, Counter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DATASET_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final"
REPORTS_DIR = PROJECT_ROOT / "reports"
RETRAINING_DIR = PROJECT_ROOT / "ml" / "retraining"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
RETRAINING_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
EXPECTED_CLASSES = ["Healthy", "Leaf_Spot", "Leaf_webber", "Sterilic_mosaic", "Wilt"]

def run_dataset_audit():
    print("=" * 70)
    print("TUR SATHI AI - DATASET INTEGRITY & CONFLICT AUDIT")
    print("=" * 70)

    # 1. Read all image records
    records = []
    splits = ["train", "val", "test"]

    for split in splits:
        split_dir = SOURCE_DATASET_DIR / split
        if not split_dir.exists():
            continue
        for class_name in sorted(os.listdir(split_dir)):
            c_dir = split_dir / class_name
            if not c_dir.is_dir():
                continue
            for fname in sorted(os.listdir(c_dir)):
                fp = c_dir / fname
                if not fp.is_file() or fname.startswith("."):
                    continue
                if fp.suffix.lower() not in VALID_EXTENSIONS:
                    continue
                
                file_bytes = fp.read_bytes()
                sha256 = hashlib.sha256(file_bytes).hexdigest()
                md5 = hashlib.md5(file_bytes).hexdigest()
                size = fp.stat().st_size
                rel_path = fp.relative_to(PROJECT_ROOT).as_posix()

                records.append({
                    "split": split,
                    "class": class_name,
                    "filename": fname,
                    "relative_path": rel_path,
                    "size_bytes": size,
                    "md5": md5,
                    "sha256": sha256
                })

    total_records = len(records)
    print(f"Total image files discovered in production dataset: {total_records}")

    # 2. Group by SHA-256
    by_hash = defaultdict(list)
    for r in records:
        by_hash[r["sha256"]].append(r)

    total_unique_hashes = len(by_hash)
    print(f"Total unique cryptographic SHA-256 hashes: {total_unique_hashes}")

    # 3. Detect duplicate groups and label conflicts
    conflict_groups = []
    same_class_dup_groups = []

    group_id = 1
    for h, group in by_hash.items():
        if len(group) > 1:
            classes = sorted(set(x["class"] for x in group))
            splits_present = sorted(set(x["split"] for x in group))
            if len(classes) > 1:
                conflict_groups.append({
                    "group_id": group_id,
                    "sha256": h,
                    "classes": classes,
                    "splits": splits_present,
                    "count": len(group),
                    "items": group
                })
                group_id += 1
            else:
                same_class_dup_groups.append({
                    "group_id": group_id,
                    "sha256": h,
                    "class": classes[0],
                    "splits": splits_present,
                    "count": len(group),
                    "items": group
                })
                group_id += 1

    print(f"Cross-class label conflict groups: {len(conflict_groups)}")
    print(f"Same-class cross-split duplicate groups: {len(same_class_dup_groups)}")

    # 4. Generate duplicate and conflict CSV report
    csv_path = REPORTS_DIR / "duplicate_and_label_conflicts.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Group_ID", "Conflict_Type", "SHA256", "Contradictory_Classes",
            "Splits_Involved", "File_Count", "File_Path", "Original_Split", "Original_Class"
        ])
        for grp in conflict_groups:
            c_str = " | ".join(grp["classes"])
            s_str = " | ".join(grp["splits"])
            for it in grp["items"]:
                writer.writerow([
                    grp["group_id"], "CROSS_CLASS_LABEL_CONFLICT", grp["sha256"],
                    c_str, s_str, grp["count"], it["relative_path"], it["split"], it["class"]
                ])
        for grp in same_class_dup_groups:
            s_str = " | ".join(grp["splits"])
            for it in grp["items"]:
                writer.writerow([
                    grp["group_id"], "SAME_CLASS_DUPLICATE", grp["sha256"],
                    grp["class"], s_str, grp["count"], it["relative_path"], it["split"], it["class"]
                ])
    print(f"Wrote detailed duplicate review CSV -> {csv_path.relative_to(PROJECT_ROOT)}")

    # 5. Build Clean Stratified Split Manifest
    # Quarantine any hash in conflict_groups
    quarantined_hashes = set(x["sha256"] for x in conflict_groups)
    print(f"Total quarantined image hashes (due to conflicting labels): {len(quarantined_hashes)}")

    # Gather clean unique items
    clean_items_by_class = defaultdict(list)
    manifest_records = []

    # First, record quarantined files
    for grp in conflict_groups:
        for it in grp["items"]:
            manifest_records.append({
                "sha256": it["sha256"],
                "md5": it["md5"],
                "source_relative_path": it["relative_path"],
                "filename": it["filename"],
                "original_split": it["split"],
                "original_class": it["class"],
                "clean_split": "quarantine",
                "clean_class": "quarantine",
                "status": "quarantined_conflict",
                "quarantine_reason": f"Conflicting labels: {', '.join(grp['classes'])} (Group {grp['group_id']})"
            })

    # For valid hashes, pick ONE representative file per unique hash
    valid_hashes = set(by_hash.keys()) - quarantined_hashes

    # Track same-class duplicates (keep 1st, mark others as deduplicated)
    for h in sorted(valid_hashes):
        group = by_hash[h]
        rep = group[0]
        clean_items_by_class[rep["class"]].append(rep)
        if len(group) > 1:
            for extra in group[1:]:
                manifest_records.append({
                    "sha256": extra["sha256"],
                    "md5": extra["md5"],
                    "source_relative_path": extra["relative_path"],
                    "filename": extra["filename"],
                    "original_split": extra["split"],
                    "original_class": extra["class"],
                    "clean_split": "quarantine",
                    "clean_class": extra["class"],
                    "status": "quarantined_deduplicate",
                    "quarantine_reason": f"Exact duplicate of representative {rep['relative_path']}"
                })

    # Stratified split for clean unique images: 70% train, 15% val, 15% test
    random.seed(SEED)
    clean_split_counts = defaultdict(lambda: Counter())

    for c in EXPECTED_CLASSES:
        items = clean_items_by_class[c]
        random.shuffle(items)
        n = len(items)
        n_train = int(round(n * 0.70))
        n_val = int(round(n * 0.15))
        # Ensure remaining go to test
        n_test = n - n_train - n_val

        train_set = items[:n_train]
        val_set = items[n_train:n_train + n_val]
        test_set = items[n_train + n_val:]

        for it in train_set:
            clean_split_counts[c]["train"] += 1
            manifest_records.append({
                "sha256": it["sha256"],
                "md5": it["md5"],
                "source_relative_path": it["relative_path"],
                "filename": it["filename"],
                "original_split": it["split"],
                "original_class": it["class"],
                "clean_split": "train",
                "clean_class": c,
                "status": "included",
                "quarantine_reason": None
            })

        for it in val_set:
            clean_split_counts[c]["val"] += 1
            manifest_records.append({
                "sha256": it["sha256"],
                "md5": it["md5"],
                "source_relative_path": it["relative_path"],
                "filename": it["filename"],
                "original_split": it["split"],
                "original_class": it["class"],
                "clean_split": "val",
                "clean_class": c,
                "status": "included",
                "quarantine_reason": None
            })

        for it in test_set:
            clean_split_counts[c]["test"] += 1
            manifest_records.append({
                "sha256": it["sha256"],
                "md5": it["md5"],
                "source_relative_path": it["relative_path"],
                "filename": it["filename"],
                "original_split": it["split"],
                "original_class": it["class"],
                "clean_split": "test",
                "clean_class": c,
                "status": "included",
                "quarantine_reason": None
            })

    print("\nClean Dataset Stratified Split (Leak-Free & Conflict-Free):")
    print(f"{'Class':18s} | {'Train':>6s} | {'Val':>6s} | {'Test':>6s} | {'Total Clean':>11s}")
    print("-" * 55)
    total_train = total_val = total_test = 0
    for c in EXPECTED_CLASSES:
        tr = clean_split_counts[c]["train"]
        va = clean_split_counts[c]["val"]
        te = clean_split_counts[c]["test"]
        tot = tr + va + te
        total_train += tr
        total_val += va
        total_test += te
        print(f"{c:18s} | {tr:6d} | {va:6d} | {te:6d} | {tot:11d}")
    print("-" * 55)
    total_clean = total_train + total_val + total_test
    print(f"{'TOTAL':18s} | {total_train:6d} | {total_val:6d} | {total_test:6d} | {total_clean:11d}")
    print(f"Quarantined files: {total_records - total_clean} ({len(conflict_groups)} unique conflict hashes)")

    # 6. Save Clean Manifest (JSON and CSV)
    clean_manifest_json = RETRAINING_DIR / "clean_dataset_manifest.json"
    clean_manifest_csv = RETRAINING_DIR / "clean_dataset_manifest.csv"

    manifest_data = {
        "dataset_name": "TurSathi Pigeonpea Clean Retraining Dataset",
        "created_at": "2026-10-26",
        "random_seed": SEED,
        "classes": EXPECTED_CLASSES,
        "summary": {
            "total_source_files": total_records,
            "total_unique_hashes": total_unique_hashes,
            "total_quarantined_files": total_records - total_clean,
            "total_clean_unique_images": total_clean,
            "splits": {
                "train": total_train,
                "val": total_val,
                "test": total_test
            },
            "per_class_clean_counts": {c: dict(clean_split_counts[c]) for c in EXPECTED_CLASSES}
        },
        "records": manifest_records
    }

    with open(clean_manifest_json, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    print(f"\nWrote Clean Manifest JSON -> {clean_manifest_json.relative_to(PROJECT_ROOT)}")

    with open(clean_manifest_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "sha256", "md5", "source_relative_path", "filename", "original_split",
            "original_class", "clean_split", "clean_class", "status", "quarantine_reason"
        ])
        writer.writeheader()
        writer.writerows(manifest_records)
    print(f"Wrote Clean Manifest CSV -> {clean_manifest_csv.relative_to(PROJECT_ROOT)}")

    # 7. Save Comprehensive Dataset Integrity Report
    integrity_report_json = REPORTS_DIR / "dataset_integrity_report.json"
    report_content = {
        "audit_timestamp": "2026-10-26",
        "source_dataset": str(SOURCE_DATASET_DIR.relative_to(PROJECT_ROOT)),
        "classes": EXPECTED_CLASSES,
        "total_files_audited": total_records,
        "unique_hashes": total_unique_hashes,
        "duplicate_groups_count": len(conflict_groups) + len(same_class_dup_groups),
        "conflicting_label_groups_count": len(conflict_groups),
        "conflicting_files_count": sum(grp["count"] for grp in conflict_groups),
        "conflict_combinations": dict(Counter(" & ".join(grp["classes"]) for grp in conflict_groups)),
        "quarantined_count": total_records - total_clean,
        "clean_dataset_size": total_clean,
        "clean_split_summary": {
            "train": total_train,
            "val": total_val,
            "test": total_test,
            "by_class": {c: dict(clean_split_counts[c]) for c in EXPECTED_CLASSES}
        }
    }

    with open(integrity_report_json, "w", encoding="utf-8") as f:
        json.dump(report_content, f, indent=2)
    print(f"Wrote Dataset Integrity Report JSON -> {integrity_report_json.relative_to(PROJECT_ROOT)}")
    print("=" * 70)

if __name__ == "__main__":
    run_dataset_audit()
