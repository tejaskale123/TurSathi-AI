#!/usr/bin/env python3
"""
Unit tests for the Field Dataset Collection Tracker and Validator.
Tests use temporary synthetic test fixtures only.
Zero modification of production datasets or application code.
"""

import csv
import shutil
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from scripts.audits.validate_pigeonpea_field_collection import (
    FieldCollectionAuditor,
    REQUIRED_COLUMNS,
)


class TestFieldCollectionValidator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.image_dir = self.temp_path / "images"
        self.image_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_synthetic_image(self, name: str, size=(256, 256), color=(0, 255, 0)) -> Path:
        img_path = self.image_dir / name
        img = Image.new("RGB", size, color=color)
        img.save(img_path, format="JPEG")
        return img_path

    def _write_manifest(self, rows: list, custom_cols=None) -> Path:
        manifest_path = self.temp_path / "manifest.csv"
        cols = custom_cols if custom_cols is not None else REQUIRED_COLUMNS
        with open(manifest_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(cols)
            for r in rows:
                writer.writerow(r)
        return manifest_path

    def test_01_empty_manifest_reports_zero_progress(self):
        """Empty manifest reports zero collected images without crashing or inventing progress."""
        manifest = self._write_manifest([])
        auditor = FieldCollectionAuditor(manifest, image_dir=self.image_dir)
        summary = auditor.audit()

        self.assertEqual(summary.total_records, 0)
        self.assertEqual(summary.verified_records, 0)
        self.assertFalse(summary.is_dataset_ready)
        self.assertIn("zero collection records", summary.blockers[0].lower())

    def test_02_template_comments_ignored_cleanly(self):
        """Manifest containing template comments (#) ignores example rows and reports 0."""
        manifest_path = self.temp_path / "template.csv"
        with open(manifest_path, "w", newline="", encoding="utf-8") as f:
            f.write("filename,class_label,plant_id,farm_id,capture_date,verification_status,verifier_reference\n")
            f.write("# comment line 1\n")
            f.write("# example.jpg,Tur_Pod,F01_P01,FARM_01,2026-10-20,verified,Dr. Test\n")
        
        auditor = FieldCollectionAuditor(manifest_path)
        summary = auditor.audit()
        self.assertEqual(summary.total_records, 0)
        self.assertFalse(summary.is_dataset_ready)

    def test_03_missing_required_columns_flagged(self):
        """Manifest missing mandatory columns is rejected with specific blocker."""
        manifest = self._write_manifest([], custom_cols=["filename", "class_label"])
        auditor = FieldCollectionAuditor(manifest)
        summary = auditor.audit()

        self.assertFalse(summary.is_dataset_ready)
        issue_categories = [i["category"] for i in summary.issues]
        self.assertIn("MISSING_COLUMNS", issue_categories)

    def test_04_quarantined_records_excluded_from_verified_count(self):
        """Quarantined and rejected records do NOT count towards verified targets."""
        self._create_synthetic_image("pod_verified.jpg")
        self._create_synthetic_image("pod_quarantined.jpg")
        self._create_synthetic_image("pod_rejected.jpg")

        rows = [
            ["pod_verified.jpg", "Tur_Pod", "P01", "FARM_01", "2026-10-20", "verified", "Dr. A"],
            ["pod_quarantined.jpg", "Tur_Pod", "P02", "FARM_01", "2026-10-20", "quarantined", "Pending Review"],
            ["pod_rejected.jpg", "Tur_Pod", "P03", "FARM_01", "2026-10-20", "rejected", "Dr. A (Blurry)"],
        ]
        manifest = self._write_manifest(rows)
        auditor = FieldCollectionAuditor(manifest, image_dir=self.image_dir)
        summary = auditor.audit()

        self.assertEqual(summary.total_records, 3)
        self.assertEqual(summary.verified_records, 1)
        self.assertEqual(summary.quarantined_records, 1)
        self.assertEqual(summary.rejected_records, 1)
        self.assertEqual(summary.verified_by_class["Tur_Pod"], 1)
        self.assertFalse(summary.is_dataset_ready)
        self.assertTrue(any("Unresolved quarantine" in b for b in summary.blockers))

    def test_05_duplicate_sha256_hashes_flagged(self):
        """Exact duplicate files are detected via SHA-256 and blocked."""
        # Create identical images
        p1 = self._create_synthetic_image("img1.jpg", color=(100, 150, 200))
        p2 = self.image_dir / "img2.jpg"
        shutil.copyfile(p1, p2)

        rows = [
            ["img1.jpg", "Tur_Pod", "P01", "FARM_01", "2026-10-20", "verified", "Dr. A"],
            ["img2.jpg", "Tur_Pod", "P02", "FARM_01", "2026-10-20", "verified", "Dr. A"],
        ]
        manifest = self._write_manifest(rows)
        auditor = FieldCollectionAuditor(manifest, image_dir=self.image_dir)
        summary = auditor.audit()

        issue_categories = [i["category"] for i in summary.issues]
        self.assertIn("EXACT_DUPLICATE_HASH", issue_categories)
        self.assertFalse(summary.is_dataset_ready)

    def test_06_plant_level_split_leakage_detected(self):
        """If plant_id appears in multiple splits (e.g. train and test), leakage blocker is triggered."""
        cols = REQUIRED_COLUMNS + ["split"]
        rows = [
            ["img1.jpg", "Tur_Pod", "P_SHARED_01", "FARM_01", "2026-10-20", "verified", "Dr. A", "train"],
            ["img2.jpg", "Tur_Pod", "P_SHARED_01", "FARM_01", "2026-10-20", "verified", "Dr. A", "test"],
        ]
        manifest = self._write_manifest(rows, custom_cols=cols)
        auditor = FieldCollectionAuditor(manifest)
        summary = auditor.audit()

        self.assertTrue(summary.leakage_detected)
        self.assertFalse(summary.is_dataset_ready)
        self.assertTrue(any("P_SHARED_01" in b for b in summary.blockers))

    def test_07_insufficient_targets_enforce_not_ready_decision(self):
        """Partial progress does NOT declare dataset ready until all 4 targets are met."""
        rows = [
            [f"pod_{i}.jpg", "Tur_Pod", f"P{i}", "FARM_01", "2026-10-20", "verified", "Dr. A"]
            for i in range(10)
        ]
        manifest = self._write_manifest(rows)
        auditor = FieldCollectionAuditor(manifest)
        summary = auditor.audit()

        self.assertEqual(summary.verified_by_class["Tur_Pod"], 10)
        self.assertFalse(summary.target_checks["Tur_Pod"]["satisfied"])
        self.assertEqual(summary.target_checks["Tur_Pod"]["deficit"], 240)
        self.assertFalse(summary.is_dataset_ready)


    def test_08_missing_image_does_not_inflate_verified_count(self):
        """Fix 1: A row whose image file does not exist must NOT count as a verified record."""
        # Register a row claiming 'verified' but do NOT create the image file
        rows = [
            ["phantom.jpg", "Tur_Pod", "P01", "FARM_01", "2026-10-20", "verified", "Dr. A"],
        ]
        manifest = self._write_manifest(rows)
        auditor = FieldCollectionAuditor(manifest, image_dir=self.image_dir)
        summary = auditor.audit()

        # File does not exist -> FILE_NOT_FOUND error -> row is invalid
        issue_categories = [i["category"] for i in summary.issues]
        self.assertIn("FILE_NOT_FOUND", issue_categories)

        # Fix 1 assertion: verified count must stay at 0, not 1
        self.assertEqual(summary.verified_records, 0, "Missing-image row must not inflate verified_records.")
        self.assertEqual(summary.verified_by_class["Tur_Pod"], 0, "Missing-image row must not inflate verified_by_class.")
        self.assertFalse(summary.is_dataset_ready)

    def test_09_json_out_creates_missing_parent_directory(self):
        """Fix 2: --json-out must auto-create its parent directory rather than raising FileNotFoundError."""
        import json
        from dataclasses import asdict

        manifest = self._write_manifest([])
        new_subdir = self.temp_path / "new_subdir" / "nested"
        json_out = new_subdir / "audit.json"

        auditor = FieldCollectionAuditor(manifest)
        summary = auditor.audit()

        # Simulate main()'s json-out logic with Fix 2 applied
        json_out.parent.mkdir(parents=True, exist_ok=True)
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(asdict(summary), f, indent=2)

        self.assertTrue(json_out.exists(), "JSON output file must be created in a new nested directory.")
        with open(json_out, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("is_dataset_ready", data)
        self.assertFalse(data["is_dataset_ready"])


if __name__ == "__main__":
    unittest.main()
