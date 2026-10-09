import csv
import hashlib
from pathlib import Path
from collections import defaultdict
import numpy as np
from PIL import Image

def get_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_hashes_from_dir(dir_path_str):
    hashes = set()
    p = Path(dir_path_str)
    if not p.exists():
        return hashes
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
        for f in p.rglob(ext):
            hashes.add(get_md5(f))
    return hashes

def main():
    print("=" * 80)
    print("PHASE 4D: FINAL CANDIDATE PROVENANCE AND CLASS AUDIT")
    print("=" * 80)
    
    # 1. Load hashes for exclusions
    v2_train_dir = "datasets/tur_image_validator_v2/train/Tur"
    v2_hashes = get_hashes_from_dir(v2_train_dir)
    print(f"Loaded {len(v2_hashes)} hashes from V2 training data.")
    
    holdout_dir = "datasets/tur_image_validator/real_world_test/Tur"
    holdout_hashes = get_hashes_from_dir(holdout_dir)
    print(f"Loaded {len(holdout_hashes)} hashes from frozen holdout data.\n")
    
    # 2. Gather Potential Files
    candidate_paths = []
    
    # Source A: new_disease_images
    dir_a = Path("datasets/new_disease_images")
    if dir_a.exists():
        for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
            candidate_paths.extend(dir_a.rglob(ext))
            
    # Source B: pigeonpea_disease_final
    dir_b = Path("datasets/pigeonpea_disease_final")
    if dir_b.exists():
        for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
            for f in dir_b.rglob(ext):
                if get_md5(f) not in v2_hashes:
                    candidate_paths.append(f)
                    
    # 3. Analyze and create manifest records
    seen_hashes = set()
    manifest = []
    
    # Stats trackers
    stats = {
        "total": len(candidate_paths),
        "holdout_dup": 0,
        "internal_dup": 0,
        "candidate": 0,
        "sources": defaultdict(int),
        "classes": defaultdict(int),
        "shapes": {"portrait": 0, "landscape": 0, "square": 0},
        "widths": [],
        "heights": [],
        "aspect_ratios": []
    }
    
    print("Processing images and building manifest...")
    
    for idx, f in enumerate(candidate_paths, 1):
        md5 = get_md5(f)
        
        # Determine Source Group and Original Class
        source_group = "unknown"
        original_class = "UNKNOWN"
        
        if "new_disease_images" in f.parts:
            source_group = "new_disease_images"
            # The prompt requested: "For images from datasets/new_disease_images, if there is no reliable original class, set: original_class = UNKNOWN"
            original_class = "UNKNOWN"
        elif "pigeonpea_disease_final" in f.parts:
            source_group = "pigeonpea_disease_final"
            # Preserving exact parent folder as class
            original_class = f.parent.name
            
        # Determine Candidate Status
        status = "CANDIDATE"
        if md5 in holdout_hashes:
            status = "EXCLUDE_HOLDOUT_DUPLICATE"
            stats["holdout_dup"] += 1
        elif md5 in seen_hashes:
            status = "EXCLUDE_INTERNAL_DUPLICATE"
            stats["internal_dup"] += 1
        else:
            stats["candidate"] += 1
            stats["sources"][source_group] += 1
            stats["classes"][original_class] += 1
            seen_hashes.add(md5)
            
        # Gather Image Metadata
        w, h, ar, fmt = 0, 0, 0.0, ""
        file_size = f.stat().st_size
        
        try:
            with Image.open(f) as img:
                w, h = img.size
                fmt = img.format or "UNKNOWN"
                ar = w / h
                
                # Only track shape/dimensions for actual accepted candidates
                if status == "CANDIDATE":
                    stats["widths"].append(w)
                    stats["heights"].append(h)
                    stats["aspect_ratios"].append(ar)
                    
                    if ar > 1.05:
                        stats["shapes"]["landscape"] += 1
                    elif ar < 0.95:
                        stats["shapes"]["portrait"] += 1
                    else:
                        stats["shapes"]["square"] += 1
        except Exception:
            pass
            
        record = {
            "candidate_id": f"CAND_{idx:04d}",
            "original_source_path": str(f),
            "source_group": source_group,
            "filename": f.name,
            "extension": f.suffix,
            "width": w,
            "height": h,
            "aspect_ratio": round(ar, 4),
            "file_size": file_size,
            "md5": md5,
            "original_class": original_class,
            "is_holdout_dup": "YES" if status == "EXCLUDE_HOLDOUT_DUPLICATE" else "NO",
            "is_internal_dup": "YES" if status == "EXCLUDE_INTERNAL_DUPLICATE" else "NO",
            "final_candidate_status": status
        }
        manifest.append(record)
        
    # 4. Write CSV
    csv_file = "v3_candidate_manifest.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=manifest[0].keys())
        writer.writeheader()
        writer.writerows(manifest)
        
    # 5. Write TXT Summary
    txt_file = "v3_candidate_summary.txt"
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write("============================================================\n")
        f.write("V3 CANDIDATE SUMMARY\n")
        f.write("============================================================\n")
        f.write(f"Total Source Images          : {stats['total']}\n")
        f.write(f"Excluded Internal Duplicates : {stats['internal_dup']}\n")
        f.write(f"Excluded Holdout Duplicates  : {stats['holdout_dup']}\n")
        f.write(f"Final Candidate Count        : {stats['candidate']}\n")
        f.write("-" * 60 + "\n")
        f.write("Candidate Count by Source Group:\n")
        for src, cnt in stats["sources"].items():
            f.write(f"  - {src}: {cnt}\n")
        f.write("-" * 60 + "\n")
        f.write("Candidate Count by Original Class:\n")
        for cls, cnt in stats["classes"].items():
            f.write(f"  - {cls}: {cnt}\n")
        f.write("-" * 60 + "\n")
        f.write(f"Portrait Images              : {stats['shapes']['portrait']}\n")
        f.write(f"Landscape Images             : {stats['shapes']['landscape']}\n")
        f.write(f"Square Images                : {stats['shapes']['square']}\n")
        f.write("-" * 60 + "\n")
        
        if stats["candidate"] > 0:
            f.write(f"Mean Width                   : {np.mean(stats['widths']):.2f}\n")
            f.write(f"Median Width                 : {np.median(stats['widths']):.2f}\n")
            f.write(f"Mean Height                  : {np.mean(stats['heights']):.2f}\n")
            f.write(f"Median Height                : {np.median(stats['heights']):.2f}\n")
            f.write(f"Mean Aspect Ratio            : {np.mean(stats['aspect_ratios']):.4f}\n")
            f.write(f"Median Aspect Ratio          : {np.median(stats['aspect_ratios']):.4f}\n")
        
        f.write("============================================================\n")

    print(f"Manifest written to: {csv_file}")
    print(f"Summary written to : {txt_file}")
    print("Done.")

if __name__ == "__main__":
    main()
