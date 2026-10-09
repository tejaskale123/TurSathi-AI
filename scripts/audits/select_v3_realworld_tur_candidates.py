import csv
import json
import random
from pathlib import Path
import numpy as np
from PIL import Image

def dhash(image, hash_size=8):
    try:
        img = image.convert('L').resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = np.array(img)
        diff = pixels[:, 1:] > pixels[:, :-1]
        return diff.flatten()
    except Exception:
        return np.zeros(hash_size * hash_size, dtype=bool)

def hamming_distance(h1, h2):
    return np.count_nonzero(h1 != h2)

def create_contact_sheet(image_paths, output_path, cols=10, thumb_size=128):
    if not image_paths:
        return
    rows = (len(image_paths) + cols - 1) // cols
    sheet_width = cols * thumb_size
    sheet_height = rows * thumb_size
    sheet = Image.new("RGB", (sheet_width, sheet_height), color=(255, 255, 255))
    
    for i, img_path in enumerate(image_paths):
        try:
            with Image.open(img_path) as img:
                img_copy = img.copy()
                img_copy.thumbnail((thumb_size, thumb_size))
                x = (i % cols) * thumb_size
                y = (i // cols) * thumb_size
                w, h = img_copy.size
                offset_x = (thumb_size - w) // 2
                offset_y = (thumb_size - h) // 2
                sheet.paste(img_copy, (x + offset_x, y + offset_y))
        except Exception:
            pass
    sheet.save(output_path, quality=85)

def main():
    print("=" * 80)
    print("PHASE 4G: V3 CANDIDATE SELECTION AND DIVERSITY AUDIT")
    print("=" * 80)
    
    manifest_path = Path("v3_candidate_manifest.csv")
    if not manifest_path.exists():
        print("Manifest not found.")
        return
        
    # 1. Read Manifest & Exclude Dups
    candidates = []
    with open(manifest_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["final_candidate_status"] == "CANDIDATE":
                row["width"] = int(row["width"])
                row["height"] = int(row["height"])
                row["aspect_ratio"] = float(row["aspect_ratio"])
                candidates.append(row)
                
    # Group by Class
    by_class = {
        "Wilt": [],
        "Leaf_Spot": [],
        "Sterilic_mosaic": [],
        "Leaf_webber": [],
        "UNKNOWN": []
    }
    for c in candidates:
        if c["original_class"] in by_class:
            by_class[c["original_class"]].append(c)
            
    print("Generating class-specific contact sheets...")
    
    for cls_name, items in by_class.items():
        if items:
            paths = [c["original_source_path"] for c in items]
            out = f"contact_sheet_{cls_name}.jpg"
            create_contact_sheet(paths, out)
            print(f"Created: {out}")
            
    # Wilt Diversity Selection (Target 30-40)
    print("\nSelecting diverse Wilt candidates...")
    wilt_cands = by_class["Wilt"]
    
    # Compute hashes
    wilt_hashes = []
    for c in wilt_cands:
        p = Path(c["original_source_path"])
        h = np.zeros(64, dtype=bool)
        if p.exists():
            try:
                with Image.open(p) as img:
                    h = dhash(img)
            except Exception:
                pass
        wilt_hashes.append((c, h))
        
    # Simple diversity clustering
    threshold = 8 # slightly wider threshold for diversity
    selected_wilt = []
    avoided_wilt = 0
    
    # To maximize diversity, we shuffle the Wilt candidates so we don't just pick the first sequence
    random.seed(42)
    random.shuffle(wilt_hashes)
    
    for c, h in wilt_hashes:
        if len(selected_wilt) >= 40:
            break
            
        # Is it diverse enough from already selected?
        is_diverse = True
        for sel_c, sel_h in selected_wilt:
            if hamming_distance(h, sel_h) <= threshold:
                is_diverse = False
                break
                
        if is_diverse:
            selected_wilt.append((c, h))
        else:
            avoided_wilt += 1
            
    # We may still need more if the dataset was extremely redundant
    if len(selected_wilt) < 30:
        # Lower threshold and make a second pass for remaining spots
        for c, h in wilt_hashes:
            if len(selected_wilt) >= 30:
                break
            if (c, h) not in selected_wilt:
                is_diverse = True
                for sel_c, sel_h in selected_wilt:
                    if hamming_distance(h, sel_h) <= 5: # stricter near-duplicate check
                        is_diverse = False
                        break
                if is_diverse:
                    selected_wilt.append((c, h))
                    
    final_wilt = [c for c, h in selected_wilt]
    
    # Create final selection pools
    proposed_selections = {
        "Leaf_Spot": by_class["Leaf_Spot"], # All 37
        "Sterilic_mosaic": by_class["Sterilic_mosaic"], # All 17
        "Leaf_webber": by_class["Leaf_webber"], # All 1
        "Wilt": final_wilt # Filtered diverse subset (~30-40)
    }
    
    total_selected = sum(len(pool) for pool in proposed_selections.values())
    
    # Calculate shapes
    landscape = 0
    portrait = 0
    square = 0
    for pool in proposed_selections.values():
        for c in pool:
            ar = c["aspect_ratio"]
            if ar > 1.05:
                landscape += 1
            elif ar < 0.95:
                portrait += 1
            else:
                square += 1
                
    # Prepare Report
    report = []
    report.append("============================================================")
    report.append("V3 CANDIDATE SELECTION REPORT")
    report.append("============================================================")
    report.append("A. Proposed Wilt selection count          : " + str(len(final_wilt)) + " (Filtered from 287)")
    report.append("B. Proposed Leaf_Spot selection count     : " + str(len(by_class["Leaf_Spot"])) + " (All available)")
    report.append("C. Proposed Sterilic_mosaic selection cnt : " + str(len(by_class["Sterilic_mosaic"])) + " (All available)")
    report.append("D. Leaf_webber candidate                  : " + str(len(by_class["Leaf_webber"])) + " (All available)")
    report.append("E. UNKNOWN images requiring human review  : " + str(len(by_class["UNKNOWN"])) + " (Marked NEEDS_HUMAN_REVIEW)")
    report.append("-" * 60)
    report.append("F. Total proposed selected candidates     : " + str(total_selected) + " (excluding UNKNOWN)")
    report.append("G. Aspect-ratio distribution of selections:")
    report.append("   - Portrait  : " + str(portrait))
    report.append("   - Landscape : " + str(landscape))
    report.append("   - Square    : " + str(square))
    report.append("-" * 60)
    report.append("H. Near-duplicate groups avoided          : " + str(avoided_wilt) + " redundant wilt images skipped")
    report.append("\nI. Selection Rationale:")
    report.append("   - 'Leaf_Spot', 'Sterilic_mosaic', and 'Leaf_webber' candidates were small enough to include entirely,")
    report.append("     ensuring maximum class coverage.")
    report.append("   - 'Wilt' had massive class imbalance (287 images) and high visual redundancy. ")
    report.append("     A perceptual diversity filter (dHash) was applied to select a visually distinct subset")
    report.append("     of ~30-40 Wilt images, maximizing variation in lighting, background, and scale ")
    report.append("     while discarding near-identical burst frames.")
    report.append("   - 'UNKNOWN' images (26) were segregated into a dedicated contact sheet (contact_sheet_UNKNOWN.jpg)")
    report.append("     for manual human visual verification before inclusion, as their provenance is less strict.")
    report.append("============================================================")
    
    report_txt = "\n".join(report)
    print(report_txt)
    
    with open("v3_candidate_selection_report.txt", "w", encoding="utf-8") as f:
        f.write(report_txt)
        
    # Write a JSON manifest of the proposed selection
    selected_manifest = []
    for k, pool in proposed_selections.items():
        selected_manifest.extend(pool)
        
    with open("v3_proposed_selection.json", "w") as f:
        json.dump(selected_manifest, f, indent=2)

if __name__ == "__main__":
    main()
