import os
import sys
import hashlib
from collections import defaultdict
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent

def get_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def check_folder(folder_name):
    folder_path = REPO_ROOT / "datasets" / folder_name
    if not folder_path.exists():
        print(f"Folder {folder_name} does not exist.")
        return

    hash_map = defaultdict(list)
    split_map = defaultdict(lambda: defaultdict(list))
    total_imgs = 0

    for root, dirs, files in os.walk(folder_path):
        rel_root = Path(root).relative_to(folder_path)
        parts = rel_root.parts
        if not parts:
            continue
        split = parts[0]
        cls = parts[1] if len(parts) > 1 else "_no_class_"

        for f in files:
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp")):
                total_imgs += 1
                fp = Path(root) / f
                sha = get_sha256(fp)
                rel_path = str(fp.relative_to(REPO_ROOT)).replace("\\", "/")
                hash_map[sha].append((split, cls, rel_path))
                split_map[split][cls].append(rel_path)

    # Analyze duplicates
    internal_dups = {sha: occs for sha, occs in hash_map.items() if len(occs) > 1}
    cross_split_dups = {}
    same_split_dups = {}
    class_conflict_dups = {}

    for sha, occs in internal_dups.items():
        splits = set(o[0] for o in occs)
        classes = set(o[1] for o in occs)
        if len(splits) > 1:
            cross_split_dups[sha] = occs
        else:
            same_split_dups[sha] = occs
        if len(classes) > 1:
            class_conflict_dups[sha] = occs

    print("=" * 70)
    print(f"FOLDER: datasets/{folder_name}/")
    print(f"  Total Images: {total_imgs}")
    print(f"  Unique SHA-256 Hashes: {len(hash_map)}")
    print(f"  Total Duplicate Hash Groups: {len(internal_dups)}")
    print(f"  Cross-Split Duplicate Groups (DATA LEAKAGE): {len(cross_split_dups)}")
    print(f"  Same-Split Duplicate Groups: {len(same_split_dups)}")
    print(f"  Class Label Conflict Groups: {len(class_conflict_dups)}")

    if cross_split_dups:
        print(f"  Sample Cross-Split Duplicates (Data Leakage):")
        for sha, occs in list(cross_split_dups.items())[:3]:
            print(f"    Hash: {sha[:16]}...")
            for s, c, p in occs:
                print(f"      [{s}] class={c} -> {p}")

    if class_conflict_dups:
        print(f"  Sample Class Conflict Duplicates:")
        for sha, occs in list(class_conflict_dups.items())[:3]:
            print(f"    Hash: {sha[:16]}...")
            for s, c, p in occs:
                print(f"      [{s}] class={c} -> {p}")

if __name__ == "__main__":
    for f in [
        "pigeonpea_disease_final",
        "pigeonpea_disease_clean_candidate_v1",
        "tur_image_validator",
        "tur_image_validator_v2",
        "tur_image_validator_v3",
    ]:
        check_folder(f)
