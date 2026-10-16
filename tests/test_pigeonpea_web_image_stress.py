# -*- coding: utf-8 -*-
"""
Focused unit tests for Phase 5A: Pigeonpea Web Image Stress Testing Tool.
"""

import unittest
import pathlib
import hashlib
import torch
from scripts.audits.run_pigeonpea_web_image_stress_test import (
    validate_safety_boundaries,
    load_model_for_inference,
    EXPECTED_CLASSES,
    DEFAULT_PROD_CKPT,
    DEFAULT_EXP_CKPT,
    DEFAULT_INPUT_DIR,
    PROHIBITED_OUTPUT_ROOTS
)


class TestWebImageStressRunner(unittest.TestCase):

    def test_checkpoint_existence_and_classes(self):
        """Verify both model checkpoints exist and contain expected 5 classes in order."""
        self.assertTrue(DEFAULT_PROD_CKPT.exists(), "Production checkpoint missing")
        self.assertTrue(DEFAULT_EXP_CKPT.exists(), "Experimental checkpoint missing")

        device = torch.device("cpu")
        _, prod_classes = load_model_for_inference(DEFAULT_PROD_CKPT, device)
        _, exp_classes = load_model_for_inference(DEFAULT_EXP_CKPT, device)

        self.assertEqual(prod_classes, EXPECTED_CLASSES)
        self.assertEqual(exp_classes, EXPECTED_CLASSES)

    def test_prohibited_output_boundaries(self):
        """Verify that writing into protected directories is blocked."""
        for prohibited in PROHIBITED_OUTPUT_ROOTS:
            with self.assertRaises(SystemExit):
                validate_safety_boundaries(prohibited)

    def test_input_directory_inventory_and_duplicate_detection(self):
        """Verify 42 files exist in new_disease_images, with 1 zero-byte file and 5 duplicate pairs."""
        self.assertTrue(DEFAULT_INPUT_DIR.exists(), "Input directory missing")
        files = sorted(list(DEFAULT_INPUT_DIR.iterdir()))
        self.assertEqual(len(files), 42, "Expected exactly 42 files in new_disease_images")

        # Zero-byte file verification
        zero_byte_files = [f for f in files if f.stat().st_size == 0]
        self.assertEqual(len(zero_byte_files), 1)
        self.assertEqual(zero_byte_files[0].name, "new_disease_images")

        # Duplicate hash detection
        hash_counts = {}
        for f in files:
            h = hashlib.sha256(f.read_bytes()).hexdigest()
            hash_counts[h] = hash_counts.get(h, 0) + 1

        duplicate_groups = [fl for fl in hash_counts.values() if fl > 1]
        self.assertEqual(len(duplicate_groups), 5, "Expected exactly 5 duplicate groups")


if __name__ == "__main__":
    unittest.main()
