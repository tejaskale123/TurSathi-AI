import csv
from pathlib import Path
from collections import defaultdict
import numpy as np
from PIL import Image

def dhash(image, hash_size=8):
    """
    Calculate a simple difference hash (dHash) for an image.
    Resizes the image to (hash_size + 1) x hash_size, converts to grayscale,
    and compares adjacent pixels.
    """
    try:
        # Convert to grayscale and resize
        image = image.convert('L').resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = np.array(image)
        # Compare adjacent pixels
        diff = pixels[:, 1:] > pixels[:, :-1]
        return diff.flatten()
    except Exception:
        return np.zeros(hash_size * hash_size, dtype=bool)

def hamming_distance(hash1, hash2):
    return np.count_nonzero(hash1 != hash2)

def main():
    print("=" * 80)
    print("PHASE 4F: V3 CANDIDATE DISTRIBUTION AND SAMPLING AUDIT")
    print("=" * 80)
    
    manifest_path = Path("v3_candidate_manifest.csv")
    if not manifest_path.exists():
        print("Manifest not found.")
        return
        
    candidates = []
    with open(manifest_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["final_candidate_status"] == "CANDIDATE":
                row["width"] = int(row["width"])
                row["height"] = int(row["height"])
                row["aspect_ratio"] = float(row["aspect_ratio"])
                candidates.append(row)
                
    total_clean = len(candidates)
    
    # Class tracking
    classes = defaultdict(list)
    sources = defaultdict(list)
    
    for c in candidates:
        classes[c["original_class"]].append(c)
        sources[c["source_group"]].append(c)
        
    def get_stats(group_candidates):
        if not group_candidates:
            return {}
            
        widths = [c["width"] for c in group_candidates]
        heights = [c["height"] for c in group_candidates]
        ars = [c["aspect_ratio"] for c in group_candidates]
        exts = defaultdict(int)
        
        landscape = 0
        portrait = 0
        square = 0
        
        for c in group_candidates:
            exts[c["extension"].lower()] += 1
            ar = c["aspect_ratio"]
            if ar > 1.05:
                landscape += 1
            elif ar < 0.95:
                portrait += 1
            else:
                square += 1
                
        return {
            "count": len(group_candidates),
            "landscape": landscape,
            "portrait": portrait,
            "square": square,
            "mean_w": np.mean(widths),
            "mean_h": np.mean(heights),
            "median_w": np.median(widths),
            "median_h": np.median(heights),
            "min_w": np.min(widths),
            "max_w": np.max(widths),
            "min_h": np.min(heights),
            "max_h": np.max(heights),
            "mean_ar": np.mean(ars),
            "median_ar": np.median(ars),
            "extensions": dict(exts)
        }
        
    # Visual Redundancy Audit (dHash)
    print("Computing perceptual hashes for redundancy audit...")
    hashes = []
    for c in candidates:
        path = Path(c["original_source_path"])
        h = np.zeros(64, dtype=bool)
        if path.exists():
            try:
                with Image.open(path) as img:
                    h = dhash(img)
            except Exception:
                pass
        hashes.append((c, h))
        
    # Group near-duplicates
    threshold = 5  # dHash threshold for near-identical (out of 64 bits)
    redundancy_groups = []
    visited = set()
    
    for i in range(len(hashes)):
        if i in visited:
            continue
            
        c1, h1 = hashes[i]
        group = [c1]
        visited.add(i)
        
        for j in range(i + 1, len(hashes)):
            if j in visited:
                continue
                
            c2, h2 = hashes[j]
            dist = hamming_distance(h1, h2)
            if dist <= threshold:
                group.append(c2)
                visited.add(j)
                
        if len(group) > 1:
            redundancy_groups.append(group)
            
    # Prepare Report
    report = []
    report.append("============================================================")
    report.append("V3 CANDIDATE DISTRIBUTION REPORT")
    report.append("============================================================")
    report.append(f"Total Clean Candidates : {total_clean}")
    
    report.append("\n--- DISTRIBUTION BY ORIGINAL CLASS ---")
    for cls_name, cls_cands in classes.items():
        stats = get_stats(cls_cands)
        report.append(f"\nCLASS: {cls_name} ({stats['count']} images)")
        report.append(f"  Shape: {stats['portrait']} Portrait, {stats['landscape']} Landscape, {stats['square']} Square")
        report.append(f"  Width: Mean {stats['mean_w']:.1f}, Median {stats['median_w']:.1f} (Range {stats['min_w']}-{stats['max_w']})")
        report.append(f"  Height: Mean {stats['mean_h']:.1f}, Median {stats['median_h']:.1f} (Range {stats['min_h']}-{stats['max_h']})")
        report.append(f"  Aspect Ratio: Mean {stats['mean_ar']:.4f}, Median {stats['median_ar']:.4f}")
        ext_str = ", ".join(f"{k}: {v}" for k,v in stats['extensions'].items())
        report.append(f"  Extensions: {ext_str}")

    report.append("\n--- DISTRIBUTION BY SOURCE ---")
    for src_name, src_cands in sources.items():
        stats = get_stats(src_cands)
        report.append(f"\nSOURCE: {src_name} ({stats['count']} images)")
        report.append(f"  Shape: {stats['portrait']} Portrait, {stats['landscape']} Landscape, {stats['square']} Square")
        
    report.append("\n--- VISUAL REDUNDANCY AUDIT ---")
    report.append(f"Method: dHash (8x8 = 64 bit hash)")
    report.append(f"Threshold for near-identical: <= {threshold} bits difference")
    
    near_dup_images = sum(len(g) for g in redundancy_groups)
    redundant_removals = sum(len(g) - 1 for g in redundancy_groups)
    
    report.append(f"Found {len(redundancy_groups)} near-duplicate groups.")
    report.append(f"Total images involved in near-duplicate groups: {near_dup_images}")
    report.append(f"Estimated visually redundant images (if preserving 1 per group): {redundant_removals}")
    
    if total_clean > 0:
        redundancy_rate = (redundant_removals / total_clean) * 100
        report.append(f"Estimated redundancy rate: {redundancy_rate:.1f}%")
        
    report.append("\n--- RECOMMENDATIONS & SAMPLING STRATEGY ---")
    report.append("1. Should all 368 candidates be used?")
    report.append("   No. Using all 368 images directly would heavily bias the validator towards 'Wilt' (287 images), leading to a validator that might associate 'Tur' heavily with wilt symptoms rather than general leaf structure.")
    report.append("2. Is a class-balanced/subsampled candidate pool safer?")
    report.append("   Yes. A balanced pool prevents feature bias and ensures the validator learns generic 'Tur' features rather than specific disease features.")
    report.append("3. How many images per class would be reasonable?")
    report.append("   Since Sterilic_mosaic has 17 images and Leaf_Spot has 37, a reasonable subsampling strategy would be to cap the 'Wilt' class at ~30-40 images. This would create a balanced pool of ~100 diverse, high-quality, non-redundant real-world images.")
    report.append("4. Should UNKNOWN images be manually reviewed?")
    report.append("   Yes. The 26 UNKNOWN images from 'new_disease_images' should be quickly visually inspected to ensure they are indeed Tur leaves, as their provenance is less strict than the finalized disease dataset.")
    report.append("5. Does any class appear too small?")
    report.append("   'Leaf_webber' has only 1 image, which is statistically insignificant for representing that specific disease state, but still useful as a generic Tur leaf instance.")
    
    report.append("============================================================")
    
    report_txt = "\n".join(report)
    print(report_txt)
    
    with open("v3_candidate_distribution_report.txt", "w", encoding="utf-8") as f:
        f.write(report_txt)
        
    print("Done. Report written.")

if __name__ == "__main__":
    main()
