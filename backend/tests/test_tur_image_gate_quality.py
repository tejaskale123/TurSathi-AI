# -*- coding: utf-8 -*-
"""
Focused regression and unit test suite for TurImageGate quality improvements.

Tests:
1. Valid clear real-world leaf passes image gate.
2. Undersized images (< 224x224) are rejected with reason 'image_too_small'.
3. Corrupted image files are rejected with reason 'corrupted_image'.
4. Artificially blurred images (Laplacian variance < 35.0) are rejected with reason 'image_too_blurry'.
5. Non-existent image path is rejected with reason 'file_not_found'.
6. Grayscale (L) and transparent (RGBA) images are handled safely without crashing.
7. User-facing message backward compatibility (always contains standard guidance string).
"""

import sys
import tempfile
from pathlib import Path
import unittest

import numpy as np
import cv2
from PIL import Image

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

from app.ml.tur_image_gate import TurImageGate, MIN_IMAGE_DIMENSION, BLUR_THRESHOLD


class TestTurImageGateQuality(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.gate = TurImageGate()
        cls.test_dir = tempfile.TemporaryDirectory()
        cls.temp_path = Path(cls.test_dir.name)

        # Fixture 1: Real clear leaf from dataset
        cls.real_tur_path = Path("datasets/tur_image_validator/real_world_test/Tur/realworld_tur_01.png")

        # Fixture 2: Undersized image (150x150)
        cls.undersized_path = cls.temp_path / "undersized_150x150.png"
        small_img = Image.new("RGB", (150, 150), color=(34, 139, 34))
        small_img.save(cls.undersized_path)

        # Fixture 3: Corrupt image
        cls.corrupt_path = cls.temp_path / "corrupt.jpg"
        cls.corrupt_path.write_bytes(b"NOT_A_REAL_JPEG_HEADER_CORRUPT_BYTES")

        # Fixture 4: Synthetic clear pattern image (500x500)
        cls.clear_synthetic_path = cls.temp_path / "clear_synthetic.png"
        grid = np.zeros((500, 500, 3), dtype=np.uint8)
        grid[::20, :, :] = 255
        grid[:, ::20, :] = 255
        Image.fromarray(grid).save(cls.clear_synthetic_path)

        # Fixture 5: Severely blurred image (500x500)
        cls.blurred_path = cls.temp_path / "blurred.png"
        blurred = cv2.GaussianBlur(grid, (51, 51), 0)
        Image.fromarray(blurred).save(cls.blurred_path)

        # Fixture 6: Grayscale image (300x300)
        cls.grayscale_path = cls.temp_path / "grayscale.png"
        gray = Image.new("L", (300, 300), color=128)
        gray.save(cls.grayscale_path)

        # Fixture 7: RGBA image (300x300)
        cls.rgba_path = cls.temp_path / "rgba.png"
        rgba = Image.new("RGBA", (300, 300), color=(34, 139, 34, 255))
        rgba.save(cls.rgba_path)

        # Fixture 8: Severely underexposed/dark image (300x300, mean ~10)
        cls.dark_path = cls.temp_path / "dark.png"
        dark_arr = np.random.randint(5, 15, (300, 300, 3), dtype=np.uint8)
        Image.fromarray(dark_arr).save(cls.dark_path)

        # Fixture 9: Severely overexposed/bright image (300x300, mean ~250)
        cls.bright_path = cls.temp_path / "bright.png"
        bright_arr = np.random.randint(245, 255, (300, 300, 3), dtype=np.uint8)
        Image.fromarray(bright_arr).save(cls.bright_path)

    @classmethod
    def tearDownClass(cls):
        cls.test_dir.cleanup()

    def test_01_real_tur_image_passes(self):
        """A legitimate high-resolution clear Tur leaf photo passes all quality & crop checks."""
        self.assertTrue(self.real_tur_path.exists(), f"Fixture missing: {self.real_tur_path}")
        result = self.gate.validate(self.real_tur_path)
        self.assertTrue(result.is_valid_tur)
        self.assertEqual(result.label, "Tur")
        self.assertGreaterEqual(result.confidence, 0.90)
        self.assertEqual(result.reason, "validator_confident_tur")

    def test_02_undersized_image_rejected(self):
        """Images below MIN_IMAGE_DIMENSION (224x224) are rejected with reason 'image_too_small'."""
        result = self.gate.validate(self.undersized_path)
        self.assertFalse(result.is_valid_tur)
        self.assertEqual(result.reason, "image_too_small")
        self.assertIn("Please upload a clear Tur/Pigeonpea leaf image.", result.message)
        self.assertIn("224x224 pixels", result.message)
        self.assertIsNotNone(result.message_mr)
        self.assertIn("फोटो", result.message_mr)

    def test_03_corrupted_image_rejected(self):
        """Malformed or unidentifiable image files are safely rejected without crashing."""
        result = self.gate.validate(self.corrupt_path)
        self.assertFalse(result.is_valid_tur)
        self.assertEqual(result.reason, "corrupted_image")
        self.assertIn("Please upload a clear Tur/Pigeonpea leaf image.", result.message)
        self.assertIsNotNone(result.message_mr)

    def test_04_blurry_image_rejected(self):
        """Images with Laplacian variance below BLUR_THRESHOLD are rejected with 'image_too_blurry'."""
        result = self.gate.validate(self.blurred_path)
        self.assertFalse(result.is_valid_tur)
        self.assertEqual(result.reason, "image_too_blurry")
        self.assertIn("Image appears too blurry or out of focus.", result.message)
        self.assertIn("Please upload a clear Tur/Pigeonpea leaf image.", result.message)
        self.assertIsNotNone(result.message_mr)
        self.assertIn("अस्पष्ट", result.message_mr)

    def test_05_file_not_found(self):
        """Non-existent path returns file_not_found error safely."""
        missing = self.temp_path / "non_existent.jpg"
        result = self.gate.validate(missing)
        self.assertFalse(result.is_valid_tur)
        self.assertEqual(result.reason, "file_not_found")

    def test_06_grayscale_and_rgba_modes_handled_safely(self):
        """Grayscale and RGBA images are converted to RGB and processed without unhandled exceptions."""
        res_gray = self.gate.validate(self.grayscale_path)
        self.assertIsInstance(res_gray.is_valid_tur, bool)

        res_rgba = self.gate.validate(self.rgba_path)
        self.assertIsInstance(res_rgba.is_valid_tur, bool)

    def test_07_api_message_compatibility(self):
        """Every rejected validation result provides a user-facing message compatible with API schemas."""
        for path in [self.undersized_path, self.corrupt_path, self.blurred_path, self.dark_path, self.bright_path]:
            res = self.gate.validate(path)
            self.assertFalse(res.is_valid_tur)
            self.assertIsNotNone(res.message)
            self.assertIn("Please upload a clear Tur/Pigeonpea leaf image", res.message)

    def test_08_dark_low_lighting_image_rejected(self):
        """Severely underexposed / dark images (< 35.0 mean brightness) are rejected with reason 'image_too_dark'."""
        result = self.gate.validate(self.dark_path)
        self.assertFalse(result.is_valid_tur)
        self.assertEqual(result.reason, "image_too_dark")
        self.assertIn("Image is too dark or poorly lit.", result.message)
        self.assertIsNotNone(result.message_mr)
        self.assertIn("प्रकाश खूप कमी", result.message_mr)

    def test_09_overexposed_bright_image_rejected(self):
        """Severely overexposed / washed out images (> 235.0 mean brightness) are rejected with reason 'image_too_bright'."""
        result = self.gate.validate(self.bright_path)
        self.assertFalse(result.is_valid_tur)
        self.assertEqual(result.reason, "image_too_bright")
        self.assertIn("Image is overexposed or too bright.", result.message)
        self.assertIsNotNone(result.message_mr)
        self.assertIn("प्रकाश खूप जास्त", result.message_mr)


if __name__ == "__main__":
    unittest.main()

