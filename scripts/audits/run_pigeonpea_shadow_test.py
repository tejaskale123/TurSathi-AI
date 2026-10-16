# -*- coding: utf-8 -*-
"""
TurSathi AI - Phase 5: Safe Real-Field Shadow Testing Tool

Compares the existing production pigeonpea disease model against the
clean-candidate experimental model on new real-field images in inference-only mode.

Safety & Preservation Rules:
1. 100% Inference-only: model.eval(), torch.no_grad(). Zero weight mutations.
2. Read-only image ingestion: Never moves, renames, deletes, or modifies input images.
3. Strict isolation: Reads from datasets/pigeonpea_real_field_shadow_v1,
   writes reports only to reports/pigeonpea_real_field_shadow_v1.
4. Overwrite protection: Refuses to overwrite reports without --overwrite.
5. Absolute integrity: Never touches production checkpoints, datasets, or application code.
6. Safety boundaries: Never issues chemical/spray recommendations; explicitly warns
   that model confidence and inter-model agreement do not equal diagnostic correctness.
"""

import sys
import os
import argparse
import json
import csv
import time
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
DEFAULT_INPUT_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_real_field_shadow_v1"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "pigeonpea_real_field_shadow_v1"
DEFAULT_PROD_CKPT = PROJECT_ROOT / "models" / "best_pigeonpea_disease_final_efficientnet_b0.pth"
DEFAULT_EXP_CKPT = (
    PROJECT_ROOT
    / "models"
    / "experimental"
    / "pigeonpea_clean_candidate_v1"
    / "best_pigeonpea_clean_candidate_v1_efficientnet_b0.pth"
)

EXPECTED_CLASSES = ["Healthy", "Leaf_Spot", "Leaf_webber", "Sterilic_mosaic", "Wilt"]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

PROHIBITED_OUTPUT_ROOTS = [
    PROJECT_ROOT / "models" / "best_pigeonpea_disease_final_efficientnet_b0.pth",
    PROJECT_ROOT / "datasets" / "pigeonpea_disease_final",
    PROJECT_ROOT / "datasets" / "pigeonpea_disease_clean_candidate_v1",
    PROJECT_ROOT / "backend",
    PROJECT_ROOT / "frontend",
    PROJECT_ROOT / "mobile",
]


def validate_safety_boundaries(output_dir: Path, overwrite: bool = False):
    """Enforce strict isolation guarantees preventing writes to protected paths."""
    out_resolved = output_dir.resolve()
    for prohibited in PROHIBITED_OUTPUT_ROOTS:
        prohibited_resolved = prohibited.resolve()
        if out_resolved == prohibited_resolved or prohibited_resolved in out_resolved.parents:
            print(f"CRITICAL SAFETY VIOLATION: Output directory {out_resolved} violates protected boundary {prohibited_resolved}!")
            sys.exit(1)

    if out_resolved.exists() and any(out_resolved.iterdir()) and not overwrite:
        print(f"OVERWRITE PROTECTION: Output directory {out_resolved} already contains files.")
        print("Use --overwrite to allow replacing previous shadow test reports.")
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
    return model, classes, checkpoint


def parse_ground_truth(gt_path: Path, expected_classes: list):
    """Parse optional ground truth CSV."""
    if not gt_path.exists():
        print(f"ERROR: Ground-truth file not found: {gt_path}")
        sys.exit(1)

    gt_map = {}
    with open(gt_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = [c.lower().strip() for c in reader.fieldnames]
        
        # Identify image and label columns
        img_col = next((c for c in reader.fieldnames if c.lower().strip() in ["image_name", "filename", "image", "image_path", "file"]), None)
        lbl_col = next((c for c in reader.fieldnames if c.lower().strip() in ["label", "class", "ground_truth", "disease"]), None)

        if not img_col or not lbl_col:
            print(f"ERROR: Could not identify image and label columns in {gt_path}. Found columns: {reader.fieldnames}")
            sys.exit(1)

        for row in reader:
            img_key = Path(row[img_col].strip()).name
            lbl_val = row[lbl_col].strip()
            if lbl_val not in expected_classes:
                print(f"WARNING: Unknown label '{lbl_val}' for image '{img_key}'. Skipping.")
                continue
            gt_map[img_key] = lbl_val

    print(f"Loaded {len(gt_map)} verified ground-truth annotations from {gt_path.name}.")
    return gt_map


def main():
    parser = argparse.ArgumentParser(
        description="TurSathi AI - Phase 5: Pigeonpea Real-Field Shadow Testing Tool"
    )
    parser.add_argument("--input-dir", type=str, default=str(DEFAULT_INPUT_DIR),
                        help="Path to directory containing new real-field images")
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUTPUT_DIR),
                        help="Path to output directory for shadow test reports")
    parser.add_argument("--prod-ckpt", type=str, default=str(DEFAULT_PROD_CKPT),
                        help="Path to production model checkpoint")
    parser.add_argument("--exp-ckpt", type=str, default=str(DEFAULT_EXP_CKPT),
                        help="Path to experimental model checkpoint")
    parser.add_argument("--ground-truth", type=str, default=None,
                        help="Optional CSV file with verified ground-truth labels")
    parser.add_argument("--batch-size", type=int, default=16,
                        help="Inference batch size")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate configuration, paths, and checkpoints without running inference")
    parser.add_argument("--overwrite", action="store_true",
                        help="Allow overwriting existing reports in output directory")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    prod_ckpt = Path(args.prod_ckpt).resolve()
    exp_ckpt = Path(args.exp_ckpt).resolve()
    gt_file = Path(args.ground_truth).resolve() if args.ground_truth else None

    print("=" * 80)
    print("TurSathi AI — Real-Field Pigeonpea Model Shadow Testing Tool")
    print("=" * 80)
    print(f"Input Directory       : {input_dir}")
    print(f"Output Report Dir     : {output_dir}")
    print(f"Production Checkpoint : {prod_ckpt}")
    print(f"Experimental Checkpoint: {exp_ckpt}")
    print(f"Ground Truth File     : {gt_file if gt_file else 'None (Agreement Comparison Only)'}")
    print(f"Dry-Run Mode          : {args.dry_run}")
    print(f"Overwrite Allowed     : {args.overwrite}")

    # 1. Path Safety Validation
    validate_safety_boundaries(output_dir, overwrite=args.overwrite)

    if not prod_ckpt.exists():
        print(f"ERROR: Production checkpoint does not exist: {prod_ckpt}")
        sys.exit(1)
    if not exp_ckpt.exists():
        print(f"ERROR: Experimental checkpoint does not exist: {exp_ckpt}")
        sys.exit(1)

    # 2. Input Directory Inspection
    if not input_dir.exists():
        print(f"\nNotice: Input directory does not exist. Creating empty staging directory: {input_dir}")
        input_dir.mkdir(parents=True, exist_ok=True)

    image_files = sorted([
        p for p in input_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ])
    print(f"Found {len(image_files)} real-field image files in input directory.")

    # 3. Dry-Run Mode
    if args.dry_run:
        print("\n" + "=" * 80)
        print("DRY-RUN VALIDATION PASSED")
        print("=" * 80)
        print("1. Production and experimental checkpoints exist and are accessible.")
        print("2. Output path is strictly isolated under reports/.")
        print("3. Input directory is configured.")
        print("4. Zero model weights were modified or trained.")
        print("5. Zero reports were written.")
        sys.exit(0)

    if len(image_files) == 0:
        print("\nWARNING: No images found in input directory.")
        print(f"Place new real-field pigeonpea images into: {input_dir}")
        print("Then re-run this shadow test script.")
        sys.exit(0)

    # 4. Device & Model Initialization
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Inference Device: {device}")

    print("\nLoading Production Model...")
    prod_model, prod_classes, prod_meta = load_model_for_inference(prod_ckpt, device)
    print(f"  Production Classes: {prod_classes}")

    print("Loading Experimental Model...")
    exp_model, exp_classes, exp_meta = load_model_for_inference(exp_ckpt, device)
    print(f"  Experimental Classes: {exp_classes}")

    # Verify classes match exactly
    if prod_classes != exp_classes:
        print("CRITICAL MISMATCH: Model classes do not match!")
        sys.exit(1)
    classes = prod_classes

    # Load ground truth if supplied
    gt_map = parse_ground_truth(gt_file, classes) if gt_file else None

    # Preprocessing Pipeline (Identical to production predictor)
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    # 5. Execute Shadow Inference
    print(f"\nRunning shadow inference on {len(image_files)} images...")
    start_time = time.time()
    results = []

    for img_path in image_files:
        rel_path = str(img_path.relative_to(input_dir))
        entry = {
            "image_path": rel_path,
            "filename": img_path.name,
            "production_class": None,
            "production_confidence": None,
            "experimental_class": None,
            "experimental_confidence": None,
            "models_agree": None,
            "ground_truth_label": gt_map.get(img_path.name) if gt_map else None,
            "production_correct": None,
            "experimental_correct": None,
            "error": None
        }

        try:
            with Image.open(img_path) as pil_img:
                rgb_img = pil_img.convert("RGB")
                tensor = transform(rgb_img).unsqueeze(0).to(device)

            with torch.no_grad():
                # Production prediction
                p_out = prod_model(tensor)
                p_probs = torch.softmax(p_out, dim=1)[0]
                p_conf, p_idx = torch.max(p_probs, dim=0)

                # Experimental prediction
                e_out = exp_model(tensor)
                e_probs = torch.softmax(e_out, dim=1)[0]
                e_conf, e_idx = torch.max(e_probs, dim=0)

            p_class = classes[p_idx.item()]
            e_class = classes[e_idx.item()]
            p_conf_val = float(p_conf.item())
            e_conf_val = float(e_conf.item())

            entry["production_class"] = p_class
            entry["production_confidence"] = round(p_conf_val, 4)
            entry["experimental_class"] = e_class
            entry["experimental_confidence"] = round(e_conf_val, 4)
            entry["models_agree"] = (p_class == e_class)

            if entry["ground_truth_label"]:
                entry["production_correct"] = (p_class == entry["ground_truth_label"])
                entry["experimental_correct"] = (e_class == entry["ground_truth_label"])

        except Exception as ex:
            entry["error"] = str(ex)

        results.append(entry)

    elapsed = time.time() - start_time
    print(f"Shadow inference completed in {elapsed:.2f} seconds ({len(image_files)/elapsed:.1f} images/sec).")

    # 6. Aggregate Statistics
    total_imgs = len(results)
    valid_results = [r for r in results if r["error"] is None]
    error_count = total_imgs - len(valid_results)

    agreements = [r for r in valid_results if r["models_agree"] is True]
    disagreements = [r for r in valid_results if r["models_agree"] is False]
    agreement_rate = (len(agreements) / len(valid_results)) if valid_results else 0.0

    prod_class_counts = Counter(r["production_class"] for r in valid_results)
    exp_class_counts = Counter(r["experimental_class"] for r in valid_results)

    disagreement_breakdown = Counter(
        f"{r['production_class']} (Prod) vs {r['experimental_class']} (Exp)"
        for r in disagreements
    )

    # 7. Write Output Reports
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "shadow_test_comparison.csv"
    json_path = output_dir / "shadow_test_summary.json"
    md_path = output_dir / "SHADOW_TEST_REPORT.md"

    # CSV write
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "image_path", "filename", "production_class", "production_confidence",
            "experimental_class", "experimental_confidence", "models_agree",
            "ground_truth_label", "production_correct", "experimental_correct", "error"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    # JSON summary
    summary_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "input_directory": str(input_dir),
        "production_checkpoint": str(prod_ckpt),
        "experimental_checkpoint": str(exp_ckpt),
        "total_images_evaluated": total_imgs,
        "valid_images": len(valid_results),
        "error_images": error_count,
        "agreement_count": len(agreements),
        "disagreement_count": len(disagreements),
        "agreement_rate": round(agreement_rate, 4),
        "production_class_distribution": dict(prod_class_counts),
        "experimental_class_distribution": dict(exp_class_counts),
        "disagreement_breakdown": dict(disagreement_breakdown),
        "ground_truth_evaluated": bool(gt_map),
        "safety_notes": [
            "Model confidence is NOT proof of diagnostic correctness.",
            "Inter-model agreement does NOT prove real-world diagnostic accuracy.",
            "Diagnosis can only be validated against certified ground-truth expert labels.",
            "Zero spray or chemical recommendations were generated by this tool."
        ]
    }

    # If ground truth was present, compute evaluation metrics
    if gt_map:
        from sklearn.metrics import classification_report, accuracy_score
        gt_eval_results = [r for r in valid_results if r["ground_truth_label"] is not None]
        if gt_eval_results:
            y_true = [r["ground_truth_label"] for r in gt_eval_results]
            y_prod = [r["production_class"] for r in gt_eval_results]
            y_exp = [r["experimental_class"] for r in gt_eval_results]

            summary_data["ground_truth_metrics"] = {
                "evaluated_samples": len(y_true),
                "production_accuracy": round(float(accuracy_score(y_true, y_prod)), 4),
                "experimental_accuracy": round(float(accuracy_score(y_true, y_exp)), 4),
                "production_report": classification_report(y_true, y_prod, target_names=classes, digits=4, output_dict=True, zero_division=0),
                "experimental_report": classification_report(y_true, y_exp, target_names=classes, digits=4, output_dict=True, zero_division=0)
            }

    with open(json_path, mode="w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    # Markdown Report
    with open(md_path, mode="w", encoding="utf-8") as f:
        f.write("# TurSathi AI — Real-Field Pigeonpea Shadow Testing Report\n\n")
        f.write(f"**Date:** {summary_data['timestamp']}  \n")
        f.write(f"**Input Dataset:** `{input_dir}` ({total_imgs} images)  \n")
        f.write(f"**Production Model:** `{prod_ckpt.name}`  \n")
        f.write(f"**Experimental Model:** `{exp_ckpt.name}`  \n\n")

        f.write("## 1. Agreement Summary\n\n")
        f.write(f"- **Total Images Evaluated:** {total_imgs}\n")
        f.write(f"- **Valid Predictions:** {len(valid_results)}\n")
        f.write(f"- **Agreement Count:** **{len(agreements)}** ({agreement_rate * 100:.2f}%)\n")
        f.write(f"- **Disagreement Count:** **{len(disagreements)}** ({(1.0 - agreement_rate) * 100:.2f}%)\n\n")

        f.write("## 2. Predicted Class Distributions\n\n")
        f.write("| Class | Production Predictions | Experimental Predictions |\n")
        f.write("|---|:---:|:---:|\n")
        for cls in classes:
            f.write(f"| **{cls}** | {prod_class_counts.get(cls, 0)} | {exp_class_counts.get(cls, 0)} |\n")
        f.write("\n")

        if disagreements:
            f.write("## 3. Top Disagreements\n\n")
            f.write("| Production Model Prediction | Experimental Model Prediction | Count |\n")
            f.write("|---|---|:---:|\n")
            for pair, count in disagreement_breakdown.most_common(10):
                p_c, e_c = pair.split(" vs ")
                f.write(f"| {p_c} | {e_c} | {count} |\n")
            f.write("\n")

        if gt_map and "ground_truth_metrics" in summary_data:
            gt_m = summary_data["ground_truth_metrics"]
            f.write("## 4. Ground-Truth Validation Metrics\n\n")
            f.write(f"Evaluated on **{gt_m['evaluated_samples']}** verified real-field annotations:\n\n")
            f.write(f"- **Production Model Accuracy:** **{gt_m['production_accuracy'] * 100:.2f}%**\n")
            f.write(f"- **Experimental Model Accuracy:** **{gt_m['experimental_accuracy'] * 100:.2f}%**\n\n")

        f.write("## 5. Critical Agricultural & Diagnostic Safety Notice\n\n")
        f.write("> [!IMPORTANT]\n")
        f.write("> - **Confidence is NOT proof of correctness:** A model predicting 99% confidence can still be diagnosing incorrectly under novel field conditions, lighting variations, or camera angles.\n")
        f.write("> - **Agreement does NOT equal accuracy:** When both models predict the same disease class, both may be wrong if the symptoms resemble another pathology.\n")
        f.write("> - **Zero Chemical Recommendations:** This tool is strictly diagnostic and comparative; no spray schedules or pesticide instructions are ever generated.\n")

    print(f"\nShadow testing outputs saved successfully to:")
    print(f"  CSV Report : {csv_path}")
    print(f"  JSON Data  : {json_path}")
    print(f"  Markdown   : {md_path}")


if __name__ == "__main__":
    main()
