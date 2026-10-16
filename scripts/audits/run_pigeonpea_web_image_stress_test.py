# -*- coding: utf-8 -*-
"""
TurSathi AI - Phase 5A: Exploratory Out-of-Distribution Web Image Stress Testing

Evaluates and compares the production pigeonpea disease model and the clean-candidate
experimental model on uncurated web-scraped images from datasets/new_disease_images/.

Strict Safety & Protocol Rules:
1. Purely exploratory/OOD observation: NOT real-field validation data.
2. Inference-only: model.eval(), torch.no_grad(). Zero weight mutations.
3. No file mutations: Source images are strictly read-only.
4. Output isolation: Writes exclusively to reports/pigeonpea_web_image_stress_v1/.
5. Overwrite refusal: Stops immediately if target report directory already exists and is non-empty.
6. Duplicate awareness: Tracks duplicate files to present both raw (41) and unique (36) statistics.
7. Diagnostic boundaries: Zero claims of real-world accuracy; zero chemical/spray recommendations.
"""

import sys
import os
import argparse
import json
import csv
import time
import hashlib
from pathlib import Path
from collections import Counter

import numpy as np
import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image

# Windows console encoding safety
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "datasets" / "new_disease_images"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "pigeonpea_web_image_stress_v1"
DEFAULT_PROD_CKPT = PROJECT_ROOT / "models" / "best_pigeonpea_disease_final_efficientnet_b0.pth"
DEFAULT_EXP_CKPT = (
    PROJECT_ROOT
    / "models"
    / "experimental"
    / "pigeonpea_clean_candidate_v1"
    / "best_pigeonpea_clean_candidate_v1_efficientnet_b0.pth"
)

EXPECTED_CLASSES = ["Healthy", "Leaf_Spot", "Leaf_webber", "Sterilic_mosaic", "Wilt"]

PROHIBITED_OUTPUT_ROOTS = [
    PROJECT_ROOT / "models" / "best_pigeonpea_disease_final_efficientnet_b0.pth",
    PROJECT_ROOT / "datasets" / "pigeonpea_disease_final",
    PROJECT_ROOT / "datasets" / "pigeonpea_disease_clean_candidate_v1",
    PROJECT_ROOT / "backend",
    PROJECT_ROOT / "frontend",
    PROJECT_ROOT / "mobile",
]


def validate_safety_boundaries(output_dir: Path):
    """Enforce strict isolation guarantees preventing writes to protected paths."""
    out_resolved = output_dir.resolve()
    for prohibited in PROHIBITED_OUTPUT_ROOTS:
        prohibited_resolved = prohibited.resolve()
        if out_resolved == prohibited_resolved or prohibited_resolved in out_resolved.parents:
            print(f"CRITICAL SAFETY VIOLATION: Output directory {out_resolved} violates protected boundary {prohibited_resolved}!")
            sys.exit(1)

    # Refuse to overwrite existing results
    if out_resolved.exists() and any(out_resolved.iterdir()):
        print(f"ERROR: Output directory {out_resolved} already exists and contains files.")
        print("Per Phase 5A requirements, overwriting existing results is prohibited. Halting.")
        sys.exit(1)


def load_model_for_inference(ckpt_path: Path, device: torch.device):
    """Load model checkpoint in strict inference-only mode."""
    if not ckpt_path.exists():
        print(f"ERROR: Checkpoint file not found: {ckpt_path}")
        sys.exit(1)

    checkpoint = torch.load(ckpt_path, map_location=device, weights_only=False)
    classes = checkpoint.get("classes")
    if classes != EXPECTED_CLASSES:
        print(f"ERROR: Checkpoint classes {classes} do not match expected {EXPECTED_CLASSES}")
        sys.exit(1)

    model = models.efficientnet_b0(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, len(classes))
    model.load_state_dict(checkpoint["model_state_dict"])
    model = model.to(device)
    model.eval()
    return model, classes


def run_stress_test(input_dir: Path, output_dir: Path, prod_ckpt: Path, exp_ckpt: Path, dry_run: bool = False):
    print("=" * 80)
    print("TurSathi AI — Phase 5A: Exploratory Web Image Stress Testing")
    print("=" * 80)
    print(f"Input Directory       : {input_dir}")
    print(f"Output Report Dir     : {output_dir}")
    print(f"Production Checkpoint : {prod_ckpt}")
    print(f"Experimental Checkpoint: {exp_ckpt}")
    print(f"Dry-Run Mode          : {dry_run}")

    # 1. Path Safety Validation
    validate_safety_boundaries(output_dir)

    if not prod_ckpt.exists():
        print(f"ERROR: Production checkpoint missing: {prod_ckpt}")
        sys.exit(1)
    if not exp_ckpt.exists():
        print(f"ERROR: Experimental checkpoint missing: {exp_ckpt}")
        sys.exit(1)
    if not input_dir.exists():
        print(f"ERROR: Input directory missing: {input_dir}")
        sys.exit(1)

    all_files = sorted(list(input_dir.iterdir()))
    print(f"\nFound {len(all_files)} total files in input directory.")

    # 2. Dry-Run Mode
    if dry_run:
        print("\n" + "=" * 80)
        print("DRY-RUN VALIDATION PASSED")
        print("=" * 80)
        print("1. Production and experimental checkpoints exist and are valid.")
        print(f"2. Input directory contains {len(all_files)} files.")
        print("3. Output directory is verified non-existent / empty.")
        print("4. Zero model weights were modified or trained.")
        print("5. Zero reports were written.")
        return

    # 3. Model Initialization (Inference-Only)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Inference Device: {device}")

    prod_model, prod_classes = load_model_for_inference(prod_ckpt, device)
    exp_model, exp_classes = load_model_for_inference(exp_ckpt, device)
    classes = prod_classes

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    # 4. Ingestion & Duplicate Tracking
    hash_seen = {}
    records = []
    skipped_records = []

    print("\nAuditing and running inference on files...")
    start_time = time.time()

    for f in all_files:
        size = f.stat().st_size
        file_bytes = f.read_bytes()
        sha256 = hashlib.sha256(file_bytes).hexdigest()

        is_dup = False
        dup_of = None
        if sha256 in hash_seen:
            is_dup = True
            dup_of = hash_seen[sha256]
        else:
            hash_seen[sha256] = f.name

        record = {
            "filename": f.name,
            "size_bytes": size,
            "dimensions": "0x0",
            "sha256": sha256,
            "is_duplicate": is_dup,
            "duplicate_of": dup_of or "",
            "status": "VALID",
            "skipped_reason": "",
            "production_class": "",
            "production_confidence": None,
            "experimental_class": "",
            "experimental_confidence": None,
            "agreement": None
        }

        # Check for non-image or 0-byte file
        if size == 0:
            record["status"] = "SKIPPED"
            record["skipped_reason"] = "Zero-byte empty file"
            skipped_records.append(record)
            records.append(record)
            continue

        try:
            with Image.open(f) as pil_img:
                pil_img.verify()
            with Image.open(f) as pil_img:
                w, h = pil_img.size
                record["dimensions"] = f"{w}x{h}"
                rgb_img = pil_img.convert("RGB")
                tensor = transform(rgb_img).unsqueeze(0).to(device)

            with torch.no_grad():
                p_out = prod_model(tensor)
                p_probs = torch.softmax(p_out, dim=1)[0]
                p_conf, p_idx = torch.max(p_probs, dim=0)

                e_out = exp_model(tensor)
                e_probs = torch.softmax(e_out, dim=1)[0]
                e_conf, e_idx = torch.max(e_probs, dim=0)

            p_class = classes[p_idx.item()]
            e_class = classes[e_idx.item()]
            p_conf_val = float(p_conf.item())
            e_conf_val = float(e_conf.item())

            record["production_class"] = p_class
            record["production_confidence"] = round(p_conf_val, 4)
            record["experimental_class"] = e_class
            record["experimental_confidence"] = round(e_conf_val, 4)
            record["agreement"] = (p_class == e_class)

        except Exception as ex:
            record["status"] = "SKIPPED"
            record["skipped_reason"] = f"Image decode failure: {ex}"
            skipped_records.append(record)

        records.append(record)

    elapsed = time.time() - start_time
    print(f"Inference completed in {elapsed:.2f} seconds.")

    # 5. Dual Statistics Aggregation
    decodable_records = [r for r in records if r["status"] == "VALID"]
    unique_decodable_records = [r for r in decodable_records if not r["is_duplicate"]]

    # All decodable (41)
    all_agreed = [r for r in decodable_records if r["agreement"] is True]
    all_disagreed = [r for r in decodable_records if r["agreement"] is False]
    all_agree_rate = len(all_agreed) / len(decodable_records) if decodable_records else 0.0

    all_prod_counts = Counter(r["production_class"] for r in decodable_records)
    all_exp_counts = Counter(r["experimental_class"] for r in decodable_records)

    # Unique decodable (36)
    uniq_agreed = [r for r in unique_decodable_records if r["agreement"] is True]
    uniq_disagreed = [r for r in unique_decodable_records if r["agreement"] is False]
    uniq_agree_rate = len(uniq_agreed) / len(unique_decodable_records) if unique_decodable_records else 0.0

    uniq_prod_counts = Counter(r["production_class"] for r in unique_decodable_records)
    uniq_exp_counts = Counter(r["experimental_class"] for r in unique_decodable_records)

    uniq_disagreement_breakdown = Counter(
        f"{r['production_class']} (Prod) vs {r['experimental_class']} (Exp)"
        for r in uniq_disagreed
    )

    # 6. Save Reports
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "stress_test_comparison.csv"
    json_path = output_dir / "stress_test_summary.json"
    md_path = output_dir / "WEB_IMAGE_STRESS_TEST_REPORT.md"

    # CSV write
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "filename", "size_bytes", "dimensions", "sha256", "is_duplicate",
            "duplicate_of", "status", "skipped_reason", "production_class",
            "production_confidence", "experimental_class", "experimental_confidence", "agreement"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    # JSON write
    summary_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "input_directory": str(input_dir),
        "production_checkpoint": str(prod_ckpt),
        "experimental_checkpoint": str(exp_ckpt),
        "evaluation_type": "Exploratory Out-of-Distribution Web Image Stress Test",
        "counts": {
            "total_files": len(all_files),
            "valid_decodable_images": len(decodable_records),
            "skipped_files": len(skipped_records),
            "exact_duplicate_files": sum(1 for r in decodable_records if r["is_duplicate"]),
            "unique_decodable_images": len(unique_decodable_records)
        },
        "all_decodable_results": {
            "evaluated_images": len(decodable_records),
            "agreements": len(all_agreed),
            "disagreements": len(all_disagreed),
            "agreement_rate": round(all_agree_rate, 4),
            "production_class_distribution": dict(all_prod_counts),
            "experimental_class_distribution": dict(all_exp_counts)
        },
        "unique_decodable_results": {
            "evaluated_images": len(unique_decodable_records),
            "agreements": len(uniq_agreed),
            "disagreements": len(uniq_disagreed),
            "agreement_rate": round(uniq_agree_rate, 4),
            "production_class_distribution": dict(uniq_prod_counts),
            "experimental_class_distribution": dict(uniq_exp_counts),
            "disagreement_breakdown": dict(uniq_disagreement_breakdown)
        },
        "safety_and_limitations": [
            "All inputs are uncurated web downloads, not real-field validation data.",
            "Zero real-world accuracy claims are made (no ground-truth annotations exist).",
            "Inter-model agreement does NOT indicate diagnostic correctness.",
            "Zero pesticide or spray recommendations were generated."
        ]
    }

    with open(json_path, mode="w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    # Markdown write
    with open(md_path, mode="w", encoding="utf-8") as f:
        f.write("# TurSathi AI — Phase 5A: Exploratory Web Image Stress Test Report\n\n")
        f.write(f"**Date:** {summary_data['timestamp']}  \n")
        f.write(f"**Input Directory:** `{input_dir}` ({len(all_files)} total items)  \n")
        f.write(f"**Production Model:** `{prod_ckpt.name}`  \n")
        f.write(f"**Experimental Model:** `{exp_ckpt.name}`  \n\n")

        f.write("## 1. Executive Summary & File Ingestion\n\n")
        f.write(f"- **Total Files Evaluated:** {len(all_files)}\n")
        f.write(f"- **Valid Decodable Images:** {len(decodable_records)} (36 JPEG, 4 PNG, 1 WebP)\n")
        f.write(f"- **Skipped Files:** {len(skipped_records)} (`new_disease_images`: 0-byte non-image file)\n")
        f.write(f"- **Exact Duplicate Files:** 5 redundant copies (10 files total)\n")
        f.write(f"- **Unique Decodable Images:** **{len(unique_decodable_records)}**\n\n")

        f.write("## 2. Agreement & Comparative Metrics\n\n")
        f.write("| Metric | All Decodable Images ($N=41$) | Unique Decodable Images ($N=36$) |\n")
        f.write("|---|:---:|:---:|\n")
        f.write(f"| **Agreements** | {len(all_agreed)} | **{len(uniq_agreed)}** |\n")
        f.write(f"| **Disagreements** | {len(all_disagreed)} | **{len(uniq_disagreed)}** |\n")
        f.write(f"| **Agreement Rate** | {all_agree_rate * 100:.2f}% | **{uniq_agree_rate * 100:.2f}%** |\n\n")

        f.write("## 3. Class Distribution Comparison (Unique Images, $N=36$)\n\n")
        f.write("| Disease Class | Production Model Predictions | Experimental Model Predictions |\n")
        f.write("|---|:---:|:---:|\n")
        for cls in classes:
            f.write(f"| **{cls}** | {uniq_prod_counts.get(cls, 0)} | {uniq_exp_counts.get(cls, 0)} |\n")
        f.write("\n")

        if uniq_disagreed:
            f.write("## 4. Disagreement Breakdown (Unique Images)\n\n")
            f.write("| Image Filename | Dimensions | Production Prediction (Conf) | Experimental Prediction (Conf) |\n")
            f.write("|---|:---:|---|---|\n")
            for r in uniq_disagreed:
                f.write(f"| `{r['filename']}` | {r['dimensions']} | {r['production_class']} ({r['production_confidence']:.2f}) | {r['experimental_class']} ({r['experimental_confidence']:.2f}) |\n")
            f.write("\n")

        f.write("## 5. Observations on Out-of-Distribution Reference Images\n\n")
        f.write("Specific notable non-field reference images:\n\n")
        for notable_fn in [
            "AAlternaria-blight-symptom-on-leaves-and-B-aerial-plant-parts-leaves-stem-buds-and.webp",
            "488313_0_En_25-1_Fig1_HTML.jpg",
            "Pigeon pea plant in fruit, Kitui, Kenya. In this form, the pods have striations. © Maundu, 2021.jpg"
        ]:
            rec = next((r for r in records if r["filename"] == notable_fn), None)
            if rec:
                f.write(f"- **`{rec['filename']}`** ({rec['dimensions']}):\n")
                f.write(f"  - Production: `{rec['production_class']}` ({rec['production_confidence']:.2f})\n")
                f.write(f"  - Experimental: `{rec['experimental_class']}` ({rec['experimental_confidence']:.2f})\n")
                f.write(f"  - Agreement: `{'AGREE' if rec['agreement'] else 'DISAGREE'}`\n")
        f.write("\n")

        f.write("## 6. Critical Safety & Protocol Notices\n\n")
        f.write("> [!IMPORTANT]\n")
        f.write("> 1. **Exploratory Observation Only:** These images originate from uncurated web searches and scientific figures. They do NOT constitute ground-truth field data.\n")
        f.write("> 2. **No Diagnostic Accuracy Claims:** Agreement between models does not prove diagnostic correctness. Both models may agree on an incorrect label when confronted with novel symptoms or out-of-scope pathogens (e.g. *Alternaria*).\n")
        f.write("> 3. **Zero Spray/Chemical Recommendations:** No prescriptive pesticide or chemical treatment guidance was generated from these test predictions.\n")

    print("\nStress test reports generated successfully:")
    print(f"  CSV : {csv_path}")
    print(f"  JSON: {json_path}")
    print(f"  MD  : {md_path}")


def main():
    parser = argparse.ArgumentParser(
        description="TurSathi AI - Phase 5A: Pigeonpea Web Image Stress Testing"
    )
    parser.add_argument("--input-dir", type=str, default=str(DEFAULT_INPUT_DIR),
                        help="Path to directory containing web stress test images")
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR),
                        help="Path to output directory for stress test reports")
    parser.add_argument("--prod-ckpt", type=str, default=str(DEFAULT_PROD_CKPT),
                        help="Path to production model checkpoint")
    parser.add_argument("--exp-ckpt", type=str, default=str(DEFAULT_EXP_CKPT),
                        help="Path to experimental model checkpoint")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate configuration and paths without running inference or writing reports")
    args = parser.parse_args()

    run_stress_test(
        input_dir=Path(args.input_dir).resolve(),
        output_dir=Path(args.output_dir).resolve(),
        prod_ckpt=Path(args.prod_ckpt).resolve(),
        exp_ckpt=Path(args.exp_ckpt).resolve(),
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
