#!/usr/bin/env python3
"""
TurSathi AI — Field Dataset Collection Tracker and Verification Audit Utility.

Audits field collection manifests for the pigeonpea organ validator without modifying
any source files, images, or application state (read-only audit).

Enforces:
- Required metadata columns and non-null values.
- Allowed class labels and verification statuses.
- Strict isolation of quarantined and rejected images from verified readiness counts.
- Image file existence, decode integrity, and SHA-256 deduplication.
- Zero plant-level and farm-level split leakage across dataset partitions.
- Minimum target thresholds:
    - Tur_Pod: >= 250 verified images
    - Tur_WholePlant_or_Canopy: >= 200 verified images
    - Not_Tur_or_Unsupported: >= 100 verified images
    - Distinct farms: >= 5 geographically separated plots
"""

import argparse
import csv
import hashlib
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ==============================================================================
# Targets and Constraints (from PHASE5D_A_DESIGN_REPORT & FIELD_COLLECTION_PREPARATION)
# ==============================================================================

TARGET_TUR_POD: int = 250
TARGET_TUR_WHOLE_PLANT: int = 200
TARGET_NOT_TUR_DISTRACTOR: int = 100
TARGET_DISTINCT_FARMS: int = 5

REQUIRED_COLUMNS: List[str] = [
    "filename",
    "class_label",
    "plant_id",
    "farm_id",
    "capture_date",
    "verification_status",
    "verifier_reference",
]

ALLOWED_CLASSES: Set[str] = {
    "Tur_Pod",
    "Tur_WholePlant_or_Canopy",
    "Tur_Leaf",
    "Not_Tur_or_Unsupported",
}

ALLOWED_STATUSES: Set[str] = {
    "verified",
    "quarantined",
    "rejected",
}


@dataclass
class AuditIssue:
    severity: str  # "ERROR" or "WARNING"
    category: str
    message: str
    record_index: Optional[int] = None
    filename: Optional[str] = None


@dataclass
class AuditSummary:
    total_records: int = 0
    valid_syntax_records: int = 0
    verified_records: int = 0
    quarantined_records: int = 0
    rejected_records: int = 0
    counts_by_class: Dict[str, Dict[str, int]] = field(default_factory=dict)
    distinct_farms: List[str] = field(default_factory=list)
    distinct_plants_count: int = 0
    verified_by_class: Dict[str, int] = field(default_factory=dict)
    target_checks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    leakage_detected: bool = False
    is_dataset_ready: bool = False
    blockers: List[str] = field(default_factory=list)
    issues: List[Dict[str, Any]] = field(default_factory=list)


class FieldCollectionAuditor:
    """
    Read-only audit utility for field collection manifests.
    """

    def __init__(
        self,
        manifest_path: Path,
        image_dir: Optional[Path] = None,
        check_images: bool = True,
    ) -> None:
        self.manifest_path = Path(manifest_path)
        self.image_dir = Path(image_dir) if image_dir else None
        self.check_images = check_images
        self.issues: List[AuditIssue] = []

    def log_issue(
        self,
        severity: str,
        category: str,
        message: str,
        record_index: Optional[int] = None,
        filename: Optional[str] = None,
    ) -> None:
        self.issues.append(
            AuditIssue(
                severity=severity,
                category=category,
                message=message,
                record_index=record_index,
                filename=filename,
            )
        )

    def audit(self) -> AuditSummary:
        summary = AuditSummary()

        if not self.manifest_path.exists():
            self.log_issue("ERROR", "MANIFEST_NOT_FOUND", f"Manifest file does not exist: {self.manifest_path}")
            summary.blockers.append(f"Manifest not found: {self.manifest_path}")
            summary.issues = [asdict(i) for i in self.issues]
            return summary

        # 1. Parse CSV
        rows: List[Dict[str, str]] = []
        try:
            with open(self.manifest_path, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                header: Optional[List[str]] = None
                for line_num, raw_row in enumerate(reader, start=1):
                    # Skip empty rows or comment rows
                    if not raw_row or not any(field.strip() for field in raw_row):
                        continue
                    first_cell = raw_row[0].strip()
                    if first_cell.startswith("#"):
                        continue
                    if header is None:
                        header = [c.strip() for c in raw_row]
                        continue
                    row_dict = {
                        header[i]: raw_row[i].strip() if i < len(raw_row) else ""
                        for i in range(len(header))
                    }
                    rows.append(row_dict)
        except Exception as exc:
            self.log_issue("ERROR", "CSV_PARSE_ERROR", f"Failed to read CSV: {exc}")
            summary.blockers.append(f"CSV parse error: {exc}")
            summary.issues = [asdict(i) for i in self.issues]
            return summary

        summary.total_records = len(rows)

        if not header:
            self.log_issue("ERROR", "EMPTY_MANIFEST", "Manifest does not contain a header line.")
            summary.blockers.append("Manifest header is missing.")
            summary.issues = [asdict(i) for i in self.issues]
            return summary

        # Check required columns
        missing_cols = [c for c in REQUIRED_COLUMNS if c not in header]
        if missing_cols:
            self.log_issue("ERROR", "MISSING_COLUMNS", f"Missing required columns: {missing_cols}")
            summary.blockers.append(f"Missing required columns: {missing_cols}")

        # If zero rows (e.g. empty template), report cleanly without fabricating progress
        if summary.total_records == 0:
            summary.blockers.append("Manifest contains zero collection records (Collection has not started).")
            self._evaluate_readiness(summary, set(), set(), {})
            summary.issues = [asdict(i) for i in self.issues]
            return summary

        # 2. Row-by-Row Validation
        filenames_seen: Set[str] = set()
        file_hashes: Dict[str, str] = {}
        farms_seen: Set[str] = set()
        plants_seen: Set[str] = set()

        # Split leakage tracking: plant_id -> set of splits, farm_id -> set of splits
        plant_to_splits: Dict[str, Set[str]] = {}
        farm_to_splits: Dict[str, Set[str]] = {}

        counts_by_class: Dict[str, Dict[str, int]] = {
            c: {"verified": 0, "quarantined": 0, "rejected": 0, "other": 0}
            for c in ALLOWED_CLASSES
        }
        verified_by_class: Dict[str, int] = {c: 0 for c in ALLOWED_CLASSES}

        valid_records = 0

        for idx, row in enumerate(rows, start=1):
            row_valid = True
            fname = row.get("filename", "")
            clabel = row.get("class_label", "")
            pid = row.get("plant_id", "")
            fid = row.get("farm_id", "")
            status = row.get("verification_status", "").lower()
            split = row.get("split", "").lower()

            # Missing required fields
            for req in REQUIRED_COLUMNS:
                if not row.get(req, ""):
                    self.log_issue("ERROR", "MISSING_VALUE", f"Record #{idx} missing required field '{req}'", idx, fname)
                    row_valid = False

            # Duplicate filename in manifest
            if fname:
                if fname in filenames_seen:
                    self.log_issue("ERROR", "DUPLICATE_FILENAME", f"Duplicate filename '{fname}' at row #{idx}", idx, fname)
                    row_valid = False
                filenames_seen.add(fname)

            # Class label check
            if clabel not in ALLOWED_CLASSES:
                self.log_issue("ERROR", "INVALID_CLASS", f"Unrecognized class '{clabel}' at row #{idx}", idx, fname)
                row_valid = False

            # Verification status check
            if status not in ALLOWED_STATUSES:
                self.log_issue("ERROR", "INVALID_STATUS", f"Unrecognized verification status '{status}' at row #{idx}", idx, fname)
                row_valid = False

            if fid:
                farms_seen.add(fid)
            if pid:
                plants_seen.add(pid)

            # Aggregate raw counts by class (all statuses, regardless of row_valid)
            if clabel in counts_by_class:
                if status in counts_by_class[clabel]:
                    counts_by_class[clabel][status] += 1
                else:
                    counts_by_class[clabel]["other"] += 1

            # Count non-verified statuses immediately (quarantine/reject are informational)
            if status == "quarantined":
                summary.quarantined_records += 1
            elif status == "rejected":
                summary.rejected_records += 1
            # NOTE: verified_records and verified_by_class are deferred to after all
            # row-level checks complete so that image-existence and decode failures
            # cannot inflate the verified count (see fix applied at end of row loop).

            # Split leakage tracking if split column is provided
            if split:
                if pid:
                    plant_to_splits.setdefault(pid, set()).add(split)
                if fid:
                    farm_to_splits.setdefault(fid, set()).add(split)

            # Image existence and decodability check
            if self.image_dir and fname:
                img_path = self.image_dir / fname
                if not img_path.exists():
                    self.log_issue("ERROR", "FILE_NOT_FOUND", f"Image file '{fname}' not found in {self.image_dir}", idx, fname)
                    row_valid = False
                elif self.check_images and HAS_PIL:
                    try:
                        with Image.open(img_path) as img:
                            img.verify()
                        with Image.open(img_path) as img:
                            w, h = img.size
                            if w < 224 or h < 224:
                                self.log_issue("WARNING", "IMAGE_BELOW_MIN_DIMENSION", f"Image '{fname}' resolution {w}x{h} < 224x224", idx, fname)
                    except Exception as img_exc:
                        self.log_issue("ERROR", "CORRUPT_IMAGE", f"Image '{fname}' cannot be decoded: {img_exc}", idx, fname)
                        row_valid = False

                # Hash deduplication check
                if img_path.exists():
                    try:
                        h_sha = hashlib.sha256()
                        with open(img_path, "rb") as f_img:
                            while chunk := f_img.read(65536):
                                h_sha.update(chunk)
                        sha_digest = h_sha.hexdigest()
                        if sha_digest in file_hashes:
                            self.log_issue(
                                "ERROR",
                                "EXACT_DUPLICATE_HASH",
                                f"Image '{fname}' has identical SHA-256 hash to '{file_hashes[sha_digest]}'",
                                idx,
                                fname,
                            )
                            row_valid = False
                        else:
                            file_hashes[sha_digest] = fname
                    except Exception as h_exc:
                        self.log_issue("WARNING", "HASH_ERROR", f"Failed to hash '{fname}': {h_exc}", idx, fname)

            if row_valid:
                valid_records += 1
                # Fix 1: count toward verified only when the entire row is valid
                # (schema, file existence, decode integrity, and no duplicate hash).
                if status == "verified" and clabel in verified_by_class:
                    verified_by_class[clabel] += 1
                    summary.verified_records += 1

        summary.valid_syntax_records = valid_records
        summary.counts_by_class = counts_by_class
        summary.verified_by_class = verified_by_class
        summary.distinct_farms = sorted(list(farms_seen))
        summary.distinct_plants_count = len(plants_seen)

        # 3. Check for Split Leakage
        leakage_detected = False
        for pid, splits in plant_to_splits.items():
            if len(splits) > 1:
                leakage_detected = True
                self.log_issue(
                    "ERROR",
                    "PLANT_SPLIT_LEAKAGE",
                    f"Plant ID '{pid}' appears in multiple splits: {sorted(list(splits))}",
                )
                summary.blockers.append(f"Plant ID '{pid}' leaked across splits: {sorted(list(splits))}")

        for fid, splits in farm_to_splits.items():
            if len(splits) > 1:
                leakage_detected = True
                self.log_issue(
                    "ERROR",
                    "FARM_SPLIT_LEAKAGE",
                    f"Farm ID '{fid}' appears in multiple splits: {sorted(list(splits))}",
                )
                summary.blockers.append(f"Farm ID '{fid}' leaked across splits: {sorted(list(splits))}")

        summary.leakage_detected = leakage_detected

        # 4. Target Threshold Evaluations
        self._evaluate_readiness(summary, farms_seen, plants_seen, verified_by_class)

        summary.issues = [asdict(i) for i in self.issues]
        return summary

    def _evaluate_readiness(
        self,
        summary: AuditSummary,
        farms_seen: Set[str],
        plants_seen: Set[str],
        verified_by_class: Dict[str, int],
    ) -> None:
        pod_verified = verified_by_class.get("Tur_Pod", 0)
        canopy_verified = verified_by_class.get("Tur_WholePlant_or_Canopy", 0)
        distractor_verified = verified_by_class.get("Not_Tur_or_Unsupported", 0)
        farm_count = len(farms_seen)

        summary.target_checks = {
            "Tur_Pod": {
                "target": TARGET_TUR_POD,
                "verified": pod_verified,
                "satisfied": pod_verified >= TARGET_TUR_POD,
                "deficit": max(0, TARGET_TUR_POD - pod_verified),
            },
            "Tur_WholePlant_or_Canopy": {
                "target": TARGET_TUR_WHOLE_PLANT,
                "verified": canopy_verified,
                "satisfied": canopy_verified >= TARGET_TUR_WHOLE_PLANT,
                "deficit": max(0, TARGET_TUR_WHOLE_PLANT - canopy_verified),
            },
            "Not_Tur_or_Unsupported": {
                "target": TARGET_NOT_TUR_DISTRACTOR,
                "verified": distractor_verified,
                "satisfied": distractor_verified >= TARGET_NOT_TUR_DISTRACTOR,
                "deficit": max(0, TARGET_NOT_TUR_DISTRACTOR - distractor_verified),
            },
            "Distinct_Farms": {
                "target": TARGET_DISTINCT_FARMS,
                "actual": farm_count,
                "satisfied": farm_count >= TARGET_DISTINCT_FARMS,
                "deficit": max(0, TARGET_DISTINCT_FARMS - farm_count),
            },
        }

        # Determine readiness blockers
        if pod_verified < TARGET_TUR_POD:
            summary.blockers.append(f"Tur_Pod deficit: {pod_verified}/{TARGET_TUR_POD} verified images.")
        if canopy_verified < TARGET_TUR_WHOLE_PLANT:
            summary.blockers.append(f"Tur_WholePlant_or_Canopy deficit: {canopy_verified}/{TARGET_TUR_WHOLE_PLANT} verified images.")
        if distractor_verified < TARGET_NOT_TUR_DISTRACTOR:
            summary.blockers.append(f"Not_Tur_or_Unsupported deficit: {distractor_verified}/{TARGET_NOT_TUR_DISTRACTOR} verified images.")
        if farm_count < TARGET_DISTINCT_FARMS:
            summary.blockers.append(f"Distinct farm deficit: {farm_count}/{TARGET_DISTINCT_FARMS} distinct farms.")
        if summary.quarantined_records > 0:
            summary.blockers.append(f"Unresolved quarantine: {summary.quarantined_records} records require agronomist review.")
        if summary.leakage_detected:
            summary.blockers.append("Split leakage detected: Plant or farm IDs repeated across dataset partitions.")

        error_issues = [i for i in self.issues if i.severity == "ERROR"]
        if error_issues:
            summary.blockers.append(f"Manifest contains {len(error_issues)} error issues requiring resolution.")

        # Ready ONLY if all targets met, zero leakages, zero critical errors, zero unreviewed quarantine
        summary.is_dataset_ready = len(summary.blockers) == 0


def format_audit_report(summary: AuditSummary) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("TUR SATHI AI — FIELD DATASET COLLECTION AUDIT REPORT")
    lines.append("=" * 70)
    lines.append(f"Total Collection Records:     {summary.total_records}")
    lines.append(f"Verified Records:             {summary.verified_records}")
    lines.append(f"Quarantined Records:          {summary.quarantined_records}")
    lines.append(f"Rejected Records:             {summary.rejected_records}")
    lines.append(f"Distinct Farms:               {len(summary.distinct_farms)} -> {summary.distinct_farms}")
    lines.append(f"Distinct Plants:              {summary.distinct_plants_count}")
    lines.append("-" * 70)
    lines.append("PROGRESS VS TARGET THRESHOLDS:")
    for k, v in summary.target_checks.items():
        curr = v.get("verified", v.get("actual", 0))
        tgt = v["target"]
        sat = "PASS [OK]" if v["satisfied"] else f"DEFICIT (-{v['deficit']})"
        lines.append(f"  {k:<26}: {curr:>4} / {tgt:>4}  [{sat}]")
    lines.append("-" * 70)
    lines.append(f"DATASET READY FOR TRAINING:   {'YES [APPROVED]' if summary.is_dataset_ready else 'NO [HOLD]'}")
    if summary.blockers:
        lines.append("\nACTIVE BLOCKERS:")
        for b in summary.blockers:
            lines.append(f"  * {b}")
    lines.append("=" * 70)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit Pigeonpea Field Collection Manifest.")
    parser.add_argument("--manifest", required=True, type=Path, help="Path to field collection metadata CSV.")
    parser.add_argument("--image-dir", type=Path, default=None, help="Directory containing collected image files.")
    parser.add_argument("--no-image-check", action="store_true", help="Skip checking image existence and decodability.")
    parser.add_argument("--json-out", type=Path, default=None, help="Path to write JSON summary.")

    args = parser.parse_args()

    auditor = FieldCollectionAuditor(
        manifest_path=args.manifest,
        image_dir=args.image_dir,
        check_images=not args.no_image_check,
    )

    summary = auditor.audit()
    report_text = format_audit_report(summary)
    print(report_text)

    if args.json_out:
        # Fix 2: create parent directory automatically so --json-out works on new paths.
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(asdict(summary), f, indent=2)

    sys.exit(0 if summary.is_dataset_ready else 1)


if __name__ == "__main__":
    main()
