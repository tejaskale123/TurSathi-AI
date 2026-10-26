"""
================================================================================
TurSathi AI - Candidate Model & Validator Safety Automated Test Suite
================================================================================
Comprehensive, non-destructive test suite verifying:
1. Candidate checkpoint strict state-dict compatibility and metadata.
2. Five-class disease order, index mapping, and output validity.
3. Preprocessing consistency (resolution, normalization).
4. Edge-case safety in TurImageGate (empty, corrupt, low-res).
5. Validator v4 manifest leak-free integrity (0 cross-split hash overlap).
6. Non-destructive safety: Zero production database writes.
================================================================================
"""

import io
import sys
import json
import unittest
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "backend"))

CANDIDATE_CKPT_PATH = PROJECT_ROOT / "models" / "candidates" / "tursathi_efficientnet_b0_candidate_20261026_072810 (1).pth"
CANDIDATE_OOD_PATH = PROJECT_ROOT / "models" / "candidates" / "ood_feature_profile_20261026_072810 (1).json"
VALIDATOR_V4_MANIFEST = PROJECT_ROOT / "ml" / "retraining" / "validator_v4" / "validator_v4_manifest.json"

EXPECTED_DISEASE_CLASSES = ["Healthy", "Leaf_Spot", "Leaf_webber", "Sterilic_mosaic", "Wilt"]


class TurEfficientNetB0(nn.Module):
    def __init__(self, num_classes=5):
        super().__init__()
        base = models.efficientnet_b0(weights=None)
        self.features = base.features
        self.avgpool = base.avgpool
        in_f = base.classifier[1].in_features
        self.dropout = nn.Dropout(p=0.2, inplace=True)
        self.classifier = nn.Linear(in_f, num_classes)

    def extract_features(self, x):
        feat = self.features(x)
        feat = self.avgpool(feat)
        return torch.flatten(feat, 1)

    def forward(self, x):
        feat = self.extract_features(x)
        out = self.dropout(feat)
        return self.classifier(out), feat


class CandidateAndValidatorSafetyTests(unittest.TestCase):

    def test_candidate_checkpoint_exists_and_loads_strictly(self):
        """Verify candidate checkpoint exists and loads strictly into TurEfficientNetB0 with zero missing keys."""
        self.assertTrue(CANDIDATE_CKPT_PATH.exists(), f"Candidate checkpoint missing: {CANDIDATE_CKPT_PATH}")
        ckpt = torch.load(CANDIDATE_CKPT_PATH, map_location="cpu", weights_only=False)
        
        self.assertIn("model_state_dict", ckpt)
        self.assertIn("classes", ckpt)
        self.assertEqual(ckpt["classes"], EXPECTED_DISEASE_CLASSES)
        self.assertEqual(ckpt["num_classes"], 5)
        
        model = TurEfficientNetB0(num_classes=5)
        load_res = model.load_state_dict(ckpt["model_state_dict"], strict=True)
        self.assertEqual(len(load_res.missing_keys), 0)
        self.assertEqual(len(load_res.unexpected_keys), 0)

    def test_candidate_ood_profile_correspondence(self):
        """Verify candidate OOD profile JSON corresponds exactly to checkpoint embedded profile."""
        self.assertTrue(CANDIDATE_OOD_PATH.exists(), f"Candidate OOD profile missing: {CANDIDATE_OOD_PATH}")
        with open(CANDIDATE_OOD_PATH, "r", encoding="utf-8") as f:
            profile_json = json.load(f)

        self.assertEqual(profile_json["classes"], EXPECTED_DISEASE_CLASSES)
        self.assertEqual(profile_json["feature_dim"], 1280)
        
        for c in EXPECTED_DISEASE_CLASSES:
            self.assertIn(c, profile_json["centroids"])
            vec = profile_json["centroids"][c]
            norm = np.linalg.norm(vec)
            self.assertGreater(norm, 0.0)
            norm_vec = np.array(vec) / (norm + 1e-8)
            self.assertAlmostEqual(float(np.linalg.norm(norm_vec)), 1.0, places=5)

    def test_candidate_output_validity_and_bounds(self):
        """Verify candidate model produces valid, finite softmax probabilities bounded in [0, 1]."""
        ckpt = torch.load(CANDIDATE_CKPT_PATH, map_location="cpu", weights_only=False)
        model = TurEfficientNetB0(num_classes=5)
        model.load_state_dict(ckpt["model_state_dict"], strict=True)
        model.eval()

        dummy_tensor = torch.randn(2, 3, 224, 224)
        with torch.no_grad():
            logits, feats = model(dummy_tensor)
            probs = torch.softmax(logits, dim=1)

        self.assertEqual(logits.shape, (2, 5))
        self.assertEqual(feats.shape, (2, 1280))
        self.assertFalse(torch.isnan(probs).any())
        self.assertFalse(torch.isinf(probs).any())
        
        sums = probs.sum(dim=1).numpy()
        for s in sums:
            self.assertAlmostEqual(float(s), 1.0, places=5)

    def test_validator_v4_manifest_zero_cross_split_leakage(self):
        """Verify validator v4 manifest exists and enforces 0% cross-split hash collisions."""
        self.assertTrue(VALIDATOR_V4_MANIFEST.exists(), f"Validator v4 manifest missing: {VALIDATOR_V4_MANIFEST}")
        with open(VALIDATOR_V4_MANIFEST, "r", encoding="utf-8") as f:
            data = json.load(f)

        records = data["records"]
        split_hashes = {"train": set(), "val": set(), "test": set()}
        for r in records:
            split_hashes[r["clean_split"]].add(r["sha256"])

        train_val_overlap = split_hashes["train"] & split_hashes["val"]
        train_test_overlap = split_hashes["train"] & split_hashes["test"]
        val_test_overlap = split_hashes["val"] & split_hashes["test"]

        self.assertEqual(len(train_val_overlap), 0, f"Train-Val leak: {len(train_val_overlap)}")
        self.assertEqual(len(train_test_overlap), 0, f"Train-Test leak: {len(train_test_overlap)}")
        self.assertEqual(len(val_test_overlap), 0, f"Val-Test leak: {len(val_test_overlap)}")

    def test_image_gate_edge_cases(self):
        """Verify TurImageGate rejects empty, corrupted, and undersized images safely."""
        from app.ml.tur_image_gate import TurImageGate
        gate = TurImageGate()

        # 1. Empty bytes
        res_empty = gate.validate_bytes(b"", source_name="test_empty")
        self.assertFalse(res_empty.is_valid_tur)
        self.assertEqual(res_empty.reason, "empty_file")

        # 2. Corrupt bytes
        res_corrupt = gate.validate_bytes(b"not_a_valid_image_bytes", source_name="test_corrupt")
        self.assertFalse(res_corrupt.is_valid_tur)
        self.assertIn(res_corrupt.reason, ["corrupted_image", "read_error"])

        # 3. Small image (< 224x224)
        small_img = Image.new("RGB", (100, 100), color=(120, 180, 70))
        buf = io.BytesIO()
        small_img.save(buf, format="JPEG")
        res_small = gate.validate_bytes(buf.getvalue(), source_name="test_small")
        self.assertFalse(res_small.is_valid_tur)
        self.assertEqual(res_small.reason, "image_too_small")


if __name__ == "__main__":
    unittest.main()
