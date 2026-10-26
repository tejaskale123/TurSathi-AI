#!/usr/bin/env python3
"""
================================================================================
TurSathi AI - Hard-Negative Intake and Validation Processor
================================================================================
Parses hard-negative intake CSV files, computes cryptographic hashes, audits
files for decodability, verifies botanical label policies, prevents cross-split
duplication, and produces an auditable candidate manifest.

STRICT SAFETY:
- Read-only on existing datasets and manifests.
- Does NOT modify validator_v4_manifest.json or production model weights.
- Emits candidate manifest to:
  ml/retraining/validator_v4/candidate_hard_negatives_manifest.json
================================================================================
"""

import csv
import io
import json
import sys
import hashlib
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "ml" / "retraining" / "validator_v4"))

from hard_negative_schema import (
    HardNegativeRecord,
    HardNegativeManifestValidator,
    ReviewerStatus,
    VerifiedLabel,
    OrganCategory,
    SplitAssignment
)

BASE_VALIDATOR_MANIFEST = PROJECT_ROOT / "ml" / "retraining" / "validator_v4" / "validator_v4_manifest.json"
COLLECTION_MANIFEST = PROJECT_ROOT / "ml" / "retraining" / "validator_v4" / "hard_negative_collection_manifest.json"
OUTPUT_CANDIDATE_MANIFEST = PROJECT_ROOT / "ml" / "retraining" / "validator_v4" / "candidate_hard_negatives_manifest.json"


def compute_sha256(path: Path) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def process_intake(csv_path: Path, dry_run: bool = False):
    print("=" * 80)
    print("PROCESSING HARD-NEGATIVE DATA INTAKE & LABEL POLICY VERIFICATION")
    print("=" * 80)
    print(f"Intake CSV: {csv_path.resolve()}")

    if not csv_path.exists():
        print(f"[FAIL] Intake CSV file does not exist: {csv_path}")
        sys.exit(1)

    # 1. Load baseline hashes to detect collisions with existing dataset
    base_hashes: Set[str] = set()
    if BASE_VALIDATOR_MANIFEST.exists():
        with open(BASE_VALIDATOR_MANIFEST, "r", encoding="utf-8") as f:
            base_data = json.load(f)
        base_hashes = set(r["sha256"] for r in base_data.get("records", []))
        print(f"Loaded {len(base_hashes)} baseline hashes from validator_v4_manifest.json")

    # 2. Parse CSV rows
    raw_rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row_idx, row in enumerate(reader, 1):
            if not row or row[0].strip().startswith("#"):
                continue
            if row[0].strip().lower() == "image_id":
                continue  # skip header
            raw_rows.append((row_idx, row))

    print(f"Total non-comment rows to process: {len(raw_rows)}")

    if not raw_rows:
        print("\n[Notice] No active rows in CSV. The template currently contains only guidance examples.")
        print("To catalog new field images, add data rows to hard_negative_intake_template.csv.")
        return

    # 3. Validate each row
    errors = []
    records: List[HardNegativeRecord] = []
    batch_hashes = defaultdict(list)
    dup_group_splits = defaultdict(set)

    for line_num, row in raw_rows:
        if len(row) < 9:
            errors.append(f"Line {line_num}: expected 9 columns, got {len(row)}.")
            continue

        image_id = row[0].strip()
        rel_path = row[1].strip()
        source = row[2].strip()
        label = row[3].strip()
        category = row[4].strip()
        status = row[5].strip()
        notes = row[6].strip()
        dup_grp = row[7].strip() if row[7].strip() else None
        split = row[8].strip()

        # Check file existence
        file_path = PROJECT_ROOT / rel_path
        if not file_path.exists():
            errors.append(f"Line {line_num} (ID: {image_id}): file not found on disk at '{rel_path}'")
            continue

        # Check image decodability
        try:
            with Image.open(file_path) as im:
                im.verify()
        except Exception as e:
            errors.append(f"Line {line_num} (ID: {image_id}): unreadable or corrupted image: {e}")
            continue

        # Compute hash
        sha256 = compute_sha256(file_path)
        batch_hashes[sha256].append(image_id)

        # Check collision with baseline dataset
        if sha256 in base_hashes:
            errors.append(
                f"Line {line_num} (ID: {image_id}): SHA-256 matches an existing image in validator_v4_manifest.json. "
                "Redundant copies of baseline images cannot be re-added as hard negatives."
            )

        # Enforce label policies
        # Policy A: Unsupported pigeonpea diseases must NEVER be labeled Not_Tur
        if category == OrganCategory.UNSUPPORTED_PIGEONPEA_DISEASE.value:
            if label != VerifiedLabel.TUR_UNSUPPORTED_DISEASE.value:
                errors.append(
                    f"Line {line_num} (ID: {image_id}): Unsupported pigeonpea disease must have verified_label='{VerifiedLabel.TUR_UNSUPPORTED_DISEASE.value}', "
                    f"got '{label}'. Do NOT label genuine pigeonpea diseases as Not_Tur."
                )

        # Policy B: Non-leaf organs must have verified_label Tur_Non_Leaf_Organ
        if category in [OrganCategory.PIGEONPEA_POD.value, OrganCategory.PIGEONPEA_STEM_ROOT.value]:
            if label != VerifiedLabel.TUR_NON_LEAF_ORGAN.value:
                errors.append(
                    f"Line {line_num} (ID: {image_id}): Category '{category}' must have verified_label='{VerifiedLabel.TUR_NON_LEAF_ORGAN.value}', "
                    f"got '{label}'."
                )

        # Policy C: PENDING_REVIEW images must remain unassigned
        if status == ReviewerStatus.PENDING_REVIEW.value:
            if split != SplitAssignment.UNASSIGNED.value:
                errors.append(
                    f"Line {line_num} (ID: {image_id}): Image has status 'PENDING_REVIEW' but is assigned to split '{split}'. "
                    "Unreviewed images must be 'unassigned'."
                )

        # Policy D: Duplicate groups must not cross splits
        if dup_grp and split != SplitAssignment.UNASSIGNED.value:
            dup_group_splits[dup_grp].add(split)

        records.append(HardNegativeRecord(
            image_id=image_id,
            relative_file_path=rel_path,
            source_provenance=source,
            verified_label=label,
            organ_category=category,
            reviewer_status=status,
            reviewer_notes=notes,
            sha256=sha256,
            duplicate_group_id=dup_grp,
            split_assignment=split,
            date_added=datetime.now().strftime("%Y-%m-%d")
        ))

    # Cross-check duplicate groups across splits
    for grp, splits in dup_group_splits.items():
        if len(splits) > 1:
            errors.append(f"DATA LEAKAGE: Duplicate group '{grp}' is split across: {splits}. All duplicates must be in the same split.")

    # 4. Report findings
    if errors:
        print(f"\n[FAIL] Found {len(errors)} validation errors:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    print(f"\n[PASS] All {len(records)} records passed validation.")

    # Categorization summary
    counts_by_cat = defaultdict(int)
    counts_by_label = defaultdict(int)
    counts_by_split = defaultdict(int)

    for r in records:
        counts_by_cat[r.organ_category] += 1
        counts_by_label[r.verified_label] += 1
        counts_by_split[r.split_assignment] += 1

    print("\n--- Processed Intake Summary ---")
    print(f"Total Valid Records: {len(records)}")
    print("By Verified Label:")
    for lbl, cnt in counts_by_label.items():
        print(f"  - {lbl:25s}: {cnt}")
    print("By Organ Category:")
    for cat, cnt in counts_by_cat.items():
        print(f"  - {cat:25s}: {cnt}")
    print("By Split Assignment:")
    for spl, cnt in counts_by_split.items():
        print(f"  - {spl:25s}: {cnt}")

    if not dry_run:
        payload = {
            "candidate_manifest_version": "v4_hard_negative_staged_v1",
            "created_at": datetime.now().isoformat(),
            "source_csv": str(csv_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "total_records": len(records),
            "records": [r.to_dict() for r in records]
        }
        with open(OUTPUT_CANDIDATE_MANIFEST, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"\n[Saved] Candidate Staging Manifest -> {OUTPUT_CANDIDATE_MANIFEST}")
    else:
        print("\n[Dry Run] Validation completed without writing candidate manifest.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TurSathi AI Hard-Negative Intake Processor")
    parser.add_argument(
        "--csv-path",
        type=str,
        default="ml/retraining/validator_v4/hard_negative_intake_template.csv",
        help="Path to the hard-negative intake CSV"
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing manifest")
    args = parser.parse_args()

    process_intake(PROJECT_ROOT / args.csv_path, dry_run=args.dry_run)
