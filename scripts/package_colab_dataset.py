#!/usr/bin/env python3
"""
TurSathi AI - Dataset Packaging for Google Colab
Packages the 5-class pigeon pea dataset (train, val, test) + OOD evaluation images
into a single, clean zip archive ready for Colab upload.
"""

import os
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DATASET_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final"
OOD_SOURCE_DIR = PROJECT_ROOT / "datasets" / "new_disease_images"
OUTPUT_ZIP = PROJECT_ROOT / "Tur_Disease_Dataset_Colab_Ready.zip"

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

def build_zip():
    print(f"Packaging dataset into: {OUTPUT_ZIP}...")
    file_count = 0

    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zip_out:
        # 1. Package 5-class in-distribution splits (train, val, test)
        for split in ["train", "val", "test"]:
            split_dir = SOURCE_DATASET_DIR / split
            if not split_dir.exists():
                print(f"Warning: {split_dir} does not exist.")
                continue
            for root, _, files in os.walk(split_dir):
                for f in sorted(files):
                    f_path = Path(root) / f
                    if f_path.suffix.lower() in VALID_EXTENSIONS:
                        # e.g., train/Healthy/image.jpg
                        arcname = f_path.relative_to(SOURCE_DATASET_DIR).as_posix()
                        zip_out.write(f_path, arcname)
                        file_count += 1

        # 2. Package OOD external evaluation images
        if OOD_SOURCE_DIR.exists():
            for f in sorted(os.listdir(OOD_SOURCE_DIR)):
                f_path = OOD_SOURCE_DIR / f
                if f_path.is_file() and f_path.suffix.lower() in VALID_EXTENSIONS:
                    arcname = f"ood_evaluation/{f}"
                    zip_out.write(f_path, arcname)
                    file_count += 1

    size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    print(f"Successfully packaged {file_count} images into {OUTPUT_ZIP.name} ({size_mb:.2f} MB)")

if __name__ == "__main__":
    build_zip()
