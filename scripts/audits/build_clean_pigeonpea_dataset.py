# -*- coding: utf-8 -*-
"""
TurSathi AI - Phase 3: Build Clean Pigeonpea Candidate Dataset v1
Constructs datasets/pigeonpea_disease_clean_candidate_v1 from approved manifests.

Safety Rules:
- 100% Non-Destructive: Source files are only read/copied; never moved or deleted.
- Original dataset datasets/pigeonpea_disease_final remains byte-identical.
- Checkpoint models/best_pigeonpea_disease_final_efficientnet_b0.pth remains byte-identical.
- Clean dataset output to datasets/pigeonpea_disease_clean_candidate_v1.
- Build reports output to reports/pigeonpea_clean_candidate_build/.
"""

import sys
import os
import shutil
import csv
import json
import hashlib
import time
from pathlib import Path
from collections import defaultdict, Counter

# Windows encoding safety
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DATASET_ROOT = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final"
DEST_DATASET_ROOT = PROJECT_ROOT / "datasets" / "pigeonpea_disease_clean_candidate_v1"
CHECKPOINT_PATH = PROJECT_ROOT / "models" / "best_pigeonpea_disease_final_efficientnet_b0.pth"

MANIFEST_DIR = PROJECT_ROOT / "reports" / "pigeonpea_dataset_repair_plan" / "data"
AUDIT_DATA_DIR = PROJECT_ROOT / "reports" / "pigeonpea_dataset_forensic_audit" / "data"
BUILD_REPORT_DIR = PROJECT_ROOT / "reports" / "pigeonpea_clean_candidate_build"

EXPECTED_CLASSES = ["Healthy", "Leaf_Spot", "Leaf_webber", "Sterilic_mosaic", "Wilt"]
SPLITS = ["train", "val", "test"]

def get_file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    start_time = time.time()
    BUILD_REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("TurSathi AI - Phase 3: Build Clean Pigeonpea Dataset")
    print(f"Source Dataset : {SRC_DATASET_ROOT}")
    print(f"Destination    : {DEST_DATASET_ROOT}")
    print(f"Report Dir     : {BUILD_REPORT_DIR}")
    print("=" * 80)

    # 1. Baseline checkpoint integrity check
    if not CHECKPOINT_PATH.exists():
        print(f"ERROR: Checkpoint {CHECKPOINT_PATH} not found!")
        sys.exit(1)
    pre_checkpoint_sha = get_file_sha256(CHECKPOINT_PATH)
    print(f"Verified Model Checkpoint SHA-256: {pre_checkpoint_sha[:16]}...")

    # 2. Baseline source dataset integrity check
    baseline_manifest_path = AUDIT_DATA_DIR / "08_sha256_manifest.json"
    with open(baseline_manifest_path, encoding="utf-8") as f:
        baseline_sha_map = json.load(f)
    print(f"Loaded {len(baseline_sha_map)} baseline file hashes for source dataset.")

    # 3. Load Phase 2 manifests
    proposed_manifest_path = MANIFEST_DIR / "04_proposed_group_aware_split_manifest.csv"
    exact_exclusion_path = MANIFEST_DIR / "01_exact_duplicate_exclusion_manifest.csv"
    wilt_family_path = MANIFEST_DIR / "03_wilt_source_family_manifest.csv"

    with open(proposed_manifest_path, encoding="utf-8") as f:
        proposed_rows = list(csv.DictReader(f))

    with open(exact_exclusion_path, encoding="utf-8") as f:
        exact_exclusions = list(csv.DictReader(f))

    with open(wilt_family_path, encoding="utf-8") as f:
        wilt_families = {r["relative_path"]: r for r in csv.DictReader(f)}

    print(f"\nManifest verification:")
    print(f"  Total rows in proposed split manifest: {len(proposed_rows)}")
    print(f"  Exact cross-class duplicate exclusions : {len(exact_exclusions)}")
    print(f"  Total Wilt family records indexed     : {len(wilt_families)}")

    # Filter candidate pool
    candidates = [r for r in proposed_rows if r["inclusion_status"] == "PROPOSED_CANDIDATE"]
    eval_augs_excluded = [r for r in proposed_rows if r["inclusion_status"] == "EXCLUDE_SYNTHETIC_EVAL_DERIVATIVE"]

    print(f"  Approved candidate images to build    : {len(candidates)}")
    print(f"  Excluded Wilt eval augmentations      : {len(eval_augs_excluded)}")

    # Verification: candidate count reconciliation
    expected_candidates = 1858 - len(exact_exclusions) - len(eval_augs_excluded)
    if len(candidates) != expected_candidates:
        print(f"INCONSISTENCY ERROR: Expected {expected_candidates} candidates but found {len(candidates)}!")
        sys.exit(1)
    print(f"  Reconciliation Check PASSED: 1858 - 111 - 71 = {len(candidates)}.")

    # 4. Prepare Destination Directory
    if DEST_DATASET_ROOT.exists():
        print(f"Cleaning previous build in {DEST_DATASET_ROOT}...")
        shutil.rmtree(DEST_DATASET_ROOT)

    for sp in SPLITS:
        for cls in EXPECTED_CLASSES:
            (DEST_DATASET_ROOT / sp / cls).mkdir(parents=True, exist_ok=True)

    # 5. Copy Candidate Images
    print("\n[Copying images to clean candidate dataset v1]...")
    copied_records = []
    class_split_counts = defaultdict(lambda: Counter())

    for idx, cand in enumerate(candidates, 1):
        src_rel = cand["relative_path"]
        src_abs = SRC_DATASET_ROOT / src_rel
        sp = cand["proposed_split"]
        cls = cand["assigned_class"]

        if not src_abs.exists():
            print(f"ERROR: Missing source image {src_abs}!")
            sys.exit(1)

        src_hash = get_file_sha256(src_abs)
        if src_hash != cand["file_sha256"]:
            print(f"INTEGRITY ERROR: Hash mismatch on source file {src_rel}!")
            sys.exit(1)

        # Destination filename: preserve original filename
        dst_filename = src_abs.name
        dst_rel = f"{sp}/{cls}/{dst_filename}"
        dst_abs = DEST_DATASET_ROOT / sp / cls / dst_filename

        # Copy using shutil.copy2 to preserve metadata
        shutil.copy2(src_abs, dst_abs)

        # Verify copied file
        dst_hash = get_file_sha256(dst_abs)
        if dst_hash != src_hash:
            print(f"COPY VERIFICATION ERROR: Destination hash mismatch on {dst_rel}!")
            sys.exit(1)

        # Family / provenance tracking
        family_id = "N/A"
        if cls == "Wilt" and src_rel in wilt_families:
            family_id = wilt_families[src_rel]["family_id"]

        copied_records.append({
            "candidate_id": f"CLEAN_{idx:04d}",
            "dest_relative_path": dst_rel,
            "split": sp,
            "class": cls,
            "filename": dst_filename,
            "file_sha256": dst_hash,
            "file_size": dst_abs.stat().st_size,
            "source_relative_path": src_rel,
            "source_family_id": family_id,
            "is_augmentation": cand["is_augmentation"],
            "upstream_source": cand["upstream_source"],
            "upstream_filename": cand["upstream_filename"]
        })
        class_split_counts[cls][sp] += 1

    print(f"Successfully copied {len(copied_records)} candidate images.")

    # 6. Post-Build Integrity Checks
    print("\n[Verifying Post-Build Integrity]...")

    # A. Checkpoint unchanged
    post_checkpoint_sha = get_file_sha256(CHECKPOINT_PATH)
    if post_checkpoint_sha != pre_checkpoint_sha:
        print("CRITICAL ERROR: Model checkpoint was modified during build!")
        sys.exit(1)
    else:
        print("CHECKPOINT INTEGRITY PASSED: Model checkpoint remains byte-identical.")

    # B. Source dataset unchanged
    source_mutations = []
    for rel_path, meta in baseline_sha_map.items():
        src_f = SRC_DATASET_ROOT / rel_path
        cur_sha = get_file_sha256(src_f)
        if cur_sha != meta["sha256"]:
            source_mutations.append(rel_path)

    if source_mutations:
        print(f"CRITICAL ERROR: {len(source_mutations)} original dataset files were mutated!")
        sys.exit(1)
    else:
        print("SOURCE DATASET INTEGRITY PASSED: All 1,858 original files remain byte-identical.")

    # 7. Write Manifest and Deliverables
    print("\nWriting build manifests...")
    manifest_out_path = BUILD_REPORT_DIR / "clean_candidate_v1_manifest.csv"
    with open(manifest_out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "candidate_id", "dest_relative_path", "split", "class", "filename",
            "file_sha256", "file_size", "source_relative_path", "source_family_id",
            "is_augmentation", "upstream_source", "upstream_filename"
        ])
        writer.writeheader()
        writer.writerows(copied_records)

    # Class / split reconciliation summary
    summary_counts = {}
    for cls in EXPECTED_CLASSES:
        counts = class_split_counts[cls]
        summary_counts[cls] = {
            "train": counts["train"],
            "val": counts["val"],
            "test": counts["test"],
            "total": sum(counts.values())
        }

    build_metadata = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "source_dataset_root": str(SRC_DATASET_ROOT),
        "dest_dataset_root": str(DEST_DATASET_ROOT),
        "checkpoint_path": str(CHECKPOINT_PATH),
        "checkpoint_sha256": post_checkpoint_sha,
        "total_source_images": len(baseline_sha_map),
        "excluded_exact_cross_class_duplicates": len(exact_exclusions),
        "excluded_wilt_eval_augmentations": len(eval_augs_excluded),
        "total_clean_candidate_images": len(copied_records),
        "per_class_counts": summary_counts,
        "elapsed_seconds": round(time.time() - start_time, 2)
    }

    with open(BUILD_REPORT_DIR / "build_metadata.json", "w", encoding="utf-8") as f:
        json.dump(build_metadata, f, indent=2)

    print("\n" + "=" * 80)
    print("CLEAN CANDIDATE DATASET V1 BUILD COMPLETE")
    print("=" * 80)
    print(f"Total Copied Files : {len(copied_records)}")
    print("Distribution by class and split:")
    for cls, cnts in summary_counts.items():
        print(f"  {cls:<18} Train={cnts['train']:<4} Val={cnts['val']:<4} Test={cnts['test']:<4} Total={cnts['total']}")

if __name__ == "__main__":
    main()
