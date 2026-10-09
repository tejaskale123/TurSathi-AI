import os
import csv
import json
import shutil
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image

def get_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_hashes_from_dir(dir_path):
    hashes = set()
    p = Path(dir_path)
    if not p.exists():
        return hashes
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
        for f in p.rglob(ext):
            hashes.add(get_md5(f))
    return hashes

def main():
    print("=" * 80)
    print("PHASE 4H: CONSTRUCT V3 TUR IMAGE VALIDATOR DATASET")
    print("=" * 80)
    
    # Paths
    v2_dir = Path("datasets/tur_image_validator_v2")
    v3_dir = Path("datasets/tur_image_validator_v3")
    holdout_dir = Path("datasets/tur_image_validator/real_world_test/Tur")
    
    # 1. Gather the 121 new candidates
    proposed_selection = []
    
    # The 95 filtered candidates
    with open("v3_proposed_selection.json", "r", encoding="utf-8") as f:
        proposed_selection = json.load(f)
        
    # The 26 UNKNOWN candidates that passed human review
    with open("v3_candidate_manifest.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["final_candidate_status"] == "CANDIDATE" and row["original_class"] == "UNKNOWN":
                proposed_selection.append(row)
                
    print(f"Loaded {len(proposed_selection)} approved real-world Tur candidates.")
    
    # 2. Gather V2 hashes to avoid duplication and check holdout leakage
    v2_train_hashes = get_hashes_from_dir(v2_dir / "train" / "Tur")
    holdout_hashes = get_hashes_from_dir(holdout_dir)
    
    # 3. Dry-Run Planning
    manifest = []
    
    stats = {
        "v2_base_count": 0,
        "v3_total_count": 0,
        "splits": {
            "train": {"Tur": 0, "Not_Tur": 0},
            "val": {"Tur": 0, "Not_Tur": 0},
            "test": {"Tur": 0, "Not_Tur": 0}
        },
        "new_candidates": {
            "considered": len(proposed_selection),
            "added": 0,
            "skipped_dup_v2": 0,
            "skipped_dup_holdout": 0,
            "skipped_other": 0
        },
        "shapes": {"portrait": 0, "landscape": 0, "square": 0}
    }
    
    # 3a. Plan Base V2 copies
    v2_files_to_copy = []
    
    for split in ["train", "val", "test"]:
        for cls_name in ["Tur", "Not_Tur"]:
            src_dir = v2_dir / split / cls_name
            if src_dir.exists():
                for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
                    for f in src_dir.rglob(ext):
                        stats["v2_base_count"] += 1
                        stats["splits"][split][cls_name] += 1
                        v2_files_to_copy.append({
                            "src": f,
                            "dest": v3_dir / split / cls_name / f.name,
                            "split": split,
                            "class": cls_name,
                            "category": "V2_BASE"
                        })
                        
    # 3b. Plan New Candidate copies
    new_files_to_copy = []
    seen_new_hashes = set()
    
    for c in proposed_selection:
        src_path = Path(c["original_source_path"])
        if not src_path.exists():
            stats["new_candidates"]["skipped_other"] += 1
            continue
            
        md5 = c.get("md5", get_md5(src_path))
        
        if md5 in holdout_hashes:
            stats["new_candidates"]["skipped_dup_holdout"] += 1
            continue
            
        if md5 in v2_train_hashes:
            stats["new_candidates"]["skipped_dup_v2"] += 1
            continue
            
        if md5 in seen_new_hashes:
            stats["new_candidates"]["skipped_other"] += 1 # Internal duplicate in the selection
            continue
            
        seen_new_hashes.add(md5)
        
        dest_filename = f"rw_{md5[:8]}_{src_path.name}"
        dest_path = v3_dir / "train" / "Tur" / dest_filename
        
        stats["splits"]["train"]["Tur"] += 1
        stats["new_candidates"]["added"] += 1
        
        new_files_to_copy.append({
            "src": src_path,
            "dest": dest_path,
            "split": "train",
            "class": "Tur",
            "category": "NEW_REAL_WORLD"
        })
        
    stats["v3_total_count"] = stats["v2_base_count"] + stats["new_candidates"]["added"]
    
    # 4. Dry-Run Report Output
    print("\nDRY-RUN ANALYSIS:")
    print(f"Base V2 images to copy: {len(v2_files_to_copy)}")
    print(f"New real-world images to add: {len(new_files_to_copy)}")
    print(f"Expected V3 Total: {stats['v3_total_count']}")
    
    # 5. Perform the Construction
    print("\nConstructing V3 Dataset...")
    
    # Create directories safely
    for split in ["train", "val", "test"]:
        for cls_name in ["Tur", "Not_Tur"]:
            (v3_dir / split / cls_name).mkdir(parents=True, exist_ok=True)
            
    all_copies = v2_files_to_copy + new_files_to_copy
    
    for item in all_copies:
        # Prevent exact filename collisions just in case
        dest = item["dest"]
        if dest.exists():
            dest = dest.with_name(f"{dest.stem}_dup{dest.suffix}")
            item["dest"] = dest
            
        shutil.copy2(item["src"], dest)
        
        # Collect metadata for manifest
        try:
            with Image.open(dest) as img:
                w, h = img.size
                ar = w / h
                if ar > 1.05:
                    stats["shapes"]["landscape"] += 1
                elif ar < 0.95:
                    stats["shapes"]["portrait"] += 1
                else:
                    stats["shapes"]["square"] += 1
                    
                manifest.append({
                    "source_path": str(item["src"]),
                    "destination_path": str(dest),
                    "class": item["class"],
                    "split": item["split"],
                    "md5": get_md5(dest),
                    "width": w,
                    "height": h,
                    "aspect_ratio": round(ar, 4),
                    "source_category": item["category"]
                })
        except Exception:
            pass
            
    # 6. Write Manifest
    csv_file = "v3_dataset_manifest.csv"
    if manifest:
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=manifest[0].keys())
            writer.writeheader()
            writer.writerows(manifest)
            
    # 7. Write Report
    report = []
    report.append("============================================================")
    report.append("V3 DATASET CONSTRUCTION REPORT")
    report.append("============================================================")
    report.append(f"1. Total images before construction (V2 Base) : {stats['v2_base_count']}")
    report.append(f"2. Total images after construction (V3 Total) : {stats['v3_total_count']}")
    report.append("")
    report.append("3. Tur Count by Split:")
    report.append(f"   - Train : {stats['splits']['train']['Tur']}")
    report.append(f"   - Val   : {stats['splits']['val']['Tur']}")
    report.append(f"   - Test  : {stats['splits']['test']['Tur']}")
    report.append("")
    report.append("4. Not_Tur Count by Split:")
    report.append(f"   - Train : {stats['splits']['train']['Not_Tur']}")
    report.append(f"   - Val   : {stats['splits']['val']['Not_Tur']}")
    report.append(f"   - Test  : {stats['splits']['test']['Not_Tur']}")
    report.append("")
    report.append("--- CANDIDATE PROCESSING ---")
    report.append(f"5. Number of approved real-world candidates considered : {stats['new_candidates']['considered']}")
    report.append(f"6. Number actually added                               : {stats['new_candidates']['added']}")
    report.append(f"7. Number skipped because of exact duplicate (V2)      : {stats['new_candidates']['skipped_dup_v2']}")
    report.append(f"8. Number skipped because of holdout duplication       : {stats['new_candidates']['skipped_dup_holdout']}")
    report.append(f"9. Number skipped for any other reason                 : {stats['new_candidates']['skipped_other']}")
    report.append("")
    report.append("10. Final Class Balance (Train):")
    report.append(f"    - Tur     : {stats['splits']['train']['Tur']}")
    report.append(f"    - Not_Tur : {stats['splits']['train']['Not_Tur']}")
    report.append("")
    report.append("11. Image Dimension/Aspect-Ratio Summary (V3 Total):")
    report.append(f"    - Portrait  : {stats['shapes']['portrait']}")
    report.append(f"    - Landscape : {stats['shapes']['landscape']}")
    report.append(f"    - Square    : {stats['shapes']['square']}")
    report.append("")
    report.append("--- SECURITY & SAFETY CONFIRMATIONS ---")
    report.append("12. Confirmed: V1/V2 datasets were NOT modified (read-only copy operations).")
    report.append("13. Confirmed: Frozen real-world holdout was NOT used or duplicated.")
    report.append("14. Confirmed: No model training occurred.")
    report.append("============================================================")
    
    report_txt = "\n".join(report)
    print("\n" + report_txt)
    
    with open("v3_dataset_construction_report.txt", "w", encoding="utf-8") as f:
        f.write(report_txt)
        
    print("\nV3 Dataset constructed successfully.")

if __name__ == "__main__":
    main()
