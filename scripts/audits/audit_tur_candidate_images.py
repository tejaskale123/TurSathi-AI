import sys
import hashlib
import json
from pathlib import Path
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

def create_contact_sheet(image_paths, output_path, cols=10, thumb_size=128):
    """Creates a simple visual contact sheet without modifying original images."""
    if not image_paths:
        return
        
    # Calculate rows
    rows = (len(image_paths) + cols - 1) // cols
    
    # Create blank canvas
    sheet_width = cols * thumb_size
    sheet_height = rows * thumb_size
    sheet = Image.new("RGB", (sheet_width, sheet_height), color=(255, 255, 255))
    
    for i, img_path in enumerate(image_paths):
        try:
            with Image.open(img_path) as img:
                img_copy = img.copy()
                img_copy.thumbnail((thumb_size, thumb_size))
                
                # Center the thumbnail in its cell
                x = (i % cols) * thumb_size
                y = (i // cols) * thumb_size
                
                # Calculate offsets for centering
                w, h = img_copy.size
                offset_x = (thumb_size - w) // 2
                offset_y = (thumb_size - h) // 2
                
                sheet.paste(img_copy, (x + offset_x, y + offset_y))
        except Exception:
            pass
            
    sheet.save(output_path, quality=85)

def main():
    print("=" * 80)
    print("PHASE 4C: CANDIDATE TUR IMAGE VERIFICATION")
    print("=" * 80)
    
    # 1. Load hashes for exclusions
    v2_train_dir = "datasets/tur_image_validator_v2/train/Tur"
    v2_hashes = get_hashes_from_dir(v2_train_dir)
    print(f"Loaded {len(v2_hashes)} hashes from V2 training data.")
    
    holdout_dir = "datasets/tur_image_validator/real_world_test/Tur"
    holdout_hashes = get_hashes_from_dir(holdout_dir)
    print(f"Loaded {len(holdout_hashes)} hashes from frozen holdout data.\n")
    
    # 2. Gather Candidates
    candidate_paths = []
    
    # Source A: new_disease_images
    dir_a = Path("datasets/new_disease_images")
    if dir_a.exists():
        for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
            candidate_paths.extend(dir_a.rglob(ext))
            
    # Source B: pigeonpea_disease_final (excluding V2 training duplicates)
    dir_b = Path("datasets/pigeonpea_disease_final")
    if dir_b.exists():
        for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
            for f in dir_b.rglob(ext):
                # We skip if it is in V2 hashes
                if get_md5(f) not in v2_hashes:
                    candidate_paths.append(f)
                    
    print(f"Found {len(candidate_paths)} potential candidate files.\n")
    
    # 3. Analyze Candidates
    candidates_info = []
    seen_hashes = set()
    
    widths = []
    heights = []
    aspect_ratios = []
    
    square = 0
    portrait = 0
    landscape = 0
    
    duplicate_of_holdout = 0
    duplicate_internal = 0
    
    valid_image_paths = []
    
    print("Analyzing candidates...")
    
    for f in candidate_paths:
        md5 = get_md5(f)
        
        is_holdout_dup = md5 in holdout_hashes
        if is_holdout_dup:
            duplicate_of_holdout += 1
            
        is_internal_dup = md5 in seen_hashes
        if is_internal_dup:
            duplicate_internal += 1
            
        seen_hashes.add(md5)
        
        try:
            # Gather file info
            file_size = f.stat().st_size
            
            with Image.open(f) as img:
                w, h = img.size
                fmt = img.format
                
                ar = w / h
                
                widths.append(w)
                heights.append(h)
                aspect_ratios.append(ar)
                
                if ar > 1.05:
                    landscape += 1
                elif ar < 0.95:
                    portrait += 1
                else:
                    square += 1
                    
                valid_image_paths.append(f)
                
                candidates_info.append({
                    "path": str(f),
                    "filename": f.name,
                    "width": w,
                    "height": h,
                    "aspect_ratio": round(ar, 4),
                    "format": fmt,
                    "size_bytes": file_size,
                    "md5": md5,
                    "is_internal_duplicate": is_internal_dup,
                    "is_holdout_duplicate": is_holdout_dup
                })
        except Exception as e:
            print(f"Error processing {f.name}: {e}")
            
    # 4. Generate Contact Sheet
    contact_sheet_path = "candidate_contact_sheet.jpg"
    print(f"\nGenerating contact sheet at {contact_sheet_path}...")
    create_contact_sheet(valid_image_paths, contact_sheet_path)
    
    # 5. Write raw data to JSON for detailed review if needed
    with open("candidate_audit_details.json", "w") as jf:
        json.dump(candidates_info, jf, indent=2)
        
    # 6. Report Summary
    print("\n" + "=" * 60)
    print("CANDIDATE SUMMARY")
    print("=" * 60)
    print(f"Total Candidates Examined : {len(candidate_paths)}")
    print(f"Valid Image Files         : {len(valid_image_paths)}")
    print(f"Unique MD5 Hashes         : {len(seen_hashes)}")
    print(f"Internal Duplicates       : {duplicate_internal}")
    print(f"Holdout Duplicates        : {duplicate_of_holdout}")
    print("-" * 60)
    print(f"Square Images             : {square}")
    print(f"Portrait Images           : {portrait}")
    print(f"Landscape Images          : {landscape}")
    print("-" * 60)
    if widths:
        print(f"Mean Width                : {np.mean(widths):.2f}")
        print(f"Mean Height               : {np.mean(heights):.2f}")
        print(f"Median Width              : {np.median(widths):.2f}")
        print(f"Median Height             : {np.median(heights):.2f}")
        print(f"Mean Aspect Ratio         : {np.mean(aspect_ratios):.4f}")
        print(f"Median Aspect Ratio       : {np.median(aspect_ratios):.4f}")
    
    print("=" * 60)
    print(f"Details saved to : candidate_audit_details.json")
    print(f"Contact sheet    : {contact_sheet_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
