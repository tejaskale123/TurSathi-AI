import sys
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

def get_v2_training_hashes(v2_dir):
    v2_hashes = set()
    v2_path = Path(v2_dir)
    if not v2_path.exists():
        print(f"Error: {v2_dir} does not exist.")
        return v2_hashes
        
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
        for f in v2_path.rglob(ext):
            v2_hashes.add(get_md5(f))
    return v2_hashes

def audit_directory(directory_path, v2_hashes, skip_dirs):
    dir_path = Path(directory_path)
    if not dir_path.exists() or not dir_path.is_dir():
        return None
        
    # Skip excluded dirs
    for skip in skip_dirs:
        if skip in str(dir_path.resolve()):
            return None
            
    image_files = []
    extensions = set()
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
        for f in dir_path.rglob(ext):
            # Check skip dirs again per file just to be safe
            skip_file = False
            for skip in skip_dirs:
                if skip in str(f.resolve()):
                    skip_file = True
                    break
            if not skip_file:
                image_files.append(f)
                extensions.add(f.suffix.lower())
                
    if not image_files:
        return None
        
    widths = []
    heights = []
    aspect_ratios = []
    landscape = 0
    portrait = 0
    square = 0
    
    exact_duplicates = 0
    
    for f in image_files:
        if get_md5(f) in v2_hashes:
            exact_duplicates += 1
            
        try:
            with Image.open(f) as img:
                w, h = img.size
                widths.append(w)
                heights.append(h)
                ar = w / h
                aspect_ratios.append(ar)
                
                if ar > 1.05:
                    landscape += 1
                elif ar < 0.95:
                    portrait += 1
                else:
                    square += 1
        except Exception:
            pass
            
    stats = {
        "path": str(dir_path),
        "count": len(image_files),
        "extensions": list(extensions),
        "mean_w": np.mean(widths) if widths else 0,
        "mean_h": np.mean(heights) if heights else 0,
        "median_w": np.median(widths) if widths else 0,
        "median_h": np.median(heights) if heights else 0,
        "landscape": landscape,
        "portrait": portrait,
        "square": square,
        "duplicates": exact_duplicates
    }
    
    return stats

def main():
    print("=" * 80)
    print("PHASE 4B: EXISTING REAL-WORLD TUR DATA INVENTORY")
    print("=" * 80)
    
    v2_dir = "datasets/tur_image_validator_v2/train/Tur"
    print(f"Loading MD5 hashes from {v2_dir}...")
    v2_hashes = get_v2_training_hashes(v2_dir)
    print(f"Loaded {len(v2_hashes)} unique V2 hashes.\n")
    
    skip_dirs = [
        str(Path("datasets/tur_image_validator_v2/train/Tur").resolve()),
        str(Path("datasets/tur_image_validator/real_world_test").resolve()),
        str(Path("PPLD_extracted/PPLD_backup_before_duplicate_removal").resolve())
    ]
    
    candidate_dirs = [
        "datasets/new_disease_images",
        "datasets/tur",
        "datasets/tur_varieties",
        "datasets/external_pigeonpea_field",
        "datasets/pigeonpea_disease_final",
        "PPLD_extracted"
    ]
    
    print(f"{'Directory':<45} | {'Count':<6} | {'Ext':<10} | {'Shape (L/P/S)':<15} | {'Mean WxH':<15} | {'Dups':<5}")
    print("-" * 110)
    
    for cdir in candidate_dirs:
        stats = audit_directory(cdir, v2_hashes, skip_dirs)
        if stats:
            exts = ",".join(stats["extensions"])
            shape = f"{stats['landscape']}/{stats['portrait']}/{stats['square']}"
            mean_dim = f"{int(stats['mean_w'])}x{int(stats['mean_h'])}"
            print(f"{stats['path']:<45} | {stats['count']:<6} | {exts:<10} | {shape:<15} | {mean_dim:<15} | {stats['duplicates']:<5}")
            
    print("\nAudit complete.")

if __name__ == "__main__":
    main()
