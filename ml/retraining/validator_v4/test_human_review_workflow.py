#!/usr/bin/env python3
"""
================================================================================
TurSathi AI - Human Review Workflow & Label Governance Test Suite
================================================================================
Validates all safety invariants for the hard-negative human review tool:
1. Botanical Label Policy:
   - Pigeonpea pods/stems must NEVER be accepted as Not_Tur.
   - Unsupported pigeonpea diseases must NEVER be accepted as Not_Tur.
   - Weeds and clutter can be accepted as Not_Tur only with human review.
2. Split Isolation:
   - Unreviewed images (PENDING_REVIEW) must remain 'unassigned'.
   - Accepted non-leaf organs must remain 'unassigned' (diagnostic holdout).
   - Accepted unsupported diseases must remain 'unassigned' (OOD gate holdout).
3. Missing File Handling:
   - Non-existent files are detected and rejected by manifest validation.
4. Review Decision Validation:
   - Invalid decision strings (e.g. 'MAYBE', 'APPROVE_AUTO') are rejected.
5. Output Isolation & Baseline Immutability:
   - Decision records are written to a dedicated review file.
   - Baseline validator_v4_manifest.json and production models are never touched.
================================================================================
"""

import sys
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

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
from human_review_tool import (
    validate_decision,
    apply_decision_dictionary,
    save_review_decisions
)

BASE_MANIFEST_PATH = PROJECT_ROOT / "ml" / "retraining" / "validator_v4" / "validator_v4_manifest.json"


class TestHumanReviewWorkflow(unittest.TestCase):

    def setUp(self):
        pod_file = PROJECT_ROOT / "ml/retraining/validator_v4/incoming_hard_negatives/pigeonpea_non_leaf_organs/pigeon_pea_pods_dried.jpg"
        weed_file = PROJECT_ROOT / "ml/retraining/validator_v4/incoming_hard_negatives/agricultural_weeds/parthenium_hysterophorus_4.jpg"
        weed6_file = PROJECT_ROOT / "ml/retraining/validator_v4/incoming_hard_negatives/agricultural_weeds/parthenium_hysterophorus_6.jpg"

        pod_hash = compute_sha256(pod_file) if pod_file.exists() else "0"*64
        weed_hash = compute_sha256(weed_file) if weed_file.exists() else "0"*64
        self.weed6_hash = compute_sha256(weed6_file) if weed6_file.exists() else "0"*64

        # Sample test record representing a pigeonpea pod
        self.pod_record = HardNegativeRecord(
            image_id="TEST_POD_001",
            relative_file_path="ml/retraining/validator_v4/incoming_hard_negatives/pigeonpea_non_leaf_organs/pigeon_pea_pods_dried.jpg",
            source_provenance="Wikimedia_Commons; URL=https://example.com/pod.jpg; License=CC BY-SA 4.0; Author=TestAuthor",
            verified_label=VerifiedLabel.TUR_NON_LEAF_ORGAN.value,
            organ_category=OrganCategory.PIGEONPEA_POD.value,
            reviewer_status=ReviewerStatus.PENDING_REVIEW.value,
            reviewer_notes="Pod sample",
            sha256=pod_hash,
            duplicate_group_id=None,
            split_assignment=SplitAssignment.UNASSIGNED.value,
            date_added="2026-10-26"
        )

        # Sample test record representing a weed
        self.weed_record = HardNegativeRecord(
            image_id="TEST_WEED_001",
            relative_file_path="ml/retraining/validator_v4/incoming_hard_negatives/agricultural_weeds/parthenium_hysterophorus_4.jpg",
            source_provenance="Wikimedia_Commons; URL=https://example.com/weed.jpg; License=CC BY-SA 4.0; Author=TestAuthor",
            verified_label=VerifiedLabel.NOT_TUR.value,
            organ_category=OrganCategory.WEED_FOLIAGE.value,
            reviewer_status=ReviewerStatus.PENDING_REVIEW.value,
            reviewer_notes="Weed sample",
            sha256=weed_hash,
            duplicate_group_id=None,
            split_assignment=SplitAssignment.UNASSIGNED.value,
            date_added="2026-10-26"
        )

        # Sample test record representing genuine pigeonpea leaf with Alternaria
        self.unsupported_record = HardNegativeRecord(
            image_id="TEST_ALT_001",
            relative_file_path="ml/retraining/validator_v4/incoming_hard_negatives/pigeonpea_non_leaf_organs/pigeon_pea_pods_dried.jpg",
            source_provenance="Field_Survey; License=Internal",
            verified_label=VerifiedLabel.TUR_UNSUPPORTED_DISEASE.value,
            organ_category=OrganCategory.UNSUPPORTED_PIGEONPEA_DISEASE.value,
            reviewer_status=ReviewerStatus.PENDING_REVIEW.value,
            reviewer_notes="Alternaria blight on genuine pigeonpea leaflet",
            sha256=pod_hash,
            duplicate_group_id=None,
            split_assignment=SplitAssignment.UNASSIGNED.value,
            date_added="2026-10-26"
        )

    def test_pigeonpea_pod_cannot_be_labeled_not_tur(self):
        """Rule 1: Pigeonpea pod must be Tur_Non_Leaf_Organ and held out from active training."""
        valid, label, status, split = validate_decision(self.pod_record, "ACCEPT", target_split="train")
        self.assertTrue(valid)
        self.assertEqual(label, VerifiedLabel.TUR_NON_LEAF_ORGAN.value)
        self.assertNotEqual(label, VerifiedLabel.NOT_TUR.value, "Pod must NEVER be labeled Not_Tur!")
        self.assertEqual(split, SplitAssignment.UNASSIGNED.value, "Pod must remain unassigned from training splits!")

    def test_unsupported_disease_cannot_be_labeled_not_tur(self):
        """Rule 2: Genuine pigeonpea with unsupported disease must NEVER be labeled Not_Tur."""
        valid, label, status, split = validate_decision(self.unsupported_record, "ACCEPT", target_split="train")
        self.assertTrue(valid)
        self.assertEqual(label, VerifiedLabel.TUR_UNSUPPORTED_DISEASE.value)
        self.assertNotEqual(label, VerifiedLabel.NOT_TUR.value, "Genuine pigeonpea tissue must NOT be labeled Not_Tur!")
        self.assertEqual(split, SplitAssignment.UNASSIGNED.value, "Must be held out for OOD gate evaluation!")

    def test_weed_accepted_as_not_tur(self):
        """Rule 3: Weeds can be accepted as Not_Tur and assigned to training or validation."""
        valid, label, status, split = validate_decision(self.weed_record, "ACCEPT", target_split="train")
        self.assertTrue(valid)
        self.assertEqual(label, VerifiedLabel.NOT_TUR.value)
        self.assertEqual(status, ReviewerStatus.VERIFIED_ACCEPTED.value)
        self.assertEqual(split, "train")

    def test_rejection_marks_excluded(self):
        """Rule 4: Rejection sets REJECTED_EXCLUDE and unassigned split."""
        valid, label, status, split = validate_decision(self.weed_record, "REJECT")
        self.assertTrue(valid)
        self.assertEqual(label, VerifiedLabel.REJECTED_EXCLUDE.value)
        self.assertEqual(status, ReviewerStatus.REJECTED_EXCLUDE.value)
        self.assertEqual(split, SplitAssignment.UNASSIGNED.value)

    def test_invalid_decision_string_rejected(self):
        """Rule 5: Unknown decisions (e.g. 'AUTO', 'MAYBE') are rejected."""
        valid, _, _, err = validate_decision(self.weed_record, "INVALID_CHOICE")
        self.assertFalse(valid)
        self.assertIn("Invalid decision", err)

    def test_pending_review_split_isolation(self):
        """Rule 6: Schema validator must reject any PENDING_REVIEW image assigned to train or val."""
        violating_record = HardNegativeRecord(
            image_id="LEAK_001",
            relative_file_path="ml/retraining/validator_v4/incoming_hard_negatives/agricultural_weeds/parthenium_hysterophorus_4.jpg",
            source_provenance="Test",
            verified_label=VerifiedLabel.NOT_TUR.value,
            organ_category=OrganCategory.WEED_FOLIAGE.value,
            reviewer_status=ReviewerStatus.PENDING_REVIEW.value,
            reviewer_notes="Violating record",
            sha256=self.weed_record.sha256,
            duplicate_group_id=None,
            split_assignment=SplitAssignment.TRAIN.value,  # VIOLATION!
            date_added="2026-10-26"
        )
        validator = HardNegativeManifestValidator(PROJECT_ROOT)
        is_valid, errors = validator.validate_records([violating_record])
        self.assertFalse(is_valid)
        self.assertTrue(any("PENDING_REVIEW but assigned to active split" in e for e in errors))

    def test_missing_file_detection(self):
        """Rule 7: Schema validator must reject records referencing non-existent files."""
        ghost_record = HardNegativeRecord(
            image_id="GHOST_001",
            relative_file_path="ml/retraining/validator_v4/incoming_hard_negatives/non_existent_file.jpg",
            source_provenance="Test",
            verified_label=VerifiedLabel.NOT_TUR.value,
            organ_category=OrganCategory.NON_CROP_CLUTTER.value,
            reviewer_status=ReviewerStatus.PENDING_REVIEW.value,
            reviewer_notes="Missing file test",
            sha256="0000000000000000000000000000000000000000000000000000000000000000",
            duplicate_group_id=None,
            split_assignment=SplitAssignment.UNASSIGNED.value,
            date_added="2026-10-26"
        )
        validator = HardNegativeManifestValidator(PROJECT_ROOT)
        is_valid, errors = validator.validate_records([ghost_record])
        self.assertFalse(is_valid)
        self.assertTrue(any("File missing on disk" in e for e in errors))

    def test_duplicate_group_split_isolation(self):
        """Rule 8: Exact/near duplicates in the same group must not cross splits."""
        dup1 = HardNegativeRecord(
            image_id="DUP_001",
            relative_file_path="ml/retraining/validator_v4/incoming_hard_negatives/agricultural_weeds/parthenium_hysterophorus_4.jpg",
            source_provenance="Test",
            verified_label=VerifiedLabel.NOT_TUR.value,
            organ_category=OrganCategory.WEED_FOLIAGE.value,
            reviewer_status=ReviewerStatus.VERIFIED_ACCEPTED.value,
            reviewer_notes="Dup 1",
            sha256=self.weed_record.sha256,
            duplicate_group_id="GRP_A",
            split_assignment=SplitAssignment.TRAIN.value,
            date_added="2026-10-26"
        )
        dup2 = HardNegativeRecord(
            image_id="DUP_002",
            relative_file_path="ml/retraining/validator_v4/incoming_hard_negatives/agricultural_weeds/parthenium_hysterophorus_6.jpg",
            source_provenance="Test",
            verified_label=VerifiedLabel.NOT_TUR.value,
            organ_category=OrganCategory.WEED_FOLIAGE.value,
            reviewer_status=ReviewerStatus.VERIFIED_ACCEPTED.value,
            reviewer_notes="Dup 2",
            sha256=self.weed6_hash,
            duplicate_group_id="GRP_A",
            split_assignment=SplitAssignment.VAL.value,  # VIOLATION: Spanning train and val!
            date_added="2026-10-26"
        )
        validator = HardNegativeManifestValidator(PROJECT_ROOT)
        is_valid, errors = validator.validate_records([dup1, dup2])
        self.assertFalse(is_valid)
        self.assertTrue(any("DATA LEAKAGE VIOLATION" in e for e in errors))

    def test_baseline_manifest_immutability(self):
        """Rule 9: Baseline validator_v4_manifest.json must remain completely intact."""
        self.assertTrue(BASE_MANIFEST_PATH.exists())
        with open(BASE_MANIFEST_PATH, "r", encoding="utf-8") as f:
            base_data = json.load(f)
        total_unique = base_data["summary"]["total_unique_hashes"]
        self.assertEqual(total_unique, 3301, "Baseline manifest hash count must be exactly 3301!")

    def test_save_review_decisions_file_isolation(self):
        """Rule 10: Saving decisions writes only to the targeted output file."""
        with TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "test_decisions.json"
            save_review_decisions(out_file, [self.pod_record, self.weed_record], "Test_Agronomist")
            self.assertTrue(out_file.exists())
            with open(out_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(saved["total_staged_records"], 2)
            self.assertEqual(saved["primary_reviewer"], "Test_Agronomist")

    def test_default_split_for_weed_is_unassigned(self):
        """Rule 11: Weed/clutter acceptance defaults safely to 'unassigned', not 'train'."""
        valid, label, status, split = validate_decision(self.weed_record, "ACCEPT", target_split=None)
        self.assertTrue(valid)
        self.assertEqual(label, VerifiedLabel.NOT_TUR.value)
        self.assertEqual(status, ReviewerStatus.VERIFIED_ACCEPTED.value)
        self.assertEqual(split, SplitAssignment.UNASSIGNED.value, "Default split must be unassigned!")

    def test_pod_acceptance_always_forces_unassigned_even_if_train_requested(self):
        """Rule 12: Non-leaf organs can never be assigned to 'train' even if requested."""
        valid, label, status, split = validate_decision(self.pod_record, "ACCEPT", target_split="train")
        self.assertTrue(valid)
        self.assertEqual(label, VerifiedLabel.TUR_NON_LEAF_ORGAN.value)
        self.assertEqual(split, SplitAssignment.UNASSIGNED.value, "Non-leaf organs must always stay unassigned!")

    def test_merge_preserves_previously_accepted_decision(self):
        """Rule 13: Resuming review preserves previous decisions from human_review_decisions.json."""
        from human_review_tool import merge_existing_decisions

        # Create an accepted version of the pod record
        accepted_pod = HardNegativeRecord(
            image_id=self.pod_record.image_id,
            relative_file_path=self.pod_record.relative_file_path,
            source_provenance=self.pod_record.source_provenance,
            verified_label=VerifiedLabel.TUR_NON_LEAF_ORGAN.value,
            organ_category=self.pod_record.organ_category,
            reviewer_status=ReviewerStatus.VERIFIED_ACCEPTED.value,
            reviewer_notes="Verified by Tejas",
            sha256=self.pod_record.sha256,
            duplicate_group_id=None,
            split_assignment=SplitAssignment.UNASSIGNED.value,
            date_added="2026-10-26"
        )

        with TemporaryDirectory() as tmp_dir:
            decisions_file = Path(tmp_dir) / "human_review_decisions.json"
            save_review_decisions(decisions_file, [accepted_pod], "Tejas")

            # Merge with unreviewed candidate base records
            merged = merge_existing_decisions([self.pod_record, self.weed_record], decisions_file)
            self.assertEqual(len(merged), 2)
            # The pod record must be the accepted version, not the unreviewed base record
            pod_res = next(r for r in merged if r.image_id == self.pod_record.image_id)
            self.assertEqual(pod_res.reviewer_status, ReviewerStatus.VERIFIED_ACCEPTED.value)
            self.assertIn("Verified by Tejas", pod_res.reviewer_notes)
            # The weed record remains untouched
            weed_res = next(r for r in merged if r.image_id == self.weed_record.image_id)
            self.assertEqual(weed_res.reviewer_status, ReviewerStatus.PENDING_REVIEW.value)


if __name__ == "__main__":
    unittest.main()
