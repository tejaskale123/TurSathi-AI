"""
TurSathi AI — Non-Destructive Organ Dataset Staging Script

Copies reusable pigeonpea leaf and non-tur images into the 4-class organ dataset
structure while strictly preserving all original datasets.

SAFETY CONSTRAINTS:
1. Sources are strictly READ-ONLY (uses shutil.copy2).
2. Never modifies, renames, moves, or deletes files in source directories.
3. Preserves established train/val/test split boundaries to prevent data leakage.
4. Leaves Tur_Pod and Tur_WholePlant_or_Canopy directories ready for genuine field collection.
"""

import argparse
import logging
import shutil
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("tursathi.organ_stager")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LEAF_SOURCE = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final"
NOTTUR_SOURCE = PROJECT_ROOT / "datasets" / "tur_image_validator_v3"
DEST_ROOT = PROJECT_ROOT / "datasets" / "pigeonpea_organ_dataset"

# Exclude "Wilt": 100% of Wilt images (287 files) depict whole plants, stems, and distant canopy.
# Only genuine foliar leaf crops are staged as Tur_Leaf.
TRUE_LEAF_CLASSES = ["Healthy", "Leaf_Spot", "Leaf_webber", "Sterilic_mosaic"]
SPLITS = ["train", "val", "test"]


def validate_sources() -> bool:
    if not LEAF_SOURCE.exists():
        logger.error("Leaf source directory missing: %s", LEAF_SOURCE)
        return False
    if not NOTTUR_SOURCE.exists():
        logger.error("Not_Tur source directory missing: %s", NOTTUR_SOURCE)
        return False
    return True


def stage_dataset(dry_run: bool = False):
    logger.info("Starting organ dataset staging (dry_run=%s)", dry_run)
    logger.info("Destination: %s", DEST_ROOT)

    if not validate_sources():
        sys.exit(1)

    copied_leaf = 0
    copied_nottur = 0

    for split in SPLITS:
        leaf_dest = DEST_ROOT / split / "Tur_Leaf"
        nottur_dest = DEST_ROOT / split / "Not_Tur_or_Unsupported"
        pod_dest = DEST_ROOT / split / "Tur_Pod"
        canopy_dest = DEST_ROOT / split / "Tur_WholePlant_or_Canopy"

        if not dry_run:
            leaf_dest.mkdir(parents=True, exist_ok=True)
            nottur_dest.mkdir(parents=True, exist_ok=True)
            pod_dest.mkdir(parents=True, exist_ok=True)
            canopy_dest.mkdir(parents=True, exist_ok=True)

        # 1. Stage genuine Tur_Leaf from pigeonpea_disease_final (excluding Wilt whole-plant photos)
        for disease in TRUE_LEAF_CLASSES:
            src_dir = LEAF_SOURCE / split / disease
            if not src_dir.exists():
                continue
            for img in src_dir.glob("*.*"):
                if img.suffix.lower() not in [".jpg", ".jpeg", ".png", ".webp"]:
                    continue
                target = leaf_dest / f"{disease.lower()}_{img.name}"
                if not target.exists():
                    if not dry_run:
                        shutil.copy2(img, target)
                    copied_leaf += 1

        # 2. Stage Not_Tur_or_Unsupported from tur_image_validator_v3
        src_nottur = NOTTUR_SOURCE / split / "Not_Tur"
        if src_nottur.exists():
            for img in src_nottur.glob("*.*"):
                if img.suffix.lower() not in [".jpg", ".jpeg", ".png", ".webp"]:
                    continue
                target = nottur_dest / img.name
                if not target.exists():
                    if not dry_run:
                        shutil.copy2(img, target)
                    copied_nottur += 1

    print("\n" + "=" * 60)
    print("STAGING SUMMARY:")
    print("=" * 60)
    print(f"  Tur_Leaf images staged                 : {copied_leaf:>5d}")
    print(f"  Not_Tur_or_Unsupported images staged   : {copied_nottur:>5d}")
    print(f"  Tur_Pod images available              :     0 (Awaiting field collection)")
    print(f"  Tur_WholePlant_or_Canopy available     :     0 (Awaiting field collection)")
    print("=" * 60)
    print("STATUS: Original datasets remain untouched and immutable.")


def main():
    parser = argparse.ArgumentParser(description="Stage reusable classes for organ detector")
    parser.add_argument("--execute", action="store_true", help="Execute copy operation (default is dry-run)")
    args = parser.parse_args()

    stage_dataset(dry_run=not args.execute)


if __name__ == "__main__":
    main()
