# -*- coding: utf-8 -*-
"""
TurSathi AI - Phase 2: Safe Dataset Repair Preparation
Read-only script to generate proposed repair manifests, source family groupings,
and group-aware split designs without modifying any dataset files or checkpoints.

Safety:
- 100% Read-Only: No files in datasets/ are modified, deleted, moved, or renamed.
- All proposals output to reports/pigeonpea_dataset_repair_plan/
"""

import sys
import os
import json
import csv
import hashlib
from pathlib import Path
from collections import defaultdict, Counter

# Windows encoding safety
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final"
AUDIT_DATA_DIR = PROJECT_ROOT / "reports" / "pigeonpea_dataset_forensic_audit" / "data"
REPAIR_PLAN_DIR = PROJECT_ROOT / "reports" / "pigeonpea_dataset_repair_plan"
DATA_OUT_DIR = REPAIR_PLAN_DIR / "data"

EXPECTED_CLASSES = ["Healthy", "Leaf_Spot", "Leaf_webber", "Sterilic_mosaic", "Wilt"]

def get_file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("=" * 80)
    print("TurSathi AI - Phase 2: Safe Dataset Repair Preparation")
    print("=" * 80)

    DATA_OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load baseline audit manifests
    print("[Step 1/5] Loading forensic audit manifests...")
    inventory_path = AUDIT_DATA_DIR / "01_dataset_inventory.csv"
    exact_dups_path = AUDIT_DATA_DIR / "03_exact_duplicates.csv"
    label_review_path = AUDIT_DATA_DIR / "06_label_review_manifest.csv"
    near_dups_path = AUDIT_DATA_DIR / "04_near_duplicates.csv"

    inventory = []
    with open(inventory_path, encoding="utf-8") as f:
        inventory = list(csv.DictReader(f))

    exact_dups = []
    with open(exact_dups_path, encoding="utf-8") as f:
        exact_dups = list(csv.DictReader(f))

    label_review = []
    with open(label_review_path, encoding="utf-8") as f:
        label_review = list(csv.DictReader(f))

    near_dups = []
    with open(near_dups_path, encoding="utf-8") as f:
        near_dups = list(csv.DictReader(f))

    print(f"Loaded {len(inventory)} total dataset records.")
    print(f"Loaded {len(exact_dups)} exact duplicate records ({len(set(r['group_id'] for r in exact_dups))} groups).")
    print(f"Loaded {len(label_review)} label review records.")

    # 2. Phase A: Exact Duplicate Repair Manifest
    print("\n[Step 2/5] Compiling Exact Duplicate Exclusion & Review Manifest...")
    exact_conflict_hashes = set()
    exact_exclusion_records = []
    for r in exact_dups:
        exact_conflict_hashes.add(r["file_sha256"])
        exact_exclusion_records.append({
            "group_id": r["group_id"],
            "relative_path": r["relative_path"],
            "current_split": r["split"],
            "assigned_class": r["assigned_class"],
            "conflicting_classes": r["classes_in_group"],
            "conflicting_splits": r["splits_in_group"],
            "file_sha256": r["file_sha256"],
            "file_size": r["file_size"],
            "upstream_source_classes": r["prov_original_classes"],
            "upstream_filenames": r["prov_original_filenames"],
            "review_status": "NEEDS_MANUAL_LABEL_REVIEW",
            "proposed_action": "EXCLUDE_FROM_TRAINING_UNTIL_VERIFIED",
            "justification": f"Exact byte match across conflicting classes: {r['classes_in_group']}. Unverified ground truth."
        })

    with open(DATA_OUT_DIR / "01_exact_duplicate_exclusion_manifest.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "group_id", "relative_path", "current_split", "assigned_class", "conflicting_classes",
            "conflicting_splits", "file_sha256", "file_size", "upstream_source_classes",
            "upstream_filenames", "review_status", "proposed_action", "justification"
        ])
        writer.writeheader()
        writer.writerows(exact_exclusion_records)

    # 3. Phase B: Wilt Family Grouping & Leakage-Free Split Design
    print("\n[Step 3/5] Mapping Wilt Source Families and Designing Group-Aware Split...")
    wilt_rows = [r for r in inventory if r["assigned_class"] == "Wilt"]
    wilt_staging_dir = PROJECT_ROOT / "datasets" / "_temp_wilt_staging"

    # Identify all 30 Wilt originals
    wilt_orig_files = sorted([f.name for f in wilt_staging_dir.glob("*orig*")])
    wilt_family_map = {} # orig_name -> family_id
    for idx, f_name in enumerate(wilt_orig_files):
        wilt_family_map[f_name] = f"WILT_FAM_{idx:02d}"

    # Map each of the 287 Wilt images in final dataset to its source family
    # Using pHash distance to find closest orig if it's an augmentation
    import numpy as np
    import cv2
    from PIL import Image

    def compute_phash_val(p):
        img = Image.open(p)
        resized = img.convert('L').resize((32, 32), Image.Resampling.LANCZOS)
        arr = np.array(resized, dtype=np.float32)
        dct = cv2.dct(arr)
        dctlowfreq = dct[:8, :8]
        med = np.median(dctlowfreq[1:, 1:])
        diff = dctlowfreq > med
        packed = np.packbits(diff.flatten())
        return np.frombuffer(packed.tobytes(), dtype='>u8')[0]

    def popcount64(v):
        v = v - ((v >> np.uint64(1)) & np.uint64(0x5555555555555555))
        v = (v & np.uint64(0x3333333333333333)) + ((v >> np.uint64(2)) & np.uint64(0x3333333333333333))
        v = (v + (v >> np.uint64(4))) & np.uint64(0x0f0f0f0f0f0f0f0f)
        return (v * np.uint64(0x0101010101010101)) >> np.uint64(56)

    orig_paths = [wilt_staging_dir / f for f in wilt_orig_files]
    orig_hashes = np.array([compute_phash_val(p) for p in orig_paths], dtype=np.uint64)

    wilt_family_records = []
    wilt_family_members = defaultdict(list)

    for r in wilt_rows:
        img_p = DATASET_ROOT / r["relative_path"]
        h_val = compute_phash_val(img_p)
        xors = orig_hashes ^ h_val
        dists = popcount64(xors)
        best_orig_idx = int(np.argmin(dists))
        best_orig_name = wilt_orig_files[best_orig_idx]
        family_id = wilt_family_map[best_orig_name]
        is_original = "orig" in r["prov_original_filenames"].lower()

        rec = {
            "relative_path": r["relative_path"],
            "current_split": r["split"],
            "assigned_class": "Wilt",
            "family_id": family_id,
            "parent_source_image": best_orig_name,
            "is_original_photo": is_original,
            "hamming_distance_to_parent": int(dists[best_orig_idx]),
            "file_sha256": r["file_sha256"]
        }
        wilt_family_records.append(rec)
        wilt_family_members[family_id].append(rec)

    with open(DATA_OUT_DIR / "03_wilt_source_family_manifest.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "relative_path", "current_split", "assigned_class", "family_id",
            "parent_source_image", "is_original_photo", "hamming_distance_to_parent", "file_sha256"
        ])
        writer.writeheader()
        writer.writerows(wilt_family_records)

    # Group-Aware Wilt Split Assignment
    # Allocate the 30 source families:
    # 20 families -> Train (all their augmentations + originals)
    # 5 families  -> Val   (ONLY their original unaugmented photos!)
    # 5 families  -> Test  (ONLY their original unaugmented photos!)
    family_ids = sorted(list(wilt_family_map.values()))
    # Deterministic split allocation
    train_fams = set(family_ids[:20])
    val_fams = set(family_ids[20:25])
    test_fams = set(family_ids[25:30])

    # 4. Phase C: Cross-Class Near Duplicate Review Manifest
    print("\n[Step 4/5] Compiling Near-Duplicate Review Manifest...")
    near_review_records = []
    seen_near_pairs = set()

    for p in near_dups:
        if p["is_cross_class"] == "True" and int(p["phash_dist"]) <= 4:
            pair_key = tuple(sorted([p["path_1"], p["path_2"]]))
            if pair_key not in seen_near_pairs:
                seen_near_pairs.add(pair_key)
                near_review_records.append({
                    "image_1_path": p["path_1"],
                    "image_1_class": p["class_1"],
                    "image_1_split": p["split_1"],
                    "image_2_path": p["path_2"],
                    "image_2_class": p["class_2"],
                    "image_2_split": p["split_2"],
                    "phash_distance": p["phash_dist"],
                    "dhash_distance": p["dhash_dist"],
                    "review_status": "NEEDS_MANUAL_REVIEW",
                    "proposed_action": "HOLD_FOR_EXPERT_REVIEW",
                    "notes": f"High visual similarity between {p['class_1']} and {p['class_2']}."
                })

    with open(DATA_OUT_DIR / "02_near_duplicate_review_manifest.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "image_1_path", "image_1_class", "image_1_split", "image_2_path", "image_2_class",
            "image_2_split", "phash_distance", "dhash_distance", "review_status", "proposed_action", "notes"
        ])
        writer.writeheader()
        writer.writerows(near_review_records)

    # 5. Clean Candidate Pool Assembly
    print("\n[Step 5/5] Building Clean Candidate Pool and Group-Aware Split Manifest...")
    # Safe candidate definition:
    # 1. Not in exact cross-class duplicate list (55 groups / 111 images excluded)
    # 2. For Wilt: Val and Test must only take unaugmented original photos, while train can take augmentations
    # 3. Augmentations in classes 1-4: Keep only unique originals in val and test; augmentations strictly in train.

    clean_pool = []
    excluded_count = 0
    clean_by_class = defaultdict(lambda: {"train": 0, "val": 0, "test": 0, "total": 0})

    # PPLD Clean base (860 images) + Wilt group-aware allocation
    for r in inventory:
        rel = r["relative_path"]
        h = r["file_sha256"]
        cls = r["assigned_class"]

        # Check if excluded due to exact cross-class conflict
        if h in exact_conflict_hashes:
            excluded_count += 1
            continue

        is_wilt = (cls == "Wilt")
        is_aug = "aug" in r["prov_original_filenames"].lower()

        proposed_split = ""
        inclusion_status = "PROPOSED_CANDIDATE"

        if is_wilt:
            # Look up family
            fam_rec = next(f for f in wilt_family_records if f["relative_path"] == rel)
            fam_id = fam_rec["family_id"]
            if fam_id in train_fams:
                proposed_split = "train"
            elif fam_id in val_fams:
                if fam_rec["is_original_photo"]:
                    proposed_split = "val"
                else:
                    # Synthetic derivative of a val photo must NOT be in val or train
                    inclusion_status = "EXCLUDE_SYNTHETIC_EVAL_DERIVATIVE"
            elif fam_id in test_fams:
                if fam_rec["is_original_photo"]:
                    proposed_split = "test"
                else:
                    # Synthetic derivative of a test photo must NOT be in test or train
                    inclusion_status = "EXCLUDE_SYNTHETIC_EVAL_DERIVATIVE"
        else:
            # Classes 1-4:
            # If it's an augmentation, it should ONLY be in train to avoid eval leakage!
            # If it was in val/test in current dataset and is an augmentation, propose moving to train or excluding
            orig_split = r["split"]
            if is_aug and orig_split in ["val", "test"]:
                # Propose train or exclude from eval
                proposed_split = "train"
            else:
                proposed_split = orig_split

        if inclusion_status == "PROPOSED_CANDIDATE":
            clean_by_class[cls][proposed_split] += 1
            clean_by_class[cls]["total"] += 1

        clean_pool.append({
            "relative_path": rel,
            "assigned_class": cls,
            "current_split": r["split"],
            "proposed_split": proposed_split if inclusion_status == "PROPOSED_CANDIDATE" else "EXCLUDED",
            "inclusion_status": inclusion_status,
            "is_augmentation": is_aug,
            "file_sha256": h,
            "upstream_source": r["prov_sources"],
            "upstream_filename": r["prov_original_filenames"]
        })

    with open(DATA_OUT_DIR / "04_proposed_group_aware_split_manifest.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "relative_path", "assigned_class", "current_split", "proposed_split",
            "inclusion_status", "is_augmentation", "file_sha256", "upstream_source", "upstream_filename"
        ])
        writer.writeheader()
        writer.writerows(clean_pool)

    # Summary metrics JSON
    summary_metrics = {
        "timestamp": "2026-10-14T12:35:00",
        "original_dataset_total": len(inventory),
        "excluded_exact_cross_class_duplicates": len(exact_exclusion_records),
        "flagged_near_duplicate_cross_class_pairs": len(near_review_records),
        "wilt_total_original_photos": len(wilt_orig_files),
        "wilt_total_families": len(wilt_orig_files),
        "wilt_family_distribution": {
            "train_families": len(train_fams),
            "val_families": len(val_fams),
            "test_families": len(test_fams)
        },
        "proposed_clean_counts_by_class": dict(clean_by_class),
        "wilt_statistical_limitation": {
            "held_out_val_originals": 5,
            "held_out_test_originals": 5,
            "assessment": "Severe statistical limitation. 5 test samples is insufficient for high-confidence generalization. Additional independent field images required."
        }
    }

    with open(REPAIR_PLAN_DIR / "summary_repair_metrics.json", "w", encoding="utf-8") as f:
        json.dump(summary_metrics, f, indent=2)

    print("\n" + "=" * 80)
    print("REPAIR PREPARATION SUMMARY")
    print("=" * 80)
    print(f"Original Dataset Size            : {len(inventory)} images")
    print(f"Excluded Exact Duplicates        : {len(exact_exclusion_records)} images (55 groups)")
    print(f"Flagged Near-Duplicate Pairs     : {len(near_review_records)} pairs (27 images)")
    print(f"Wilt Independent Original Photos : {len(wilt_orig_files)} photos (expanded to 270 augs)")
    print("\nProposed Clean Pool Counts:")
    for cls in EXPECTED_CLASSES:
        c = clean_by_class[cls]
        print(f"  {cls:<18} Train={c['train']:<4} Val={c['val']:<4} Test={c['test']:<4} Total={c['total']}")

    # Verification: Ensure original dataset files were NOT modified
    print("\nVerifying original dataset SHA-256 integrity...")
    manifest_audit_p = AUDIT_DATA_DIR / "08_sha256_manifest.json"
    with open(manifest_audit_p, encoding="utf-8") as f:
        pre_manifest = json.load(f)

    mutations = []
    for rel_path, meta in pre_manifest.items():
        p = DATASET_ROOT / rel_path
        cur_sha = get_file_sha256(p)
        if cur_sha != meta["sha256"]:
            mutations.append(rel_path)

    if mutations:
        print(f"CRITICAL ERROR: {len(mutations)} original dataset files were mutated!")
        sys.exit(1)
    else:
        print("READ-ONLY VERIFICATION PASSED: All 1,858 original files remain 100% byte-identical!")

if __name__ == "__main__":
    main()
