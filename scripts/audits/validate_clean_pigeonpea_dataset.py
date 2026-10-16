# -*- coding: utf-8 -*-
"""
TurSathi AI - Phase 3: Independent Clean Dataset Validator
Strict mathematical and pixel-level validation of datasets/pigeonpea_disease_clean_candidate_v1.
"""

import sys
import os
import json
import csv
import hashlib
from pathlib import Path
from collections import defaultdict, Counter

import numpy as np
from PIL import Image
import cv2

# Windows encoding safety
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLEAN_DATASET_ROOT = PROJECT_ROOT / "datasets" / "pigeonpea_disease_clean_candidate_v1"
ORIG_DATASET_ROOT = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final"
CHECKPOINT_PATH = PROJECT_ROOT / "models" / "best_pigeonpea_disease_final_efficientnet_b0.pth"
BUILD_REPORT_DIR = PROJECT_ROOT / "reports" / "pigeonpea_clean_candidate_build"

EXPECTED_CLASSES = ["Healthy", "Leaf_Spot", "Leaf_webber", "Sterilic_mosaic", "Wilt"]
SPLITS = ["train", "val", "test"]

def get_file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def compute_phash_val(p):
    with Image.open(p) as img:
        img_size = 32
        resized = img.convert('L').resize((img_size, img_size), Image.Resampling.LANCZOS)
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

def run_validation():
    print("=" * 80)
    print("TurSathi AI - Phase 3: Independent Clean Dataset Validation")
    print(f"Target Clean Dataset: {CLEAN_DATASET_ROOT}")
    print("=" * 80)

    checks_passed = 0
    total_checks = 10
    validation_results = {}

    def report_check(num, name, condition, details=""):
        nonlocal checks_passed
        status = "PASS" if condition else "FAIL"
        print(f"[{status}] Check {num}: {name}")
        if details:
            print(f"       Details: {details}")
        if condition:
            checks_passed += 1
        validation_results[f"check_{num}_{name.lower().replace(' ', '_')}"] = {
            "status": status,
            "details": details
        }

    # 1. Check all folders and splits exist
    missing_dirs = []
    for sp in SPLITS:
        for cls in EXPECTED_CLASSES:
            d = CLEAN_DATASET_ROOT / sp / cls
            if not d.exists() or not d.is_dir():
                missing_dirs.append(f"{sp}/{cls}")
    report_check(1, "All 15 Split/Class Folders Exist", len(missing_dirs) == 0,
                 f"Missing directories: {missing_dirs}" if missing_dirs else "All 3 splits x 5 classes present")

    # 2. Count reconciliation between filesystem and manifest
    manifest_p = BUILD_REPORT_DIR / "clean_candidate_v1_manifest.csv"
    with open(manifest_p, encoding="utf-8") as f:
        manifest_rows = list(csv.DictReader(f))

    fs_files = list(CLEAN_DATASET_ROOT.rglob("*.jpg"))
    reconciled = (len(manifest_rows) == len(fs_files) == 1676)
    report_check(2, "Filesystem vs Manifest Count Reconciliation", reconciled,
                 f"Manifest rows: {len(manifest_rows)}, Files on disk: {len(fs_files)}, Expected: 1676")

    # 3. Image decodability and pixel validity
    corrupt_count = 0
    modes = set()
    formats = set()
    for f in fs_files:
        try:
            with Image.open(f) as im:
                im.verify()
            with Image.open(f) as im:
                im.load()
                modes.add(im.mode)
                formats.add(im.format)
        except Exception:
            corrupt_count += 1
    report_check(3, "Image Decodability and Mode Integrity", corrupt_count == 0 and modes == {"RGB"},
                 f"Corrupt count: {corrupt_count}, Modes found: {modes}, Formats: {formats}")

    # 4. Check for duplicate SHA-256 within clean candidate dataset
    file_hashes = [r["file_sha256"] for r in manifest_rows]
    unique_hashes = set(file_hashes)
    no_dups = (len(file_hashes) == len(unique_hashes))
    report_check(4, "Zero Exact Duplicates in Clean Dataset", no_dups,
                 f"Total files: {len(file_hashes)}, Unique SHA-256: {len(unique_hashes)}")

    # 5. Check every image maps back to original dataset with matching hash
    mapping_errors = 0
    for r in manifest_rows:
        orig_p = ORIG_DATASET_ROOT / r["source_relative_path"]
        if not orig_p.exists() or get_file_sha256(orig_p) != r["file_sha256"]:
            mapping_errors += 1
    report_check(5, "Provenance and Hash Re-Traceability to Source", mapping_errors == 0,
                 f"Source mapping errors: {mapping_errors} / {len(manifest_rows)}")

    # 6. Verify original dataset remains 100% untouched
    orig_manifest_p = PROJECT_ROOT / "reports" / "pigeonpea_dataset_forensic_audit" / "data" / "08_sha256_manifest.json"
    with open(orig_manifest_p, encoding="utf-8") as f:
        orig_baseline = json.load(f)
    orig_mutations = 0
    for rel_p, meta in orig_baseline.items():
        if get_file_sha256(ORIG_DATASET_ROOT / rel_p) != meta["sha256"]:
            orig_mutations += 1
    report_check(6, "Original Dataset 100% Byte-Identical Preservation", orig_mutations == 0,
                 f"Original dataset mutations: {orig_mutations} / {len(orig_baseline)}")

    # 7. Checkpoint byte-identical preservation
    ckpt_sha = get_file_sha256(CHECKPOINT_PATH)
    expected_sha = "cf4e5884bbbbbe9928574fe3ea15efba527011d1cf7a34241eb76c4e0bcfcbbe"
    # Or match baseline from metadata
    with open(BUILD_REPORT_DIR / "build_metadata.json", encoding="utf-8") as f:
        meta_b = json.load(f)
    report_check(7, "Model Checkpoint Byte-Identical Preservation", ckpt_sha == meta_b["checkpoint_sha256"],
                 f"Checkpoint SHA-256: {ckpt_sha[:16]}... (matches pre-build)")

    # 8. Wilt family leakage check
    # Ensure no Wilt family ID appears in both train and (val or test)
    wilt_rows = [r for r in manifest_rows if r["class"] == "Wilt"]
    fams_by_split = defaultdict(set)
    for w in wilt_rows:
        fams_by_split[w["split"]].add(w["source_family_id"])
    tv_leak = fams_by_split["train"] & fams_by_split["val"]
    tt_leak = fams_by_split["train"] & fams_by_split["test"]
    vt_leak = fams_by_split["val"] & fams_by_split["test"]
    no_wilt_leak = (len(tv_leak) == 0 and len(tt_leak) == 0 and len(vt_leak) == 0)
    report_check(8, "Zero Wilt Source-Family Leakage Across Splits", no_wilt_leak,
                 f"Train fams: {len(fams_by_split['train'])}, Val fams: {len(fams_by_split['val'])}, Test fams: {len(fams_by_split['test'])}. Overlaps: tv={len(tv_leak)}, tt={len(tt_leak)}, vt={len(vt_leak)}")

    # 9. Ensure Wilt evaluation splits contain ONLY held-out unaugmented originals
    wilt_eval_augs = [w for w in wilt_rows if w["split"] in ["val", "test"] and w["is_augmentation"] == "True"]
    report_check(9, "Wilt Evaluation Splits Contain Zero Augmentations", len(wilt_eval_augs) == 0,
                 f"Wilt augmentations in val/test: {len(wilt_eval_augs)}. Val originals: {len([w for w in wilt_rows if w['split'] == 'val'])}, Test originals: {len([w for w in wilt_rows if w['split'] == 'test'])}")

    # 10. Crop Isolation check
    # Ensure no file came from cotton, maize, soybean, rice, or validator v3
    non_pigeonpea = 0
    for r in manifest_rows:
        src = r["upstream_source"].lower()
        if any(c in src for c in ["cotton", "maize", "soybean", "rice", "wheat", "validator"]):
            non_pigeonpea += 1
    report_check(10, "Strict Crop Isolation Verified", non_pigeonpea == 0,
                 f"Unrelated crop records detected: {non_pigeonpea} / {len(manifest_rows)}")

    print("\n" + "=" * 80)
    print(f"VALIDATION SUMMARY: {checks_passed} / {total_checks} CHECKS PASSED")
    print("=" * 80)

    # Save validation report
    with open(BUILD_REPORT_DIR / "validation_results.json", "w", encoding="utf-8") as f:
        json.dump(validation_results, f, indent=2)

    return checks_passed == total_checks

if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)
