import sys
import json
import hashlib
from pathlib import Path
import numpy as np
import pytest
import torch
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "backend"))
MANIFEST_FILE = PROJECT_ROOT / "ml" / "retraining" / "clean_dataset_manifest.json"
PRODUCTION_CKPT = PROJECT_ROOT / "models" / "best_pigeonpea_disease_final_efficientnet_b0.pth"
EXPECTED_CLASSES = ["Healthy", "Leaf_Spot", "Leaf_webber", "Sterilic_mosaic", "Wilt"]

def test_clean_manifest_exists_and_valid():
    assert MANIFEST_FILE.exists(), f"Clean manifest missing: {MANIFEST_FILE}"
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert "summary" in manifest
    assert "records" in manifest
    assert manifest["classes"] == EXPECTED_CLASSES
    summary = manifest["summary"]
    assert summary["total_clean_unique_images"] == 1747
    assert summary["total_quarantined_files"] == 111

def test_zero_duplicate_leakage_in_clean_split():
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    split_hashes = {"train": set(), "val": set(), "test": set()}
    for r in manifest["records"]:
        if r["status"] == "included":
            s = r["clean_split"]
            assert s in split_hashes
            assert r["sha256"] not in split_hashes[s], f"Duplicate within split {s}: {r['sha256']}"
            split_hashes[s].add(r["sha256"])

    # Assert mathematical isolation between splits
    assert len(split_hashes["train"] & split_hashes["val"]) == 0, "Train-Val leakage detected!"
    assert len(split_hashes["train"] & split_hashes["test"]) == 0, "Train-Test leakage detected!"
    assert len(split_hashes["val"] & split_hashes["test"]) == 0, "Val-Test leakage detected!"

def test_all_conflicts_strictly_quarantined():
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    conflict_records = [r for r in manifest["records"] if r["status"] == "quarantined_conflict"]
    assert len(conflict_records) == 111
    for r in conflict_records:
        assert r["clean_split"] == "quarantine"
        assert r["quarantine_reason"] is not None

def test_preprocessing_consistency():
    from torchvision import transforms
    from ml.retraining.train_clean_pipeline import get_transforms

    try:
        from app.ml.tur_predictor import TurDiseasePredictor
    except ModuleNotFoundError:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / "backend"))
        from app.ml.tur_predictor import TurDiseasePredictor

    predictor = TurDiseasePredictor()
    inference_transform = predictor._transform
    _, eval_transform = get_transforms()

    # Create dummy PIL image
    img = Image.new("RGB", (300, 400), color=(120, 150, 90))

    t_inf = inference_transform(img)
    t_eval = eval_transform(img)

    assert t_inf.shape == t_eval.shape == torch.Size([3, 224, 224])
    # Differences must be bounded (floating point precision)
    diff = torch.abs(t_inf - t_eval).max().item()
    assert diff < 1e-4, f"Transform discrepancy detected: max diff = {diff}"

def test_production_checkpoint_contract():
    assert PRODUCTION_CKPT.exists()
    ckpt = torch.load(PRODUCTION_CKPT, map_location="cpu", weights_only=False)
    assert "model_state_dict" in ckpt
    assert "classes" in ckpt
    assert ckpt["classes"] == EXPECTED_CLASSES
    assert ckpt["num_classes"] == 5
    assert ckpt["image_size"] == 224

    sd = ckpt["model_state_dict"]
    assert ("classifier.weight" in sd) or ("classifier.1.weight" in sd)
    assert ("classifier.bias" in sd) or ("classifier.1.bias" in sd)
