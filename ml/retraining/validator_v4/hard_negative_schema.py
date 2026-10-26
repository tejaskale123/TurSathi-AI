#!/usr/bin/env python3
"""
================================================================================
TurSathi AI - Hard-Negative Data Governance Schema & Verification Tool
================================================================================
Defines strict metadata schema, validation constraints, and provenance auditing
for collecting and integrating hard-negative images into Validator v4.

STRICT SAFETY CONSTRAINTS:
1. No unreviewed image can be assigned to train/val/calibration/test splits.
2. Tur_Unsupported_Disease must NEVER be mislabeled as Not_Tur.
3. Pigeonpea pods, stems, roots must be distinguished from leaves.
4. Exact duplicate and near-duplicate groups must NEVER cross splits.
5. Zero destructive operations: read-only verification of existing datasets.
================================================================================
"""

import hashlib
import json
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class VerifiedLabel(str, Enum):
    NOT_TUR = "Not_Tur"                                # Genuine negative (other crops, weeds, clutter)
    TUR_NON_LEAF_ORGAN = "Tur_Non_Leaf_Organ"          # Genuine pigeonpea, but non-leaf (pod, stem, root)
    TUR_UNSUPPORTED_DISEASE = "Tur_Unsupported_Disease"  # Genuine pigeonpea leaf, but disease outside 5 classes
    UNREVIEWED = "UNREVIEWED"                          # Pending human agronomist review
    REJECTED_EXCLUDE = "REJECTED_EXCLUDE"              # Corrupt, blurry, or invalid file


class OrganCategory(str, Enum):
    PIGEONPEA_POD = "pigeonpea_pod"
    PIGEONPEA_STEM_ROOT = "pigeonpea_stem_root"
    WEED_FOLIAGE = "weed_foliage"
    NON_CROP_CLUTTER = "non_crop_clutter"
    OTHER_CROP_LEAF = "other_crop_leaf"
    UNSUPPORTED_PIGEONPEA_DISEASE = "unsupported_pigeonpea_disease"
    ACADEMIC_FIGURE = "academic_figure"
    UNVERIFIED = "unverified"


class ReviewerStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    VERIFIED_ACCEPTED = "VERIFIED_ACCEPTED"
    FLAGGED_CONFLICT = "FLAGGED_CONFLICT"
    REJECTED_EXCLUDE = "REJECTED_EXCLUDE"


class SplitAssignment(str, Enum):
    UNASSIGNED = "unassigned"
    TRAIN = "train"
    VAL = "val"
    CALIBRATION = "calibration"
    TEST_HOLDOUT = "test_holdout"


@dataclass
class HardNegativeRecord:
    image_id: str
    relative_file_path: str
    source_provenance: str
    verified_label: str
    organ_category: str
    reviewer_status: str
    reviewer_notes: str
    sha256: str
    duplicate_group_id: Optional[str]
    split_assignment: str
    date_added: str

    def to_dict(self) -> Dict:
        return asdict(self)


def compute_sha256(file_path: Path) -> str:
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class HardNegativeManifestValidator:
    """Audits hard-negative records against strict ML safety constraints."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def validate_records(self, records: List[HardNegativeRecord]) -> Tuple[bool, List[str]]:
        errors = []
        seen_ids: Set[str] = set()
        hash_to_id: Dict[str, str] = {}
        dup_group_to_splits: Dict[str, Set[str]] = {}

        for rec in records:
            # 1. Unique ID check
            if rec.image_id in seen_ids:
                errors.append(f"Duplicate image_id: {rec.image_id}")
            seen_ids.add(rec.image_id)

            # 2. File existence check
            abs_path = self.project_root / rec.relative_file_path
            if not abs_path.exists():
                errors.append(f"File missing on disk: {rec.relative_file_path} (ID: {rec.image_id})")
                continue

            # 3. Cryptographic hash re-verification
            real_hash = compute_sha256(abs_path)
            if real_hash != rec.sha256:
                errors.append(f"SHA-256 mismatch for {rec.image_id}: recorded {rec.sha256[:12]} vs actual {real_hash[:12]}")

            # 4. Unreviewed status safety constraint
            if rec.reviewer_status == ReviewerStatus.PENDING_REVIEW.value:
                if rec.split_assignment != SplitAssignment.UNASSIGNED.value:
                    errors.append(
                        f"SAFETY VIOLATION: {rec.image_id} is PENDING_REVIEW but assigned to active split '{rec.split_assignment}'. "
                        "Unreviewed images must remain 'unassigned'."
                    )

            # 5. Unsupported Pigeonpea Disease integrity constraint
            if rec.organ_category == OrganCategory.UNSUPPORTED_PIGEONPEA_DISEASE.value:
                if rec.verified_label == VerifiedLabel.NOT_TUR.value:
                    errors.append(
                        f"LABELING ERROR: {rec.image_id} has organ_category 'unsupported_pigeonpea_disease' "
                        f"but verified_label is set to 'Not_Tur'. Genuine pigeonpea diseases must NOT be labeled as Not_Tur."
                    )

            # 6. Duplicate group split isolation constraint
            if rec.duplicate_group_id and rec.split_assignment != SplitAssignment.UNASSIGNED.value:
                grp = rec.duplicate_group_id
                if grp not in dup_group_to_splits:
                    dup_group_to_splits[grp] = set()
                dup_group_to_splits[grp].add(rec.split_assignment)

        # Check for duplicate groups crossing splits
        for grp, splits in dup_group_to_splits.items():
            if len(splits) > 1:
                errors.append(
                    f"DATA LEAKAGE VIOLATION: Duplicate group '{grp}' spans multiple splits: {splits}. "
                    "All instances of duplicate/near-duplicate images must reside within the same split."
                )

        is_valid = len(errors) == 0
        return is_valid, errors
