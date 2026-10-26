import os
import shutil
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = REPO_ROOT / "datasets"

SAFE_TO_REMOVE = [
    DATASETS_DIR / "tur_image_validator_v2",
    DATASETS_DIR / "_temp_wilt_staging",
    DATASETS_DIR / "tur",
    DATASETS_DIR / "external_pigeonpea_field",
    DATASETS_DIR / "pigeonpea_real_field_shadow_v1",
]

def execute_cleanup():
    print("=" * 70)
    print("TUR SATHI AI - EXECUTING APPROVED DATASET CLEANUP (CATEGORY 3)")
    print("=" * 70)

    # Pre-check disk space
    total, used, free_before = shutil.disk_usage(DATASETS_DIR)
    print(f"Free disk space before cleanup: {free_before / (1024*1024):.1f} MB")

    total_removed_files = 0
    total_removed_bytes = 0

    for target in SAFE_TO_REMOVE:
        if not target.exists():
            print(f"Skipping (not found): {target.name}")
            continue

        print(f"\nProcessing: {target.relative_to(REPO_ROOT)}...")
        file_count = 0
        byte_count = 0
        for root, dirs, files in os.walk(target):
            for f in files:
                fp = Path(root) / f
                file_count += 1
                byte_count += fp.stat().st_size

        print(f"  Files: {file_count:,} | Size: {byte_count / (1024*1024):.2f} MB")

        # Perform deletion
        shutil.rmtree(target)
        print(f"  ✅ Successfully removed: {target.name}")

        total_removed_files += file_count
        total_removed_bytes += byte_count

    _, _, free_after = shutil.disk_usage(DATASETS_DIR)
    reclaimed_mb = (free_after - free_before) / (1024*1024)

    print("\n" + "=" * 70)
    print("CLEANUP EXECUTION COMPLETED")
    print(f"Total files removed: {total_removed_files:,}")
    print(f"Total disk space reclaimed: {total_removed_bytes / (1024*1024):.2f} MB (~{total_removed_bytes / (1024*1024*1024):.2f} GB)")
    print(f"Free disk space now: {free_after / (1024*1024):.1f} MB")
    print("=" * 70)

if __name__ == "__main__":
    execute_cleanup()
