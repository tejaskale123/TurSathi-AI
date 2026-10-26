#!/usr/bin/env python3
"""
TurSathi AI - Package Clean Retraining Dataset for Google Colab
Phase C Implementation:
Reads ml/retraining/clean_dataset_manifest.json and packages strictly the clean,
non-quarantined images directly into a single zip file for upload to Google Colab.
Includes the 41 external OOD evaluation images for real-world negative rejection testing.
"""

import os
import json
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_FILE = PROJECT_ROOT / "ml" / "retraining" / "clean_dataset_manifest.json"
OOD_SOURCE_DIR = PROJECT_ROOT / "datasets" / "new_disease_images"
OUTPUT_ZIP = PROJECT_ROOT / "ml" / "retraining" / "TurSathi_Pigeonpea_Clean_Dataset.zip"

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

def build_clean_zip():
    print("=" * 70)
    print("TUR SATHI AI - PACKAGING CLEAN RETRAINING DATASET")
    print("=" * 70)

    if not MANIFEST_FILE.exists():
        raise FileNotFoundError(f"Clean manifest not found at: {MANIFEST_FILE}")

    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    records = manifest.get("records", [])
    included_records = [r for r in records if r.get("status") == "included"]
    print(f"Total included clean images to package: {len(included_records)}")

    # Check disk space
    import shutil
    _, _, free_bytes = shutil.disk_usage(PROJECT_ROOT)
    free_mb = free_bytes / (1024 * 1024)
    print(f"Available disk space: {free_mb:.1f} MB (Expected zip size: ~85 MB)")

    packaged_count = 0
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zip_out:
        # 1. Write clean split files: train/<class>/..., val/<class>/..., test/<class>/...
        for rec in included_records:
            src_path = PROJECT_ROOT / rec["source_relative_path"]
            if not src_path.exists():
                print(f"Warning: source file missing: {src_path}")
                continue

            # Arcname inside zip: <clean_split>/<clean_class>/<filename>
            arcname = f"{rec['clean_split']}/{rec['clean_class']}/{rec['filename']}"
            zip_out.write(src_path, arcname)
            packaged_count += 1

        # 2. Write external OOD evaluation images
        ood_count = 0
        if OOD_SOURCE_DIR.exists():
            for f in sorted(os.listdir(OOD_SOURCE_DIR)):
                fp = OOD_SOURCE_DIR / f
                if fp.is_file() and fp.suffix.lower() in VALID_EXTENSIONS:
                    arcname = f"ood_evaluation/{f}"
                    zip_out.write(fp, arcname)
                    ood_count += 1
        print(f"Packaged {ood_count} external OOD evaluation images.")

        # 3. Add manifest metadata to zip
        zip_out.write(MANIFEST_FILE, "clean_dataset_manifest.json")

    size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    print(f"\nSuccessfully packaged clean dataset into:\n  {OUTPUT_ZIP.resolve()}")
    print(f"Total files in archive: {packaged_count} in-distribution + {ood_count} OOD images")
    print(f"Archive Size: {size_mb:.2f} MB")
    print("=" * 70)

if __name__ == "__main__":
    build_clean_zip()
