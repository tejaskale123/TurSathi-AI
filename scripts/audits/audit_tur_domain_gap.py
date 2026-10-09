import sys
from pathlib import Path
import numpy as np
from PIL import Image

def analyze_directory(directory_path, name):
    print(f"\nAnalyzing {name} ({directory_path})...")
    
    path = Path(directory_path)
    if not path.exists():
        print(f"ERROR: Path {path} does not exist.")
        return None
        
    image_files = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
        image_files.extend(path.rglob(ext))
        
    if not image_files:
        print("No images found.")
        return None
        
    widths = []
    heights = []
    aspect_ratios = []
    landscape = 0
    portrait = 0
    square = 0
    
    brightnesses = []
    saturations = []
    
    for f in image_files:
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
                    
                # Simple color metrics (convert to HSV for saturation)
                img_hsv = img.convert("HSV")
                h_ch, s_ch, v_ch = img_hsv.split()
                
                # Mean brightness (V channel)
                v_arr = np.array(v_ch)
                brightnesses.append(np.mean(v_arr))
                
                # Mean saturation (S channel)
                s_arr = np.array(s_ch)
                saturations.append(np.mean(s_arr))
                
        except Exception as e:
            print(f"Error reading {f}: {e}")
            
    stats = {
        "count": len(image_files),
        "mean_w": np.mean(widths),
        "mean_h": np.mean(heights),
        "median_w": np.median(widths),
        "median_h": np.median(heights),
        "min_w": np.min(widths),
        "max_w": np.max(widths),
        "min_h": np.min(heights),
        "max_h": np.max(heights),
        "mean_ar": np.mean(aspect_ratios),
        "median_ar": np.median(aspect_ratios),
        "landscape": landscape,
        "portrait": portrait,
        "square": square,
        "mean_brightness": np.mean(brightnesses),
        "mean_saturation": np.mean(saturations)
    }
    
    return stats

def main():
    print("=" * 60)
    print("PHASE 4A: REAL-WORLD DOMAIN GAP AUDIT")
    print("=" * 60)
    
    train_dir = "datasets/tur_image_validator_v2/train/Tur"
    real_world_dir = "datasets/tur_image_validator/real_world_test/Tur"
    
    train_stats = analyze_directory(train_dir, "TRAINING TUR DATA")
    real_stats = analyze_directory(real_world_dir, "REAL-WORLD TUR HOLDOUT")
    
    if not train_stats or not real_stats:
        print("Could not complete audit.")
        return
        
    print("\n" + "=" * 60)
    print("COMPARISON REPORT")
    print("=" * 60)
    
    print(f"{'Metric':<25} | {'Training (V2)':<15} | {'Real-World':<15}")
    print("-" * 60)
    print(f"{'Image Count':<25} | {train_stats['count']:<15} | {real_stats['count']:<15}")
    print(f"{'Mean Width':<25} | {train_stats['mean_w']:<15.2f} | {real_stats['mean_w']:<15.2f}")
    print(f"{'Mean Height':<25} | {train_stats['mean_h']:<15.2f} | {real_stats['mean_h']:<15.2f}")
    print(f"{'Median Width':<25} | {train_stats['median_w']:<15.2f} | {real_stats['median_w']:<15.2f}")
    print(f"{'Median Height':<25} | {train_stats['median_h']:<15.2f} | {real_stats['median_h']:<15.2f}")
    print(f"{'Min Width':<25} | {train_stats['min_w']:<15} | {real_stats['min_w']:<15}")
    print(f"{'Max Width':<25} | {train_stats['max_w']:<15} | {real_stats['max_w']:<15}")
    print(f"{'Min Height':<25} | {train_stats['min_h']:<15} | {real_stats['min_h']:<15}")
    print(f"{'Max Height':<25} | {train_stats['max_h']:<15} | {real_stats['max_h']:<15}")
    print(f"{'Mean Aspect Ratio':<25} | {train_stats['mean_ar']:<15.4f} | {real_stats['mean_ar']:<15.4f}")
    print(f"{'Median Aspect Ratio':<25} | {train_stats['median_ar']:<15.4f} | {real_stats['median_ar']:<15.4f}")
    print(f"{'Landscape Images':<25} | {train_stats['landscape']:<15} | {real_stats['landscape']:<15}")
    print(f"{'Portrait Images':<25} | {train_stats['portrait']:<15} | {real_stats['portrait']:<15}")
    print(f"{'Square Images':<25} | {train_stats['square']:<15} | {real_stats['square']:<15}")
    print(f"{'Mean Brightness (0-255)':<25} | {train_stats['mean_brightness']:<15.2f} | {real_stats['mean_brightness']:<15.2f}")
    print(f"{'Mean Saturation (0-255)':<25} | {train_stats['mean_saturation']:<15.2f} | {real_stats['mean_saturation']:<15.2f}")

if __name__ == "__main__":
    main()
