#!/usr/bin/env python3
"""
================================================================================
TurSathi AI - Hard-Negative Collection Manifest Builder
================================================================================
Constructs hard_negative_collection_manifest.json by scanning existing verified
negative images and unreviewed exploratory images with cryptographic auditing.

STRICT SAFETY:
- Read-only on source files.
- Writes only inside ml/retraining/validator_v4/.
================================================================================
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "ml" / "retraining" / "validator_v4"

def compute_sha256(path: Path) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def build_manifest():
    print("=" * 80)
    print("BUILDING AUDITABLE HARD-NEGATIVE COLLECTION MANIFEST")
    print("=" * 80)

    records = []
    
    # 1. Real-World Tested Hard Negatives (datasets/tur_image_validator/real_world_test/Not_Tur)
    rw_dir = PROJECT_ROOT / "datasets" / "tur_image_validator" / "real_world_test" / "Not_Tur"
    if rw_dir.exists():
        for idx, f in enumerate(sorted(rw_dir.glob("*.*")), 1):
            if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                h = compute_sha256(f)
                records.append({
                    "image_id": f"HN_RW_{idx:03d}",
                    "relative_file_path": str(f.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "source_provenance": "datasets/tur_image_validator/real_world_test/Not_Tur",
                    "verified_label": "Not_Tur",
                    "organ_category": "other_crop_leaf",
                    "reviewer_status": "VERIFIED_ACCEPTED",
                    "reviewer_notes": "Verified non-pigeonpea crop foliage from frozen holdout evaluation.",
                    "sha256": h,
                    "duplicate_group_id": None,
                    "split_assignment": "test_holdout",
                    "date_added": "2026-10-26"
                })

    # 2. Exploratory Collection (datasets/new_disease_images)
    ext_dir = PROJECT_ROOT / "datasets" / "new_disease_images"
    valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    
    # Known duplicate hashes
    dup_map = {
        "cbb731eb1f8876c265691079d343c16ee0a1f2f0a51be3ea59546059d332aa6c": "DUP_GRP_01", # image.png, image copy.png
        "0c6a858e775196f7e8a93aa9aef462c19eec8e7b9b00cb3e536ec6f55502c4eb": "DUP_GRP_02", # images (3).jpg, images (10).jpg
        "3f7be737fb12217cb0b522858b993ae14979ff176f1a8e1cb68ae9858739d48b": "DUP_GRP_03", # images (15).jpg, images (17).jpg
        "9195b035179294e5b3ee0b7ceeebe6c5dc3a362ff1875151e3c23ca5584852c4": "DUP_GRP_04", # images (18).jpg, images (23).jpg
        "1a7fec062ddcc729a6e1180cf7bc516168541249b6b72049e25d2105e46c76db": "DUP_GRP_05", # images (9).jpg, images (20).jpg
    }

    if ext_dir.exists():
        for idx, f in enumerate(sorted(ext_dir.iterdir()), 1):
            if f.is_file() and f.suffix.lower() in valid_exts:
                h = compute_sha256(f)
                
                # Check for special audited cases
                if "Kitui, Kenya" in f.name:
                    records.append({
                        "image_id": f"HN_EXP_{idx:03d}",
                        "relative_file_path": str(f.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                        "source_provenance": "datasets/new_disease_images (Wikimedia Maundu 2021)",
                        "verified_label": "Tur_Non_Leaf_Organ",
                        "organ_category": "pigeonpea_pod",
                        "reviewer_status": "VERIFIED_ACCEPTED",
                        "reviewer_notes": "Genuine pigeonpea pod cluster in fruit. NOT a leaf. Must be held for organ discrimination, NOT labeled as Not_Tur.",
                        "sha256": h,
                        "duplicate_group_id": None,
                        "split_assignment": "unassigned",
                        "date_added": "2026-10-26"
                    })
                elif "Alternaria" in f.name:
                    records.append({
                        "image_id": f"HN_EXP_{idx:03d}",
                        "relative_file_path": str(f.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                        "source_provenance": "datasets/new_disease_images (ResearchGate)",
                        "verified_label": "Tur_Unsupported_Disease",
                        "organ_category": "unsupported_pigeonpea_disease",
                        "reviewer_status": "VERIFIED_ACCEPTED",
                        "reviewer_notes": "Pigeonpea Alternaria blight. Genuine pigeonpea, but disease outside the 5 target classes. Held for OOD evaluation, NOT labeled as Not_Tur.",
                        "sha256": h,
                        "duplicate_group_id": None,
                        "split_assignment": "unassigned",
                        "date_added": "2026-10-26"
                    })
                elif "Fig1_HTML" in f.name:
                    records.append({
                        "image_id": f"HN_EXP_{idx:03d}",
                        "relative_file_path": str(f.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                        "source_provenance": "datasets/new_disease_images (Springer Nature publication)",
                        "verified_label": "Not_Tur",
                        "organ_category": "academic_figure",
                        "reviewer_status": "VERIFIED_ACCEPTED",
                        "reviewer_notes": "Academic multi-panel diagram with letters and text. Valid negative non-leaf clutter.",
                        "sha256": h,
                        "duplicate_group_id": None,
                        "split_assignment": "test_holdout",
                        "date_added": "2026-10-26"
                    })
                else:
                    dup_grp = dup_map.get(h, None)
                    records.append({
                        "image_id": f"HN_EXP_{idx:03d}",
                        "relative_file_path": str(f.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                        "source_provenance": "datasets/new_disease_images (uncurated web scrape)",
                        "verified_label": "UNREVIEWED",
                        "organ_category": "unverified",
                        "reviewer_status": "PENDING_REVIEW",
                        "reviewer_notes": "Unverified web-scraped thumbnail. Requires human agronomist review before assigning to any split.",
                        "sha256": h,
                        "duplicate_group_id": dup_grp,
                        "split_assignment": "unassigned",
                        "date_added": "2026-10-26"
                    })

    # Summary Statistics
    counts_by_status = {}
    counts_by_category = {}
    counts_by_label = {}
    for r in records:
        counts_by_status[r["reviewer_status"]] = counts_by_status.get(r["reviewer_status"], 0) + 1
        counts_by_category[r["organ_category"]] = counts_by_category.get(r["organ_category"], 0) + 1
        counts_by_label[r["verified_label"]] = counts_by_label.get(r["verified_label"], 0) + 1

    summary = {
        "total_cataloged_images": len(records),
        "target_collection_goal": 300,
        "counts_by_reviewer_status": counts_by_status,
        "counts_by_organ_category": counts_by_category,
        "counts_by_verified_label": counts_by_label,
        "shortage_analysis": {
            "target_total_hard_negatives": 300,
            "actual_verified_hard_negatives": counts_by_status.get("VERIFIED_ACCEPTED", 0) - counts_by_label.get("Tur_Non_Leaf_Organ", 0) - counts_by_label.get("Tur_Unsupported_Disease", 0),
            "pending_human_review_count": counts_by_status.get("PENDING_REVIEW", 0),
            "net_shortage_against_target": 300 - (counts_by_status.get("VERIFIED_ACCEPTED", 0) - counts_by_label.get("Tur_Non_Leaf_Organ", 0) - counts_by_label.get("Tur_Unsupported_Disease", 0)),
            "category_shortages": {
                "pigeonpea_non_leaf_organs": {"target": 100, "verified": counts_by_category.get("pigeonpea_pod", 0) + counts_by_category.get("pigeonpea_stem_root", 0), "shortage": 100 - (counts_by_category.get("pigeonpea_pod", 0) + counts_by_category.get("pigeonpea_stem_root", 0))},
                "agricultural_weeds": {"target": 100, "verified": counts_by_category.get("weed_foliage", 0), "shortage": 100 - counts_by_category.get("weed_foliage", 0)},
                "field_clutter_and_soil": {"target": 100, "verified": counts_by_category.get("non_crop_clutter", 0) + counts_by_category.get("academic_figure", 0), "shortage": 100 - (counts_by_category.get("non_crop_clutter", 0) + counts_by_category.get("academic_figure", 0))}
            }
        }
    }

    payload = {
        "manifest_version": "v4_hard_negative_audit_v1",
        "created_at": datetime.now().isoformat(),
        "summary": summary,
        "records": records
    }

    out_json = OUTPUT_DIR / "hard_negative_collection_manifest.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Total cataloged images: {len(records)}")
    print(f"Verified Accepted:      {counts_by_status.get('VERIFIED_ACCEPTED', 0)}")
    print(f"Pending Review:         {counts_by_status.get('PENDING_REVIEW', 0)}")
    print(f"Net Shortage to 300:    {summary['shortage_analysis']['net_shortage_against_target']}")
    print(f"[Saved] Manifest -> {out_json}")


if __name__ == "__main__":
    build_manifest()
