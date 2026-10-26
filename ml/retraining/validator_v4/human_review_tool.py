#!/usr/bin/env python3
"""
================================================================================
TurSathi AI - Hard-Negative Human Review & Label Governance Tool
================================================================================
Provides an auditable human review interface for staging, verifying, and
labeling hard-negative images before Validator v4 integration.

STRICT SAFETY CONSTRAINTS:
1. Never marks an image verified automatically.
2. Never claims to visually inspect an image without launching a real viewer.
3. Botanical Label Policies:
   - Pigeonpea non-leaf organs (pods, stems, roots) must NEVER be labeled Not_Tur.
     (Must be Tur_Non_Leaf_Organ and isolated from training splits).
   - Genuine pigeonpea leaves with unsupported diseases must NEVER be labeled Not_Tur.
     (Must be Tur_Unsupported_Disease and isolated for OOD evaluation).
   - Weed and clutter images can only be accepted as Not_Tur after human review.
4. Preserves source license, attribution, author, and URL metadata.
5. Prevents unreviewed images (PENDING_REVIEW) from entering active splits (train/val).
6. Writes decisions to a separate review file (`human_review_decisions.json`).
   Does NOT overwrite baseline validator_v4_manifest.json or production checkpoints.
================================================================================
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image

# Ensure stdout handles UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "ml" / "retraining" / "validator_v4"))

from hard_negative_schema import (
    HardNegativeRecord,
    HardNegativeManifestValidator,
    ReviewerStatus,
    VerifiedLabel,
    OrganCategory,
    SplitAssignment,
    compute_sha256
)

CANDIDATE_MANIFEST_PATH = PROJECT_ROOT / "ml" / "retraining" / "validator_v4" / "candidate_hard_negatives_manifest.json"
DEFAULT_DECISIONS_PATH = PROJECT_ROOT / "ml" / "retraining" / "validator_v4" / "human_review_decisions.json"
BASE_MANIFEST_PATH = PROJECT_ROOT / "ml" / "retraining" / "validator_v4" / "validator_v4_manifest.json"


def launch_image_viewer(abs_path: Path):
    """Launches the default system image viewer on Windows or cross-platform."""
    if not abs_path.exists():
        print(f"[FAIL] Image file not found: {abs_path}")
        return

    print(f"Opening image viewer for: {abs_path.name}")
    try:
        if sys.platform == "win32":
            os.startfile(str(abs_path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(abs_path)])
        else:
            subprocess.Popen(["xdg-open", str(abs_path)])
    except Exception as e:
        print(f"[Notice] Could not launch external viewer: {e}")
        try:
            with Image.open(abs_path) as im:
                im.show()
        except Exception as e2:
            print(f"[Notice] PIL show also failed: {e2}. Please view file at: {abs_path}")


def load_candidate_records(manifest_path: Path) -> List[HardNegativeRecord]:
    """Loads records from the candidate manifest."""
    if not manifest_path.exists():
        print(f"[FAIL] Candidate manifest not found: {manifest_path}")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = [HardNegativeRecord(**r) for r in data.get("records", [])]
    return records


def merge_existing_decisions(
    base_records: List[HardNegativeRecord],
    decisions_path: Path
) -> List[HardNegativeRecord]:
    """Preserves and merges previously reviewed decisions without data loss."""
    if not decisions_path.exists():
        return base_records

    try:
        with open(decisions_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        saved_map = {
            r["image_id"]: HardNegativeRecord(**r)
            for r in saved_data.get("records", [])
        }
        merged = []
        for b in base_records:
            if b.image_id in saved_map:
                merged.append(saved_map[b.image_id])
            else:
                merged.append(b)
        return merged
    except Exception as e:
        print(f"[Notice] Could not load prior decisions ({e}); preserving candidate records.")
        return base_records


def validate_decision(
    rec: HardNegativeRecord,
    decision: str,
    target_split: Optional[str] = None
) -> Tuple[bool, str, str, str]:
    """
    Validates a human decision against botanical label rules and split isolation.
    Returns: (is_valid, verified_label, reviewer_status, split_assignment)
    """
    decision = decision.upper().strip()

    if decision not in ["ACCEPT", "REJECT", "NEEDS_REVIEW", "SKIP"]:
        return False, "", "", f"Invalid decision '{decision}'. Must be ACCEPT, REJECT, or NEEDS_REVIEW."

    if decision in ["NEEDS_REVIEW", "SKIP"]:
        return (
            True,
            rec.verified_label,
            ReviewerStatus.PENDING_REVIEW.value,
            SplitAssignment.UNASSIGNED.value
        )

    if decision == "REJECT":
        return (
            True,
            VerifiedLabel.REJECTED_EXCLUDE.value,
            ReviewerStatus.REJECTED_EXCLUDE.value,
            SplitAssignment.UNASSIGNED.value
        )

    # decision == "ACCEPT"
    # Rule 1: Pigeonpea pods, stems, roots must NEVER be labeled Not_Tur
    if rec.organ_category in [OrganCategory.PIGEONPEA_POD.value, OrganCategory.PIGEONPEA_STEM_ROOT.value]:
        # Must be Tur_Non_Leaf_Organ and held out in unassigned
        return (
            True,
            VerifiedLabel.TUR_NON_LEAF_ORGAN.value,
            ReviewerStatus.VERIFIED_ACCEPTED.value,
            SplitAssignment.UNASSIGNED.value
        )

    # Rule 2: Unsupported pigeonpea diseases must NEVER be labeled Not_Tur
    if rec.organ_category == OrganCategory.UNSUPPORTED_PIGEONPEA_DISEASE.value:
        # Must be Tur_Unsupported_Disease and held out in unassigned
        return (
            True,
            VerifiedLabel.TUR_UNSUPPORTED_DISEASE.value,
            ReviewerStatus.VERIFIED_ACCEPTED.value,
            SplitAssignment.UNASSIGNED.value
        )

    # Rule 3: Weeds, clutter, other crop leaves can be accepted as Not_Tur
    if rec.organ_category in [
        OrganCategory.WEED_FOLIAGE.value,
        OrganCategory.NON_CROP_CLUTTER.value,
        OrganCategory.OTHER_CROP_LEAF.value
    ]:
        split = target_split if target_split else SplitAssignment.UNASSIGNED.value
        if split not in [
            SplitAssignment.TRAIN.value,
            SplitAssignment.VAL.value,
            SplitAssignment.TEST_HOLDOUT.value,
            SplitAssignment.UNASSIGNED.value
        ]:
            return False, "", "", f"Invalid split assignment '{split}'."
        return (
            True,
            VerifiedLabel.NOT_TUR.value,
            ReviewerStatus.VERIFIED_ACCEPTED.value,
            split
        )

    # Rule 4: Genuine pigeonpea leaves (positive controls)
    if rec.organ_category == "tur_leaf":
        split = target_split if target_split else SplitAssignment.UNASSIGNED.value
        return (
            True,
            "Tur",
            ReviewerStatus.VERIFIED_ACCEPTED.value,
            split
        )

    return False, "", "", f"Unsupported organ category '{rec.organ_category}' for acceptance."


def list_staged_images(records: List[HardNegativeRecord]):
    """Prints a detailed listing of all staged candidate images."""
    print("=" * 80)
    print(f"TUR SATHI AI — STAGED HARD-NEGATIVE CANDIDATES ({len(records)} TOTAL)")
    print("=" * 80)

    by_status = {}
    by_cat = {}

    for idx, r in enumerate(records, 1):
        abs_p = PROJECT_ROOT / r.relative_file_path
        exists_str = "EXISTS" if abs_p.exists() else "MISSING!"
        print(f"\n[{idx:2d}/{len(records)}] Image ID: {r.image_id}")
        print(f"  Relative Path:  {r.relative_file_path}")
        print(f"  Absolute Path:  {abs_p.resolve()} [{exists_str}]")
        print(f"  Category:       {r.organ_category}")
        print(f"  Candidate Lbl:  {r.verified_label}")
        print(f"  Review Status:  {r.reviewer_status} (Split: {r.split_assignment})")
        print(f"  Provenance:     {r.source_provenance[:80]}...")
        print(f"  Reviewer Notes: {r.reviewer_notes}")
        print(f"  SHA-256 Hash:   {r.sha256[:16]}...")

        by_status[r.reviewer_status] = by_status.get(r.reviewer_status, 0) + 1
        by_cat[r.organ_category] = by_cat.get(r.organ_category, 0) + 1

    print("\n" + "=" * 80)
    print("STATUS SUMMARY:")
    for st, cnt in by_status.items():
        print(f"  - {st:25s}: {cnt}")
    print("CATEGORY SUMMARY:")
    for ct, cnt in by_cat.items():
        print(f"  - {ct:25s}: {cnt}")
    print("=" * 80)


def apply_decision_dictionary(
    records: List[HardNegativeRecord],
    decisions_map: Dict[str, Dict],
    reviewer_name: str
) -> Tuple[List[HardNegativeRecord], List[str]]:
    """Applies a dictionary of decisions to records."""
    updated = []
    errors = []

    for r in records:
        if r.image_id in decisions_map:
            d_info = decisions_map[r.image_id]
            decision = d_info.get("decision", "NEEDS_REVIEW")
            target_split = d_info.get("split_assignment", SplitAssignment.UNASSIGNED.value)
            custom_note = d_info.get("notes", "")

            valid, label, status, split_or_err = validate_decision(r, decision, target_split)
            if not valid:
                errors.append(f"Image {r.image_id}: {split_or_err}")
                updated.append(r)
                continue

            # Update record
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            combined_notes = f"{r.reviewer_notes} | Reviewer: {reviewer_name} [{stamp}]: Decision={decision}. {custom_note}".strip()

            updated.append(HardNegativeRecord(
                image_id=r.image_id,
                relative_file_path=r.relative_file_path,
                source_provenance=r.source_provenance,
                verified_label=label,
                organ_category=r.organ_category,
                reviewer_status=status,
                reviewer_notes=combined_notes,
                sha256=r.sha256,
                duplicate_group_id=r.duplicate_group_id,
                split_assignment=split_or_err,
                date_added=r.date_added
            ))
        else:
            updated.append(r)

    return updated, errors


def run_interactive_review(
    records: List[HardNegativeRecord],
    reviewer_name: str,
    auto_open: bool = False,
    re_review_all: bool = False
) -> List[HardNegativeRecord]:
    """Runs an interactive command-line review session."""
    reviewed = []
    total = len(records)

    already_done = sum(1 for r in records if r.reviewer_status in [ReviewerStatus.VERIFIED_ACCEPTED.value, ReviewerStatus.REJECTED_EXCLUDE.value])

    print("=" * 80)
    print("TUR SATHI AI — HARD-NEGATIVE INTERACTIVE HUMAN REVIEW TOOL")
    print("=" * 80)
    print(f"Reviewer: {reviewer_name}")
    print(f"Auto-Open Viewer: {auto_open}")
    print(f"Total Staged Records: {total} (Previously Reviewed: {already_done})")
    print("Commands per image: [A]ccept, [R]eject, [N]eeds review, [V]iew image, [Q]uit & save")
    print("-" * 80)

    for idx, r in enumerate(records, 1):
        abs_p = PROJECT_ROOT / r.relative_file_path

        # If already reviewed and not forced to re-review, preserve decision
        if not re_review_all and r.reviewer_status in [ReviewerStatus.VERIFIED_ACCEPTED.value, ReviewerStatus.REJECTED_EXCLUDE.value]:
            print(f"[Item {idx:2d}/{total}] {r.image_id}: Already {r.reviewer_status} (label: {r.verified_label}, split: {r.split_assignment}). Preserving decision.")
            reviewed.append(r)
            continue

        print(f"\n================================================================================")
        print(f"[Review Item {idx}/{total}] Image ID: {r.image_id}")
        print(f"================================================================================")
        print(f"  File:           {abs_p.resolve()}")
        print(f"  Category:       {r.organ_category}")
        print(f"  Candidate Lbl:  {r.verified_label}")
        print(f"  Provenance:     {r.source_provenance[:90]}...")
        print(f"  Review Notes:   {r.reviewer_notes}")
        print(f"  Current Split:  {r.split_assignment}")

        if auto_open:
            launch_image_viewer(abs_p)

        while True:
            raw_choice = input("\nEnter Decision ([A]ccept / [R]eject / [N]eeds review / [V]iew / [Q]uit): ").strip()
            choice = raw_choice.upper()

            if not choice:
                print("No decision entered. Please enter 'A' to Accept, 'R' to Reject, 'N' for Needs Review, 'V' to View, or 'Q' to Quit.")
                continue

            if choice == "V":
                launch_image_viewer(abs_p)
                continue

            if choice == "Q":
                print("\n[Save & Exit] Session paused by reviewer.")
                # Preserve remaining unreviewed items
                reviewed.extend(records[idx - 1:])
                return reviewed

            if choice in ["A", "ACCEPT"]:
                split_choice = SplitAssignment.UNASSIGNED.value
                if r.organ_category in [OrganCategory.PIGEONPEA_POD.value, OrganCategory.PIGEONPEA_STEM_ROOT.value]:
                    print("  [Policy] Pigeonpea non-leaf organ: strictly held out as 'unassigned' (Tur_Non_Leaf_Organ).")
                    split_choice = SplitAssignment.UNASSIGNED.value
                elif r.organ_category == OrganCategory.UNSUPPORTED_PIGEONPEA_DISEASE.value:
                    print("  [Policy] Genuine pigeonpea with unsupported disease: strictly held out as 'unassigned' (Tur_Unsupported_Disease).")
                    split_choice = SplitAssignment.UNASSIGNED.value
                elif r.organ_category in [OrganCategory.WEED_FOLIAGE.value, OrganCategory.NON_CROP_CLUTTER.value, OrganCategory.OTHER_CROP_LEAF.value]:
                    print("  Select Target Split for Accepted Not_Tur Image:")
                    print("    [1] train")
                    print("    [2] val")
                    print("    [3] test_holdout")
                    print("    [4] unassigned (default - safe holdout)")
                    s_in = input("  Choice (1-4, default 4 [unassigned]): ").strip()
                    s_map = {"1": "train", "2": "val", "3": "test_holdout", "4": "unassigned"}
                    split_choice = s_map.get(s_in, SplitAssignment.UNASSIGNED.value)

                note_in = input("  Optional verification note (press Enter to skip): ").strip()
                valid, label, status, split = validate_decision(r, "ACCEPT", split_choice)
                if not valid:
                    print(f"  [ERROR] {split}. Try again.")
                    continue

                stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                note_suffix = f" | Verified by {reviewer_name} [{stamp}]"
                if note_in:
                    note_suffix += f": {note_in}"
                note = f"{r.reviewer_notes}{note_suffix}".strip()

                reviewed.append(HardNegativeRecord(
                    image_id=r.image_id,
                    relative_file_path=r.relative_file_path,
                    source_provenance=r.source_provenance,
                    verified_label=label,
                    organ_category=r.organ_category,
                    reviewer_status=status,
                    reviewer_notes=note,
                    sha256=r.sha256,
                    duplicate_group_id=r.duplicate_group_id,
                    split_assignment=split,
                    date_added=r.date_added
                ))
                print(f"  [ACCEPTED] Image {r.image_id} marked {status} with label '{label}' (Split: {split}).")
                break

            elif choice in ["R", "REJECT"]:
                reason_in = input("  Rejection reason (press Enter for 'unsuitable'): ").strip()
                reason = reason_in if reason_in else "unsuitable"
                valid, label, status, split = validate_decision(r, "REJECT")
                stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                note = f"{r.reviewer_notes} | REJECTED by {reviewer_name} [{stamp}]: {reason}".strip()
                reviewed.append(HardNegativeRecord(
                    image_id=r.image_id,
                    relative_file_path=r.relative_file_path,
                    source_provenance=r.source_provenance,
                    verified_label=label,
                    organ_category=r.organ_category,
                    reviewer_status=status,
                    reviewer_notes=note,
                    sha256=r.sha256,
                    duplicate_group_id=r.duplicate_group_id,
                    split_assignment=split,
                    date_added=r.date_added
                ))
                print(f"  [REJECTED] Image {r.image_id} excluded.")
                break

            elif choice in ["N", "NEEDS_REVIEW", "S", "SKIP"]:
                note_in = input("  Reason image needs further review (optional, press Enter to skip): ").strip()
                stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                note_suffix = f" | Flagged by {reviewer_name} [{stamp}]"
                if note_in:
                    note_suffix += f": {note_in}"
                note = f"{r.reviewer_notes}{note_suffix}".strip()
                reviewed.append(HardNegativeRecord(
                    image_id=r.image_id,
                    relative_file_path=r.relative_file_path,
                    source_provenance=r.source_provenance,
                    verified_label=r.verified_label,
                    organ_category=r.organ_category,
                    reviewer_status=ReviewerStatus.PENDING_REVIEW.value,
                    reviewer_notes=note,
                    sha256=r.sha256,
                    duplicate_group_id=r.duplicate_group_id,
                    split_assignment=SplitAssignment.UNASSIGNED.value,
                    date_added=r.date_added
                ))
                print(f"  [PENDING] Image {r.image_id} left in PENDING_REVIEW.")
                break

            else:
                print("  Invalid input. Please choose A (Accept), R (Reject), N (Needs review), V (View image), or Q (Quit).")

    return reviewed


def save_review_decisions(
    output_path: Path,
    records: List[HardNegativeRecord],
    reviewer_name: str
):
    """Saves review records to a dedicated review decisions file."""
    # Run schema validator before writing
    validator = HardNegativeManifestValidator(PROJECT_ROOT)
    is_valid, errors = validator.validate_records(records)
    if not is_valid:
        print("\n[FAIL] Schema validation failed for reviewed decisions:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    accepted_cnt = sum(1 for r in records if r.reviewer_status == ReviewerStatus.VERIFIED_ACCEPTED.value)
    rejected_cnt = sum(1 for r in records if r.reviewer_status == ReviewerStatus.REJECTED_EXCLUDE.value)
    pending_cnt = sum(1 for r in records if r.reviewer_status == ReviewerStatus.PENDING_REVIEW.value)

    payload = {
        "review_document_version": "v4_human_review_decisions_v1",
        "last_updated": datetime.now().isoformat(),
        "primary_reviewer": reviewer_name,
        "total_staged_records": len(records),
        "summary": {
            "verified_accepted": accepted_cnt,
            "rejected_excluded": rejected_cnt,
            "pending_review": pending_cnt,
            "target_collection_goal": 300,
            "net_shortage_against_target": max(0, 300 - accepted_cnt)
        },
        "records": [r.to_dict() for r in records]
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"\n[Saved] Review decisions saved to: {output_path.resolve()}")
    print(f"  - Verified Accepted: {accepted_cnt}")
    print(f"  - Rejected Excluded: {rejected_cnt}")
    print(f"  - Pending Review:    {pending_cnt}")


def main():
    parser = argparse.ArgumentParser(description="TurSathi AI Hard-Negative Human Review Tool")
    parser.add_argument(
        "--manifest",
        type=str,
        default=str(CANDIDATE_MANIFEST_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        help="Path to candidate manifest to review"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_DECISIONS_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        help="Path to save review decisions"
    )
    parser.add_argument("--list-only", action="store_true", help="List all staged images and exit")
    parser.add_argument("--auto-open", action="store_true", help="Automatically launch image viewer for each item")
    parser.add_argument("--re-review-all", action="store_true", help="Re-prompt previously reviewed images instead of preserving prior decisions")
    parser.add_argument("--reviewer-name", type=str, default="Lead_Agronomist_Reviewer", help="Reviewer identifier")
    parser.add_argument(
        "--apply-decisions",
        type=str,
        default=None,
        help="Path to JSON file with scripted decisions (for testing or automated batch review)"
    )
    args = parser.parse_args()

    manifest_path = PROJECT_ROOT / args.manifest
    output_path = PROJECT_ROOT / args.output
    records = load_candidate_records(manifest_path)

    # Merge previously recorded decisions if the decisions output file already exists
    if output_path.exists():
        records = merge_existing_decisions(records, output_path)

    if args.list_only:
        list_staged_images(records)
        return

    if args.apply_decisions:
        decisions_file = PROJECT_ROOT / args.apply_decisions
        if not decisions_file.exists():
            print(f"[FAIL] Decision file missing: {decisions_file}")
            sys.exit(1)
        with open(decisions_file, "r", encoding="utf-8") as f:
            d_map = json.load(f)
        print(f"Applying {len(d_map)} scripted decisions from: {decisions_file} ...")
        reviewed, errors = apply_decision_dictionary(records, d_map, args.reviewer_name)
        if errors:
            print(f"[FAIL] Found {len(errors)} decision validation errors:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
    else:
        reviewed = run_interactive_review(
            records,
            args.reviewer_name,
            auto_open=args.auto_open,
            re_review_all=args.re_review_all
        )

    save_review_decisions(output_path, reviewed, args.reviewer_name)


if __name__ == "__main__":
    main()
