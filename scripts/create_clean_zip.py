import os
import zipfile
from pathlib import Path

def create_project_zip(output_zip_path="tursathi_clean_project.zip"):
    root_dir = Path(".").resolve()
    print(f"Creating clean project zip: {output_zip_path}")
    
    # Directories to completely skip
    exclude_dirs = {
        ".git", ".pytest_cache", ".venv", "venv", "env", "node_modules",
        ".expo", ".next", "dist", "build", "datasets", "PPLD_extracted",
        "PPLD_processed", "tur_dataset_source",
        "A novel pigeonpea leaf dataset for detection and classification of pigeonpea leaf diseases",
        "archive", "scratch", "backups", "tursathi_pgdata", "__pycache__", ".history",
        ".idea", ".vscode"
    }
    
    # Extensions to completely skip
    exclude_exts = {
        ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff", ".tif",
        ".zip", ".tar", ".gz", ".7z", ".rar", ".dump", ".sqlite", ".db",
        ".pyc", ".pyo", ".pyd", ".log", ".bak", ".bak_f22", ".backup"
    }
    
    # Specific files to exclude
    exclude_files = {
        "Tur_Disease_Dataset.zip", "tursathi_db_backup_pre_guidance_cache.dump",
        output_zip_path, "project_extraction.txt"
    }

    included_count = 0
    total_uncompressed_bytes = 0
    
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(root_dir):
            rel_root = Path(root).relative_to(root_dir)
            
            # Prune excluded directories in-place
            dirs[:] = [
                d for d in dirs 
                if d not in exclude_dirs and not d.startswith(".") and not d.endswith("_backup")
            ]
            
            for file in files:
                if file in exclude_files:
                    continue
                
                ext = Path(file).suffix.lower()
                
                # Check extension
                if ext in exclude_exts:
                    # Allow mobile app branding icons only
                    rel_file_path = (rel_root / file).as_posix()
                    if rel_file_path.startswith("mobile/assets/images/") and ext in {".png"}:
                        pass
                    else:
                        continue
                elif ext == ".png":
                    # Check if it is an app asset or dataset/report image
                    rel_file_path = (rel_root / file).as_posix()
                    if not (rel_file_path.startswith("mobile/assets/") or rel_file_path.startswith("frontend/public/") or rel_file_path.startswith("frontend/src/assets/")):
                        continue

                file_path = Path(root) / file
                arcname = (rel_root / file).as_posix()
                
                zf.write(file_path, arcname)
                included_count += 1
                total_uncompressed_bytes += file_path.stat().st_size

    zip_size_mb = Path(output_zip_path).stat().st_size / (1024 * 1024)
    print(f"Done! Included {included_count} files.")
    print(f"Uncompressed size: {total_uncompressed_bytes / (1024 * 1024):.2f} MB")
    print(f"Final zip file: {output_zip_path} ({zip_size_mb:.2f} MB)")

if __name__ == "__main__":
    create_project_zip()
