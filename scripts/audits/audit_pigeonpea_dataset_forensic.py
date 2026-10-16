# -*- coding: utf-8 -*-
"""
TurSathi AI - Pigeonpea Disease Dataset Forensic Audit
Read-only forensic inspection of datasets/pigeonpea_disease_final
and upstream provenance sources.

Safety Rules:
- 100% Read-Only: No files are created, modified, renamed, or deleted in the dataset.
- Deterministic execution with fixed seeds and explicit error handling.
- Audit artifacts saved exclusively to reports/pigeonpea_dataset_forensic_audit/
"""

import sys
import os
import json
import csv
import hashlib
import time
from pathlib import Path
from collections import defaultdict, Counter

import numpy as np
from PIL import Image
import cv2

# Set stdout/stderr encoding on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "pigeonpea_dataset_forensic_audit"
DATA_OUTPUT_DIR = OUTPUT_DIR / "data"

EXPECTED_CLASSES = ["Healthy", "Leaf_Spot", "Leaf_webber", "Sterilic_mosaic", "Wilt"]
SPLITS = ["train", "val", "test"]
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}

def get_file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def get_decoded_pixel_sha256(img):
    rgb_img = img.convert("RGB")
    return hashlib.sha256(rgb_img.tobytes()).hexdigest()

def compute_dhash(img, hash_size=8):
    resized = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    arr = np.array(resized)
    diff = arr[:, 1:] > arr[:, :-1]
    packed = np.packbits(diff.flatten())
    # Return as uint64
    return np.frombuffer(packed.tobytes(), dtype=">u8")[0]

def compute_phash(img, hash_size=8, highfreq_factor=4):
    img_size = hash_size * highfreq_factor
    resized = img.convert("L").resize((img_size, img_size), Image.Resampling.LANCZOS)
    arr = np.array(resized, dtype=np.float32)
    dct = cv2.dct(arr)
    dctlowfreq = dct[:hash_size, :hash_size]
    med = np.median(dctlowfreq[1:, 1:])
    diff = dctlowfreq > med
    packed = np.packbits(diff.flatten())
    # Return as uint64
    return np.frombuffer(packed.tobytes(), dtype=">u8")[0]

def popcount64(v):
    # Vectorized 64-bit Hamming weight
    v = v - ((v >> np.uint64(1)) & np.uint64(0x5555555555555555))
    v = (v & np.uint64(0x3333333333333333)) + ((v >> np.uint64(2)) & np.uint64(0x3333333333333333))
    v = (v + (v >> np.uint64(4))) & np.uint64(0x0f0f0f0f0f0f0f0f)
    return (v * np.uint64(0x0101010101010101)) >> np.uint64(56)

def index_upstream_sources():
    print("Indexing upstream provenance sources...")
    upstream_index = {}
    sources = [
        ("PPLD_extracted", PROJECT_ROOT / "PPLD_extracted"),
        ("PPLD_processed", PROJECT_ROOT / "PPLD_processed"),
        ("temp_wilt_staging", PROJECT_ROOT / "datasets" / "_temp_wilt_staging"),
        ("new_disease_images", PROJECT_ROOT / "datasets" / "new_disease_images"),
    ]
    for source_name, source_path in sources:
        if not source_path.exists():
            continue
        for f in source_path.rglob("*"):
            if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS:
                try:
                    h = get_file_sha256(f)
                    rel_p = str(f.relative_to(PROJECT_ROOT))
                    upstream_index.setdefault(h, []).append({
                        "source": source_name,
                        "path": rel_p,
                        "parent": f.parent.name,
                        "filename": f.name
                    })
                except Exception as e:
                    pass
    print(f"Indexed {len(upstream_index)} unique file hashes across upstream sources.")
    return upstream_index

def run_audit():
    start_time = time.time()
    DATA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("TurSathi AI - Five-Class Pigeonpea Dataset Forensic Audit")
    print(f"Dataset Target: {DATASET_ROOT}")
    print(f"Audit Output  : {OUTPUT_DIR}")
    print("=" * 80)

    if not DATASET_ROOT.exists():
        print(f"ERROR: Dataset root {DATASET_ROOT} does not exist.")
        sys.exit(1)

    # 1. Index upstream sources for provenance tracking
    upstream_index = index_upstream_sources()

    # 2. Collect all files and record pre-audit hashes
    print("\n[Step 1/6] Scanning and validating all files in dataset...")
    all_files = []
    pre_audit_manifest = {}

    for split in SPLITS:
        split_dir = DATASET_ROOT / split
        if not split_dir.exists():
            continue
        for cls in EXPECTED_CLASSES:
            cls_dir = split_dir / cls
            if not cls_dir.exists():
                continue
            for f in sorted(cls_dir.iterdir()):
                if f.is_file():
                    all_files.append((split, cls, f))

    # Also detect any rogue files outside the standard split/class structure
    rogue_files = []
    for f in DATASET_ROOT.rglob("*"):
        if f.is_file():
            rel = f.relative_to(DATASET_ROOT)
            parts = rel.parts
            if len(parts) != 3 or parts[0] not in SPLITS or parts[1] not in EXPECTED_CLASSES:
                rogue_files.append(str(rel))

    print(f"Total structured dataset files found: {len(all_files)}")
    print(f"Rogue / misplaced files found      : {len(rogue_files)}")

    # 3. File inventory and corruption inspection
    file_records = []
    corrupt_records = []
    dhash_list = []
    phash_list = []

    print("\n[Step 2/6] Deep pixel decoding, format validation, and perceptual hashing...")
    for idx, (split, cls, file_path) in enumerate(all_files):
        rel_path = str(file_path.relative_to(DATASET_ROOT))
        file_size = file_path.stat().st_size
        file_sha256 = get_file_sha256(file_path)
        pre_audit_manifest[rel_path] = {
            "size": file_size,
            "sha256": file_sha256,
            "mtime": file_path.stat().st_mtime
        }

        ext = file_path.suffix.lower()
        is_corrupt = False
        error_detail = ""
        width, height = 0, 0
        img_format = ""
        img_mode = ""
        aspect_ratio = 0.0
        pixel_sha256 = ""
        dh = np.uint64(0)
        ph = np.uint64(0)

        # Size check
        if file_size == 0:
            is_corrupt = True
            error_detail = "ZERO_BYTE_FILE"

        # Image integrity check
        if not is_corrupt:
            try:
                # 1. Structural verify
                with Image.open(file_path) as img:
                    img_format = img.format or ""
                    img_mode = img.mode or ""
                    width, height = img.size
                    img.verify()
                
                # Format vs extension mismatch check
                ext_clean = ext.lstrip(".")
                if ext_clean in ["jpg", "jpeg"] and img_format.lower() not in ["jpeg", "jpg"]:
                    error_detail = f"FORMAT_MISMATCH: ext={ext} but actual format={img_format}"
                elif ext_clean == "png" and img_format.lower() != "png":
                    error_detail = f"FORMAT_MISMATCH: ext={ext} but actual format={img_format}"

                # 2. Pixel load and decode
                with Image.open(file_path) as img:
                    img.load()
                    aspect_ratio = round(width / max(height, 1), 4)
                    pixel_sha256 = get_decoded_pixel_sha256(img)
                    dh = compute_dhash(img)
                    ph = compute_phash(img)

                # Channels / mode anomalies
                if img_mode not in ["RGB", "L"]:
                    if not error_detail:
                        error_detail = f"UNUSUAL_MODE: {img_mode}"

                if width < 32 or height < 32:
                    error_detail = f"EXTREME_SMALL_DIMENSIONS: {width}x{height}"

            except Exception as e:
                is_corrupt = True
                error_detail = f"DECODE_ERROR: {str(e)}"

        if is_corrupt or error_detail.startswith("FORMAT_MISMATCH") or error_detail.startswith("DECODE_ERROR"):
            corrupt_records.append({
                "relative_path": rel_path,
                "split": split,
                "class": cls,
                "file_size": file_size,
                "format": img_format,
                "mode": img_mode,
                "width": width,
                "height": height,
                "error": error_detail
            })

        # Upstream provenance matching
        prov = upstream_index.get(file_sha256, [])
        prov_sources = list({p["source"] for p in prov})
        prov_parents = list({p["parent"] for p in prov})
        prov_filenames = list({p["filename"] for p in prov})

        record = {
            "index": idx,
            "relative_path": rel_path,
            "filename": file_path.name,
            "split": split,
            "assigned_class": cls,
            "file_size": file_size,
            "extension": ext,
            "actual_format": img_format,
            "mode": img_mode,
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "file_sha256": file_sha256,
            "pixel_sha256": pixel_sha256,
            "dhash_hex": f"{dh:016x}",
            "phash_hex": f"{ph:016x}",
            "is_corrupt": is_corrupt,
            "anomaly": error_detail,
            "prov_sources": ";".join(prov_sources) if prov_sources else "UNKNOWN",
            "prov_original_classes": ";".join(prov_parents) if prov_parents else "UNKNOWN",
            "prov_original_filenames": ";".join(prov_filenames[:3]) if prov_filenames else "UNKNOWN"
        }
        file_records.append(record)
        dhash_list.append(dh)
        phash_list.append(ph)

    print(f"Processed {len(file_records)} images.")
    print(f"Corrupt / format anomaly records: {len(corrupt_records)}")

    # 4. Exact Duplicates & Near Duplicates Detection
    print("\n[Step 3/6] Detecting exact duplicates (byte & pixel level)...")
    sha_to_records = defaultdict(list)
    pixel_sha_to_records = defaultdict(list)

    for r in file_records:
        sha_to_records[r["file_sha256"]].append(r)
        if r["pixel_sha256"]:
            pixel_sha_to_records[r["pixel_sha256"]].append(r)

    exact_dup_groups = [g for g in sha_to_records.values() if len(g) > 1]
    pixel_exact_groups = [g for g in pixel_sha_to_records.values() if len(g) > 1]

    print(f"Exact file-hash duplicate groups : {len(exact_dup_groups)} (total duplicate instances: {sum(len(g) for g in exact_dup_groups)})")
    print(f"Exact decoded-pixel groups       : {len(pixel_exact_groups)} (total duplicate instances: {sum(len(g) for g in pixel_exact_groups)})")

    # Detailed duplicate classification
    exact_duplicates_csv = []
    leakage_groups = []
    cross_class_exact_conflicts = []

    for group_id, g in enumerate(exact_dup_groups, 1):
        splits_in_group = {r["split"] for r in g}
        classes_in_group = {r["assigned_class"] for r in g}
        is_cross_split = len(splits_in_group) > 1
        is_cross_class = len(classes_in_group) > 1

        for r in g:
            exact_duplicates_csv.append({
                "group_id": group_id,
                "relative_path": r["relative_path"],
                "split": r["split"],
                "assigned_class": r["assigned_class"],
                "file_sha256": r["file_sha256"],
                "file_size": r["file_size"],
                "is_cross_split": is_cross_split,
                "splits_in_group": ";".join(sorted(splits_in_group)),
                "is_cross_class": is_cross_class,
                "classes_in_group": ";".join(sorted(classes_in_group)),
                "prov_original_classes": r["prov_original_classes"],
                "prov_original_filenames": r["prov_original_filenames"]
            })

        if is_cross_split:
            leakage_groups.append({
                "leakage_id": f"EXACT_LEAK_{group_id:03d}",
                "leakage_type": "EXACT_BYTE_DUPLICATE",
                "confidence": "CONFIRMED",
                "splits_involved": ";".join(sorted(splits_in_group)),
                "classes_involved": ";".join(sorted(classes_in_group)),
                "paths": [r["relative_path"] for r in g],
                "file_sha256": g[0]["file_sha256"],
                "notes": f"Byte-identical image appears in splits: {', '.join(sorted(splits_in_group))}"
            })

        if is_cross_class:
            cross_class_exact_conflicts.append({
                "conflict_id": f"EXACT_CLASS_CONF_{group_id:03d}",
                "confidence": "CONFIRMED_LABEL_CONFLICT",
                "classes_involved": ";".join(sorted(classes_in_group)),
                "splits_involved": ";".join(sorted(splits_in_group)),
                "paths": [r["relative_path"] for r in g],
                "file_sha256": g[0]["file_sha256"],
                "prov_classes": g[0]["prov_original_classes"],
                "notes": f"Identical image assigned to conflicting classes: {', '.join(sorted(classes_in_group))}"
            })

    # 5. Near Duplicate Detection using Vectorized Hamming Distance on pHash and dHash
    print("\n[Step 4/6] Computing perceptual similarity matrix (pHash & dHash)...")
    N = len(file_records)
    ph_array = np.array(phash_list, dtype=np.uint64)
    dh_array = np.array(dhash_list, dtype=np.uint64)

    # Compute pairwise XOR and popcount in chunks to minimize peak memory
    near_dup_pairs = []
    chunk_size = 500

    for i_start in range(0, N, chunk_size):
        i_end = min(i_start + chunk_size, N)
        ph_chunk = ph_array[i_start:i_end]
        dh_chunk = dh_array[i_start:i_end]

        # Pairwise distance matrices for chunk against all
        ph_xor = ph_chunk[:, None] ^ ph_array[None, :]
        dh_xor = dh_chunk[:, None] ^ dh_array[None, :]

        ph_dist = popcount64(ph_xor)
        dh_dist = popcount64(dh_xor)

        for i_rel in range(i_end - i_start):
            i = i_start + i_rel
            # Only consider j > i
            js = np.where((ph_dist[i_rel] <= 6) & (dh_dist[i_rel] <= 8))[0]
            for j in js:
                if j <= i:
                    continue
                
                r1 = file_records[i]
                r2 = file_records[j]

                # Skip exact duplicates already tracked
                if r1["file_sha256"] == r2["file_sha256"]:
                    continue

                p_d = int(ph_dist[i_rel, j])
                d_d = int(dh_dist[i_rel, j])

                near_dup_pairs.append({
                    "path_1": r1["relative_path"],
                    "split_1": r1["split"],
                    "class_1": r1["assigned_class"],
                    "path_2": r2["relative_path"],
                    "split_2": r2["split"],
                    "class_2": r2["assigned_class"],
                    "phash_dist": p_d,
                    "dhash_dist": d_d,
                    "is_cross_split": r1["split"] != r2["split"],
                    "is_cross_class": r1["assigned_class"] != r2["assigned_class"],
                    "prov_1": r1["prov_original_filenames"],
                    "prov_2": r2["prov_original_filenames"],
                })

    print(f"Near-duplicate pairs detected (pHash dist <= 6, dHash dist <= 8, non-exact): {len(near_dup_pairs)}")

    # Classify near-duplicate cross-split leakage and cross-class conflicts
    near_leakage_pairs = [p for p in near_dup_pairs if p["is_cross_split"]]
    near_cross_class_pairs = [p for p in near_dup_pairs if p["is_cross_class"]]

    print(f"  - Cross-split near-duplicate leakage pairs : {len(near_leakage_pairs)}")
    print(f"  - Cross-class near-duplicate conflict pairs : {len(near_cross_class_pairs)}")

    # 6. Label Review Manifest Assembly
    print("\n[Step 5/6] Building Label Quality & Wrong-Crop Review Manifest...")
    label_review_manifest = []

    # A. Exact conflicts
    for conf in cross_class_exact_conflicts:
        for p in conf["paths"]:
            rec = next(r for r in file_records if r["relative_path"] == p)
            label_review_manifest.append({
                "relative_path": rec["relative_path"],
                "split": rec["split"],
                "assigned_class": rec["assigned_class"],
                "review_category": "CONFIRMED_CROSS_CLASS_DUPLICATE",
                "severity": "CRITICAL",
                "confidence": "CONFIRMED",
                "evidence": f"Exact byte match across classes: {conf['classes_involved']}. Upstream prov: {rec['prov_original_classes']}",
                "upstream_source": rec["prov_sources"],
                "upstream_filenames": rec["prov_original_filenames"],
                "recommended_action": "EXCLUDE_OR_RESOLVE_LABEL"
            })

    # B. Near-duplicate cross-class conflicts (dist <= 4)
    seen_near_conflict_paths = set()
    for p in near_cross_class_pairs:
        if p["phash_dist"] <= 4:
            for path_key, split_key, cls_key, opp_cls in [
                ("path_1", "split_1", "class_1", p["class_2"]),
                ("path_2", "split_2", "class_2", p["class_1"])
            ]:
                pth = p[path_key]
                if pth not in seen_near_conflict_paths:
                    seen_near_conflict_paths.add(pth)
                    rec = next(r for r in file_records if r["relative_path"] == pth)
                    label_review_manifest.append({
                        "relative_path": rec["relative_path"],
                        "split": rec["split"],
                        "assigned_class": rec["assigned_class"],
                        "review_category": "SUSPECTED_CROSS_CLASS_NEAR_DUPLICATE",
                        "severity": "HIGH",
                        "confidence": "SUSPECTED",
                        "evidence": f"Perceptually near-identical (phash_dist={p['phash_dist']}, dhash_dist={p['dhash_dist']}) to image in {opp_cls}",
                        "upstream_source": rec["prov_sources"],
                        "upstream_filenames": rec["prov_original_filenames"],
                        "recommended_action": "NEEDS_MANUAL_REVIEW"
                    })

    # C. Wilt Synthetic Family Review:
    # Wilt class has 30 original images augmented to 300 images.
    # Check how many augmented wilt derivatives leak across splits!
    wilt_aug_leakage = []
    for p in near_leakage_pairs:
        if p["class_1"] == "Wilt" and p["class_2"] == "Wilt":
            wilt_aug_leakage.append(p)

    print(f"  - Wilt augmentation cross-split leakage pairs: {len(wilt_aug_leakage)}")

    # 7. Class & Split Counts Reconciliation
    print("\n[Step 6/6] Generating inventory, metrics, and reconciliation tables...")
    counts_table = defaultdict(lambda: defaultdict(int))
    unique_sha_table = defaultdict(lambda: defaultdict(set))

    for r in file_records:
        counts_table[r["assigned_class"]][r["split"]] += 1
        counts_table[r["assigned_class"]]["total"] += 1
        unique_sha_table[r["assigned_class"]][r["split"]].add(r["file_sha256"])
        unique_sha_table[r["assigned_class"]]["total"].add(r["file_sha256"])

    reconciliation_csv = []
    for cls in EXPECTED_CLASSES:
        train_cnt = counts_table[cls]["train"]
        val_cnt = counts_table[cls]["val"]
        test_cnt = counts_table[cls]["test"]
        total_cnt = counts_table[cls]["total"]

        train_u = len(unique_sha_table[cls]["train"])
        val_u = len(unique_sha_table[cls]["val"])
        test_u = len(unique_sha_table[cls]["test"])
        total_u = len(unique_sha_table[cls]["total"])

        reconciliation_csv.append({
            "class": cls,
            "train_count": train_cnt,
            "train_unique_sha": train_u,
            "val_count": val_cnt,
            "val_unique_sha": val_u,
            "test_count": test_cnt,
            "test_unique_sha": test_u,
            "total_count": total_cnt,
            "total_unique_sha": total_u,
            "duplicate_loss": total_cnt - total_u
        })

    # 8. Post-audit integrity verification: confirm 0 dataset mutations
    print("\nVerifying read-only integrity...")
    post_audit_manifest = {}
    mutations = []
    for split, cls, file_path in all_files:
        rel_path = str(file_path.relative_to(DATASET_ROOT))
        post_sha = get_file_sha256(file_path)
        post_size = file_path.stat().st_size
        post_mtime = file_path.stat().st_mtime
        pre = pre_audit_manifest[rel_path]
        if post_sha != pre["sha256"] or post_size != pre["size"]:
            mutations.append({
                "path": rel_path,
                "pre_sha": pre["sha256"],
                "post_sha": post_sha
            })

    if mutations:
        print(f"CRITICAL ERROR: {len(mutations)} files were mutated during the audit!")
    else:
        print("READ-ONLY VERIFICATION PASSED: 100% of dataset files remain byte-identical!")

    # 9. Write all CSV and JSON output files
    print("\nWriting audit deliverables...")

    # A. File inventory CSV
    with open(DATA_OUTPUT_DIR / "01_dataset_inventory.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "index", "relative_path", "filename", "split", "assigned_class", "file_size",
            "extension", "actual_format", "mode", "width", "height", "aspect_ratio",
            "file_sha256", "pixel_sha256", "dhash_hex", "phash_hex", "is_corrupt",
            "anomaly", "prov_sources", "prov_original_classes", "prov_original_filenames"
        ])
        writer.writeheader()
        writer.writerows(file_records)

    # B. Corrupt images CSV
    with open(DATA_OUTPUT_DIR / "02_corrupt_invalid_images.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "relative_path", "split", "class", "file_size", "format", "mode", "width", "height", "error"
        ])
        writer.writeheader()
        writer.writerows(corrupt_records)

    # C. Exact duplicates CSV
    with open(DATA_OUTPUT_DIR / "03_exact_duplicates.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "group_id", "relative_path", "split", "assigned_class", "file_sha256", "file_size",
            "is_cross_split", "splits_in_group", "is_cross_class", "classes_in_group",
            "prov_original_classes", "prov_original_filenames"
        ])
        writer.writeheader()
        writer.writerows(exact_duplicates_csv)

    # D. Near duplicates CSV
    with open(DATA_OUTPUT_DIR / "04_near_duplicates.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "path_1", "split_1", "class_1", "path_2", "split_2", "class_2",
            "phash_dist", "dhash_dist", "is_cross_split", "is_cross_class", "prov_1", "prov_2"
        ])
        writer.writeheader()
        writer.writerows(near_dup_pairs)

    # E. Split leakage CSV
    leakage_records = []
    for lk in leakage_groups:
        for p in lk["paths"]:
            rec = next(r for r in file_records if r["relative_path"] == p)
            leakage_records.append({
                "leakage_id": lk["leakage_id"],
                "leakage_type": lk["leakage_type"],
                "confidence": lk["confidence"],
                "relative_path": rec["relative_path"],
                "split": rec["split"],
                "assigned_class": rec["assigned_class"],
                "file_sha256": rec["file_sha256"],
                "splits_involved": lk["splits_involved"],
                "classes_involved": lk["classes_involved"],
                "notes": lk["notes"]
            })
    for idx, p in enumerate(near_leakage_pairs, 1):
        leakage_records.append({
            "leakage_id": f"NEAR_LEAK_{idx:03d}",
            "leakage_type": "PERCEPTUAL_NEAR_DUPLICATE",
            "confidence": "SUSPECTED",
            "relative_path": f"{p['path_1']} <-> {p['path_2']}",
            "split": f"{p['split_1']} <-> {p['split_2']}",
            "assigned_class": f"{p['class_1']} <-> {p['class_2']}",
            "file_sha256": "N/A",
            "splits_involved": f"{p['split_1']};{p['split_2']}",
            "classes_involved": f"{p['class_1']};{p['class_2']}",
            "notes": f"phash_dist={p['phash_dist']}, dhash_dist={p['dhash_dist']}"
        })
    with open(DATA_OUTPUT_DIR / "05_split_leakage.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "leakage_id", "leakage_type", "confidence", "relative_path", "split", "assigned_class",
            "file_sha256", "splits_involved", "classes_involved", "notes"
        ])
        writer.writeheader()
        writer.writerows(leakage_records)

    # F. Label review manifest CSV
    with open(DATA_OUTPUT_DIR / "06_label_review_manifest.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "relative_path", "split", "assigned_class", "review_category", "severity",
            "confidence", "evidence", "upstream_source", "upstream_filenames", "recommended_action"
        ])
        writer.writeheader()
        writer.writerows(label_review_manifest)

    # G. Reconciliation CSV
    with open(DATA_OUTPUT_DIR / "07_class_split_reconciliation.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "class", "train_count", "train_unique_sha", "val_count", "val_unique_sha",
            "test_count", "test_unique_sha", "total_count", "total_unique_sha", "duplicate_loss"
        ])
        writer.writeheader()
        writer.writerows(reconciliation_csv)

    # H. SHA256 integrity manifest JSON
    with open(DATA_OUTPUT_DIR / "08_sha256_manifest.json", "w", encoding="utf-8") as f:
        json.dump(pre_audit_manifest, f, indent=2)

    # Summary JSON
    summary_data = {
        "audit_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "dataset_root": str(DATASET_ROOT),
        "total_files": len(file_records),
        "total_unique_sha256": len(sha_to_records),
        "total_unique_decoded_pixels": len(pixel_sha_to_records),
        "total_corrupt_files": len(corrupt_records),
        "exact_duplicate_groups": len(exact_dup_groups),
        "exact_duplicate_instances": sum(len(g) for g in exact_dup_groups),
        "exact_cross_split_leakage_groups": len(leakage_groups),
        "exact_cross_class_conflict_groups": len(cross_class_exact_conflicts),
        "near_duplicate_pairs": len(near_dup_pairs),
        "near_duplicate_cross_split_leakage_pairs": len(near_leakage_pairs),
        "near_duplicate_cross_class_conflict_pairs": len(near_cross_class_pairs),
        "wilt_cross_split_leakage_pairs": len(wilt_aug_leakage),
        "label_review_candidates": len(label_review_manifest),
        "mutations_detected": len(mutations),
        "class_counts": {r["class"]: r for r in reconciliation_csv}
    }
    with open(OUTPUT_DIR / "summary_findings.json", "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    elapsed = time.time() - start_time
    print(f"\nAudit completed in {elapsed:.2f} seconds.")
    print(f"Summary JSON saved to: {OUTPUT_DIR / 'summary_findings.json'}")

if __name__ == "__main__":
    run_audit()
