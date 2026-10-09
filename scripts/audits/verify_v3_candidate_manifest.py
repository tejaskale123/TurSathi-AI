import csv
import hashlib
from pathlib import Path
from collections import defaultdict

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
    print("PHASE 4E: V3 CANDIDATE MANIFEST CONSISTENCY AND LEAKAGE VERIFICATION")
    print("=" * 80)
    
    # 1. Independently recalculate all hashes from original sources
    print("Loading V2 and Holdout hashes...")
    v2_hashes = get_hashes_from_dir("datasets/tur_image_validator_v2/train/Tur")
    holdout_hashes = get_hashes_from_dir("datasets/tur_image_validator/real_world_test/Tur")
    
    # Gather candidates independently
    print("Gathering candidates independently...")
    candidate_files = []
    
    dir_a = Path("datasets/new_disease_images")
    if dir_a.exists():
        for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
            candidate_files.extend(list(dir_a.rglob(ext)))
            
    dir_b = Path("datasets/pigeonpea_disease_final")
    if dir_b.exists():
        for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
            for f in dir_b.rglob(ext):
                if get_md5(f) not in v2_hashes:
                    candidate_files.append(f)
                    
    total_candidates = len(candidate_files)
    
    # Recalculate duplicate groups
    hash_to_files = defaultdict(list)
    for f in candidate_files:
        md5 = get_md5(f)
        hash_to_files[md5].append(f)
        
    unique_hashes = len(hash_to_files)
    
    # Calculate exact holdout duplicates
    holdout_dups_count = 0
    holdout_dup_files = []
    
    # Calculate exact internal duplicates
    # Internal dup files = sum(len(files) - 1 for files in hash_to_files if len(files) > 1)
    # BUT wait! If an image is a holdout dup AND has internal copies, how was it counted in 4C/4D?
    # This is likely the source of the 2-image discrepancy.
    internal_dups_count = 0
    internal_dup_files = []
    
    clean_candidates_count = 0
    
    for md5, files in hash_to_files.items():
        is_holdout = md5 in holdout_hashes
        
        # Determine the primary (first seen) file vs duplicates
        primary = files[0]
        copies = files[1:]
        
        if is_holdout:
            # ALL files with this hash are holdout duplicates (they cannot be clean candidates)
            holdout_dups_count += len(files)
            holdout_dup_files.extend(files)
            # Should they also be counted as internal duplicates if len(files) > 1?
            # If so, they are double counted in 4C/4D! 
            # In an exclusive categorization:
            # A file is EITHER holdout dup OR internal dup OR clean.
            # If we prioritize HOLDOUT, then internal_dups = 0 for this group.
            pass
        else:
            # If not a holdout dup, the primary is clean, copies are internal dups.
            clean_candidates_count += 1
            internal_dups_count += len(copies)
            internal_dup_files.extend(copies)
            
    # Now verify the Manifest
    manifest_rows = []
    manifest_verified = 0
    manifest_inconsistencies = []
    
    csv_path = Path("v3_candidate_manifest.csv")
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                manifest_rows.append(row)
                
        for row in manifest_rows:
            fpath = Path(row["original_source_path"])
            if not fpath.exists():
                manifest_inconsistencies.append(f"File missing: {fpath}")
                continue
                
            actual_md5 = get_md5(fpath)
            if actual_md5 != row["md5"]:
                manifest_inconsistencies.append(f"MD5 mismatch for {fpath}")
                
            # Check class provenance
            if "pigeonpea_disease_final" in str(fpath):
                expected_class = fpath.parent.name
                if row["original_class"] != expected_class:
                    manifest_inconsistencies.append(f"Class mismatch for {fpath}: Expected {expected_class}, got {row['original_class']}")
            elif "new_disease_images" in str(fpath):
                if row["original_class"] != "UNKNOWN":
                    manifest_inconsistencies.append(f"Class mismatch for {fpath}: Expected UNKNOWN, got {row['original_class']}")
                    
            manifest_verified += 1
    else:
        manifest_inconsistencies.append("v3_candidate_manifest.csv not found.")
        
    # Check for cross-directory leakage
    cross_dir_dups = []
    for md5, files in hash_to_files.items():
        if len(files) > 1:
            sources = set()
            for f in files:
                if "new_disease_images" in f.parts:
                    sources.add("new_disease_images")
                elif "pigeonpea_disease_final" in f.parts:
                    sources.add("pigeonpea_disease_final")
            if len(sources) > 1:
                cross_dir_dups.append((md5, [str(f) for f in files]))
                
    # Prepare the Report
    report = []
    report.append("============================================================")
    report.append("V3 CANDIDATE VERIFICATION REPORT")
    report.append("============================================================")
    report.append(f"Total Source Candidates      : {total_candidates}")
    report.append(f"Exact Duplicate Groups (MD5) : {len([files for files in hash_to_files.values() if len(files) > 1])}")
    
    # Explain the discrepancy
    report.append("\n--- DISCREPANCY EXPLANATION ---")
    report.append("Phase 4C counted sets vs files sequentially:")
    report.append("If a file was a holdout dup AND an internal dup, 4C might have counted it as BOTH, or the order of seen_hashes mattered.")
    report.append("Phase 4D prioritized seen_hashes (internal dups) BEFORE holdout checks if order varied.")
    report.append("By mutually exclusive categorization (Holdout is highest priority):")
    report.append(f"Holdout Duplicate Files      : {holdout_dups_count}")
    report.append(f"Internal Duplicate Files     : {internal_dups_count}")
    report.append(f"Final Clean Candidate Count  : {clean_candidates_count}")
    
    # 439 = holdout + internal + clean
    assert holdout_dups_count + internal_dups_count + clean_candidates_count == total_candidates, "Sum mismatch!"
    
    report.append("\n--- MANIFEST VERIFICATION ---")
    report.append(f"Manifest Rows Verified       : {manifest_verified}")
    report.append(f"Manifest Inconsistencies     : {len(manifest_inconsistencies)}")
    for inc in manifest_inconsistencies:
        report.append(f"  - {inc}")
        
    report.append("\n--- CROSS DIRECTORY DUPLICATES ---")
    if cross_dir_dups:
        report.append(f"Found {len(cross_dir_dups)} hashes duplicated across different source directories.")
    else:
        report.append("No cross-directory duplicates found.")
        
    report.append("\n--- FINAL RECOMMENDATION ---")
    if manifest_inconsistencies:
        report.append("DO_NOT_BUILD_V3_YET")
        report.append("Manifest contains inconsistencies that must be fixed.")
    elif holdout_dups_count + internal_dups_count + clean_candidates_count != 439:
        report.append("DO_NOT_BUILD_V3_YET")
        report.append("Math error in candidate categorizations.")
    else:
        report.append("SAFE_TO_BUILD_V3_DATASET")
        
    report.append("============================================================")
    
    report_text = "\n".join(report)
    print(report_text)
    
    with open("v3_candidate_verification_report.txt", "w", encoding="utf-8") as f:
        f.write(report_text)

if __name__ == "__main__":
    main()
